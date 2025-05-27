#!/usr/bin/env python3
import sys
import os
import time
import threading
from unittest.mock import Mock, patch

# Add --cutless to simulate the command line argument BEFORE any imports
if '--cutless' not in sys.argv:
    sys.argv.append('--cutless')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class MockPage4:
    """Mock Page4 that simulates the real UI component behavior"""
    def __init__(self, logic_controller):
        self.logic = logic_controller
        # Start with the current state from LogicController
        self.cutless_checkbox_visible = logic_controller.cutless
        
        # Subscribe to cutless state changes like the real Page4 does
        self.logic.subscribe_to_cutless_state(self.handle_cutless_state_update)
        
    def handle_cutless_state_update(self, enabled):
        """Handle cutless state updates from LogicController (like real Page4)"""
        print(f"   DEBUG: MockPage4.handle_cutless_state_update called with: '{enabled}' (type: {type(enabled)})")
        # Convert string 'true'/'false' to boolean if needed
        if isinstance(enabled, str):
            enabled = enabled.lower() == 'true'
            print(f"   DEBUG: Converted string to bool: {enabled}")
        self.update_cutless_checkbox(enabled)
        
    def update_cutless_checkbox(self, enabled):
        """Show/hide the cutless checkbox (like real Page4)"""
        self.cutless_checkbox_visible = enabled
        print(f"   MockPage4: Checkbox visibility updated to: {'VISIBLE' if enabled else 'HIDDEN'}")

def test_scenario_1_bad_url():
    """Test scenario 1: User starts app with --cutless, enters bad DizqueTV URL"""
    print("\n" + "="*60)
    print("SCENARIO 1: Bad DizqueTV URL")
    print("="*60)
    
    # Import after setting sys.argv
    from GUI.FlagManager import FlagManager
    from GUI.FrontEndLogic import LogicController
    
    print(f"1. Initial state after imports:")
    print(f"   FlagManager.cutless: {FlagManager.cutless}")
    print(f"   FlagManager.cutless_in_args: {FlagManager.cutless_in_args}")
    
    # Simulate user flow through Page1
    print("\n2. User navigates to Page1 and enters details:")
    logic = LogicController()
    
    # Create a mock Page4 that subscribes to cutless updates (like real UI)
    mock_page4 = MockPage4(logic)
    print(f"   MockPage4 created, initial checkbox visible: {mock_page4.cutless_checkbox_visible}")
    
    # User selects libraries and enters platform details
    logic._set_data("selected_anime_library", "Anime")
    logic._set_data("selected_toonami_library", "Toonami") 
    logic._set_data("platform_url", "http://localhost:99999")  # Bad URL
    logic._set_data("platform_type", "dizquetv")
    
    print(f"   Platform: dizquetv")
    print(f"   URL: http://localhost:99999")
    
    # User clicks Continue - this triggers compatibility check
    print("\n3. User clicks Continue (triggers compatibility check):")
    logic.check_dizquetv_compatibility()
    
    # Wait for async operations and callbacks
    time.sleep(0.5)
    
    print(f"\n4. State after compatibility check:")
    print(f"   FlagManager.cutless: {FlagManager.cutless}")
    print(f"   LogicController.cutless: {LogicController.cutless}")
    print(f"   logic.cutless: {logic.cutless}")
    
    # Check what the UI component (mock Page4) sees
    print(f"\n5. UI Component (MockPage4) state:")
    print(f"   MockPage4 checkbox visible: {mock_page4.cutless_checkbox_visible}")
    print(f"   EXPECTED: Checkbox should be HIDDEN")
    print(f"   ACTUAL: Checkbox is {'VISIBLE' if mock_page4.cutless_checkbox_visible else 'HIDDEN'}")
    
    assert not mock_page4.cutless_checkbox_visible, (
        "Checkbox should be HIDDEN when DizqueTV URL is bad, but it is VISIBLE"
    )

