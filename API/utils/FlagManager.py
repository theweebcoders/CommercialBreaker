import sys
import threading
import os
from .NetworkUtils import CurlHttpClient, RequestException

class FlagManager:
    """
    Centralized flag management for CommercialBreaker.
    Handles all command-line arguments, environment variables, and runtime flags.
    
    Usage:
        from GUI import FlagManager
        
        # Check if a flag is enabled
        if FlagManager.cutless:
            # Do cutless-specific things
            
        # Change flag at runtime
        FlagManager.set_cutless(True)
    """
    _instance = None
    _lock = threading.Lock()
    
    # Define class-level flags for static access
    docker = '--docker' in sys.argv
    cutless_in_args = '--cutless' in sys.argv
    cutless = cutless_in_args  # Initialize with CLI value
    webui = '--webui' in sys.argv
    clydes = '--clydes' in sys.argv
    
    # Check environment variables (important for Docker)
    if os.environ.get('CUTLESS', '').lower() in ('true', '1', 'yes'):
        cutless = True
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance of FlagManager exists"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FlagManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize instance variables and callbacks"""
        # Store callbacks for features that need notification on change
        self._cutless_callbacks = []
    
    @staticmethod
    def register_cutless_callback(callback):
        """Register a callback function that will be notified when cutless state changes"""
        instance = FlagManager()
        if callback not in instance._cutless_callbacks:
            instance._cutless_callbacks.append(callback)
    
    @classmethod
    def set_cutless(cls, enabled):
        """Set the cutless flag state and notify all registered callbacks"""
        previous = cls.cutless
        cls.cutless = enabled
        
        # Notify callbacks only if the state changed
        if previous != enabled:
            instance = cls()
            instance._notify_cutless_callbacks()
    
    def _notify_cutless_callbacks(self):
        """Notify all registered callbacks about cutless state change"""
        for callback in self._cutless_callbacks:
            try:
                callback(FlagManager.cutless)
            except Exception as e:
                print(f"Error in cutless callback: {e}")
                
    @classmethod
    def evaluate_platform_compatibility(cls, platform_type, platform_url=None):
        """
        Evaluate if cutless should be enabled based on platform compatibility
        
        Args:
            platform_type (str): The type of platform ('tunarr', 'dizquetv', or 'combreakdirect')
            platform_url (str, optional): The URL of the platform
            
        Returns:
            bool: Whether cutless is enabled after evaluation
        """
        # If cutless wasn't in args, don't even evaluate
        if not cls.cutless_in_args:
            cls.set_cutless(False)
            return False
            
        # Tunarr doesn't support cutless
        if platform_type == 'tunarr':
            cls.set_cutless(False)
            print("Cutless mode disabled: Tunarr platform selected")
            return False

        if platform_type == 'combreakdirect':
            cls.set_cutless(True)
            print("Cutless mode enabled: ComBreakDirect always runs in cutless mode")
            return True

        # For dizqueTV, run compatibility check
        elif platform_type == 'dizquetv' and platform_url:
            compatible = cls._check_dizquetv_advanced(platform_url)
            if compatible:
                cls.set_cutless(True)
                print("Cutless mode enabled: DizqueTV compatibility confirmed")
            else:
                cls.set_cutless(False)
                print("Cutless mode disabled: DizqueTV compatibility check failed")
            return compatible
            
        # No platform specified yet, keep current state
        return cls.cutless

    @classmethod
    def _check_dizquetv_advanced(cls, base_url: str, timeout: float = 10.0) -> bool:
        """
        Fetch <base_url>/templates/program-config.html and verify that the
        advanced-options accordion (movieAdvancedOpen) is present.

        Returns True if found, False otherwise.
        """
        tpl_url = base_url.rstrip('/') + '/templates/program-config.html'
        try:
            print(f"Cutless check: testing connection to {tpl_url}")
            r = CurlHttpClient.get(tpl_url, timeout=int(timeout))
            print(f"Cutless check: received response with status {r.status_code}")
            r.raise_for_status()
        except RequestException as exc:
            print(f"Cutless check: failed to reach dizqueTV template ({exc})")
            print(f"Cutless check: URL was {tpl_url}")
            return False

        has_cutless_feature = 'movieAdvancedOpen' in r.text
        if has_cutless_feature:
            print("Cutless check: found movieAdvancedOpen in template (cutless compatible)")
        else:
            print("Cutless check: movieAdvancedOpen not found (standard DizqueTV, not cutless fork)")
        return has_cutless_feature
    
    @classmethod
    def broadcast_status_update(cls, message):
        """Broadcast a status update about flag changes"""
        # This can be expanded later if needed
        print(message)

# Initialize the singleton instance
flag_manager = FlagManager()
