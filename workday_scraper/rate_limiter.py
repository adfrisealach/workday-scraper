"""
Rate limiter for the Workday Scraper.

This module provides an adaptive rate limiter that adjusts the delay between
requests based on success and failure patterns, helping to prevent the scraper
from overwhelming the target servers or triggering rate limiting.
"""

import time
import threading
from datetime import datetime, timedelta

from .logging_utils import get_logger

logger = get_logger()


class AdaptiveRateLimiter:
    """Rate limiter with adaptive delay based on response patterns."""
    
    def __init__(self, initial_delay=1.0, min_delay=0.5, max_delay=30.0, 
                backoff_factor=1.5, success_threshold=10, domain=None):
        """Initialize the AdaptiveRateLimiter.
        
        Args:
            initial_delay (float): Initial delay between requests in seconds.
            min_delay (float): Minimum delay between requests in seconds.
            max_delay (float): Maximum delay between requests in seconds.
            backoff_factor (float): Factor by which to increase delay on failure.
            success_threshold (int): Number of consecutive successes before reducing delay.
            domain (str, optional): Domain name for domain-specific rate limiting.
        """
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.success_threshold = success_threshold
        self.domain = domain
        
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0
        self.total_requests = 0
        self.total_wait_time = 0
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        logger.info(f"Initialized rate limiter", extra={
            "domain": domain,
            "initial_delay": initial_delay,
            "min_delay": min_delay,
            "max_delay": max_delay
        })
    
    def wait(self):
        """Wait appropriate time before next request.
        
        Returns:
            float: The actual time waited in seconds.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            
            wait_time = 0
            if elapsed < self.current_delay:
                wait_time = self.current_delay - elapsed
                time.sleep(wait_time)
            
            self.last_request_time = time.time()
            self.total_requests += 1
            self.total_wait_time += wait_time
            
            if self.total_requests % 10 == 0:
                logger.debug(f"Rate limiter stats", extra={
                    "domain": self.domain,
                    "current_delay": self.current_delay,
                    "total_requests": self.total_requests,
                    "avg_wait_time": self.total_wait_time / self.total_requests if self.total_requests > 0 else 0
                })
            
            return wait_time
    
    def success(self):
        """Record successful request and potentially reduce delay.
        
        Returns:
            bool: True if the delay was reduced, False otherwise.
        """
        with self.lock:
            self.success_count += 1
            self.failure_count = 0
            
            # After X consecutive successes, cautiously reduce delay
            if self.success_count >= self.success_threshold:
                old_delay = self.current_delay
                self.current_delay = max(self.current_delay / 1.2, self.min_delay)
                self.success_count = 0
                
                if old_delay != self.current_delay:
                    logger.debug(f"Rate limiter: decreased delay", extra={
                        "domain": self.domain,
                        "old_delay": old_delay,
                        "new_delay": self.current_delay
                    })
                    return True
            
            return False
    
    def failure(self, error_type=None):
        """Record failed request and increase delay.
        
        Args:
            error_type (str, optional): Type of error that occurred.
        
        Returns:
            float: The new delay value.
        """
        with self.lock:
            self.failure_count += 1
            self.success_count = 0
            
            old_delay = self.current_delay
            
            # Increase delay, more aggressively for certain error types
            if error_type == "rate_limit":
                # Much more aggressive backoff for rate limit errors
                multiplier = 3.0
            elif error_type == "timeout":
                # More aggressive backoff for timeouts
                multiplier = 2.0
            else:
                multiplier = self.backoff_factor
            
            # Apply exponential backoff based on consecutive failures
            failure_multiplier = multiplier ** min(self.failure_count, 3)
            self.current_delay = min(self.current_delay * failure_multiplier, self.max_delay)
            
            logger.info(f"Rate limiter: increased delay", extra={
                "domain": self.domain,
                "old_delay": old_delay,
                "new_delay": self.current_delay,
                "error_type": error_type,
                "failure_count": self.failure_count
            })
            
            return self.current_delay
    
    def get_stats(self):
        """Get statistics about the rate limiter's performance.
        
        Returns:
            dict: Statistics about the rate limiter.
        """
        with self.lock:
            return {
                "domain": self.domain,
                "current_delay": self.current_delay,
                "total_requests": self.total_requests,
                "total_wait_time": self.total_wait_time,
                "avg_wait_time": self.total_wait_time / self.total_requests if self.total_requests > 0 else 0,
                "success_count": self.success_count,
                "failure_count": self.failure_count
            }


class DomainRateLimiter:
    """Rate limiter that manages separate limiters for different domains."""
    
    def __init__(self, default_initial_delay=1.0, default_min_delay=0.5, 
                default_max_delay=30.0, default_backoff_factor=1.5):
        """Initialize the DomainRateLimiter.
        
        Args:
            default_initial_delay (float): Default initial delay for new domains.
            default_min_delay (float): Default minimum delay for new domains.
            default_max_delay (float): Default maximum delay for new domains.
            default_backoff_factor (float): Default backoff factor for new domains.
        """
        self.default_initial_delay = default_initial_delay
        self.default_min_delay = default_min_delay
        self.default_max_delay = default_max_delay
        self.default_backoff_factor = default_backoff_factor
        
        self.limiters = {}
        self.lock = threading.Lock()
    
    def get_limiter(self, domain):
        """Get or create a rate limiter for the specified domain.
        
        Args:
            domain (str): Domain name.
        
        Returns:
            AdaptiveRateLimiter: Rate limiter for the domain.
        """
        with self.lock:
            if domain not in self.limiters:
                self.limiters[domain] = AdaptiveRateLimiter(
                    initial_delay=self.default_initial_delay,
                    min_delay=self.default_min_delay,
                    max_delay=self.default_max_delay,
                    backoff_factor=self.default_backoff_factor,
                    domain=domain
                )
            
            return self.limiters[domain]
    
    def wait(self, domain):
        """Wait appropriate time before next request to the specified domain.
        
        Args:
            domain (str): Domain name.
        
        Returns:
            float: The actual time waited in seconds.
        """
        limiter = self.get_limiter(domain)
        return limiter.wait()
    
    def success(self, domain):
        """Record successful request to the specified domain.
        
        Args:
            domain (str): Domain name.
        
        Returns:
            bool: True if the delay was reduced, False otherwise.
        """
        limiter = self.get_limiter(domain)
        return limiter.success()
    
    def failure(self, domain, error_type=None):
        """Record failed request to the specified domain.
        
        Args:
            domain (str): Domain name.
            error_type (str, optional): Type of error that occurred.
        
        Returns:
            float: The new delay value.
        """
        limiter = self.get_limiter(domain)
        return limiter.failure(error_type)
    
    def get_stats(self):
        """Get statistics about all rate limiters.
        
        Returns:
            dict: Statistics about all rate limiters.
        """
        with self.lock:
            return {domain: limiter.get_stats() for domain, limiter in self.limiters.items()}


# Create a global instance for convenience
domain_rate_limiter = DomainRateLimiter()


def get_domain_from_url(url):
    """Extract the domain from a URL.
    
    Args:
        url (str): URL to extract domain from.
    
    Returns:
        str: Domain name.
    """
    from urllib.parse import urlparse
    
    parsed_url = urlparse(url)
    return parsed_url.netloc


def rate_limited_request(url, request_func, *args, **kwargs):
    """Execute a request with rate limiting.
    
    Args:
        url (str): URL to request.
        request_func (callable): Function to execute the request.
        *args: Positional arguments to pass to request_func.
        **kwargs: Keyword arguments to pass to request_func.
    
    Returns:
        Any: Result of the request function.
    """
    domain = get_domain_from_url(url)
    
    # Wait before making the request
    domain_rate_limiter.wait(domain)
    
    try:
        # Execute the request
        result = request_func(*args, **kwargs)
        
        # Record success
        domain_rate_limiter.success(domain)
        
        return result
    except Exception as e:
        # Determine error type
        error_type = None
        if "rate limit" in str(e).lower() or "429" in str(e):
            error_type = "rate_limit"
        elif "timeout" in str(e).lower():
            error_type = "timeout"
        
        # Record failure
        domain_rate_limiter.failure(domain, error_type)
        
        # Re-raise the exception
        raise