"""
MessageBroker Module

Provides a unified in-memory message broker system for CommercialBreaker.
This replaces both direct callbacks and Redis pub/sub with a single communication
mechanism that works across all interfaces (GUI, WebUI, CLI).
"""

import threading
import queue
from typing import Dict, List, Any, Optional, Set, Union


class MessageBroker:
    """
    Thread-safe in-memory message broker that allows publishing and subscribing to channels.
    
    This is implemented as a singleton pattern so that the same broker can be
    accessed from anywhere in the application.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure only one instance of MessageBroker exists (singleton pattern)"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MessageBroker, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize broker state"""
        self._subscribers: Dict[str, List[queue.Queue]] = {}
        self._subscriber_lock = threading.Lock()
    
    def publish(self, channel: str, message: Any) -> None:
        """
        Publish a message to a channel.
        
        Args:
            channel: The channel to publish to
            message: The message to publish (can be any serializable object)
        """
        with self._subscriber_lock:
            # If no one is listening to this channel, just return
            if channel not in self._subscribers:
                return
                
            # Send message to all subscribers
            for subscriber_queue in self._subscribers[channel]:
                try:
                    # Use a non-blocking put to avoid deadlocks
                    # If queue is full, we will lose the message for that subscriber
                    subscriber_queue.put_nowait((channel, message))
                except queue.Full:
                    # Log or handle if needed; queue is full and message was dropped
                    pass
    
    def subscribe(self, channels: Union[str, List[str]]) -> queue.Queue:
        """
        Subscribe to one or more channels.
        
        Args:
            channels: A channel name or list of channel names to subscribe to
            
        Returns:
            A Queue object that will receive (channel, message) tuples
        """
        # Convert single channel to list for consistent handling
        if isinstance(channels, str):
            channels = [channels]
        
        # Create a new queue for this subscription
        subscriber_queue = queue.Queue(maxsize=100)  # Limit queue size to prevent memory issues
        
        with self._subscriber_lock:
            # Add queue to each requested channel
            for channel in channels:
                if channel not in self._subscribers:
                    self._subscribers[channel] = []
                self._subscribers[channel].append(subscriber_queue)
                
        return subscriber_queue
    
    def unsubscribe(self, subscriber_queue: queue.Queue, channels: Optional[List[str]] = None) -> None:
        """
        Unsubscribe a queue from specific channels or all channels.
        
        Args:
            subscriber_queue: The queue to unsubscribe
            channels: List of channels to unsubscribe from, or None to unsubscribe from all
        """
        with self._subscriber_lock:
            # If channels not specified, unsubscribe from all
            if channels is None:
                for channel_subscribers in self._subscribers.values():
                    if subscriber_queue in channel_subscribers:
                        channel_subscribers.remove(subscriber_queue)
            else:
                # Unsubscribe from specified channels
                for channel in channels:
                    if channel in self._subscribers and subscriber_queue in self._subscribers[channel]:
                        self._subscribers[channel].remove(subscriber_queue)
                        
                        # Clean up empty channel lists
                        if not self._subscribers[channel]:
                            del self._subscribers[channel]


# Singleton getter function
def get_message_broker() -> MessageBroker:
    """Get the global message broker instance."""
    return MessageBroker()