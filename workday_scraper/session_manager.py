"""
Session manager for the Workday Scraper.

This module provides a session manager that efficiently reuses and manages
browser sessions, improving performance and resource usage.
"""

import time
import threading
import queue
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

from .logging_utils import get_logger

logger = get_logger()


class WebdriverSessionManager:
    """Manages a pool of webdriver sessions for efficient reuse."""
    
    def __init__(self, max_sessions=3, session_timeout=900, headless=True):
        """Initialize the WebdriverSessionManager.
        
        Args:
            max_sessions (int): Maximum number of concurrent sessions.
            session_timeout (int): Session timeout in seconds.
            headless (bool): Whether to run browsers in headless mode.
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.headless = headless
        
        # Use a queue for available sessions
        self.available_sessions = queue.Queue()
        
        # Track all sessions (both in-use and available)
        self.all_sessions = []
        
        # Lock for thread safety
        self.session_lock = threading.Lock()
        
        # Webdriver manager availability
        self.webdriver_manager_available = False
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            self.webdriver_manager_available = True
        except ImportError:
            pass
        
        logger.info(f"Initialized session manager", extra={
            "max_sessions": max_sessions,
            "session_timeout": session_timeout,
            "headless": headless,
            "webdriver_manager_available": self.webdriver_manager_available
        })
    
    def _create_driver(self):
        """Create a new webdriver instance.
        
        Returns:
            webdriver.Chrome: A new Chrome webdriver instance.
        """
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # Add additional options that might help with stability
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Try to use WebDriverManager if available
        try:
            if self.webdriver_manager_available:
                from webdriver_manager.chrome import ChromeDriverManager
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            else:
                driver = webdriver.Chrome(options=options)
        except Exception as e:
            logger.error(f"Error creating Chrome driver: {str(e)}")
            logger.info("Falling back to default ChromeDriver")
            driver = webdriver.Chrome(options=options)
        
        return driver
    
    def get_session(self, wait_timeout=120):
        """Get an available session or create a new one if needed.
        
        Args:
            wait_timeout (int): Maximum time to wait for an available session in seconds.
        
        Returns:
            tuple: (driver, session_id) - The webdriver instance and a session identifier.
        
        Raises:
            TimeoutError: If no session becomes available within the timeout.
        """
        # First try to get a session from the queue
        try:
            session_id = self.available_sessions.get(block=False)
            with self.session_lock:
                for session in self.all_sessions:
                    if session['id'] == session_id:
                        if self._is_session_valid(session):
                            logger.debug(f"Reusing existing session {session_id}")
                            session['last_used'] = time.time()
                            session['in_use'] = True
                            return session['driver'], session_id
                        else:
                            # Session is invalid, remove it and create a new one
                            logger.debug(f"Session {session_id} is invalid, creating a new one")
                            self._cleanup_session(session)
                            self.all_sessions.remove(session)
                            break
            
            # If we get here, the session was invalid or not found
            self.available_sessions.task_done()
        except queue.Empty:
            # No available sessions in the queue
            pass
        
        # Create a new session if under the limit, otherwise wait for one to become available
        with self.session_lock:
            active_count = sum(1 for s in self.all_sessions if s['in_use'] or time.time() - s['last_used'] < self.session_timeout)
            
            if active_count < self.max_sessions:
                # Create a new session
                try:
                    driver = self._create_driver()
                    session_id = id(driver)
                    session = {
                        'id': session_id,
                        'driver': driver,
                        'created': time.time(),
                        'last_used': time.time(),
                        'in_use': True
                    }
                    self.all_sessions.append(session)
                    logger.info(f"Created new session {session_id}")
                    return driver, session_id
                except Exception as e:
                    logger.error(f"Failed to create new session: {str(e)}")
                    raise
        
        # If we get here, we need to wait for a session to become available
        logger.warning(f"All sessions in use, waiting for one to become available")
        start_time = time.time()
        
        while time.time() - start_time < wait_timeout:
            try:
                session_id = self.available_sessions.get(block=True, timeout=1)
                with self.session_lock:
                    for session in self.all_sessions:
                        if session['id'] == session_id:
                            if self._is_session_valid(session):
                                logger.debug(f"Reusing existing session {session_id} after waiting")
                                session['last_used'] = time.time()
                                session['in_use'] = True
                                return session['driver'], session_id
                            else:
                                # Session is invalid, remove it and continue waiting
                                logger.debug(f"Session {session_id} is invalid, continuing to wait")
                                self._cleanup_session(session)
                                self.all_sessions.remove(session)
                                break
                
                # If we get here, the session was invalid or not found
                self.available_sessions.task_done()
            except queue.Empty:
                # No available sessions yet, continue waiting
                self._cleanup_sessions()  # Try to clean up expired sessions
        
        # If we get here, we timed out waiting for a session
        raise TimeoutError(f"Timed out waiting for an available session after {wait_timeout} seconds")
    
    def release_session(self, session_id):
        """Mark a session as available for reuse.
        
        Args:
            session_id: The session identifier to release.
        
        Returns:
            bool: True if the session was released, False if it wasn't found.
        """
        with self.session_lock:
            for session in self.all_sessions:
                if session['id'] == session_id:
                    session['in_use'] = False
                    session['last_used'] = time.time()
                    self.available_sessions.put(session_id)
                    logger.debug(f"Released session {session_id}")
                    return True
        
        logger.warning(f"Attempted to release unknown session {session_id}")
        return False
    
    def _is_session_valid(self, session):
        """Check if a session is still valid with simplified validation.
        
        Args:
            session (dict): Session information.
        
        Returns:
            bool: True if the session is valid, False otherwise.
        """
        # Check if session is expired
        if time.time() - session['last_used'] > self.session_timeout:
            logger.debug(f"Session {session['id']} expired")
            return False
        
        # Check if session is still responsive - simplified to just one essential check
        try:
            # Simple operation to check if session is alive
            session['driver'].current_url
            
            # Just one JavaScript check for responsiveness
            try:
                ready_state = session['driver'].execute_script("return document.readyState")
                return ready_state in ["complete", "interactive"]
            except Exception as js_error:
                logger.debug(f"Session {session['id']} JavaScript execution failed: {str(js_error)}")
                return False
                
        except Exception as e:
            logger.debug(f"Session {session['id']} is not responsive: {str(e)}")
            return False
    
    def _cleanup_session(self, session):
        """Clean up a session by quitting the driver.
        
        Args:
            session (dict): Session information.
        """
        try:
            session['driver'].quit()
            logger.debug(f"Cleaned up session {session['id']}")
        except Exception as e:
            logger.debug(f"Error cleaning up session {session['id']}: {str(e)}")
    
    def _cleanup_sessions(self):
        """Remove expired or crashed sessions."""
        with self.session_lock:
            now = time.time()
            active_sessions = []
            
            for session in self.all_sessions:
                # Skip sessions that are in use
                if session['in_use']:
                    active_sessions.append(session)
                    continue
                
                # Check if session is expired
                if now - session['last_used'] > self.session_timeout:
                    logger.debug(f"Removing expired session {session['id']}")
                    self._cleanup_session(session)
                    continue
                
                # Check if session is still responsive
                if not self._is_session_valid(session):
                    logger.debug(f"Removing invalid session {session['id']}")
                    self._cleanup_session(session)
                    continue
                
                # Session is still valid
                active_sessions.append(session)
            
            # Update the list of sessions
            removed_count = len(self.all_sessions) - len(active_sessions)
            if removed_count > 0:
                logger.info(f"Removed {removed_count} expired or invalid sessions")
            
            self.all_sessions = active_sessions
    
    def close_all(self):
        """Close all sessions."""
        with self.session_lock:
            for session in self.all_sessions:
                self._cleanup_session(session)
            
            self.all_sessions = []
            
            # Clear the queue
            while not self.available_sessions.empty():
                try:
                    self.available_sessions.get(block=False)
                    self.available_sessions.task_done()
                except queue.Empty:
                    break
            
            logger.info("Closed all sessions")
    
    def get_stats(self):
        """Get statistics about the session manager.
        
        Returns:
            dict: Statistics about the session manager.
        """
        with self.session_lock:
            in_use_count = sum(1 for s in self.all_sessions if s['in_use'])
            available_count = len(self.all_sessions) - in_use_count
            
            return {
                "total_sessions": len(self.all_sessions),
                "in_use_sessions": in_use_count,
                "available_sessions": available_count,
                "max_sessions": self.max_sessions
            }


# Create a global instance for convenience
session_manager = WebdriverSessionManager()


class SessionContext:
    """Context manager for automatically releasing sessions."""
    
    def __init__(self, manager=None, wait_timeout=120):
        """Initialize the SessionContext.
        
        Args:
            manager (WebdriverSessionManager, optional): Session manager to use.
                If None, uses the global session_manager.
            wait_timeout (int): Maximum time to wait for an available session in seconds.
        """
        self.manager = manager or session_manager
        self.wait_timeout = wait_timeout
        self.driver = None
        self.session_id = None
    
    def __enter__(self):
        """Get a session when entering the context.
        
        Returns:
            webdriver.Chrome: The webdriver instance.
        """
        self.driver, self.session_id = self.manager.get_session(wait_timeout=self.wait_timeout)
        return self.driver
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the session when exiting the context."""
        if self.session_id is not None:
            self.manager.release_session(self.session_id)