def test_scenario_2_good_url():
    """Test scenario 2: User starts app with --cutless, enters good DizqueTV URL"""
    print("\n" + "="*60)
    print("SCENARIO 2: Good DizqueTV URL (mocked)")
    print("="*60)
    
    # Reset modules to get fresh state
    for module in list(sys.modules.keys()):
        if module.startswith('GUI'):
            del sys.modules[module]
    
    # Mock successful dizqueTV check
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html>movieAdvancedOpen</html>'  # This is what dizqueTV returns
        mock_get.return_value = mock_response
        
        # Import after setting sys.argv
        from GUI.FlagManager import FlagManager
        from GUI.FrontEndLogic import LogicController
        
        print(f"1. Initial state after imports:")
        print(f"   FlagManager.cutless: {FlagManager.cutless}")
        print(f"   FlagManager.cutless_in_args: {FlagManager.cutless_in_args}")
        
        # Simulate user flow through Page1
        print("\n2. User navigates to Page1 and enters details:")
        logic = LogicController()
        
        # Create mock Page4 that subscribes to cutless updates
        mock_page4 = MockPage4(logic)
        print(f"   MockPage4 created, initial checkbox visible: {mock_page4.cutless_checkbox_visible}")
        
        # User selects libraries and enters platform details
        logic._set_data("selected_anime_library", "Anime")
        logic._set_data("selected_toonami_library", "Toonami")
        logic._set_data("platform_url", "http://192.168.1.100:8000")  # Good URL
        logic._set_data("platform_type", "dizquetv")
        
        print(f"   Platform: dizquetv")
        print(f"   URL: http://192.168.1.100:8000")
        
        # User clicks Continue - this triggers compatibility check
        print("\n3. User clicks Continue (triggers compatibility check):")
        logic.check_dizquetv_compatibility()
        
        # Wait for async operations and callbacks
        time.sleep(0.5)
        
        print(f"\n4. State after compatibility check:")
        print(f"   FlagManager.cutless: {FlagManager.cutless}")
        print(f"   LogicController.cutless: {LogicController.cutless}")
        print(f"   logic.cutless: {logic.cutless}")
        
        # Check what the UI component sees
        print(f"\n5. UI Component (MockPage4) state:")
        print(f"   MockPage4 checkbox visible: {mock_page4.cutless_checkbox_visible}")
        print(f"   EXPECTED: Checkbox should be VISIBLE")
        print(f"   ACTUAL: Checkbox is {'VISIBLE' if mock_page4.cutless_checkbox_visible else 'HIDDEN'}")
        
        assert mock_page4.cutless_checkbox_visible, (
            "Checkbox should be VISIBLE when DizqueTV URL is good, but it is HIDDEN"
        )

def test_scenario_3_no_cutless_flag():
    """Test scenario 3: User starts app WITHOUT --cutless flag"""
    print("\n" + "="*60)
    print("SCENARIO 3: No --cutless flag")
    print("="*60)
    
    # Remove --cutless from sys.argv
    sys.argv = [arg for arg in sys.argv if arg != '--cutless']
    
    # Reset modules to get fresh state
    for module in list(sys.modules.keys()):
        if module.startswith('GUI'):
            del sys.modules[module]
    
    # Import after modifying sys.argv
    from GUI.FlagManager import FlagManager
    from GUI.FrontEndLogic import LogicController
    
    print(f"1. Initial state after imports:")
    print(f"   sys.argv: {sys.argv}")
    print(f"   FlagManager.cutless: {FlagManager.cutless}")
    print(f"   FlagManager.cutless_in_args: {FlagManager.cutless_in_args}")
    
    # Even with a good URL, cutless should stay disabled
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html>movieAdvancedOpen</html>'
        mock_get.return_value = mock_response
        
        logic = LogicController()
        
        # Create mock Page4 to test UI component behavior
        mock_page4 = MockPage4(logic)
        print(f"   MockPage4 created, initial checkbox visible: {mock_page4.cutless_checkbox_visible}")
        
        logic._set_data("platform_url", "http://192.168.1.100:8000")
        logic._set_data("platform_type", "dizquetv")
        logic.check_dizquetv_compatibility()
        
        time.sleep(0.5)
        
        print(f"\n2. After compatibility check with good URL:")
        print(f"   FlagManager.cutless: {FlagManager.cutless}")
        print(f"   LogicController.cutless: {LogicController.cutless}")
        print(f"   logic.cutless: {logic.cutless}")
        
        # Check what the UI component sees
        print(f"\n3. UI Component (MockPage4) state:")
        print(f"   MockPage4 checkbox visible: {mock_page4.cutless_checkbox_visible}")
        print(f"   EXPECTED: Checkbox should be HIDDEN")
        print(f"   ACTUAL: Checkbox is {'VISIBLE' if mock_page4.cutless_checkbox_visible else 'HIDDEN'}")
        
        assert not mock_page4.cutless_checkbox_visible, (
            "Checkbox should be HIDDEN when --cutless flag is not present, but it is VISIBLE"
        )

def main():
    print("CUTLESS CHECKBOX TEST")
    print("\nCURRENT BUG: Checkbox shows whenever --cutless flag is present,")
    print("regardless of dizqueTV compatibility check result")
    
    results = []
    
    # Test bad URL scenario
    try:
        test_scenario_1_bad_url()
        results.append(("Scenario 1: --cutless + bad URL", True))
    except Exception as e:
        print(f"\nERROR in Scenario 1: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Scenario 1: --cutless + bad URL", False))
    
    # Test good URL scenario  
    try:
        test_scenario_2_good_url()
        results.append(("Scenario 2: --cutless + good URL", True))
    except Exception as e:
        print(f"\nERROR in Scenario 2: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Scenario 2: --cutless + good URL", False))
    
    # Test no flag scenario
    try:
        test_scenario_3_no_cutless_flag()
        results.append(("Scenario 3: No --cutless flag", True))
    except Exception as e:
        print(f"\nERROR in Scenario 3: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Scenario 3: No --cutless flag", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
        print("\nFailure Analysis:")
        print("- Scenario 1 fails because LogicController.cutless remains True")
        print("  even after FlagManager.cutless is set to False by the")
        print("  compatibility check. This causes the checkbox to show when")
        print("  it shouldn't.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

