import threading
import time
from queue import Queue, Empty
from typing import List, Callable, Any, Tuple, Optional
from .message_broker import get_message_broker

class MessageBrokerMixin:
    """
    Mixin class that provides message broker functionality to UI components.
    This replaces the RedisListenerMixin with a unified messaging approach.
    
    UI components should:
    1. Inherit from this mixin
    2. Call start_message_listener() during initialization
    3. Implement handle_message(channel, data) method
    """
    
    def after(self, time_ms: float, callback: Callable) -> None:
        """
        Schedule a callback to be called after a given time.
        This is a compatibility function that works across UI frameworks.
        
        Args:
            time_ms: Time in milliseconds before callback is executed
            callback: Function to call
        """
        threading.Timer(time_ms / 1000, callback).start()
    
    def start_message_listener(self, channels: List[str] = None) -> None:
        """
        Start listening for messages on specified channels.
        
        Args:
            channels: List of channel names to subscribe to.
                     If None, subscribes to default channels.
        """
        # Default channels used throughout the application
        if channels is None:
            channels = [
                'status_updates', 
                'progress_updates',
                'plex_servers', 
                'plex_libraries', 
                'filtered_files',
                'plex_auth_url', 
                'cutless_state',
                'new_server_choices',
                'new_library_choices'
            ]
        
        # Get the global message broker and subscribe to channels
        broker = get_message_broker()
        self.message_queue = broker.subscribe(channels)
        
        # Start processing messages
        self.after(100, self.process_messages)
    
    def process_messages(self) -> None:
        """
        Process all available messages in the queue.
        Schedules itself to run again after processing.
        """
        # Process all messages currently in queue
        while not self.message_queue.empty():
            try:
                channel, data = self.message_queue.get_nowait()
                self.dispatch_message(channel, data)
                self.message_queue.task_done()
            except Empty:
                break
        
        # Schedule to run again
        self.after(100, self.process_messages)
    
    def dispatch_message(self, channel: str, data: Any) -> None:
        """
        Dispatch a message to the appropriate handler based on channel.
        
        Args:
            channel: The channel the message was sent on
            data: The message data
        """
        # Special handling for status updates
        if channel == 'status_updates':
            self.update_status_label(data)
        
        # For all other messages, try to use handle_message if available
        elif hasattr(self, 'handle_message'):
            self.handle_message(channel, data)
    
    def update_status_label(self, status: str) -> None:
        """
        Update status display with a new status message.
        
        Args:
            status: Status message text
        """
        # Use the update_status_display method if available (for BasePage)
        if hasattr(self, 'update_status_display'):
            self.update_status_display(status)
        # Fallback for basic status labels
        elif hasattr(self, 'status_label'):
            self.status_label.set_text(f"Status: {status}")