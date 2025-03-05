"""
Error handling framework for the Workday Scraper.

This module provides a comprehensive error handling framework with custom
exception classes and context-aware recovery strategies for different types
of errors that may occur during the scraping process.
"""

import time
import traceback
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
)

# Import the logger
from .logging_utils import get_logger

logger = get_logger()


class ScraperError(Exception):
    """Base class for scraper exceptions."""
    pass


class ElementNotFoundError(ScraperError):
    """Raised when an element cannot be found."""
    pass


class PageLoadError(ScraperError):
    """Raised when a page fails to load properly."""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limiting is detected."""
    pass


class SessionError(ScraperError):
    """Raised when there's an issue with the browser session."""
    pass


class DataExtractionError(ScraperError):
    """Raised when data cannot be extracted from an element."""
    pass


class NetworkError(ScraperError):
    """Raised when there's a network-related issue."""
    pass


def handle_scraping_error(error, context, retry_function=None, max_retries=3, 
                         retry_delay=2, backoff_factor=2, **retry_kwargs):
    """Centralized error handling with context-aware recovery strategies.
    
    Args:
        error (Exception): The exception that was raised.
        context (str): Description of what was being attempted when the error occurred.
        retry_function (callable, optional): Function to retry if applicable.
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
        retry_delay (int, optional): Initial delay between retries in seconds. Defaults to 2.
        backoff_factor (int, optional): Factor by which to increase delay on each retry. Defaults to 2.
        **retry_kwargs: Additional keyword arguments to pass to the retry function.
    
    Returns:
        Any: Result of the retry function if successful, None otherwise.
    
    Raises:
        ScraperError: If the error is critical and cannot be handled.
    """
    # Calculate the current retry attempt (max_retries - remaining retries)
    current_attempt = 3 - max_retries + 1
    
    # Handle different types of exceptions
    if isinstance(error, NoSuchElementException):
        logger.warning(f"Element not found in {context}", extra={"error": str(error), "attempt": current_attempt})
        if retry_function and max_retries > 0:
            logger.info(f"Retrying {context}, {max_retries} attempts left")
            time.sleep(retry_delay)  # Backoff before retry
            return retry_function(max_retries=max_retries-1, 
                                 retry_delay=retry_delay*backoff_factor, 
                                 backoff_factor=backoff_factor, 
                                 **retry_kwargs)
        else:
            raise ElementNotFoundError(f"Element not found in {context}: {error}")
    
    elif isinstance(error, TimeoutException):
        logger.error(f"Timeout in {context}", extra={"error": str(error), "attempt": current_attempt})
        if retry_function and max_retries > 0:
            logger.info(f"Retrying {context} after timeout, {max_retries} attempts left")
            time.sleep(retry_delay * 2)  # Longer backoff for timeouts
            return retry_function(max_retries=max_retries-1, 
                                 retry_delay=retry_delay*backoff_factor, 
                                 backoff_factor=backoff_factor, 
                                 **retry_kwargs)
        else:
            raise PageLoadError(f"Timeout in {context}: {error}")
    
    elif isinstance(error, StaleElementReferenceException):
        logger.warning(f"Stale element in {context}", extra={"error": str(error), "attempt": current_attempt})
        if retry_function and max_retries > 0:
            logger.info(f"Retrying {context} after stale element, {max_retries} attempts left")
            time.sleep(retry_delay)
            return retry_function(max_retries=max_retries-1, 
                                 retry_delay=retry_delay*backoff_factor, 
                                 backoff_factor=backoff_factor, 
                                 **retry_kwargs)
        else:
            raise ElementNotFoundError(f"Stale element in {context}: {error}")
    
    elif isinstance(error, WebDriverException):
        if "rate limit" in str(error).lower() or "too many requests" in str(error).lower():
            logger.critical(f"Rate limit detected in {context}", extra={"error": str(error)})
            if retry_function and max_retries > 0:
                # Much longer backoff for rate limits
                backoff_time = retry_delay * 5
                logger.info(f"Backing off for {backoff_time}s before retrying {context}")
                time.sleep(backoff_time)
                return retry_function(max_retries=max_retries-1, 
                                     retry_delay=retry_delay*backoff_factor, 
                                     backoff_factor=backoff_factor, 
                                     **retry_kwargs)
            else:
                raise RateLimitError(f"Rate limit detected in {context}: {error}")
        else:
            logger.error(f"WebDriver error in {context}", extra={"error": str(error), "attempt": current_attempt})
            if retry_function and max_retries > 0:
                logger.info(f"Retrying {context} after WebDriver error, {max_retries} attempts left")
                time.sleep(retry_delay * 2)
                return retry_function(max_retries=max_retries-1, 
                                     retry_delay=retry_delay*backoff_factor, 
                                     backoff_factor=backoff_factor, 
                                     **retry_kwargs)
            else:
                raise SessionError(f"WebDriver error in {context}: {error}")
    
    else:
        # Handle other types of exceptions
        logger.error(f"Unexpected error in {context}: {error}", extra={"error_type": type(error).__name__})
        logger.debug(traceback.format_exc())
        
        if retry_function and max_retries > 0:
            logger.info(f"Retrying {context} after unexpected error, {max_retries} attempts left")
            time.sleep(retry_delay)
            return retry_function(max_retries=max_retries-1, 
                                 retry_delay=retry_delay*backoff_factor, 
                                 backoff_factor=backoff_factor, 
                                 **retry_kwargs)
        else:
            # Re-raise the original exception
            raise
    
    return None  # Default fallback return value


def safe_operation(operation_func, context, max_retries=3, retry_delay=2, 
                  backoff_factor=2, default_value=None, **kwargs):
    """Execute an operation with automatic error handling and retries.
    
    Args:
        operation_func (callable): The function to execute.
        context (str): Description of what is being attempted.
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
        retry_delay (int, optional): Initial delay between retries in seconds. Defaults to 2.
        backoff_factor (int, optional): Factor by which to increase delay on each retry. Defaults to 2.
        default_value (Any, optional): Value to return if all retries fail. Defaults to None.
        **kwargs: Additional keyword arguments to pass to the operation function.
    
    Returns:
        Any: Result of the operation function if successful, default_value otherwise.
    """
    try:
        return operation_func(**kwargs)
    except Exception as e:
        try:
            # Define a retry function that calls this function again with one fewer retry
            def retry_func(max_retries, retry_delay, backoff_factor, **retry_kwargs):
                merged_kwargs = {**kwargs, **retry_kwargs}
                return safe_operation(
                    operation_func, 
                    context, 
                    max_retries=max_retries, 
                    retry_delay=retry_delay, 
                    backoff_factor=backoff_factor, 
                    default_value=default_value, 
                    **merged_kwargs
                )
            
            # Handle the error with our error handling framework
            return handle_scraping_error(
                e, 
                context, 
                retry_function=retry_func, 
                max_retries=max_retries, 
                retry_delay=retry_delay, 
                backoff_factor=backoff_factor
            )
        except Exception as handled_e:
            logger.error(f"Operation failed after all retries: {context}", 
                        extra={"error": str(handled_e)})
            return default_value