import threading
from typing import Dict, List, Any, Optional
from queue import Queue
import json

class MessageBroker:
    """
    Thread-safe in-memory message broker for inter-component communication.
    
    This broker replaces both Redis pub/sub and direct callback mechanisms with
    a unified messaging system that works across all interfaces (GUI, WebUI, CLI).
    
    Usage:
        # Get the singleton instance
        broker = get_message_broker()
        
        # Publishing messages
        broker.publish("status_updates", "Processing started...")
        
        # Subscribing to channels
        queue = broker.subscribe(["status_updates", "progress_updates"])
        
        # Receiving messages (typically in a separate thread)
        while True:
            channel, message = queue.get()
            print(f"Received on {channel}: {message}")
            queue.task_done()
    """
    
    def __init__(self):
        # Lock for thread-safe operations
        self._lock = threading.RLock()
        
        # Dictionary mapping channels to sets of subscriber queues
        self._subscribers: Dict[str, List[Queue]] = {}
        
        # Dictionary tracking which channels each queue is subscribed to
        self._queue_subscriptions: Dict[Queue, List[str]] = {}
    
    def publish(self, channel: str, message: Any) -> None:
        """
        Publish a message to a channel.
        All subscribers to that channel will receive the message.
        
        Args:
            channel: The channel name to publish to
            message: The message to publish (can be any serializable object)
        """
        with self._lock:
            if channel not in self._subscribers:
                return  # No subscribers for this channel
            
            # Create a copy of the subscribers list to avoid modification during iteration
            subscribers = self._subscribers[channel].copy()
        
        # Deliver the message to each subscriber's queue
        # We do this outside the lock to avoid potential deadlocks
        for queue in subscribers:
            queue.put((channel, message))
    
    def subscribe(self, channels: List[str]) -> Queue:
        """
        Subscribe to one or more channels.
        
        Args:
            channels: List of channel names to subscribe to
            
        Returns:
            Queue object that will receive (channel, message) tuples
        """
        queue = Queue()
        
        with self._lock:
            # Record which channels this queue is subscribed to
            self._queue_subscriptions[queue] = list(channels)
            
            # Add the queue to each channel's subscribers
            for channel in channels:
                if channel not in self._subscribers:
                    self._subscribers[channel] = []
                self._subscribers[channel].append(queue)
        
        return queue
    
    def unsubscribe(self, queue: Queue, channels: Optional[List[str]] = None) -> None:
        """
        Unsubscribe a queue from channels.
        
        Args:
            queue: The queue to unsubscribe
            channels: Optional list of channels to unsubscribe from. 
                      If None, unsubscribe from all channels.
        """
        with self._lock:
            if queue not in self._queue_subscriptions:
                return  # Queue not subscribed to any channels
            
            # If channels not specified, unsubscribe from all
            channels_to_unsubscribe = channels or self._queue_subscriptions[queue]
            
            # Remove queue from each channel's subscribers
            for channel in channels_to_unsubscribe:
                if channel in self._subscribers and queue in self._subscribers[channel]:
                    self._subscribers[channel].remove(queue)
                    
                    # Clean up empty channel lists
                    if not self._subscribers[channel]:
                        del self._subscribers[channel]
            
            # Update or remove the queue's subscription record
            if channels:
                # Remove only specified channels
                for channel in channels:
                    if channel in self._queue_subscriptions[queue]:
                        self._queue_subscriptions[queue].remove(channel)
                
                # If no channels left, remove the queue
                if not self._queue_subscriptions[queue]:
                    del self._queue_subscriptions[queue]
            else:
                # Remove all channels
                del self._queue_subscriptions[queue]
    
    def get_subscriber_count(self, channel: str) -> int:
        """
        Get the number of subscribers for a channel.
        Used for debugging and metrics.
        
        Args:
            channel: The channel name to check
            
        Returns:
            Number of subscribers
        """
        with self._lock:
            if channel not in self._subscribers:
                return 0
            return len(self._subscribers[channel])


# Singleton pattern implementation
_broker_instance = None
_broker_lock = threading.Lock()

def get_message_broker() -> MessageBroker:
    """
    Get or create the singleton MessageBroker instance.
    
    Returns:
        The global MessageBroker instance
    """
    global _broker_instance
    
    if _broker_instance is None:
        with _broker_lock:
            if _broker_instance is None:
                _broker_instance = MessageBroker()
    
    return _broker_instance