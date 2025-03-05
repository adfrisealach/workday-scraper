"""
Structured logging system for the Workday Scraper.

This module provides a comprehensive logging system that outputs structured
JSON logs with contextual information, making it easier to debug and monitor
the scraping process.
"""

import logging
import json
import os
from datetime import datetime
import traceback


class StructuredLogFormatter(logging.Formatter):
    """Formatter that outputs JSON formatted logs."""
    
    def format(self, record):
        """Format the log record as a JSON object."""
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in ["args", "exc_info", "exc_text", "levelname", 
                                             "levelno", "lineno", "module", "msecs", 
                                             "msg", "name", "pathname", "process", 
                                             "processName", "relativeCreated", "thread", 
                                             "threadName", "funcName", "created", "asctime"]:
                continue
            
            # Only include serializable values
            try:
                json.dumps({key: value})
                log_record[key] = value
            except (TypeError, OverflowError):
                log_record[key] = str(value)
        
        return json.dumps(log_record)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }
    
    def format(self, record):
        """Format the log record with colors and context."""
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Basic log format with timestamp, level, and message
        log_format = f"{level_color}[{record.levelname}]{reset_color} {record.getMessage()}"
        
        # Add context information if available
        context_info = []
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in ["args", "exc_info", "exc_text", "levelname", 
                                             "levelno", "lineno", "module", "msecs", 
                                             "msg", "name", "pathname", "process", 
                                             "processName", "relativeCreated", "thread", 
                                             "threadName", "funcName", "created", "asctime"]:
                continue
            
            # Format the context value
            try:
                if isinstance(value, dict) or isinstance(value, list):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                
                # Truncate long values
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                
                context_info.append(f"{key}={value_str}")
            except:
                pass
        
        # Add context if available
        if context_info:
            log_format += f" [{', '.join(context_info)}]"
        
        # Add file and line information
        log_format += f" ({record.module}:{record.lineno})"
        
        # Add exception info if available
        if record.exc_info:
            log_format += f"\n{level_color}Exception:{reset_color} {record.exc_info[0].__name__}: {record.exc_info[1]}"
            log_format += f"\n{traceback.format_exc()}"
        
        return log_format


def setup_logging(log_file=None, log_level=logging.INFO, console_level=None):
    """Set up the logging system.
    
    Args:
        log_file (str, optional): Path to the log file. If None, file logging is disabled.
        log_level (int, optional): Logging level for the file handler. Defaults to INFO.
        console_level (int, optional): Logging level for the console handler.
                                      If None, uses the same level as log_level.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    if console_level is None:
        console_level = log_level
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    # Get the logger
    logger = logging.getLogger("workday_scraper")
    logger.setLevel(min(log_level, console_level))
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Console handler with human-readable format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    # File handler with JSON format if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredLogFormatter())
        logger.addHandler(file_handler)
    
    return logger


# Create a default logger
logger = setup_logging()


def get_logger():
    """Get the configured logger instance.
    
    Returns:
        logging.Logger: The configured logger instance.
    """
    return logger


def configure_logger(log_file=None, log_level=logging.INFO, console_level=None):
    """Configure the logger with the specified settings.
    
    Args:
        log_file (str, optional): Path to the log file. If None, file logging is disabled.
        log_level (int, optional): Logging level for the file handler. Defaults to INFO.
        console_level (int, optional): Logging level for the console handler.
                                      If None, uses the same level as log_level.
    
    Returns:
        logging.Logger: The configured logger instance.
    """
    global logger
    logger = setup_logging(log_file, log_level, console_level)
    return logger