from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import deque
from .MessageBroker import get_message_broker

class ErrorLevel:
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

class ErrorManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.message_broker = get_message_broker()
            self._error_history = deque(maxlen=100)  # Store last 100 errors
            self._setup_error_channel()
    
    def _setup_error_channel(self):
        """Initialize the error message channel in the message broker"""
        # The channel will be created automatically when first published to
        # Subscribe to error channels
        self._error_queue = self.message_broker.subscribe(["error_messages"])
    
    def send_error(self, 
                  level: str,
                  source: str,
                  operation: str,
                  message: str,
                  details: Optional[str] = None,
                  suggestion: Optional[str] = None) -> None:
        """
        Send an error message through the message broker.
        
        Args:
            level: Error level (CRITICAL, ERROR, WARNING, INFO)
            source: Component or module generating the error
            operation: Operation that triggered the error
            message: Primary error message
            details: Additional error details (optional)
            suggestion: Suggested resolution (optional)
        """
        error_data = {
            "level": level,
            "source": source,
            "operation": operation,
            "message": message,
            "details": details,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in history (only if it's not a clear action)
        self._error_history.append(error_data.copy())
        
        self.message_broker.publish('error_messages', error_data)
    
    def send_critical(self, source: str, operation: str, message: str, **kwargs) -> None:
        """Convenience method for critical errors"""
        self.send_error(ErrorLevel.CRITICAL, source, operation, message, **kwargs)
    
    def send_error_level(self, source: str, operation: str, message: str, **kwargs) -> None:
        """Convenience method for error level messages"""
        self.send_error(ErrorLevel.ERROR, source, operation, message, **kwargs)
    
    def send_warning(self, source: str, operation: str, message: str, **kwargs) -> None:
        """Convenience method for warnings"""
        self.send_error(ErrorLevel.WARNING, source, operation, message, **kwargs)
    
    def send_info(self, source: str, operation: str, message: str, **kwargs) -> None:
        """Convenience method for info messages"""
        self.send_error(ErrorLevel.INFO, source, operation, message, **kwargs)

    def clear_errors(self) -> None:
        """Clear all error messages by sending a clear signal"""
        clear_data = {
            "action": "clear",
            "timestamp": datetime.now().isoformat()
        }
        self.message_broker.publish('error_messages', clear_data)

    def get_error_history(self, 
                         level_filter: Optional[str] = None,
                         source_filter: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get error history with optional filtering.
        
        Args:
            level_filter: Filter by error level (CRITICAL, ERROR, WARNING, INFO)
            source_filter: Filter by source component
            limit: Maximum number of errors to return (most recent first)
            
        Returns:
            List of error messages matching the filters
        """
        errors = list(self._error_history)
        
        # Apply filters
        if level_filter:
            errors = [e for e in errors if e.get('level') == level_filter]
        
        if source_filter:
            errors = [e for e in errors if e.get('source') == source_filter]
        
        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Apply limit
        if limit:
            errors = errors[:limit]
            
        return errors
    
    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent N errors"""
        return self.get_error_history(limit=count)
    
    def get_errors_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get all errors of a specific level"""
        return self.get_error_history(level_filter=level)
    
    def get_critical_errors(self) -> List[Dict[str, Any]]:
        """Get all critical errors"""
        return self.get_errors_by_level(ErrorLevel.CRITICAL)
    
    def clear_error_history(self) -> None:
        """Clear the entire error history"""
        self._error_history.clear()
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get a summary of errors by level"""
        summary = {
            ErrorLevel.CRITICAL: 0,
            ErrorLevel.ERROR: 0,
            ErrorLevel.WARNING: 0,
            ErrorLevel.INFO: 0
        }
        
        for error in self._error_history:
            level = error.get('level', ErrorLevel.ERROR)
            if level in summary:
                summary[level] += 1
        
        return summary

def get_error_manager() -> ErrorManager:
    """Get the singleton ErrorManager instance"""
    return ErrorManager() 