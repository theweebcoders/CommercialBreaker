from ComBreak import CommercialBreakerLogic
from API import LogicController
from API.utils.FlagManager import FlagManager
import config
import threading
import os
import sys
import psutil
import json
import ToonamiTools
import remi.gui as gui
from remi import start, App
import time

class Styles:
    default_label_style = {
        'font-family': 'Rajdhani, Arial, sans-serif',
        'font-size': '16px',
        'font-weight': '500',
        'letter-spacing': '0.5px',
        'color': '#00ccff',
        'text-shadow': '0 0 5px rgba(0, 204, 255, 0.7)',
        'background-color': 'rgba(0, 30, 60, 0.6)',
        'padding': '6px 12px',
        'border-left': '2px solid #00ccff',
        'margin-bottom': '5px',
        'transition': 'all 0.2s ease',
        'border-radius': '0 4px 4px 0',
        'display': 'block',
        'width': 'fit-content'
    }
    title_label_style = {
        'font-family': 'Arial, sans-serif',
        'font-size': '2.5rem',
        'letter-spacing': '0.05em',
        'padding': '10px',
        'font-weight': 'bold',
        'margin': '10px',
        'color': '#0ff',
        'text-shadow': '0 0 5px #00ccff, 0 0 10px #0099ff, 0 0 20px #0066ff, 0 0 40px #003399'
    }
    default_button_style = {
        'font-family': 'inherit',
        'color': '#a5f3fc',
        'background': 'transparent',
        'border': '1px solid rgba(0, 140, 255, 0.4)',
        'box-shadow': '0 0 10px rgba(0, 140, 255, 0.2)',
        'clip-path': 'polygon(0 10px, 10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px))',
        'padding': '10px',
        'margin': '5px',
        'transition': 'all 0.3s ease'
    }
    
    # New themed button styles
    # Primary action button style (for main actions like "Continue", "Create Channel")
    primary_button_style = {
        'font-family': 'Rajdhani, sans-serif',
        'font-size': '16px',
        'font-weight': '600',
        'color': '#00ffff',
        'background': 'linear-gradient(90deg, rgba(0, 50, 100, 0.6) 0%, rgba(0, 100, 150, 0.4) 100%)',
        'border': '1px solid rgba(0, 255, 255, 0.6)',
        'box-shadow': '0 0 15px rgba(0, 255, 255, 0.3), inset 0 0 10px rgba(0, 100, 255, 0.2)',
        'clip-path': 'polygon(0 10px, 10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px))',
        'padding': '10px 20px',
        'margin': '8px',
        'transition': 'all 0.3s ease',
        'text-shadow': '0 0 5px rgba(0, 255, 255, 0.7)'
    }

    # Secondary action button (for operations like "Detect", "Cut", "Add Special Bumps")
    secondary_button_style = {
        'font-family': 'Rajdhani, sans-serif',
        'font-size': '15px',
        'font-weight': '500',
        'color': '#a5f3fc',
        'background': 'rgba(0, 40, 80, 0.4)',
        'border': '1px solid rgba(0, 140, 255, 0.5)',
        'box-shadow': '0 0 8px rgba(0, 140, 255, 0.2), inset 0 0 5px rgba(0, 60, 120, 0.3)',
        'clip-path': 'polygon(15px 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%, 0 15px)',
        'padding': '8px 16px',
        'margin': '6px',
        'transition': 'all 0.3s ease'
    }

    # Utility button style (for utility functions like "Delete", "Skip")
    utility_button_style = {
        'font-family': 'Rajdhani, sans-serif',
        'font-size': '14px',
        'font-weight': '400',
        'color': '#90c8f0',
        'background': 'rgba(20, 30, 60, 0.5)',
        'border': '1px solid rgba(100, 150, 255, 0.3)',
        'box-shadow': '0 0 5px rgba(100, 150, 255, 0.15)',
        'border-radius': '3px',
        'padding': '7px 14px',
        'margin': '5px',
        'transition': 'all 0.2s ease'
    }

    # Warning/destructive button style (for "Destructive Mode", dangerous operations)
    warning_button_style = {
        'font-family': 'Rajdhani, sans-serif',
        'font-size': '15px',
        'font-weight': '500',
        'color': '#ffcc00',
        'background': 'rgba(60, 20, 20, 0.5)',
        'border': '1px solid rgba(255, 100, 50, 0.4)',
        'box-shadow': '0 0 8px rgba(255, 100, 50, 0.2)',
        'clip-path': 'polygon(10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px), 0 10px)',
        'padding': '8px 16px',
        'margin': '6px',
        'transition': 'all 0.2s ease'
    }

    # Navigation button style (for "Back", "Start Over", etc.)
    navigation_button_style = {
        'font-family': 'Rajdhani, sans-serif',
        'font-size': '14px',
        'font-weight': '500',
        'color': '#a5f3fc',
        'background': 'transparent',
        'border': '1px solid rgba(0, 140, 255, 0.4)',
        'border-radius': '0',
        'box-shadow': 'none',
        'padding': '6px 12px',
        'margin': '5px',
        'transition': 'all 0.2s ease'
    }

    # Hover states for all button types
    primary_button_hover_style = {
        'box-shadow': '0 0 20px rgba(0, 255, 255, 0.5), inset 0 0 15px rgba(0, 150, 255, 0.3)',
        'transform': 'translateY(-2px)',
        'color': '#ffffff',
        'text-shadow': '0 0 8px rgba(0, 255, 255, 1)'
    }

    secondary_button_hover_style = {
        'box-shadow': '0 0 12px rgba(0, 170, 255, 0.3), inset 0 0 8px rgba(0, 100, 180, 0.4)',
        'transform': 'translateY(-1px)',
        'color': '#d0f0ff'
    }

    utility_button_hover_style = {
        'box-shadow': '0 0 8px rgba(120, 170, 255, 0.25)',
        'background': 'rgba(30, 40, 70, 0.6)',
        'color': '#a0d0ff'
    }

    warning_button_hover_style = {
        'box-shadow': '0 0 12px rgba(255, 120, 50, 0.3), inset 0 0 8px rgba(120, 30, 30, 0.3)',
        'transform': 'translateY(-1px)',
        'color': '#ffdd44'
    }

    navigation_button_hover_style = {
        'background': 'rgba(0, 40, 80, 0.2)',
        'border': '1px solid rgba(0, 170, 255, 0.5)',
        'color': '#c0f0ff'
    }
    
    selected_button_style = {
        'font-size': '16px',
        'font-family': 'inherit',
        'padding': '10px 20px',
        'margin': '5px',
        'border-radius': '8px',
        'background': 'transparent',
        'background-color': 'rgba(37, 99, 235, 0.3)',
        'color': '#a5f3fc',
        'transition': 'all 0.2s ease',
        'box-shadow': '0 0 15px rgba(0, 140, 255, 0.3)',
        'transform': 'scale(1.05)',
        'border': '1px solid rgba(0, 140, 255, 0.6)'
    }
    unselected_button_style = {
        'font-size': '16px',
        'font-family': 'inherit',
        'padding': '10px 20px',
        'margin': '5px',
        'border-radius': '8px',
        'background': 'transparent',
        'background-color': 'transparent',
        'color': '#a5f3fc',
        'transition': 'all 0.2s ease',
        'box-shadow': 'none',
        'transform': 'scale(1)',
        'border': '1px solid rgba(0, 140, 255, 0.2)'
    }
    default_input_style = {
        'font-size': '16px',
        'font-family': 'inherit',
        'padding': '5px',
        'margin': '5px',
        'color': '#a5f3fc',
        'background': 'rgba(0, 20, 40, 0.6)',
        'border': '1px solid rgba(0, 140, 255, 0.4)',
        'clip-path': 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))',
        'width': '100%',
        'appearance': 'none',
        '-webkit-appearance': 'none',
    }
    default_container_style = {
        'display': 'flex',
        'flex-direction': 'column',
        'align-items': 'center',
        'justify-content': 'flex-start',
        'width': '100%',
        'height': '100%',
        'background-color': '#000924',
        'background-image': 'linear-gradient(45deg, rgba(0, 140, 255, 0.2) 1px, transparent 1px), linear-gradient(-45deg, rgba(0, 140, 255, 0.3) 1px, transparent 1px)',
        'background-size': '30px 30px',
        'animation': 'grid-scroll 20s linear infinite',
        'color': '#a5f3fc',
        'font-family': 'Arial, sans-serif',
        'overflow-y': 'auto',
        'overflow-x': 'hidden'
    }
    transparent_style = {
        'background': 'transparent',
        'background-color': 'transparent',
        'box-shadow': 'none',
        'border': 'none'
    }
    # New navigation-related styles
    navigation_bar_style = {
        'display': 'flex',
        'flex-direction': 'row',
        'align-items': 'center',
        'justify-content': 'space-between',
        'width': '100%',
        'padding': '10px 20px',
        'background-color': 'rgba(0, 20, 40, 0.8)',
        'border-bottom': '2px solid rgba(0, 140, 255, 0.6)',
        'box-shadow': '0 0 20px rgba(0, 140, 255, 0.3)',
        'margin-bottom': '20px',
    }
    
    # New section header style for grouping related fields
    section_header_style = {
        'font-family': 'Orbitron, Rajdhani, sans-serif',
        'font-size': '20px',
        'font-weight': 'bold',
        'letter-spacing': '1px',
        'color': '#ffffff',
        'text-shadow': '0 0 10px #00aaff, 0 0 20px #0077ff',
        'border-bottom': '1px solid rgba(0, 170, 255, 0.5)',
        'padding-bottom': '8px',
        'margin': '20px 0 15px 0'
    }
    
    # Style for required form fields
    required_label_style = {
        'position': 'relative',
    }
    
    required_label_style.update(default_label_style)
    required_label_style['border-left'] = '2px solid #ff5f5f'
    
    nav_indicator_active = {
        'width': '14px',
        'height': '14px',
        'border-radius': '50%',
        'margin': '0 3px',
        'background-color': '#0ff',
        'box-shadow': '0 0 10px rgba(0, 255, 255, 0.8), 0 0 20px rgba(0, 140, 255, 0.4)',
        'transition': 'all 0.3s ease',
        'cursor': 'pointer'
    }
    nav_indicator_inactive = {
        'width': '12px',
        'height': '12px',
        'border-radius': '50%',
        'margin': '0 3px',
        'background-color': 'rgba(0, 140, 255, 0.4)',
        'transition': 'all 0.3s ease',
        'cursor': 'pointer'
    }
    nav_indicator_optional = {
        'width': '10px',
        'height': '10px',
        'border-radius': '50%',
        'margin': '0 3px',
        'border': '1px dashed rgba(0, 140, 255, 0.6)',
        'background-color': 'transparent',
        'transition': 'all 0.3s ease',
        'cursor': 'pointer'
    }
    nav_text_active = {
        'font-size': '14px',
        'color': '#0ff',
        'margin': '0 5px',
        'font-weight': 'bold',
        'text-shadow': '0 0 5px #00ccff',
    }
    nav_text_inactive = {
        'font-size': '14px',
        'color': '#a5f3fc',
        'margin': '0 5px',
        'opacity': '0.8',
    }
    nav_separator = {
        'width': '15px',
        'height': '1px',
        'background-color': 'rgba(0, 140, 255, 0.4)',
        'margin': '0 2px',
    }
    
    # New styles for the status bar
    status_bar_style = {
        'position': 'fixed',
        'bottom': '0',
        'left': '0',
        'width': '100%',
        'padding': '10px 20px',
        'background-color': 'rgba(0, 20, 40, 0.8)',
        'border-top': '2px solid rgba(0, 140, 255, 0.6)',
        'box-shadow': '0 -5px 15px rgba(0, 140, 255, 0.3)',
        'z-index': '1000',
        'display': 'flex',
        'justify-content': 'center',
        'align-items': 'center',
    }
    status_label_style = {
        'font-size': '18px',
        'font-weight': 'bold',
        'color': '#0ff',
        'text-shadow': '0 0 5px #00ccff',
        'padding': '5px',
        'text-align': 'center',
        'width': '100%'
    }
    status_idle_style = {
        'color': '#a5f3fc',
    }
    status_active_style = {
        'color': '#0ff',
        'text-shadow': '0 0 8px #00ccff, 0 0 15px #0066ff',
        'animation': 'pulse 2s infinite'
    }
    status_error_style = {
        'color': '#ff6b6b',
        'text-shadow': '0 0 8px #ff0000',
    }
    
    # Enhanced status bar styles
    status_bar_style = {
        'position': 'fixed',
        'bottom': '0',
        'left': '0',
        'width': '100%',
        'padding': '10px 20px',
        'background-color': 'rgba(0, 20, 40, 0.8)',
        'border-top': '2px solid rgba(0, 140, 255, 0.6)',
        'box-shadow': '0 -5px 15px rgba(0, 140, 255, 0.3)',
        'z-index': '1000',
        'display': 'flex',
        'justify-content': 'space-between',  # Changed to space-between to accommodate progress info
        'align-items': 'center',
        'clip-path': 'polygon(0 0, 100% 0, calc(100% - 15px) 100%, 15px 100%)',
        'overflow-x': 'hidden'
    }
    
    status_label_style = {
        'font-size': '18px',
        'font-weight': 'bold',
        'color': '#0ff',
        'text-shadow': '0 0 5px #00ccff',
        'padding': '5px',
        'text-align': 'center',
        'flex-grow': '1',  # Changed to flex-grow instead of width
        'white-space': 'nowrap',
        'overflow': 'hidden',
        'text-overflow': 'ellipsis'
    }
    
    status_idle_style = {
        'color': '#a5f3fc',
    }
    
    status_active_style = {
        'color': '#0ff',
        'text-shadow': '0 0 8px #00ccff, 0 0 15px #0066ff',
        'animation': 'pulse 2s infinite'
    }
    
    status_error_style = {
        'color': '#ff6b6b',
        'text-shadow': '0 0 8px #ff0000',
    }
    
    # New styles for progress elements
    progress_container_style = {
        'width': '80%',
        'height': '24px',
        'border': '1px solid rgba(0, 140, 255, 0.6)',
        'box-shadow': '0 0 10px rgba(0, 140, 255, 0.3), inset 0 0 5px rgba(0, 0, 20, 0.5)',
        'clip-path': 'polygon(0 4px, 4px 0, calc(100% - 4px) 0, 100% 4px, 100% calc(100% - 4px), calc(100% - 4px) 100%, 4px 100%, 0 calc(100% - 4px))',
        'position': 'relative',
        'overflow': 'hidden',
        'background-color': 'rgba(0, 20, 40, 0.6)',
        'margin': '10px 0'
    }
    
    progress_fill_style = {
        'width': '0%',  # Start at 0%
        'height': '100%',
        'background': 'linear-gradient(90deg, rgba(0, 140, 255, 0.4) 0%, rgba(0, 255, 255, 0.7) 100%)',
        'box-shadow': '0 0 15px rgba(0, 255, 255, 0.6)',
        'transition': 'width 0.3s ease',
        'position': 'absolute',
        'top': '0',
        'left': '0'
    }
    
    progress_text_style = {
        'position': 'absolute',
        'top': '50%',
        'left': '50%',
        'transform': 'translate(-50%, -50%)',
        'color': '#0ff',
        'font-size': '14px',
        'font-weight': 'bold',
        'text-shadow': '0 0 5px rgba(0, 255, 255, 0.8)',
        'z-index': '1'
    }
    
    # Mini progress for status bar
    status_progress_container_style = {
        'width': '150px',
        'height': '16px',
        'border': '1px solid rgba(0, 140, 255, 0.4)',
        'box-shadow': '0 0 8px rgba(0, 140, 255, 0.2), inset 0 0 3px rgba(0, 0, 20, 0.5)',
        'clip-path': 'polygon(0 3px, 3px 0, calc(100% - 3px) 0, 100% 3px, 100% calc(100% - 3px), calc(100% - 3px) 100%, 3px 100%, 0 calc(100% - 3px))',
        'position': 'relative',
        'overflow': 'hidden',
        'background-color': 'rgba(0, 20, 40, 0.6)',
        'margin-left': '15px',
        'flex-shrink': '0'
    }
    
    status_progress_fill_style = {
        'width': '0%',
        'height': '100%',
        'background': 'linear-gradient(90deg, rgba(0, 140, 255, 0.4) 0%, rgba(0, 255, 255, 0.7) 100%)',
        'box-shadow': '0 0 10px rgba(0, 255, 255, 0.4)',
        'transition': 'width 0.3s ease',
        'position': 'absolute',
        'top': '0',
        'left': '0'
    }
    
    status_progress_text_style = {
        'position': 'absolute',
        'top': '50%',
        'left': '50%',
        'transform': 'translate(-50%, -50%)',
        'color': '#0ff',
        'font-size': '11px',
        'font-weight': 'bold',
        'text-shadow': '0 0 4px rgba(0, 255, 255, 0.8)',
        'z-index': '1'
    }

class BasePage(gui.Container):
    def __init__(self, app, title_key, *args, **kwargs):
        super(BasePage, self).__init__(*args, **kwargs)
        self.app = app
        self.title_key = title_key
        self.set_size('100%', '100%')
        self.style.update(Styles.default_container_style)
        
        # Add the navigation bar at the top
        self.nav_bar = NavigationBar(app, title_key)
        self.append(self.nav_bar)
        
        # Create the main content container
        self.main_container = self.create_main_container()
        self.append(self.main_container)
        self.page_title_label = self.add_page_title(self.main_container, self.app.page_titles.get(title_key, ''))
        
        # Create error bar but don't append it yet
        self.error_bar = self.create_error_bar()
        
        # Add status bar at the bottom
        self.status_bar = self.create_status_bar()
        self.append(self.status_bar)
        
        # Set initial status to idle
        self.update_status_display("Idle")
        
        # Track progress value
        self.global_progress_value = 0
        
        # --- Error message subscription ---
        # Create a LogicController instance if we don't have one
        from API import LogicController
        if not hasattr(self.app, 'logic') or self.app.logic is None:
            self.app.logic = LogicController()
        
        # Clear any existing error state when creating a new page
        self.error_label.set_text("")
        self.error_bar_visible = False
        self.error_bar.style['display'] = 'none'
            
        def error_callback(error_data):
            # If this is a clear signal, dismiss the error bar and clear the message
            if isinstance(error_data, dict) and error_data.get('action') == 'clear':
                self.error_label.set_text("")  # Clear the message text
                self.dismiss_error_bar(None)
            else:
                # Format error message for display
                if isinstance(error_data, dict):
                    msg = error_data.get('message', str(error_data))
                    level = error_data.get('level', 'ERROR')
                    src = error_data.get('source', '')
                    op = error_data.get('operation', '')
                    details = error_data.get('details', None)
                    suggestion = error_data.get('suggestion', None)
                    parts = [f"[{level}] {src}: {msg}"]
                    if op:
                        parts[0] += f" ({op})"
                    if details:
                        parts.append(f"Details: {details}")
                    if suggestion:
                        parts.append(f"Suggestion: {suggestion}")
                    display_msg = "\n".join(parts)
                else:
                    display_msg = str(error_data)
                    level = 'DEFAULT'
                
                # Apply the appropriate style based on error level
                level_upper = level.upper() if isinstance(level, str) else 'DEFAULT'
                style = self.error_styles.get(level_upper, self.error_styles['DEFAULT'])
                
                # Apply the style to the error bar
                for prop, value in style.items():
                    if prop == 'color' or prop == 'text-shadow':
                        # Text styles go on the label
                        self.error_label.style[prop] = value
                    else:
                        # Container styles go on the error bar
                        self.error_bar.style[prop] = value
                
                # Set the message text and show the error bar
                self.error_label.set_text(display_msg)
                self.show_error_bar()
                self.app.refresh()
                
        self.app.logic.subscribe_to_error_messages(error_callback)

    def refresh_nav_bar(self):
        # Store reference to main container before removing
        main_container = self.main_container if hasattr(self, 'main_container') else None
        status_bar = self.status_bar if hasattr(self, 'status_bar') else None
        
        # Remove the existing navigation bar
        if hasattr(self, 'nav_bar'):
            self.remove_child(self.nav_bar)
        
        # Create a new navigation bar with current state
        self.nav_bar = NavigationBar(self.app, self.title_key)
        
        # Clear all children
        self.empty()
        
        # Add the nav_bar first
        self.append(self.nav_bar)
        
        # Then add back the main container if it exists
        if (main_container):
            self.append(main_container)
            
        # Add back the status bar if it exists
        if (status_bar):
            self.append(status_bar)

        self.update_page_title_text()

    def create_main_container(self):
        return gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'center',  # Changed to center vertically
            'margin': 'auto',
            'padding': '20px',
            'padding-bottom': '70px',  # Added padding to bottom to ensure content isn't hidden by the status bar
            'background': 'none',
            'box-shadow': 'none',
            'border': 'none',
            'flex-grow': '1',  # Added to allow container to grow and fill available space
            'overflow-y': 'auto',  # Added to enable scrolling if content is too large
            'overflow-x': 'hidden'
        })
    
    def create_status_bar(self):
        """Create a stylized status bar at the bottom of the page with integrated progress indicator"""
        status_bar = gui.Container(style=Styles.status_bar_style)
        
        # Main status label
        self.status_label = gui.Label("Status: Idle", style=Styles.status_label_style)
        self.status_label.style.update(Styles.status_idle_style)
        status_bar.append(self.status_label)
        
        # Add a mini progress bar to the status bar
        self.status_progress_container = gui.Container(style=Styles.status_progress_container_style)
        
        # Create the progress fill element
        self.status_progress_fill = gui.Container(style=Styles.status_progress_fill_style)
        
        # Create percentage text element
        self.status_progress_text = gui.Label("0%", style=Styles.status_progress_text_style)
        
        self.status_progress_container.append(self.status_progress_fill)
        self.status_progress_container.append(self.status_progress_text)
        
        # Initially hide the progress indicator
        self.status_progress_container.style['display'] = 'none'
        
        status_bar.append(self.status_progress_container)
        
        return status_bar
    
    def update_status_display(self, status_text, show_progress=False, progress_value=None, is_error=False):
        """Update the status display with the given text and optional progress"""
        if not hasattr(self, 'status_label'):
            return
            
        # Update the status text
        self.status_label.set_text(status_text)
        try:
            status_text_json = json.dumps(status_text)
            self.app.execute_javascript(f"""
            (function() {{
                const statusEl = document.getElementById('{self.status_label.identifier}');
                if (statusEl) {{
                    statusEl.innerText = {status_text_json};
                }}
            }})();
            """)
        except Exception as exc:
            print(f"Status DOM update failed: {exc}")
        
        # Apply appropriate styling based on whether this is an error
        if is_error:
            self.status_label.style.update(Styles.status_error_style)
        else:
            # Reset to default status style
            self.status_label.style.update(Styles.status_label_style)
            if status_text == "Idle":
                self.status_label.style.update(Styles.status_idle_style)
            elif status_text != "Idle":
                self.status_label.style.update(Styles.status_active_style)
        
        # Update progress indicator if needed
        if hasattr(self, 'status_progress_container'):
            if show_progress and progress_value is not None:
                # Store progress value
                self.global_progress_value = progress_value
                
                # Show progress container
                self.status_progress_container.style['display'] = 'block'
                
                # Update progress values
                width_percentage = min(100, max(0, progress_value))
                
                # Update via JavaScript for smooth animation
                self.app.execute_javascript(f"""
                (function() {{
                    const fillElement = document.getElementById('{self.status_progress_fill.identifier}');
                    const textElement = document.getElementById('{self.status_progress_text.identifier}');
                    if (fillElement) {{
                        fillElement.style.width = '{width_percentage}%';
                    }}
                    if (textElement) {{
                        textElement.innerText = '{width_percentage:.1f}%';
                    }}
                }})();
                """)
            else:
                # Hide progress container when not in progress mode
                self.status_progress_container.style['display'] = 'none'
            
        # Add animation CSS if it doesn't exist
        self.app.execute_javascript("""
        if (!document.getElementById('status-animation-css')) {
            var style = document.createElement('style');
            style.id = 'status-animation-css';
            style.innerHTML = `
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.7; }
                    100% { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        """)

    def show_combreakdirect_completion_dialog(self, base_url: str) -> None:
        if getattr(self, '_cbd_completion_dialog_open', False):
            return

        dialog = gui.GenericDialog(
            "Toonami Channel Created!",
            f"Your ComBreakDirect channel is ready to stream.\n\nOpen the Web UI at:\n{base_url}"
        )
        self._cbd_completion_dialog_open = True

        def on_confirm(emitter):
            self.app.execute_javascript(f"window.open('{base_url}', '_blank')")
            self._cbd_completion_dialog_open = False

        def on_cancel(emitter):
            self._cbd_completion_dialog_open = False

        dialog.set_on_confirm_dialog_listener(on_confirm)
        dialog.set_on_cancel_dialog_listener(on_cancel)
        dialog.show(self.app)

    def add_page_title(self, container, title_text):
        page_title = gui.Label(title_text, style=Styles.title_label_style)
        page_title.add_class('main-title')

        # Add hidden panic button: Click title 5 times rapidly to access diagnostics
        import time
        self._title_click_count = 0
        self._title_last_click = 0

        def on_title_click(widget):
            current_time = time.time()

            # Reset if more than 2 seconds since last click
            if current_time - self._title_last_click > 2.0:
                self._title_click_count = 0

            self._title_click_count += 1
            self._title_last_click = current_time

            # Navigate to diagnostics on 5th click
            if self._title_click_count >= 5:
                self._title_click_count = 0
                self.app.navigate_to_diagnostics()

        page_title.onclick.do(on_title_click)
        container.append(page_title)
        return page_title

    def update_page_title_text(self):
        if hasattr(self, 'page_title_label'):
            new_title = self.app.page_titles.get(self.title_key, '')
            self.page_title_label.set_text(new_title)

    def add_label(self, container, text):
        label = gui.Label(text, style=Styles.default_label_style)
        container.append(label)
        return label

    def add_input(self, container, default_value='', input_type='text'):
        input_widget = gui.Input(input_type=input_type, style=Styles.default_input_style)
        input_widget.set_value(default_value)
        container.append(input_widget)
        return input_widget

    def add_labeled_input(self, container, label_text, default_value='', input_type='text'):
        self.add_label(container, label_text)
        return self.add_input(container, default_value, input_type)

    def add_button(self, container, text, onclick_handler):
        button = gui.Button(text, width=200, height=30, style=Styles.default_button_style)
        button.onclick.do(onclick_handler)
        container.append(button)
        return button

    def add_button_with_style(self, container, text, onclick_handler, style_type='primary'):
        """Create a button with specific style and hover effects"""
        # Select the appropriate style based on the type
        if style_type == 'primary':
            base_style = Styles.primary_button_style
            hover_style = Styles.primary_button_hover_style
        elif style_type == 'secondary':
            base_style = Styles.secondary_button_style
            hover_style = Styles.secondary_button_hover_style
        elif style_type == 'utility':
            base_style = Styles.utility_button_style
            hover_style = Styles.utility_button_hover_style
        elif style_type == 'warning':
            base_style = Styles.warning_button_style
            hover_style = Styles.warning_button_hover_style
        elif style_type == 'navigation':
            base_style = Styles.navigation_button_style
            hover_style = Styles.navigation_button_hover_style
        else:
            base_style = Styles.default_button_style
            hover_style = {}

        # Create button with the base style
        button = gui.Button(text, style=base_style)
        button.onclick.do(onclick_handler)
        
        # Add the button to the container
        container.append(button)
        
        # Add hover effects via JavaScript
        hover_js = """
        (function() {
            const btn = document.getElementById('%s');
            if (btn) {
                btn.addEventListener('mouseenter', function() {
                    %s
                });
                btn.addEventListener('mouseleave', function() {
                    %s
                });
            }
        })();
        """ % (
            button.identifier,
            ';'.join([f"btn.style.{k.replace('-', '')} = '{v}'" for k, v in hover_style.items()]),
            ';'.join([f"btn.style.{k.replace('-', '')} = '{v}'" for k, v in base_style.items() if k in hover_style])
        )
        
        self.app.execute_javascript(hover_js)
        
        return button

    def init_advanced_controls(self, container):
        self.advanced_button = self.add_button_with_style(container, "Advanced", self.toggle_advanced, 'utility')
        self.advanced_button.style.update({
            'position': 'fixed',
            'right': '20px',
            'bottom': '90px',
            'z-index': '2000',
            'opacity': '0.8',
            'max-width': '200px',
            'white-space': 'nowrap',
            'overflow': 'hidden',
            'text-overflow': 'ellipsis'
        })

        self.advanced_panel = self.build_advanced_panel()
        self.advanced_panel.style.update({
            'display': 'none',
            'position': 'fixed',
            'right': '20px',
            'bottom': '140px',
            'z-index': '2000',
            'width': '360px',
            'max-width': '90vw',
            'max-height': '60vh',
            'overflow-y': 'auto',
            'overflow-x': 'hidden',
            'box-sizing': 'border-box'
        })
        container.append(self.advanced_panel)

    def toggle_advanced(self, widget=None):
        visible = getattr(self, 'advanced_panel', None) and self.advanced_panel.style.get('display') != 'none'
        if getattr(self, 'advanced_panel', None):
            self.advanced_panel.style['display'] = 'none' if visible else 'block'
            self.app.refresh()

    def build_advanced_panel(self):
        panel = gui.VBox(width='60%', style={'margin': '10px', 'padding': '10px', 'border': '1px solid rgba(0,140,255,0.4)', 'background-color': 'rgba(0,20,40,0.4)'})
        title = gui.Label("Advanced Settings", style=Styles.section_header_style)
        panel.append(title)

        self.add_label(panel, "Network (e.g., 'Toonami', 'Cartoon Network'):")
        self.network_entry = self.add_input(panel, config.network)

        btns = gui.HBox(style={'justify-content': 'space-between', 'gap': '10px', 'background': 'transparent', 'flex-wrap': 'nowrap', 'width': '100%'})
        validate_btn = self.add_button_with_style(btns, "Validate", self.on_validate_network, 'secondary')
        apply_btn = self.add_button_with_style(btns, "Apply & Restart", self.on_apply_network, 'primary')
        reset_btn = self.add_button_with_style(btns, "Reset to Default", self.on_reset_network, 'utility')
        panel.append(btns)

        common_btn_style = {
            'clip-path': 'none',
            'border-radius': '6px',
            'padding': '8px 10px',
            'font-size': '14px',
            'width': 'calc((100% - 20px)/3)',
            'height': '60px',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'center',
            'text-align': 'center',
            'white-space': 'normal',
            'line-height': '1.2',
            'box-shadow': '0 0 10px rgba(0, 140, 255, 0.2)',
            'border': '1px solid rgba(0, 140, 255, 0.4)'
        }
        for b in (validate_btn, apply_btn, reset_btn):
            b.style.update(common_btn_style)

        hint = gui.Label("Note: A full restart is required for UI text and database to reflect the new network.", style={'font-size': '12px', 'opacity': '0.8', 'margin': '6px'})
        panel.append(hint)
        return panel

    def on_validate_network(self, widget):
        value = self.network_entry.get_value()
        name = value.strip() if isinstance(value, str) else ''
        if not name:
            self.update_status_display("Validation failed: empty network name")
            return
        ok = self.logic.validate_network(name)
        if ok:
            self.update_status_display(f"Network valid: {name}")
        else:
            self.update_status_display("Validation failed")

    def on_apply_network(self, widget):
        value = self.network_entry.get_value()
        name = value.strip() if isinstance(value, str) else ''
        if not name:
            self.update_status_display("Apply failed: empty network name")
            return
        if self.logic.apply_network(name):
            self.update_status_display("Network updated. Restarting...")
            def _restart():
                try:
                    time.sleep(0.5)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                except Exception as e:
                    self.update_status_display(f"Restart failed: {e}. Please restart manually.")
            threading.Thread(target=_restart, daemon=True).start()
        else:
            self.update_status_display("Failed to update network")

    def on_reset_network(self, widget):
        if self.logic.apply_network('Toonami'):
            self.update_status_display("Network reset to 'Toonami'. Restarting...")
            def _restart():
                try:
                    time.sleep(0.5)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                except Exception as e:
                    self.update_status_display(f"Restart failed: {e}. Please restart manually.")
            threading.Thread(target=_restart, daemon=True).start()
        else:
            self.update_status_display("Failed to reset network")

    def add_dropdown(self, container, options, onchange_handler=None):
        dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        for option in options:
            dropdown.append(gui.DropDownItem(option))
        if onchange_handler:
            dropdown.onchange.do(onchange_handler)
        container.append(dropdown)
        return dropdown

    def add_checkbox(self, container, label_text, default_value=False):
        hbox = gui.HBox(style={
            'align-items': 'center',
            'margin': '5px',
            **Styles.transparent_style
        })
        checkbox = gui.CheckBox(style=Styles.transparent_style)
        checkbox.set_value(default_value)
        label = gui.Label(label_text, style=Styles.default_label_style)
        hbox.append(checkbox)
        hbox.append(label)
        container.append(hbox)
        # keep a reference to the wrapper so callers can show/hide it
        checkbox.wrapper = hbox
        return checkbox

    def create_error_bar(self):
        """Create a stylized error bar to be added/removed from the main container"""
        # Base style common to all error levels
        base_style = {
            'width': '90%',
            'padding': '10px 20px',
            'border-radius': '5px',
            'margin': '10px auto',
            'display': 'none',
            'z-index': '1001',
            'transition': 'all 0.3s ease',
            'border-left': '4px solid',
            'border-right': '1px solid',
            'border-top': '1px solid',
            'border-bottom': '1px solid',
            'box-shadow': '0 2px 10px rgba(0,0,0,0.1)'
        }
        
        # Create the container with base style
        error_bar = gui.Container(style=base_style)
        
        # Create header container with buttons
        header_container = gui.HBox(style={
            'justify-content': 'space-between',
            'align-items': 'center',
            'margin-bottom': '5px',
            'background': 'transparent'
        })
        
        # Error messages label
        error_header = gui.Label("Error Messages:", style={
            'font-size': '14px',
            'font-weight': 'bold',
            'color': 'inherit',
            'margin': '0'
        })
        
        # Button container
        button_container = gui.HBox(style={
            'align-items': 'center',
            'background': 'transparent',
            'gap': '5px'
        })
        
        # History button
        self.history_button = gui.Button("📋", style={
            'width': '25px',
            'height': '25px',
            'font-size': '14px',
            'font-weight': 'bold',
            'padding': '0',
            'margin': '0',
            'border': '1px solid rgba(255,255,255,0.3)',
            'border-radius': '3px',
            'background': 'rgba(0,0,0,0.2)',
            'color': 'inherit',
            'cursor': 'pointer',
            'title': 'View Error History'
        })
        self.history_button.onclick.do(self.show_error_history)
        
        # Dismiss button
        self.dismiss_button = gui.Button("✕", style={
            'width': '25px',
            'height': '25px',
            'font-size': '16px',
            'font-weight': 'bold',
            'padding': '0',
            'margin': '0',
            'border': '1px solid rgba(255,255,255,0.3)',
            'border-radius': '3px',
            'background': 'rgba(0,0,0,0.2)',
            'color': 'inherit',
            'cursor': 'pointer'
        })
        self.dismiss_button.onclick.do(self.dismiss_error_bar)
        
        button_container.append(self.history_button)
        button_container.append(self.dismiss_button)
        
        header_container.append(error_header)
        header_container.append(button_container)
        
        # Create the label with base text style
        self.error_label = gui.Label("", style={
            'font-size': '16px',
            'font-weight': 'bold',
            'text-align': 'left',
            'white-space': 'pre-wrap',
            'margin': '0',
            'padding': '0'
        })
        
        # Add header and label to error bar
        error_bar.append(header_container)
        error_bar.append(self.error_label)
        
        # Store the error bar element for later style updates
        self.error_bar = error_bar
        self.error_bar_visible = False
        
        # Define styles for different error levels
        self.error_styles = {
            'CRITICAL': {
                'background-color': 'rgba(120, 20, 20, 0.95)',
                'border-color': '#ff0000',
                'box-shadow': '0 0 15px rgba(255, 0, 0, 0.4)',
                'color': '#ffffff',
                'text-shadow': '0 0 8px #ff0000'
            },
            'ERROR': {
                'background-color': 'rgba(60, 20, 20, 0.9)',
                'border-color': '#ff6b6b',
                'box-shadow': '0 0 15px rgba(255, 107, 107, 0.3)',
                'color': '#ff9e9e',
                'text-shadow': '0 0 5px #ff0000'
            },
            'WARNING': {
                'background-color': 'rgba(100, 80, 0, 0.9)',
                'border-color': '#ffcc00',
                'box-shadow': '0 0 15px rgba(255, 204, 0, 0.3)',
                'color': '#fff2a8',
                'text-shadow': '0 0 5px #ffcc00'
            },
            'INFO': {
                'background-color': 'rgba(0, 60, 100, 0.9)',
                'border-color': '#00aaff',
                'box-shadow': '0 0 15px rgba(0, 170, 255, 0.3)',
                'color': '#a5e2ff',
                'text-shadow': '0 0 5px #00aaff'
            },
            'DEFAULT': {
                'background-color': 'rgba(60, 60, 60, 0.9)',
                'border-color': '#cccccc',
                'box-shadow': '0 0 15px rgba(200, 200, 200, 0.3)',
                'color': '#ffffff',
                'text-shadow': '0 0 5px #ffffff'
            }
        }
        
        error_bar.append(self.error_label)
        return error_bar
    
    def dismiss_error_bar(self, widget):
        """Hide the error display and clear the message"""
        if hasattr(self, 'error_bar') and self.error_bar_visible:
            self.error_bar.style['display'] = 'none'
            self.error_bar_visible = False
            # Clear the error message so it doesn't reappear on page navigation
            self.error_label.set_text("")
            # Clear the error state in the LogicController
            if hasattr(self.app, 'logic') and self.app.logic is not None:
                self.app.logic.clear_error_messages()
    
    def show_error_bar(self):
        """Show the error display"""
        if hasattr(self, 'error_bar') and not self.error_bar_visible:
            self.error_bar.style['display'] = 'block'
            if not self.error_bar in self.main_container.children.values():
                # Insert error bar after the title but before other content
                self.main_container.append(self.error_bar)
            self.error_bar_visible = True

    def show_error_history(self, widget):
        """Show the error history modal"""
        try:
            # Get error history from LogicController
            if not hasattr(self.app, 'logic') or self.app.logic is None:
                self._show_error_dialog("No error history available", "Error history could not be retrieved.")
                return
            
            error_history = self.app.logic.get_error_history()
            error_summary = self.app.logic.get_error_summary()
            
            if not error_history:
                self._show_error_dialog("No Error History", "No errors have been recorded yet.")
                return
            
            # Create modal dialog
            self._create_error_history_modal(error_history, error_summary)
            
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to load error history: {str(e)}")
    
    def _create_error_history_modal(self, error_history, error_summary):
        """Create and display the error history modal dialog"""
        # Create modal overlay
        modal_overlay = gui.Container(style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'background-color': 'rgba(0, 0, 0, 0.7)',
            'z-index': '9999',
            'display': 'flex',
            'justify-content': 'center',
            'align-items': 'center'
        })
        
        # Create modal dialog
        modal_dialog = gui.Container(style={
            'width': '80%',
            'max-width': '900px',
            'height': '80%',
            'max-height': '700px',
            'background-color': 'rgba(0, 20, 40, 0.95)',
            'border': '2px solid rgba(0, 140, 255, 0.6)',
            'border-radius': '10px',
            'padding': '20px',
            'overflow': 'hidden',
            'display': 'flex',
            'flex-direction': 'column',
            'box-shadow': '0 0 20px rgba(0, 140, 255, 0.3)'
        })
        
        # Header
        header_container = gui.HBox(style={
            'justify-content': 'space-between',
            'align-items': 'center',
            'margin-bottom': '15px',
            'background': 'transparent'
        })
        
        title_label = gui.Label("Error History", style={
            'font-size': '24px',
            'font-weight': 'bold',
            'color': '#00ccff',
            'text-shadow': '0 0 5px rgba(0, 204, 255, 0.7)',
            'margin': '0'
        })
        
        close_button = gui.Button("✕", style={
            'width': '30px',
            'height': '30px',
            'font-size': '18px',
            'font-weight': 'bold',
            'padding': '0',
            'margin': '0',
            'border': '1px solid rgba(255,255,255,0.3)',
            'border-radius': '5px',
            'background': 'rgba(0,0,0,0.2)',
            'color': '#ffffff',
            'cursor': 'pointer'
        })
        close_button.onclick.do(lambda w: self._close_error_history_modal(modal_overlay))
        
        header_container.append(title_label)
        header_container.append(close_button)
        
        # Summary section
        summary_container = gui.Container(style={
            'background-color': 'rgba(0, 40, 80, 0.5)',
            'border': '1px solid rgba(0, 140, 255, 0.3)',
            'border-radius': '5px',
            'padding': '10px',
            'margin-bottom': '15px'
        })
        
        summary_text = []
        if error_summary:
            summary_text.append("Summary:")
            for level, count in error_summary.items():
                if count > 0:
                    summary_text.append(f"  {level}: {count}")
        else:
            summary_text.append("No error summary available")
            
        summary_label = gui.Label("\n".join(summary_text), style={
            'font-size': '14px',
            'color': '#a5f3fc',
            'white-space': 'pre',
            'margin': '0'
        })
        summary_container.append(summary_label)
        
        # Filter controls
        filter_container = gui.HBox(style={
            'margin-bottom': '15px',
            'align-items': 'center',
            'background': 'transparent',
            'gap': '10px'
        })
        
        filter_label = gui.Label("Filter by level:", style={
            'font-size': '14px',
            'color': '#a5f3fc',
            'margin': '0'
        })
        
        self.level_filter = gui.DropDown(style={
            'width': '120px',
            'background-color': 'rgba(0, 40, 80, 0.8)',
            'color': '#a5f3fc',
            'border': '1px solid rgba(0, 140, 255, 0.3)',
            'border-radius': '3px'
        })
        self.level_filter.append('ALL', 'All Levels')
        self.level_filter.append('CRITICAL', 'Critical')
        self.level_filter.append('ERROR', 'Error')
        self.level_filter.append('WARNING', 'Warning')
        self.level_filter.append('INFO', 'Info')
        
        # Try to select 'ALL' by default, but don't fail if it's not available yet
        try:
            self.level_filter.select_by_key('ALL')
        except (KeyError, AttributeError):
            pass  # Will default to first item
            
        self.level_filter.onchange.do(lambda w, k: self._filter_error_history(error_history))
        
        filter_container.append(filter_label)
        filter_container.append(self.level_filter)
        
        # Error list container (scrollable)
        self.error_list_container = gui.Container(style={
            'flex': '1',
            'overflow-y': 'auto',
            'border': '1px solid rgba(0, 140, 255, 0.3)',
            'border-radius': '5px',
            'padding': '10px',
            'background-color': 'rgba(0, 10, 20, 0.5)'
        })
        
        # Store error history for filtering
        self.current_error_history = error_history
        self._populate_error_list(error_history)
        
        # Assemble modal
        modal_dialog.append(header_container)
        modal_dialog.append(summary_container)
        modal_dialog.append(filter_container)
        modal_dialog.append(self.error_list_container)
        
        modal_overlay.append(modal_dialog)
        
        # Add to page
        self.append(modal_overlay)
        self.error_history_modal = modal_overlay
    
    def _populate_error_list(self, error_history):
        """Populate the error list with error entries"""
        # Clear existing content
        self.error_list_container.empty()
        
        if not error_history:
            no_errors_label = gui.Label("No errors found for the selected filter.", style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'text-align': 'center',
                'margin': '20px'
            })
            self.error_list_container.append(no_errors_label)
            return
        
        for i, error in enumerate(error_history):
            error_item = self._create_error_item(error, i)
            self.error_list_container.append(error_item)
    
    def _create_error_item(self, error, index):
        """Create a single error item widget"""
        # Get error details
        level = error.get('level', 'ERROR')
        source = error.get('source', 'Unknown')
        operation = error.get('operation', 'Unknown')
        message = error.get('message', 'No message')
        timestamp = error.get('timestamp', 'Unknown time')
        details = error.get('details', '')
        suggestion = error.get('suggestion', '')
        
        # Format timestamp
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = timestamp
        
        # Choose color based on level
        level_colors = {
            'CRITICAL': '#ff4444',
            'ERROR': '#ff6b6b',
            'WARNING': '#ffcc00',
            'INFO': '#00aaff',
            'DEFAULT': '#cccccc'
        }
        level_color = level_colors.get(level, level_colors['DEFAULT'])
        
        # Create error item container
        r, g, b = int(level_color[1:3], 16), int(level_color[3:5], 16), int(level_color[5:7], 16)
        error_container = gui.Container(style={
            'border': f'1px solid {level_color}',
            'border-radius': '5px',
            'margin': '5px 0',
            'padding': '10px',
            'background-color': f'rgba({r}, {g}, {b}, 0.1)'
        })
        
        # Header line with level, source, and timestamp
        header_text = f"[{level}] {source} - {formatted_time}"
        header_label = gui.Label(header_text, style={
            'font-size': '12px',
            'font-weight': 'bold',
            'color': level_color,
            'margin': '0 0 5px 0'
        })
        
        # Operation line
        if operation:
            operation_label = gui.Label(f"Operation: {operation}", style={
                'font-size': '11px',
                'color': '#a5f3fc',
                'margin': '0 0 5px 0',
                'font-style': 'italic'
            })
            error_container.append(operation_label)
        
        # Main message
        message_label = gui.Label(message, style={
            'font-size': '13px',
            'color': '#ffffff',
            'margin': '0 0 5px 0',
            'white-space': 'pre-wrap'
        })
        
        error_container.append(header_label)
        error_container.append(message_label)
        
        # Details if available
        if details:
            details_label = gui.Label(f"Details: {details}", style={
                'font-size': '11px',
                'color': '#cccccc',
                'margin': '5px 0',
                'white-space': 'pre-wrap',
                'font-style': 'italic'
            })
            error_container.append(details_label)
        
        # Suggestion if available
        if suggestion:
            suggestion_label = gui.Label(f"Suggestion: {suggestion}", style={
                'font-size': '11px',
                'color': '#00ff88',
                'margin': '5px 0',
                'white-space': 'pre-wrap',
                'font-weight': 'bold'
            })
            error_container.append(suggestion_label)
        
        return error_container
    
    def _filter_error_history(self, full_history):
        """Filter error history based on selected level"""
        selected_level = self.level_filter.get_value()
        
        if selected_level == 'ALL':
            filtered_history = full_history
        else:
            filtered_history = [error for error in full_history if error.get('level') == selected_level]
        
        self._populate_error_list(filtered_history)
    
    def _close_error_history_modal(self, modal_overlay):
        """Close the error history modal"""
        if hasattr(self, 'error_history_modal') and self.error_history_modal:
            try:
                self.remove_child(self.error_history_modal)
                self.error_history_modal = None
            except:
                pass
    
    def _show_error_dialog(self, title, message):
        """Show a simple error dialog"""
        dialog = gui.GenericDialog(title, message)

        # Optionally, you can add custom styles to the dialog
        dialog.style.update({
            'background-color': 'rgba(0, 20, 40, 0.9)',
            'border': '1px solid rgba(0, 140, 255, 0.6)',
            'border-radius': '8px',
            'padding': '15px',
            'color': '#ffffff',
            'font-family': 'Arial, sans-serif',
            'font-size': '14px',
            'text-shadow': '0 0 5px rgba(0, 204, 255, 0.7)'
        })

        # Style the buttons (access them through children.values())
        for child in dialog.children.values():
            if hasattr(child, 'style'):
                child.style.update({
                    'font-family': 'Rajdhani, sans-serif',
                    'font-size': '14px',
                    'font-weight': '500',
                    'color': '#a5f3fc',
                    'background': 'rgba(0, 140, 255, 0.4)',
                    'border': '1px solid rgba(0, 255, 255, 0.6)',
                    'border-radius': '4px',
                    'padding': '8px 16px',
                    'margin': '5px',
                    'cursor': 'pointer',
                    'transition': 'all 0.3s ease'
                })

        dialog.show(self.app)
        return dialog

    def _show_info_dialog(self, title, message):
        """Show a simple info dialog"""
        dialog = gui.GenericDialog(title, message)

        # Add custom styles to the dialog
        dialog.style.update({
            'background-color': 'rgba(0, 20, 40, 0.9)',
            'border': '1px solid rgba(0, 140, 255, 0.6)',
            'border-radius': '8px',
            'padding': '15px',
            'color': '#ffffff',
            'font-family': 'Arial, sans-serif',
            'font-size': '14px',
            'text-shadow': '0 0 5px rgba(0, 204, 255, 0.7)'
        })

        # Style the buttons (access them through children.values())
        for child in dialog.children.values():
            if hasattr(child, 'style'):
                child.style.update({
                    'font-family': 'Rajdhani, sans-serif',
                    'font-size': '14px',
                    'font-weight': '500',
                    'color': '#a5f3fc',
                    'background': 'rgba(0, 140, 255, 0.4)',
                    'border': '1px solid rgba(0, 255, 255, 0.6)',
                    'border-radius': '4px',
                    'padding': '8px 16px',
                    'margin': '5px',
                    'cursor': 'pointer',
                    'transition': 'all 0.3s ease'
                })

        dialog.show(self.app)
        return dialog

class NavigationBar(gui.Container):
    def __init__(self, app, current_page, *args, **kwargs):
        super(NavigationBar, self).__init__(*args, **kwargs)
        self.app = app
        self.current_page = current_page
        self.set_size('100%', 'auto')
        self.style.update({
            'display': 'flex',
            'flex-direction': 'row',
            'align-items': 'center',
            'justify-content': 'space-between',
            'padding': '10px 20px',
            'background-color': 'rgba(0, 20, 40, 0.7)',
            'border-bottom': '1px solid rgba(0, 140, 255, 0.4)',
            'margin-bottom': '20px',
        })
        
        # Left container for back button
        left_container = gui.HBox(style={
            'align-items': 'center',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        
        # Back button - using add_button instead of add_button_with_style
        self.back_button = self.add_button(left_container, "← Back", self.on_back_button_click)
        # Apply navigation style manually
        self.back_button.style.update(Styles.navigation_button_style)
        
        # Right container for home/start over button
        right_container = gui.HBox(style={
            'align-items': 'center',
            'background': 'transparent',
            'background-color': 'transparent'
        })

        # Home/Start Over button - using add_button instead of add_button_with_style
        self.home_button = self.add_button(right_container, "↻ Start Over", self.on_home_button_click)
        # Apply navigation style manually
        self.home_button.style.update(Styles.navigation_button_style)

        # Center container for progress indicators
        center_container = gui.HBox(style={
            'align-items': 'center',
            'justify-content': 'center',
            'flex-grow': '1',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        
        # Create page indicators
        self.create_page_indicators(center_container)
        
        # Add containers to navbar
        self.append(left_container)
        self.append(center_container)
        self.append(right_container)

        self.set_navigation_enabled(not getattr(self.app, 'navigation_locked', False))
    
    def create_page_indicators(self, container):
        sentinel = object()
        platform_type = getattr(self.app, 'current_platform_type', sentinel)
        if platform_type is sentinel and hasattr(self.app, 'logic'):
            platform_type = self.app.logic._get_data("platform_type") or None

        manual_visible = (
            platform_type not in (None, 'combreakdirect')
            and (self.current_page == 'Page3' or self.app.visited_manual_setup)
        )

        if platform_type == 'combreakdirect':
            # Page7 ("Additional Channels" / continuation) is omitted —
            # ComBreakDirect channels auto-extend forever via the
            # LineupExtender watchdog, so the manual continuation flow has
            # nothing to do.
            pages = [
                {'id': 'Page1', 'title': 'Choose Platform', 'optional': False, 'visual_num': 1},
                {'id': 'Page4', 'title': 'Content Prep', 'optional': False, 'visual_num': 2},
                {'id': 'Page5', 'title': 'Commercial Breaker', 'optional': False, 'visual_num': 3},
                {'id': 'Page6', 'title': 'Channel Creation', 'optional': False, 'visual_num': 4},
            ]
        elif platform_type is None:
            pages = [
                {'id': 'Page1', 'title': 'Choose Platform', 'optional': False, 'visual_num': 1},
            ]
        else:
            pages = [
                {'id': 'Page1', 'title': 'Choose Platform', 'optional': False, 'visual_num': 1},
                {'id': 'Page2', 'title': 'Login to Plex', 'optional': False, 'visual_num': 2},
            ]

            if manual_visible:
                pages.append({'id': 'Page3', 'title': 'Manual Setup', 'optional': True, 'visual_num': 2})

            pages.extend([
                {'id': 'Page4', 'title': 'Content Prep', 'optional': False, 'visual_num': 3},
                {'id': 'Page5', 'title': 'Commercial Breaker', 'optional': False, 'visual_num': 4},
                {'id': 'Page6', 'title': 'Channel Creation', 'optional': False, 'visual_num': 5},
                {'id': 'Page7', 'title': 'Additional Channels', 'optional': False, 'visual_num': 6},
            ])

        for i, page in enumerate(pages):
            is_current = (page['id'] == self.current_page)
            indicator_style = {
                'width': '12px',
                'height': '12px',
                'border-radius': '50%',
                'margin': '0 2px',
                'background-color': '#0ff' if is_current else 'rgba(0, 140, 255, 0.4)',
                'box-shadow': '0 0 8px rgba(0, 255, 255, 0.8)' if is_current else 'none',
                'cursor': 'pointer'
            }
            text_style = {
                'font-size': '14px',
                'color': '#0ff' if is_current else '#a5f3fc',
                'margin': '0 5px',
                'font-weight': 'bold' if is_current else 'normal',
                'text-shadow': '0 0 5px #00ccff' if is_current else 'none'
            }
            indicator_container = gui.HBox(style={
                'align-items': 'center',
                'margin': '0 8px',
                'background': 'transparent',
                'background-color': 'transparent'
            })
            dot = gui.Container(width=12, height=12, style=indicator_style)
            dot.attributes['page_id'] = page['id']
            dot.onclick.do(self.on_indicator_click)
            indicator_container.append(dot)

            label_text = f"{page['visual_num']} - {page['title']}"
            if page['optional']:
                label_text += " (Optional)"
            label = gui.Label(label_text, style=text_style)
            indicator_container.append(label)

            container.append(indicator_container)
            if i < len(pages) - 1:
                separator = gui.Container(width=15, height=1, style={
                    'background-color': 'rgba(0, 140, 255, 0.4)',
                    'margin': '0 2px'
                })
                container.append(separator)
    def on_back_button_click(self, widget):
        # Let the app handle the back navigation with its history tracking
        self.app.go_back()
    
    def on_home_button_click(self, widget):
        # Start over from Page1
        self.app.start_over()

    def on_diagnostics_button_click(self, widget):
        # Navigate to diagnostics page
        self.app.set_current_page('Page8')

    def on_indicator_click(self, widget):
        # Navigate to the clicked page
        if getattr(self.app, 'navigation_locked', False):
            return
        page_id = widget.attributes.get('page_id')
        if page_id:
            self.app.set_current_page(page_id)

    def set_navigation_enabled(self, enabled: bool) -> None:
        for button in (self.back_button, self.home_button):
            if button and hasattr(button, 'set_enabled'):
                button.set_enabled(enabled)
    
    # Add the add_button method to NavigationBar (similar to the one in BasePage)
    def add_button(self, container, text, onclick_handler):
        button = gui.Button(text, width=200, height=30, style=Styles.default_button_style)
        button.onclick.do(onclick_handler)
        container.append(button)
        return button

class Page1(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page1, self).__init__(app, 'Page1', *args, **kwargs)
        self.logic = LogicController()

        stored_platform = self.logic._get_data("platform_type") or 'dizquetv'
        stored_url = self.logic._get_data("platform_url")
        self.selected_platform = stored_platform

        helper_text = gui.Label(
            "Pick where Commercial Breaker should manage your channel before moving on to Plex setup.",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'text-align': 'center',
                'margin': '10px 0 20px 0',
                'background': 'transparent'
            }
        )
        self.main_container.append(helper_text)

        platform_buttons = gui.HBox(style={
            'justify-content': 'center',
            'gap': '20px',
            'margin': '10px 0',
            'background': 'transparent'
        })
        self.main_container.append(platform_buttons)

        self.dizquetv_button = gui.Button("DizqueTV", width=150, height=40, style=Styles.unselected_button_style)
        self.tunarr_button = gui.Button("Tunarr", width=150, height=40, style=Styles.unselected_button_style)
        self.cbdirect_button = gui.Button("ComBreakDirect", width=180, height=40, style=Styles.unselected_button_style)

        self.dizquetv_button.onclick.do(lambda w: self.on_platform_change('dizquetv'))
        self.tunarr_button.onclick.do(lambda w: self.on_platform_change('tunarr'))
        self.cbdirect_button.onclick.do(lambda w: self.on_platform_change('combreakdirect'))

        platform_buttons.append([self.dizquetv_button, self.tunarr_button, self.cbdirect_button])

        # ComBreakDirect controls (shown only when ComBreakDirect selected and not in Docker)
        self.cbd_controls_container = gui.VBox(style={
            'display': 'none',
            'align-items': 'center',
            'margin': '20px 0',
            'background': 'transparent'
        })
        self.main_container.append(self.cbd_controls_container)

        self.cbd_start_button = gui.Button("Start ComBreakDirect Server", width=250, height=40)
        self.cbd_start_button.style.update(Styles.default_button_style)
        self.cbd_start_button.onclick.do(self.start_combreakdirect)
        self.cbd_controls_container.append(self.cbd_start_button)

        self.cbd_info_label = gui.Label(
            "ComBreakDirect needs to stay running to stream your channel. Keep Absolution open in your browser.",
            style={
                'color': '#a5f3fc',
                'font-size': '14px',
                'margin': '10px 20px',
                'text-align': 'center',
                'background': 'transparent'
            }
        )
        self.cbd_controls_container.append(self.cbd_info_label)

        self.cbd_server_running = False

        self.platform_url_label = self.add_label(self.main_container, "Platform URL:")
        self.platform_url_entry = self.add_input(self.main_container, "e.g., http://localhost:17685")

        buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '25px',
            'background': 'transparent'
        })
        self.main_container.append(buttons_container)

        self.continue_button = self.add_button_with_style(buttons_container, "Continue", self.on_continue_button_click, 'primary')

        self.init_advanced_controls(self.main_container)

        self.on_platform_change(self.selected_platform)
        if stored_url and self.selected_platform not in ('combreakdirect', None):
            self.platform_url_entry.set_value(stored_url)

    def on_platform_change(self, platform):
        """Handle platform selection button clicks"""
        self.selected_platform = platform
        cbdirect_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        if platform == 'dizquetv':
            self.dizquetv_button.style.update(Styles.selected_button_style)
            self.tunarr_button.style.update(Styles.unselected_button_style)
            self.cbdirect_button.style.update(Styles.unselected_button_style)
            self._set_platform_url_visibility(True)
            self.platform_url_entry.attributes.pop('readonly', None)
            self.platform_url_entry.set_value("e.g., http://localhost:17685")
            # Hide ComBreakDirect controls
            self.cbd_controls_container.style['display'] = 'none'
        elif platform == 'tunarr':
            self.dizquetv_button.style.update(Styles.unselected_button_style)
            self.tunarr_button.style.update(Styles.selected_button_style)
            self.cbdirect_button.style.update(Styles.unselected_button_style)
            self._set_platform_url_visibility(True)
            self.platform_url_entry.attributes.pop('readonly', None)
            self.platform_url_entry.set_value("e.g., http://localhost:8000")
            # Hide ComBreakDirect controls
            self.cbd_controls_container.style['display'] = 'none'
        else:  # combreakdirect
            self.dizquetv_button.style.update(Styles.unselected_button_style)
            self.tunarr_button.style.update(Styles.unselected_button_style)
            self.cbdirect_button.style.update(Styles.selected_button_style)
            self._set_platform_url_visibility(False)
            self.platform_url_entry.set_value(cbdirect_url)
            self.platform_url_entry.attributes['readonly'] = 'true'
            # Show ComBreakDirect controls only if NOT in Docker
            from API.utils.FlagManager import FlagManager
            if not FlagManager.docker:
                self.cbd_controls_container.style['display'] = 'flex'
            else:
                self.cbd_controls_container.style['display'] = 'none'

    def start_combreakdirect(self, widget):
        """Start the ComBreakDirect server"""
        if self.cbd_server_running:
            return

        try:
            self.logic.start_combreakdirect_server()
            self.cbd_server_running = True
            self.cbd_start_button.set_text("✓ Server Running")
            self.cbd_start_button.attributes['disabled'] = 'true'

            base_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
            self.cbd_info_label.set_text(f"Server running at {base_url}. You can close this browser tab, but keep the Python terminal/process running to keep streaming.")
        except Exception as e:
            self.cbd_info_label.set_text(f"Error starting server: {str(e)}")
            self.cbd_info_label.style['color'] = '#ff6666'

    def _set_platform_url_visibility(self, visible: bool) -> None:
        display = 'block' if visible else 'none'
        self.platform_url_label.style['display'] = display
        self.platform_url_entry.style['display'] = display

    def on_continue_button_click(self, widget):
        if self.selected_platform == 'combreakdirect':
            platform_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        else:
            platform_url = self.platform_url_entry.get_value()

        self.logic._set_data("platform_type", self.selected_platform)
        self.logic._set_data("platform_url", platform_url)

        # Let the app know which platform is active so navigation can adjust
        if hasattr(self.app, 'update_platform_type'):
            self.app.update_platform_type(self.selected_platform)

        if self.selected_platform == 'combreakdirect':
            self.logic._broadcast_status_update("Idle")
            self.app.visited_manual_setup = False
            self.app.set_current_page('Page4')
        else:
            self.app.visited_manual_setup = False
            self.app.set_current_page('Page2')
class Page2(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page2, self).__init__(app, 'Page2', *args, **kwargs)
        self.logic = LogicController()

        # Define the JavaScript function for opening URLs early in initialization
        self.app.execute_javascript("""
            window.pywebview.api.open_plex_auth_url = function(url) {
                window.open(url, '_blank');
            }
        """)

        # Subscribe to updates using simplified interface
        self.logic.subscribe_to_status_updates(self.update_status_display)
        self.logic.subscribe_to_plex_servers(self.handle_plex_servers_update)
        self.logic.subscribe_to_plex_libraries(self.handle_plex_libraries_update)
        self.logic.subscribe_to_plex_auth_url(self.handle_plex_auth_url)
        self.logic.subscribe_to_server_choices(self.handle_new_server_choices)
        self.logic.subscribe_to_library_choices(self.handle_new_library_choices)

        # Track UI state
        self.libraries_selected = 0
        self.plex_servers = []
        self.plex_libraries = []

        stored_platform_type = self.logic._get_data("platform_type")
        self.selected_platform = stored_platform_type or 'dizquetv'
        stored_url = self.logic._get_data("platform_url")

        # Platform summary
        platform_names = {
            'dizquetv': 'DizqueTV',
            'tunarr': 'Tunarr',
            'combreakdirect': 'ComBreakDirect'
        }
        pretty_platform = platform_names.get(self.selected_platform, self.selected_platform.title())
        self.platform_summary_label = gui.Label(
            f"Platform: {pretty_platform}",
            style={
                'font-size': '16px',
                'color': '#a5f3fc',
                'margin': '0 0 10px 0',
                'background': 'transparent'
            }
        )
        self.main_container.append(self.platform_summary_label)

        # Platform URL summary (already captured in Step 1)
        default_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        summary_url = default_url if self.selected_platform == 'combreakdirect' else stored_url
        self.platform_url_summary = gui.Label(
            f"Platform URL: {summary_url}",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'margin': '0 0 15px 0',
                'background': 'transparent'
            }
        )
        self.main_container.append(self.platform_url_summary)

        # Build the Plex login workflow
        self.add_label(self.main_container, "Login with Plex")
        self.login_with_plex_button = self.add_button_with_style(self.main_container, "Login with Plex", self.login_to_plex, 'primary')

        self.add_label(self.main_container, "Select a Plex Server")
        self.plex_server_dropdown = self.add_dropdown(self.main_container, ["Choose a server"], self.on_server_selected)

        self.add_label(self.main_container, "Select your Anime Library")
        self.plex_anime_library_dropdown = self.add_dropdown(self.main_container, ["Choose a library"], self.add_1_to_libraries_selected)

        self.add_label(self.main_container, f"Select your {config.network} Library")
        self.plex_library_dropdown = self.add_dropdown(self.main_container, [f"Choose a {config.network} library"], self.add_1_to_libraries_selected)

        # Continue / Skip controls
        buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '20px',
            'background': 'transparent',
            'gap': '12px'
        })
        self.main_container.append(buttons_container)

        self.continue_button = self.add_button_with_style(buttons_container, "Continue", self.on_continue_button_click, 'secondary')
        self.continue_button.style['display'] = 'none'

        self.skip_button = self.add_button_with_style(buttons_container, "Skip", self.on_skip_button_click, 'secondary')
        if self.selected_platform == 'combreakdirect':
            self.skip_button.style['display'] = 'none'

        # Advanced settings moved to platform selection (Page1)

    def login_to_plex(self, widget):
        self.logic.login_to_plex()
        self.update_status_display("Logging into Plex...")

    def on_server_selected(self, widget, value):
        self.selected_server = self.plex_server_dropdown.get_value()
        if self._is_placeholder(self.selected_server):
            return
        self.logic.on_server_selected(self.selected_server)
        self.update_status_display(f"Fetching libraries from {self.selected_server}...")

    def add_1_to_libraries_selected(self, widget, value):
        self._update_continue_state()

    def show_continue_button(self):
        self.continue_button.style['display'] = 'block'
        if self.skip_button.style.get('display') != 'none':
            self.skip_button.style['display'] = 'none'

    def update_server_dropdown(self, server_list):
        placeholder_text = "Choose a server"
        self.plex_server_dropdown.empty()
        placeholder_item = gui.DropDownItem(placeholder_text)
        placeholder_item.attributes['data-placeholder'] = 'true'
        self.plex_server_dropdown.append(placeholder_item)
        self.plex_server_dropdown.set_value(placeholder_text)
        if server_list:
            for server in server_list:
                self.plex_server_dropdown.append(gui.DropDownItem(server))
        self._update_continue_state()

    def update_library_dropdowns(self, library_list):
        anime_placeholder_text = "Choose a library"
        toonami_placeholder_text = f"Choose a {config.network} library"
        self.plex_anime_library_dropdown.empty()
        self.plex_library_dropdown.empty()

        anime_placeholder = gui.DropDownItem(anime_placeholder_text)
        anime_placeholder.attributes['data-placeholder'] = 'true'
        self.plex_anime_library_dropdown.append(anime_placeholder)
        self.plex_anime_library_dropdown.set_value(anime_placeholder_text)

        toonami_placeholder = gui.DropDownItem(toonami_placeholder_text)
        toonami_placeholder.attributes['data-placeholder'] = 'true'
        self.plex_library_dropdown.append(toonami_placeholder)
        self.plex_library_dropdown.set_value(toonami_placeholder_text)

        if library_list:
            for library in library_list:
                self.plex_anime_library_dropdown.append(gui.DropDownItem(library))
                self.plex_library_dropdown.append(gui.DropDownItem(library))
            self.libraries_selected = 0
            self.update_status_display(f"Loaded {len(library_list)} libraries")
        self._update_continue_state()

    def on_continue_button_click(self, widget):
        selected_anime_library = self.plex_anime_library_dropdown.get_value()
        selected_toonami_library = self.plex_library_dropdown.get_value()
        if self.selected_platform == 'combreakdirect':
            platform_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        else:
            platform_url = self.logic._get_data("platform_url")

        self.logic._set_data("selected_anime_library", selected_anime_library)
        self.logic._set_data("selected_toonami_library", selected_toonami_library)
        self.logic._set_data("platform_url", platform_url)
        self.logic._set_data("platform_type", self.selected_platform)
        self.logic.check_dizquetv_compatibility()
        self.logic._broadcast_status_update("Idle")
        self.app.visited_manual_setup = False
        self.app.set_current_page('Page4')

    def refresh_platform_info(self):
        # Reload current platform data and update summary/controls
        stored_platform_type = self.logic._get_data("platform_type")
        self.selected_platform = stored_platform_type or 'dizquetv'
        stored_url = self.logic._get_data("platform_url")
        default_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        summary_url = default_url if self.selected_platform == 'combreakdirect' else stored_url
        platform_names = {
            'dizquetv': 'DizqueTV',
            'tunarr': 'Tunarr',
            'combreakdirect': 'ComBreakDirect'
        }
        pretty_platform = platform_names.get(self.selected_platform, self.selected_platform.title())
        self.platform_summary_label.set_text(f"Platform: {pretty_platform}")
        self.platform_url_summary.set_text(f"Platform URL: {summary_url}")

        if self.selected_platform == 'combreakdirect':
            self.skip_button.style['display'] = 'none'
        else:
            if self.continue_button.style.get('display') == 'none':
                self.skip_button.style['display'] = 'block'

    def handle_plex_auth_url(self, auth_url):
        self.app.execute_javascript(f"window.open('{auth_url}', '_blank')")

    def handle_new_server_choices(self, _):
        pass

    def handle_new_library_choices(self, _):
        pass

    def handle_plex_servers_update(self, server_list_json):
        try:
            server_list = json.loads(server_list_json)
            self.plex_servers = server_list
            self.update_server_dropdown(server_list)
        except Exception as e:
            print(f"Error processing server list: {e}")

    def handle_plex_libraries_update(self, library_list_json):
        try:
            library_list = json.loads(library_list_json)
            self.plex_libraries = library_list
            self.update_library_dropdowns(library_list)
        except Exception as e:
            print(f"Error processing library list: {e}")

    def update_dropdown(self, server_list):
        if hasattr(self, 'plex_server_dropdown'):
            first_item = self.plex_server_dropdown.children.get('0')
            self.plex_server_dropdown.empty()
            if first_item:
                self.plex_server_dropdown.append(first_item)
                self.plex_server_dropdown.set_value(first_item.get_text())
            if server_list:
                for server in server_list:
                    self.plex_server_dropdown.append(gui.DropDownItem(server))

    def on_skip_button_click(self, widget):
        self.app.visited_manual_setup = True
        self.app.set_current_page('Page3')

    @staticmethod
    def _is_placeholder(value: str | None) -> bool:
        return not value or value.lower().startswith('choose')

    def _update_continue_state(self) -> None:
        anime_value = self.plex_anime_library_dropdown.get_value()
        toonami_value = self.plex_library_dropdown.get_value()
        if not self._is_placeholder(anime_value) and not self._is_placeholder(toonami_value):
            self.show_continue_button()
        else:
            self.continue_button.style['display'] = 'none'
            if self.selected_platform != 'combreakdirect':
                self.skip_button.style['display'] = 'block'

class Page3(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page3, self).__init__(app, 'Page3', *args, **kwargs)
        self.logic = LogicController()
        self.selected_platform = self.logic._get_data("platform_type") or 'dizquetv'
        stored_url = self.logic._get_data("platform_url")

        # Plex connection details entered manually
        self.plex_url_entry = self.add_labeled_input(self.main_container, 'Plex URL:', "e.g., http://localhost:32400")
        self.plex_token_entry = self.add_labeled_input(self.main_container, 'Plex Token:', "e.g., xxxxxxxxxxxxxx")
        self.plex_anime_library_entry = self.add_labeled_input(self.main_container, 'Plex Anime Library:', "e.g., Anime")
        self.plex_toonami_library_entry = self.add_labeled_input(self.main_container, f'Plex {config.network} Library:', f"e.g., {config.network}")

        # Platform URL summary (captured in Step 1)
        default_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        summary_url = default_url if self.selected_platform == 'combreakdirect' else stored_url
        self.platform_url_summary = gui.Label(
            f"Platform URL: {summary_url}",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'margin': '0 0 15px 0',
                'background': 'transparent'
            }
        )
        self.main_container.append(self.platform_url_summary)

        # Continue button
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')

    def on_continue_button_click(self, widget):
        self.logic = LogicController()
        plex_url = self.plex_url_entry.get_value()
        plex_token = self.plex_token_entry.get_value()
        plex_anime_library = self.plex_anime_library_entry.get_value()
        plex_toonami_library = self.plex_toonami_library_entry.get_value()
        platform_type = self.selected_platform
        if platform_type == 'combreakdirect':
            platform_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        else:
            platform_url = self.logic._get_data("platform_url")
        self.logic.on_continue_second(plex_url, plex_token, plex_anime_library, plex_toonami_library, platform_url, platform_type)
        self.app.visited_manual_setup = True
        self.app.set_current_page('Page4')

    def refresh_platform_info(self):
        self.selected_platform = self.logic._get_data("platform_type") or 'dizquetv'
        stored_url = self.logic._get_data("platform_url")
        default_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
        summary_url = default_url if self.selected_platform == 'combreakdirect' else stored_url
        self.platform_url_summary.set_text(f"Platform URL: {summary_url}")

        # Preload Plex URL
        stored_plex_url = self.logic._get_data("plex_url")
        if stored_plex_url and not stored_plex_url.startswith("e.g."):
            self.plex_url_entry.set_value(stored_plex_url)

        # Preload Plex Token
        stored_plex_token = self.logic._get_data("plex_token")
        if stored_plex_token and not stored_plex_token.startswith("e.g."):
            self.plex_token_entry.set_value(stored_plex_token)

        # Preload Anime Library
        stored_anime_library = self.logic._get_data("selected_anime_library")
        if stored_anime_library and not stored_anime_library.startswith("e.g."):
            self.plex_anime_library_entry.set_value(stored_anime_library)

        # Preload Toonami Library
        stored_toonami_library = self.logic._get_data("selected_toonami_library")
        if stored_toonami_library and not stored_toonami_library.startswith("e.g."):
            self.plex_toonami_library_entry.set_value(stored_toonami_library)
class Page4(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page4, self).__init__(app, 'Page4', *args, **kwargs)
        self.logic = LogicController()
        self.ToonamiChecker = ToonamiTools.ToonamiChecker
        
        # Subscribe to updates using simplified interface
        self.logic.subscribe_to_status_updates(self.update_status_display)
        self.logic.subscribe_to_filtered_files(self.handle_filtered_files_update)
        self.logic.subscribe_to_plex_servers(self.handle_plex_servers_update)
        self.logic.subscribe_to_plex_libraries(self.handle_plex_libraries_update)
        
        # Track filter mode selection
        self.filter_mode = "move_files"  # Default to legacy mode

        # Prepare Content button
        self.add_label(self.main_container, "Prepare my shows and bumps to be cut")
        self.prepare_button = self.add_button_with_style(self.main_container, "Prepare Content", self.prepare_content, 'primary')

        # Get Plex Timestamps button
        self.get_plex_timestamps_label = self.add_label(self.main_container, "Get Plex Timestamps")
        self.get_plex_timestamps_button = self.add_button_with_style(self.main_container, "Get Plex Timestamps", self.get_plex_timestamps, 'primary')

        # Move Filtered Shows section with centered radio buttons
        self.process_filtered_shows_label = self.add_label(self.main_container, "Process Filtered Shows")
        
        # Create a container for the radio buttons with centered layout
        self.filter_mode_container = gui.Container(style={
            'width': '100%',
            'display': 'flex',
            'justify-content': 'center',
            'margin': '10px 0',
            'background': 'transparent'
        })
        
        # Create a horizontally centered container for buttons
        buttons_row = gui.HBox(style={
            'justify-content': 'center',
            'background': 'transparent',
            'width': 'auto',
            'margin': '0 auto'
        })
        
        # Create styled button-like options for filter mode selection
        self.move_files_button = gui.Button("Move Files (Legacy)", width=200, height=40)
        self.move_files_button.style.update(Styles.selected_button_style)
        self.move_files_button.onclick.do(lambda w: self.set_filter_mode("move_files"))
        
        self.prepopulate_button = gui.Button("Prepopulate Selection", width=200, height=40)
        self.prepopulate_button.style.update(Styles.unselected_button_style)
        self.prepopulate_button.onclick.do(lambda w: self.set_filter_mode("prepopulate"))
        
        # Add buttons to the row container with spacing
        buttons_row.append(self.move_files_button)
        buttons_row.append(gui.Label("", style={'width': '20px', 'background': 'transparent'}))  # Spacer
        buttons_row.append(self.prepopulate_button)
        
        # Add row to the container
        self.filter_mode_container.append(buttons_row)
        self.main_container.append(self.filter_mode_container)
        
        # Process Filtered Shows button
        self.process_button_container = gui.Container(style={
            'width': '100%',
            'display': 'flex',
            'justify-content': 'center', 
            'margin': '10px 0',
            'background': 'transparent'
        })
        
        self.move_filtered_shows_button = self.add_button_with_style(self.process_button_container, "Process Filtered Shows", self.move_filtered, 'primary')
        self.main_container.append(self.process_button_container)

        # Continue button
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')
        self.refresh_platform_type()
    
    def set_filter_mode(self, mode):
        """Handle filter mode selection button clicks"""
        self.filter_mode = mode
        if mode == 'move_files':
            self.move_files_button.style.update(Styles.selected_button_style)
            self.prepopulate_button.style.update(Styles.unselected_button_style)
        else:
            self.move_files_button.style.update(Styles.unselected_button_style)
            self.prepopulate_button.style.update(Styles.selected_button_style)

    def get_plex_timestamps(self, widget):
        self.logic.get_plex_timestamps()

    def move_filtered(self, widget):
        # Pass the filter mode to the move_filtered method
        self.logic.move_filtered(self.filter_mode == "prepopulate")

    def on_continue_button_click(self, widget):
        self.logic.on_continue_fourth()
        self.app.set_current_page('Page5')

    def refresh_platform_type(self):
        platform_type = self.logic._get_data("platform_type")
        is_cutless_active = FlagManager.cutless
        display = 'block' if platform_type != 'combreakdirect' else 'none'
        self.get_plex_timestamps_label.style['display'] = display
        self.get_plex_timestamps_button.style['display'] = display

        # Hide Move Files option for ComBreakDirect or when cutless mode is active
        if platform_type == 'combreakdirect' or is_cutless_active:
            self.filter_mode = "prepopulate"
            if hasattr(self, 'prepopulate_button'):
                self.set_filter_mode("prepopulate")
            if hasattr(self, 'process_filtered_shows_label'):
                self.process_filtered_shows_label.style['display'] = 'none'
            if hasattr(self, 'filter_mode_container'):
                self.filter_mode_container.style['display'] = 'none'
            if hasattr(self, 'process_button_container'):
                self.process_button_container.style['display'] = 'none'
        else:
            if hasattr(self, 'process_filtered_shows_label'):
                self.process_filtered_shows_label.style['display'] = 'block'
            if hasattr(self, 'filter_mode_container'):
                self.filter_mode_container.style['display'] = 'flex'
            if hasattr(self, 'process_button_container'):
                self.process_button_container.style['display'] = 'flex'

    def prepare_content(self, widget):
        """Kick off ToonamiChecker + FolderMaker work without freezing the WebUI."""
        if not hasattr(self, 'logic') or self.logic is None:
            self.logic = LogicController()

        # Prevent duplicate scans if user double-clicks
        running_thread = getattr(self, '_prepare_content_thread', None)
        if running_thread and running_thread.is_alive():
            self.logic._broadcast_status_update("Already preparing content. Please wait...")
            return

        self.logic._broadcast_status_update("Preparing bumps...")

        if hasattr(self, 'prepare_button'):
            self.prepare_button.set_enabled(False)

        def run_prepare_work():
            self.logic._set_operation_state(True, "prepare_content")
            try:
                working_folder = self.logic._get_data("working_folder")
                anime_folder = self.logic._get_data("anime_folder")
                fmaker = ToonamiTools.FolderMaker(working_folder)
                easy_checker = self.ToonamiChecker(
                    anime_folder,
                    status_callback=self.logic._broadcast_status_update
                )

                fmaker.run()

                for i in range(25):
                    try:
                        unique_show_names, toonami_episodes = easy_checker.prepare_episode_data()
                        self.display_show_selection(unique_show_names, easy_checker, toonami_episodes)
                        self.logic._broadcast_status_update("Waiting for show selection...")
                        break
                    except Exception as e:
                        print(e)
                        time.sleep(2)
                else:
                    raise RuntimeError("Failed to run easy_checker")
            except Exception as exc:
                print(exc)
                self.logic._broadcast_status_update(f"Prepare content failed: {exc}")
            finally:
                self.logic._set_operation_state(False, "prepare_content")
                if hasattr(self, 'prepare_button'):
                    self.prepare_button.set_enabled(True)

        self._prepare_content_thread = threading.Thread(target=run_prepare_work, daemon=True)
        self._prepare_content_thread.start()

    def prepare_content_continue(self):
        self.logic = LogicController()
        self.logic._set_operation_state(True, "prepare_content_continue")
        # Remove container from UI
        self.main_container.remove_child(self.selection_container)
        
        # Update status to let user know we're processing
        self.logic._broadcast_status_update("Preparing uncut lineup...")
        
        # Force UI refresh using JavaScript
        self.app.execute_javascript("""
            setTimeout(function() {
                // Force browser reflow to update UI immediately
                document.body.style.display='none';
                document.body.offsetHeight; // Trigger reflow
                document.body.style.display='';
            }, 10);
        """)
        
        # Run the rest of the processing in a separate thread
        threading.Thread(target=self._run_prepare_content_processing).start()
    
    def _run_prepare_content_processing(self):
        """Runs the content preparation processing in a separate thread"""
        # Define all possible merger configurations
        merger_configs = [
            {'input': 'multibumps_v2_data_reordered', 'output': 'lineup_v2_uncut'},
            {'input': 'multibumps_v3_data_reordered', 'output': 'lineup_v3_uncut'},
            {'input': 'multibumps_v8_data_reordered', 'output': 'lineup_v8_uncut'},
            {'input': 'multibumps_v9_data_reordered', 'output': 'lineup_v9_uncut'},
        ]

        try:
            uncut_encoder_out = 'uncut_encoded_data'
            bump_folder = self.logic._get_data("bump_folder")
            lineup_prep = ToonamiTools.MediaProcessor(bump_folder)
            easy_encoder = ToonamiTools.ToonamiEncoder()
            uncutencoder = ToonamiTools.UncutEncoder()
            ml = ToonamiTools.Multilineup()
            merger = ToonamiTools.ShowScheduler(uncut=True)

            lineup_prep.run()
            easy_encoder.encode_and_save()
            ml.reorder_all_tables()
            uncutencoder.run()

            # Check which reordered tables actually exist and run merger only for those
            self.logic._broadcast_status_update("Creating lineups for available versions...")
            versions_processed = 0

            for config in merger_configs:
                if self.logic._check_table_exists(config['input']):
                    self.logic._broadcast_status_update(f"Processing {config['input']}...")
                    merger.run(config['input'], uncut_encoder_out, config['output'])
                    versions_processed += 1
                else:
                    print(f"Skipping {config['input']} - table does not exist")

            if versions_processed == 0:
                error_msg = "ERROR: No multibump reordered tables found. Please add multi-show bumps and try again."
                self.logic._broadcast_status_update(error_msg)
                print("No multibump tables available for lineup creation")
            else:
                # Update status when complete with version count
                self.logic._broadcast_status_update(f"Content preparation complete! Created {versions_processed} lineup versions.")
        finally:
            self.logic._set_operation_state(False, "prepare_content_continue")

    def display_show_selection(self, unique_show_names, easy_checker, toonami_episodes):
        # Sort the list alphabetically (case-insensitive)
        unique_show_names_sorted = sorted(unique_show_names, key=lambda s: s.lower())

        # Create a container for the selection UI
        self.selection_container = gui.VBox(style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin-top': '20px',
            'width': '100%',
            'background': 'transparent',
            'height': '400px',  # Fixed height to enable proper scrolling
            'overflow': 'auto'  # Enable scrolling
        })
        
        # Create a scrollable container for checkboxes
        checkbox_container = gui.VBox(style={
            'align-items': 'flex-start', 
            'justify-content': 'flex-start',
            'width': '90%',
            'padding': '10px',
            'background': 'rgba(0, 10, 30, 0.5)',
            'border': '1px solid rgba(0, 140, 255, 0.3)',
            'border-radius': '5px',
            'max-height': '300px',  # Set max height for scrolling
            'overflow-y': 'auto'    # Enable vertical scrolling
        })
        
        self.checkboxes = {}
        
        # Add a header
        header = gui.Label("Select shows to include in your lineup:", style={
            'font-size': '18px',
            'font-weight': 'bold',
            'color': '#a5f3fc',
            'margin': '10px 0',
            'text-align': 'center'
        })
        self.selection_container.append(header)
        
        # Add helper text
        helper_text = gui.Label("All shows are selected by default. Uncheck any shows you want to exclude.", style={
            'font-size': '14px',
            'color': '#a5f3fc',
            'margin-bottom': '15px',
            'text-align': 'center'
        })
        self.selection_container.append(helper_text)

        # Add checkboxes in groups for better organization
        for show in unique_show_names_sorted:
            checkbox = gui.CheckBox(checked=True, style={
                'margin-right': '10px',
                'background': 'transparent'
            })
            
            checkbox_label = gui.Label(show, style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'text-align': 'left',
                'margin': '2px 0'
            })
            
            self.checkboxes[show] = checkbox
            
            hbox = gui.HBox(style={
                'align-items': 'center',
                'justify-content': 'flex-start',
                'width': '100%',
                'padding': '3px 5px',
                'margin': '2px 0',
                'background': 'transparent'
            })
            
            hbox.append(checkbox)
            hbox.append(checkbox_label)
            checkbox_container.append(hbox)
        
        self.selection_container.append(checkbox_container)
        
        # Add buttons below the checkbox container
        buttons_container = gui.HBox(style={
            'justify-content': 'space-between',
            'width': '90%',
            'margin-top': '15px',
            'background': 'transparent'
        })
        
        # Select/Deselect all buttons
        select_all_button = self.add_button_with_style(buttons_container, "Select All", lambda w: self.toggle_all_checkboxes(True), 'secondary')
        
        deselect_all_button = self.add_button_with_style(buttons_container, "Deselect All", lambda w: self.toggle_all_checkboxes(False), 'secondary')
        
        done_button = self.add_button_with_style(buttons_container, "Done", lambda w: self.on_done_button_clicked(w, easy_checker, toonami_episodes), 'primary')
        
        buttons_container.append(select_all_button)
        buttons_container.append(deselect_all_button)
        buttons_container.append(done_button)
        
        self.selection_container.append(buttons_container)
        self.main_container.append(self.selection_container)
        
        print("Show selection displayed")

    def on_done_button_clicked(self, widget, easy_checker, toonami_episodes):
        selected_shows = [show for show, checkbox in self.checkboxes.items() if checkbox.get_value()]
        for i in range(25):
            try:
                easy_checker.process_selected_shows(selected_shows, toonami_episodes)
                break
            except Exception as e:
                print(e)
                time.sleep(2)
        self.prepare_content_continue()

    def handle_filtered_files_update(self, filtered_files):
        """Handle filtered files list update"""
        try:
            if filtered_files:
                file_count = len(filtered_files)
                self.update_status_display(f"Received {file_count} filtered files")
        except Exception as e:
            print(f"Error processing filtered files: {e}")
            
    def handle_plex_servers_update(self, server_list):
        """Handle Plex servers list update"""
        try:
            print(f"Received server list with {len(server_list)} items")
            
            # Store server list for reference
            self.plex_servers = server_list
            
            # Update server dropdown
            self.update_server_dropdown(server_list)
        except Exception as e:
            print(f"Error processing server list: {e}")
            
    def handle_plex_libraries_update(self, library_list):
        """Handle Plex libraries list update"""
        try:
            print(f"Received library list with {len(library_list)} items")
            
            # Store library list for reference
            self.plex_libraries = library_list
            
            # Update library dropdowns
            self.update_library_dropdowns(library_list)
            
            # Update status
            self.update_status_display(f"Loaded {len(library_list)} libraries")
        except Exception as e:
            print(f"Error processing library list: {e}")

    def update_server_dropdown(self, server_list):
        """Update the server dropdown with the provided list of servers"""
        # Check if dropdown exists to avoid attribute errors
        if hasattr(self, 'plex_server_dropdown'):
            # Clear existing items except for the first instruction item
            first_item = self.plex_server_dropdown.children.get('0')
            self.plex_server_dropdown.empty()
            if first_item:
                self.plex_server_dropdown.append(first_item)
            
            # Add all servers from the provided list
            if server_list:
                for server in server_list:
                    self.plex_server_dropdown.append(gui.DropDownItem(server))
                print(f"Updated server dropdown with {len(server_list)} servers")

    def toggle_all_checkboxes(self, state):
        for checkbox in self.checkboxes.values():
            checkbox.set_value(state)

class Page5(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page5, self).__init__(app, 'Page5', *args, **kwargs)
        self.cblogic = CommercialBreakerLogic()
        self.logic = LogicController()
        
        if LogicController.cutless:
            self.cutless = True
        else:
            self.cutless = False
            
        # Subscribe to updates using simplified interface
        self.logic.subscribe_to_status_updates(self.update_status_display)
        self.logic.subscribe_to_filtered_files(self.handle_filtered_files_update)
        self.logic.subscribe_to_cutless_state(self.handle_cutless_state_update)

        # Initialize the working folder and default directories
        self.working_folder = self.logic._get_data("working_folder")
        self.default_input_folder = f"{self.working_folder}/toonami_filtered"
        self.default_output_folder = f"{self.working_folder}/cut"

        # Create variables for input and output directories with defaults
        self.input_path = self.default_input_folder
        self.output_path = self.default_output_folder
        
        # Internal tracking of input mode - no UI controls needed
        self.input_mode = "folder"  # Default to folder mode
        
        # File path mapping for display/selection
        self.file_path_map = {}

        # === FOLDER MODE UI ===
        self.folder_mode_container = gui.VBox(style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'width': '100%',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        
        # Initialize input field with default value pre-filled
        self.input_path_input = self.add_labeled_input(self.folder_mode_container, "Input directory:", self.default_input_folder)
        self.main_container.append(self.folder_mode_container)
        
        # === FILE MODE UI === - Initially hidden but will be shown when files are received
        self.file_mode_container = gui.VBox(style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'width': '100%',
            'background': 'transparent',
            'background-color': 'transparent',
            'display': 'none'  # Initially hidden
        })
        
        # File selection UI
        file_list_label = gui.Label("Selected Files:", style=Styles.default_label_style)
        self.file_mode_container.append(file_list_label)
        
        # Create a container for the file listbox
        file_list_container = gui.Container(style={
            'width': '90%',
            'height': '200px',
            'margin': '10px',
            'padding': '5px',
            'border': '1px solid rgba(0, 140, 255, 0.4)',
            'background-color': 'rgba(0, 20, 40, 0.5)',
            'overflow': 'auto',
            'display': 'flex',
            'flex-direction': 'column'
        })
        
        # Create a list widget for selected files
        self.file_listbox = gui.ListView(style={
            'width': '100%',
            'height': '100%',
            'background-color': 'rgba(0, 10, 30, 0.8)',
            'color': '#a5f3fc',
            'border': 'none'
        })
        
        file_list_container.append(self.file_listbox)
        self.file_mode_container.append(file_list_container)
        self.main_container.append(self.file_mode_container)
        
        # Output path (common to both modes)
        self.output_path_input = self.add_labeled_input(self.main_container, "Output directory:", self.default_output_folder)

        # Initialize progress bar
        self.progress_value = 0

        # Create variables for checkboxes
        self.destructive_mode = False
        self.fast_mode = False
        self.low_power_mode = False

        # Page title
        self.add_label(self.main_container, "Commercial Breaker")

        # Checkbox container
        checkbox_container = gui.HBox(style={
            'justify-content': 'flex-start',
            'margin': '10px',
            **Styles.transparent_style
        })

        # Destructive Mode checkbox
        self.destructive_checkbox = self.add_checkbox(checkbox_container, 'Destructive Mode', False)
        self.destructive_checkbox.onchange.do(self.on_destructive_mode_changed)

        # Fast Mode checkbox
        self.fast_checkbox = self.add_checkbox(checkbox_container, 'Fast Mode', False)
        self.fast_checkbox.onchange.do(self.on_fast_mode_changed)

        # Low Power Mode checkbox
        self.low_power_checkbox = self.add_checkbox(checkbox_container, 'Low Power Mode', False)
        self.low_power_checkbox.onchange.do(self.on_low_power_mode_changed)
        
        # Cutless Mode checkbox  (always create – show/hide dynamically)
        self.cutless_checkbox = self.add_checkbox(checkbox_container, 'Cutless Mode', False)
        # wrapper HBox saved by add_checkbox
        self.cutless_container = self.cutless_checkbox.wrapper
        if not self.cutless:
            self.cutless_container.style['display'] = 'none'
        self.cutless_checkbox.onchange.do(self.on_cutless_mode_changed)

        self.cutless_required_label = gui.Label("Cutless Mode (Required)", style={
            **Styles.default_label_style,
            'margin': '5px 10px',
            'display': 'none'
        })
        checkbox_container.append(self.cutless_required_label)
        self.cutless_checkbox.set_value(self.cutless)
        self.cutless_mode = self.cutless_checkbox.get_value()

        self.main_container.append(checkbox_container)

        # Progress bar container with updated styling
        progress_container = gui.VBox(style={
            'align-items': 'center',
            'margin-top': '20px',
            'width': '100%',
            'background': 'transparent',
            'background-color': 'transparent'
        })

        progress_label = gui.Label("Progress:", style=Styles.default_label_style)
        progress_container.append(progress_label)

        # Create a custom styled progress container instead of the default progress bar
        self.progress_container = gui.Container(style=Styles.progress_container_style)
        
        # Create the progress fill element
        self.progress_fill = gui.Container(style=Styles.progress_fill_style)
        
        # Create percentage text element
        self.progress_text = gui.Label("0%", style=Styles.progress_text_style)
        
        self.progress_container.append(self.progress_fill)
        self.progress_container.append(self.progress_text)
        progress_container.append(self.progress_container)

        self.main_container.append(progress_container)

        # Action buttons
        self.buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '20px',
            'background': 'transparent',
            'background-color': 'transparent'
        })

        self.detect_button = self.add_button_with_style(self.buttons_container, "Detect", self.detect_commercials, 'primary')
        self.cut_button = self.add_button_with_style(self.buttons_container, "Cut", self.cut_videos, 'primary')
        self.create_cutless_button = self.add_button_with_style(self.buttons_container, "Create Cutless Data", self.create_cutless_data, 'primary')
        self.create_cutless_button.style['display'] = 'none'
        self.delete_button = self.add_button_with_style(self.buttons_container, "Delete", self.delete_txt_files, 'primary')

        self.main_container.append(self.buttons_container)
        self.update_action_buttons()
        self.apply_platform_constraints()

        # Continue button to go to the next page
        self.next_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')
        
        # Add custom progress bar animation CSS
        self.app.execute_javascript("""
        if (!document.getElementById('progress-animation-css')) {
            var style = document.createElement('style');
            style.id = 'progress-animation-css';
            style.innerHTML = `
                @keyframes progressGlow {
                    0% { box-shadow: 0 0 10px rgba(0, 255, 255, 0.4); }
                    50% { box-shadow: 0 0 20px rgba(0, 255, 255, 0.8); }
                    100% { box-shadow: 0 0 10px rgba(0, 255, 255, 0.4); }
                }
                
                @keyframes textGlow {
                    0% { text-shadow: 0 0 5px rgba(0, 255, 255, 0.6); }
                    50% { text-shadow: 0 0 10px rgba(0, 255, 255, 1); }
                    100% { text-shadow: 0 0 5px rgba(0, 255, 255, 0.6); }
                }
            `;
            document.head.appendChild(style);
        }
        """)
    
    def set_input_mode(self, mode):
        """Switch between folder mode and file selection mode without UI changes"""
        if self.logic._get_data("platform_type") == 'combreakdirect':
            mode = 'file'
        self.input_mode = mode
        
        if mode == 'folder':
            self.folder_mode_container.style['display'] = 'flex'
            self.file_mode_container.style['display'] = 'none'
            
            # Reset the input handler to use folder mode
            self.cblogic.input_handler.clear_all()
        else:  # file mode
            self.folder_mode_container.style['display'] = 'none'
            self.file_mode_container.style['display'] = 'flex'

    def update_action_buttons(self):
        """Toggle between legacy buttons and cutless pipeline."""
        if not hasattr(self, 'detect_button'):
            return
        if self.cutless_mode:
            self.detect_button.style['display'] = 'none'
            self.cut_button.style['display'] = 'none'
            self.create_cutless_button.style['display'] = 'inline-block'
        else:
            self.detect_button.style['display'] = 'inline-block'
            self.cut_button.style['display'] = 'inline-block'
            self.create_cutless_button.style['display'] = 'none'

    def create_cutless_data(self, widget):
        """Run detection and virtual cut generation sequentially."""
        if not self.validate_input_output_dirs():
            return

        # Ensure destructive mode is disabled
        if self.destructive_mode:
            self.destructive_checkbox.set_value(False)
            self.destructive_mode = False

        if not self.cutless_mode:
            self.cutless_checkbox.set_value(True)
            self.cutless_mode = True

        def pipeline():
            noop = lambda *_: None
            self.create_cutless_button.set_enabled(False)
            try:
                self._run_and_notify(
                    self.cblogic.detect_commercials,
                    noop,
                    "Detect Black Frames",
                    False,
                    False,
                    self.low_power_mode,
                    self.fast_mode,
                    self.reset_progress_bar
                )
                self._run_and_notify(
                    self.cblogic.cut_videos,
                    noop,
                    "Cut Video",
                    False,
                    True
                )
                self.update_status("Cutless data ready!")
            finally:
                self.create_cutless_button.set_enabled(True)

        threading.Thread(target=pipeline, daemon=True).start()

    def is_combreakdirect(self):
        return self.logic._get_data("platform_type") == 'combreakdirect'

    def apply_platform_constraints(self):
        """Adjust UI based on the selected platform."""
        is_cbdirect = self.is_combreakdirect()

        if is_cbdirect:
            self.set_input_mode('file')
            self.folder_mode_container.style['display'] = 'none'
            self.file_mode_container.style['display'] = 'flex'
            self.destructive_checkbox.wrapper.style['display'] = 'none'
            if self.destructive_checkbox.get_value():
                self.destructive_checkbox.set_value(False)
            self.destructive_mode = False
            self.cutless_container.style['display'] = 'none'
            self.cutless_required_label.style['display'] = 'inline-block'
            self.cutless = True
            if not self.cutless_mode:
                self.cutless_checkbox.set_value(True)
                self.cutless_mode = True
            self.update_action_buttons()
        else:
            self.folder_mode_container.style['display'] = 'flex'
            self.destructive_checkbox.wrapper.style['display'] = 'flex'
            self.cutless_required_label.style['display'] = 'none'
            if self.cutless:
                self.cutless_container.style['display'] = 'flex'
            else:
                self.cutless_container.style['display'] = 'none'
            self.update_action_buttons()

    def update_file_list(self):
        """Update the file list display with paths from the input handler"""
        # Clear existing items
        self.file_listbox.empty()
        self.file_path_map = {}
        
        # Get consolidated paths
        paths = self.cblogic.input_handler.get_consolidated_paths()
        
        # Sort alphabetically by filename
        paths.sort(key=lambda p: os.path.basename(p).lower())
        
        # Add each file to the listbox
        for path in paths:
            filename = os.path.basename(path)
            # Handle duplicate filenames
            if filename in self.file_path_map:
                count = 1
                base_name, ext = os.path.splitext(filename)
                while f"{base_name} ({count}){ext}" in self.file_path_map:
                    count += 1
                filename = f"{base_name} ({count}){ext}"
            
            # Store the mapping
            self.file_path_map[filename] = path
            
            # Create a list item with the filename
            item = gui.ListItem(filename)
            item.style.update({
                'color': '#a5f3fc',
                'background': 'rgba(0, 10, 30, 0.5)',
                'padding': '5px',
                'margin': '2px',
                'border-bottom': '1px solid rgba(0, 140, 255, 0.2)'
            })
            self.file_listbox.append(item)
            
        # Update status with count
        file_count = len(paths)
        self.update_status(f"File list updated: {file_count} files ready")

    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page6')

    # Checkbox event handlers
    def on_destructive_mode_changed(self, widget, value=None):
        """Handle when destructive mode is toggled"""
        self.destructive_mode = widget.get_value()
        
        if self.is_combreakdirect() and self.destructive_mode:
            self.destructive_checkbox.set_value(False)
            self.destructive_mode = False
            return
        
        # If Destructive Mode is turned on, turn off Cutless Mode
        if self.destructive_mode and hasattr(self, 'cutless_checkbox') and self.cutless_checkbox.get_value():
            self.cutless_checkbox.set_value(False)
            self.cutless_mode = False

    def on_fast_mode_changed(self, widget, value=None):
        """Handle when fast mode is toggled"""
        self.fast_mode = widget.get_value()
        
        # If Fast Mode is turned on, turn off Low Power Mode
        if self.fast_mode and hasattr(self, 'low_power_checkbox') and self.low_power_checkbox.get_value():
            self.low_power_checkbox.set_value(False)
            self.low_power_mode = False

    def on_low_power_mode_changed(self, widget, value=None):
        """Handle when low power mode is toggled"""
        self.low_power_mode = widget.get_value()
        
        # If Low Power Mode is turned on, turn off Fast Mode
        if self.low_power_mode and hasattr(self, 'fast_checkbox') and self.fast_checkbox.get_value():
            self.fast_checkbox.set_value(False)
            self.fast_mode = False

    def on_cutless_mode_changed(self, widget, value=None):
        """Handle when cutless mode is toggled"""
        self.cutless_mode = widget.get_value()
        
        if self.is_combreakdirect() and not self.cutless_mode:
            self.cutless_checkbox.set_value(True)
            self.cutless_mode = True
            return
        
        # If Cutless Mode is turned on, turn off Destructive Mode
        if self.cutless_mode and hasattr(self, 'destructive_checkbox') and self.destructive_checkbox.get_value():
            self.destructive_checkbox.set_value(False)
            self.destructive_mode = False
        
        self.update_action_buttons()

    # Methods for action buttons
    def detect_commercials(self, widget):
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(
                self.cblogic.detect_commercials,
                self.done_detect_commercials,
                "Detect Black Frames",
                False,
                False,
                self.low_power_mode,
                self.fast_mode,
                self.reset_progress_bar
            )).start()

    def cut_videos(self, widget):
        if self.validate_input_output_dirs():
            # Pass cutless_mode to the async _run_and_notify method
            threading.Thread(target=self._run_and_notify, args=(
                self.cblogic.cut_videos, 
                self.done_cut_videos, 
                "Cut Video", 
                self.destructive_mode,  # Pass the destructive mode value
                self.cutless_mode       # Pass the cutless mode value
            )).start()

    def delete_txt_files(self, widget):
        if not self.output_path_input.get_value():
            self.update_status("Please specify an output directory.")
            return
        self.cblogic.delete_files(self.output_path_input.get_value())
        self.update_status("Clean up done!")

    # Update the progress bar methods
    def update_progress(self, current, total):
        self.progress_value = current / total * 100
        width_percentage = min(100, max(0, self.progress_value))
        
        # Handle animation state based on progress
        animation_state = "progressGlow 2s infinite" if width_percentage > 0 else "none"
        text_animation_state = "textGlow 2s infinite" if width_percentage > 0 else "none"
        
        # Update the local progress fill width and text
        self.app.execute_javascript(f"""
        (function() {{
            const fillElement = document.getElementById('{self.progress_fill.identifier}');
            const textElement = document.getElementById('{self.progress_text.identifier}');
            if (fillElement) {{
                fillElement.style.width = '{width_percentage}%';
                fillElement.style.animation = '{animation_state}';
            }}
            if (textElement) {{
                textElement.innerText = '{width_percentage:.1f}%';
                textElement.style.animation = '{text_animation_state}';
            }}
        }})();
        """)
        
        # Also update the global status bar with percentage information
        status_text = f"Processing: {current}/{total} files"
        self.update_status_display(status_text, True, self.progress_value)
        print(f"Progress: {self.progress_value}%")

    def reset_progress_bar(self):
        self.progress_value = 0
        
        # Reset the local progress bar UI
        self.app.execute_javascript(f"""
        (function() {{
            const fillElement = document.getElementById('{self.progress_fill.identifier}');
            const textElement = document.getElementById('{self.progress_text.identifier}');
            if (fillElement) {{
                fillElement.style.width = '0%';
                fillElement.style.animation = 'none';
            }}
            if (textElement) {{
                textElement.innerText = '0%';
                textElement.style.animation = 'none';
            }}
        }})();
        """)
        
        # Reset the global status display
        self.update_status_display("Idle", False)
        print("Progress reset")

    def update_status(self, text):
        # Forward status update to message broker if applicable
        if hasattr(self.logic, '_broadcast_status_update'):
            self.logic._broadcast_status_update(text)
        
        # Show progress in status if it's a processing message
        show_progress = False
        if any(keyword in text.lower() for keyword in ['processing', 'analyzing', 'detecting', 'cutting']):
            show_progress = True
        
        # Use the new method from BasePage with progress indication
        self.update_status_display(text, show_progress, self.progress_value if show_progress else None)

    # Utility methods
    def validate_input_output_dirs(self):
        """Validate input/output directories based on the current mode"""
        self.output_path = self.output_path_input.get_value()
        
        if not self.output_path:
            self.update_status("Please specify an output directory.")
            return False
            
        if not os.path.exists(self.output_path):
            try:
                os.makedirs(self.output_path)
            except:
                self.update_status("Could not create output directory.")
                return False
        
        # Check based on input mode
        if self.input_mode == 'folder':
            self.input_path = self.input_path_input.get_value()
            if not self.input_path:
                self.update_status("Please specify an input directory.")
                return False
                
            if not os.path.isdir(self.input_path):
                self.update_status("Input directory does not exist.")
                return False
        else:  # file mode
            if not self.cblogic.input_handler.has_input():
                self.update_status("No files selected. Please add files or folders.")
                return False
        
        # Check output directory permissions
        if not os.access(self.output_path, os.W_OK):
            self.update_status("Output directory is not writable.")
            return False
            
        return True

    def _run_and_notify(self, task, done_callback, task_name, destructive_mode=False, cutless_mode=False, low_power_mode=False, fast_mode=False, reset_callback=None):
        """Run a task and update UI with progress"""
        # Reset progress before starting
        self.reset_progress_bar()
        
        # Update status display with task start info
        self.update_status(f"Started task: {task_name}")

        self.logic._set_operation_state(True, task_name)
        try:
            # Run the appropriate task with progress callback
            if task_name == "Detect Black Frames":
                if self.input_mode == 'folder':
                    # Folder mode - use the input directory
                    current_input_path = self.input_path_input.get_value()
                else:
                    # File mode - we've already populated the input handler
                    # Use a placeholder value as the actual files come from the input handler
                    current_input_path = "/"
                    
                current_output_path = self.output_path_input.get_value()
                task(current_input_path, current_output_path, self.update_progress, 
                     self.update_status, low_power_mode, fast_mode, reset_callback)
            elif task_name == "Cut Video":
                if self.input_mode == 'folder':
                    # Folder mode - use the input directory
                    current_input_path = self.input_path_input.get_value()
                else:
                    # File mode - we've already populated the input handler
                    # Use a placeholder value as the actual files come from the input handler
                    current_input_path = "/"
                
                current_output_path = self.output_path_input.get_value()
                # Pass the cutless_mode parameter to the cut_videos method
                task(current_input_path, current_output_path, self.update_progress, 
                     self.update_status, destructive_mode, cutless_mode)
            
            # Task completed successfully
            self.update_status(f"Finished task: {task_name}")
            done_callback(task_name)
        except Exception as e:
            # Handle errors
            error_message = f"Error in {task_name}: {str(e)}"
            self.update_status(error_message)
            print(error_message)
        finally:
            self.logic._set_operation_state(False, task_name)

    def done_cut_videos(self, task_name):
        self.update_status(f"{task_name} - Done!")

    def done_detect_commercials(self, task_name):
        self.update_status(f"{task_name} - Done!")

    def update_cutless_checkbox(self, enabled: bool):
        """Show / hide the Cutless-mode checkbox depending on flag state."""
        if self.is_combreakdirect():
            self.cutless_container.style['display'] = 'none'
            self.cutless_required_label.style['display'] = 'inline-block'
            return
        self.cutless_required_label.style['display'] = 'none'
        if enabled:
            self.cutless_container.style['display'] = 'flex'
        else:
            self.cutless_container.style['display'] = 'none'
            self.cutless_checkbox.set_value(False)
            self.cutless_mode = False
        self.update_action_buttons()

    # Pub-sub callback
    def on_cutless_state_change(self, enabled: bool):
        self.update_cutless_checkbox(enabled)


    def handle_filtered_files_update(self, filtered_files_json):
        """Handle filtered files list update"""
        try:
            filtered_files = json.loads(filtered_files_json)
            if filtered_files:
                # Add files to the input handler
                self.cblogic.input_handler.clear_all()
                self.cblogic.input_handler.add_files(filtered_files)
                
                # Switch to file mode and update the list
                self.set_input_mode('file')
                self.update_file_list()
                
                file_count = len(filtered_files)
                self.update_status_display(f"Received and pre-populated {file_count} filtered files. Switched to file mode.")
            else:
                self.update_status_display("Received empty list of filtered files. Staying in folder mode.")
        except json.JSONDecodeError as e:
            print(f"Error decoding filtered files JSON: {e}")
            self.update_status_display("Error processing filtered files data.")
        except Exception as e:
            print(f"Error processing filtered files: {e}")
            self.update_status_display("An unexpected error occurred while processing filtered files.")
        finally:
            self.apply_platform_constraints()
            
    def handle_plex_servers_update(self, server_list):
        """Handle Plex servers list update"""
        try:
            print(f"Received server list with {len(server_list)} items")
            
            # Store server list for reference
            self.plex_servers = server_list
            
            # Update server dropdown
            self.update_server_dropdown(server_list)
        except Exception as e:
            print(f"Error processing server list: {e}")
            
    def handle_plex_libraries_update(self, library_list):
        """Handle Plex libraries list update"""
        try:
            print(f"Received library list with {len(library_list)} items")
            
            # Store library list for reference
            self.plex_libraries = library_list
            
            # Update library dropdowns
            self.update_library_dropdowns(library_list)
            
            # Update status
            self.update_status_display(f"Loaded {len(library_list)} libraries")
        except Exception as e:
            print(f"Error processing library list: {e}")

    def handle_cutless_state_update(self, enabled):
        """Handle cutless state updates from LogicController."""
        is_enabled = enabled if isinstance(enabled, bool) else str(enabled).lower() == 'true'
        if hasattr(self, 'on_cutless_state_change'):
            self.on_cutless_state_change(is_enabled)
        if self.cutless_checkbox.get_value() != is_enabled:
            self.cutless_checkbox.set_value(is_enabled)
        self.cutless_mode = self.cutless_checkbox.get_value()
        self.cutless = is_enabled
        self.update_action_buttons()
        self.apply_platform_constraints()

class Page6(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page6, self).__init__(app, 'Page6', *args, **kwargs)
        self.logic = LogicController()
        # Subscribe to status updates
        self.logic.subscribe_to_status_updates(self.update_status_display)
        # Directly call check_platform_type instead of self.after (Remi does not support self.after)
        

        # Toonami version selection
        self.add_label(self.main_container, "What Toonami Version are you making today?")
        options = ["Select a Toonami Version", "OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = self.add_dropdown(self.main_container, options)

        # Channel number entry
        self.channel_number_entry = self.add_labeled_input(self.main_container, "What channel number do you want to use?", "e.g., 60")
        
        # Flex duration entry
        self.flex_duration_entry = self.add_labeled_input(self.main_container, "Enter your Flex duration Minutes:Seconds (How long should a commercial break be)", "e.g., 04:20")

        # Prepare Cut Anime for Lineup button
        self.add_label(self.main_container, "Prepare Cut Anime for Lineup")
        self.prepare_cut_anime_button = self.add_button_with_style(self.main_container, "Prepare Cut Anime for Lineup", self.prepare_cut_anime, 'primary')

        # Add Special Bumps to Sheet button
        self.add_label(self.main_container, "Add Special Bumps to Sheet")
        self.add_special_bumps_button = self.add_button_with_style(self.main_container, "Add Special Bumps to Sheet", self.add_special_bumps, 'primary')

        # Prepare Plex button
        self.prepare_plex_label = self.add_label(self.main_container, "Prepare Plex")
        self.prepare_plex_button = self.add_button_with_style(self.main_container, "Prepare Plex", self.create_prepare_plex, 'primary')

        # Create Toonami Channel button
        self.add_label(self.main_container, "Create Toonami Channel")
        self.create_toonami_channel_button = self.add_button_with_style(self.main_container, "Create Toonami Channel", self.create_toonami_channel, 'primary')

        # Add Flex button
        self.add_label(self.main_container, "Add Flex")
        self.add_flex_button = self.add_button_with_style(self.main_container, "Add Flex", self.add_flex, 'primary')

        # Remove individual status label since we now use the global one in BasePage

        # Info note for ComBreakDirect users — surfaced/hidden by check_platform_type.
        self.infinite_info_label = self.add_label(
            self.main_container,
            "This channel will extend automatically and never end.",
        )

        # Continue button (hidden for combreakdirect where Page 7 is unreachable)
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')
        # Now that all widgets are created, check platform type
        self.check_platform_type()

    def check_platform_type(self):
        """Check the platform type and update button display accordingly"""
        platform_type = self.logic._get_data("platform_type")
        
        if platform_type == "tunarr":
            # For Tunarr, change the button text
            self.create_toonami_channel_button.set_text("Create Toonami Channel with Flex")
            
            # Hide the add flex section completely
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'none'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                # Find the label for flex and hide it too
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'none'
                        break
        elif platform_type == "combreakdirect":
            self.create_toonami_channel_button.set_text("Create ComBreakDirect Channel")
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'none'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'none'
                        break
        else:
            # For DizqueTV (or any other platform), ensure regular button text
            self.create_toonami_channel_button.set_text("Create Toonami Channel")
            
            # Show the add flex section
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'block'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                # Find the label for flex and show it too
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'block'
                        break

        show_plex_controls = platform_type != 'combreakdirect'
        display_value = 'block' if show_plex_controls else 'none'
        if hasattr(self, 'prepare_plex_label'):
            self.prepare_plex_label.style['display'] = display_value
        if hasattr(self, 'prepare_plex_button'):
            self.prepare_plex_button.style['display'] = display_value
        if hasattr(self, 'get_plex_timestamps_label'):
            self.get_plex_timestamps_label.style['display'] = display_value
        if hasattr(self, 'get_plex_timestamps_button'):
            self.get_plex_timestamps_button.style['display'] = display_value

        # ComBreakDirect channels auto-extend forever via the LineupExtender,
        # so Page 7 (manual continuation) doesn't apply. Hide the Continue
        # button and surface a note explaining the new behavior. Other
        # platforms keep the existing manual continuation flow.
        is_combreakdirect = platform_type == 'combreakdirect'
        if hasattr(self, 'continue_button'):
            self.continue_button.style['display'] = 'none' if is_combreakdirect else 'block'
        if hasattr(self, 'infinite_info_label'):
            self.infinite_info_label.style['display'] = 'block' if is_combreakdirect else 'none'

    def refresh_platform_info(self):
        """Preload saved channel configuration when returning to this page"""
        # Preload channel number
        stored_channel_number = self.logic._get_data("channel_number")
        if stored_channel_number and not str(stored_channel_number).startswith("e.g."):
            self.channel_number_entry.set_value(str(stored_channel_number))

        # Preload flex duration
        stored_flex_duration = self.logic._get_data("flex_duration")
        if stored_flex_duration and not str(stored_flex_duration).startswith("e.g."):
            self.flex_duration_entry.set_value(str(stored_flex_duration))

    #wrapper for the prepare_cut_anime method
    def prepare_cut_anime(self, widget):
        self.logic.prepare_cut_anime()

    #wrapper for the add_special_bumps method
    def add_special_bumps(self, widget):
        self.logic.add_special_bumps()

    #wrapper for create_prepare_plex method
    def create_prepare_plex(self, widget):
        self.logic.create_prepare_plex()
        
    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page7')

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number, flex_duration)

        # Check if ComBreakDirect is selected and subscribe to completion
        platform_type = self.logic._get_data("platform_type")
        if platform_type == "combreakdirect":
            self.check_for_completion()

    def check_for_completion(self):
        """Subscribe to status updates and watch for completion"""
        def check_status(status):
            if "Toonami channel created!" in status or "New Toonami channel created!" in status or "channel created" in status.lower():
                # Show Web UI link after completion (for both Docker and non-Docker)
                base_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
                self.show_combreakdirect_completion_dialog(base_url)

        self.logic.subscribe_to_status_updates(check_status)

    def add_flex(self, widget):
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.add_flex(channel_number, flex_duration)

    def handle_message(self, channel, data):
        """Handle messages from the message broker"""
        if channel == 'cutless_state':
            # Handle cutless mode state changes
            try:
                is_enabled = data if isinstance(data, bool) else str(data).lower() == 'true'
                print(f"Cutless state changed: {is_enabled}")
            except Exception as e:
                print(f"Error processing cutless state: {e}")

class Page7(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page7, self).__init__(app, 'Page7', *args, **kwargs)
        self.logic = LogicController()
        self.logic._broadcast_status_update("Idle")

        # Subscribe to status updates
        self.logic.subscribe_to_status_updates(self.update_status_display)

        # Toonami version selection
        self.add_label(self.main_container, "What Toonami Version are you making today?")
        options = ["Select a Toonami Version", "OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = self.add_dropdown(self.main_container, options)

        # Channel number entry
        self.channel_number_entry = self.add_labeled_input(self.main_container, "What channel number do you want to use?", "e.g., 60")

        # Flex duration entry
        self.flex_duration_entry = self.add_labeled_input(self.main_container, "Enter your Flex duration Minutes:Seconds (How long should a commercial break be)", "e.g., 04:20")

        # Start from last episode checkbox
        self.start_from_last_episode_checkbox = self.add_checkbox(self.main_container, "Start from last episode?", default_value=False)

        # Prepare Toonami Channel button
        self.add_label(self.main_container, "Prepare Toonami Channel")
        self.prepare_toonami_channel_button = self.add_button_with_style(self.main_container, "Prepare Toonami Channel", self.prepare_toonami_channel, 'primary')

        # Create Toonami Channel button
        self.add_label(self.main_container, "Create Toonami Channel")
        self.create_toonami_channel_button = self.add_button_with_style(self.main_container, "Create Toonami Channel", self.create_toonami_channel, 'primary')

        # Add Flex button
        self.add_label(self.main_container, "Add Flex")
        self.add_flex_button = self.add_button_with_style(self.main_container, "Add Flex", self.add_flex, 'primary')

        # Remove individual status label since we now use the global one in BasePage
        
        # Now that all widgets are created, check platform type
        self.check_platform_type()

    def check_platform_type(self):
        """Check the platform type and update button display accordingly"""
        platform_type = self.logic._get_data("platform_type")
        
        if platform_type == "tunarr":
            # For Tunarr, change the button text
            self.create_toonami_channel_button.set_text("Create Toonami Channel with Flex")
            
            # Hide the add flex section completely
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'none'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                # Find the label for flex and hide it too
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'none'
                        break
        elif platform_type == "combreakdirect":
            self.create_toonami_channel_button.set_text("Create ComBreakDirect Channel")
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'none'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'none'
                        break
        else:
            # For DizqueTV (or any other platform), ensure regular button text
            self.create_toonami_channel_button.set_text("Create Toonami Channel")
            
            # Show the add flex section
            if hasattr(self, 'add_flex_button'):
                self.add_flex_button.style['display'] = 'block'
            if hasattr(self, 'main_container') and hasattr(self, 'add_flex_button'):
                # Find the label for flex and show it too
                for child in self.main_container.children.values():
                    if isinstance(child, gui.Label) and child.get_text() == "Add Flex":
                        child.style['display'] = 'block'
                        break

    def refresh_platform_info(self):
        """Preload saved channel configuration when returning to this page"""
        # Preload channel number
        stored_channel_number = self.logic._get_data("channel_number")
        if stored_channel_number and not str(stored_channel_number).startswith("e.g."):
            self.channel_number_entry.set_value(str(stored_channel_number))

        # Preload flex duration
        stored_flex_duration = self.logic._get_data("flex_duration")
        if stored_flex_duration and not str(stored_flex_duration).startswith("e.g."):
            self.flex_duration_entry.set_value(str(stored_flex_duration))

    def prepare_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        start_from_last_episode = self.start_from_last_episode_checkbox.get_value()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.create_toonami_channel_cont(toonami_version, channel_number, flex_duration)

        # Check if ComBreakDirect is selected and subscribe to completion
        platform_type = self.logic._get_data("platform_type")
        if platform_type == "combreakdirect":
            self.check_for_completion()

    def check_for_completion(self):
        """Subscribe to status updates and watch for completion"""
        def check_status(status):
            if "Toonami channel created!" in status or "New Toonami channel created!" in status or "channel created" in status.lower():
                # Show Web UI link after completion (for both Docker and non-Docker)
                base_url = getattr(config, 'CBDIRECT_BASE_URL', 'http://127.0.0.1:8083')
                self.show_combreakdirect_completion_dialog(base_url)

        self.logic.subscribe_to_status_updates(check_status)

    def add_flex(self, widget):
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.add_flex(channel_number, flex_duration)

    def handle_message(self, channel, data):
        """Handle messages from the message broker"""
        if channel == 'cutless_state':
            # Handle cutless mode state changes
            try:
                is_enabled = data if isinstance(data, bool) else str(data).lower() == 'true'
                print(f"Cutless state changed: {is_enabled}")
            except Exception as e:
                print(f"Error processing cutless state: {e}")

class Page8(BasePage):
    """Database Diagnostics and Validation Page"""

    def __init__(self, app, *args, **kwargs):
        super(Page8, self).__init__(app, 'Page8', *args, **kwargs)
        self.logic = LogicController()

        # Diagnostics has much taller content than other pages, so build a dedicated
        # scroll region that can grow independently of the main container.
        self._setup_scrollable_body()

        # Title and description
        helper_text = gui.Label(
            "S.A.R.A. Database Diagnostics - Monitor your pipeline progress and validate data integrity",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'text-align': 'center',
                'margin': '10px 0 20px 0',
                'background': 'transparent'
            }
        )
        self.diagnostics_body.append(helper_text)

        # Validation button
        button_container = gui.HBox(style={
            'justify-content': 'center',
            'margin': '10px 0',
            'background': 'transparent'
        })
        self.diagnostics_body.append(button_container)

        self.validate_button = self.add_button_with_style(
            button_container,
            "Run Full Validation",
            self.on_validate_click,
            'primary'
        )

        self.refresh_button = self.add_button_with_style(
            button_container,
            "Refresh Status",
            self.on_refresh_click,
            'secondary'
        )

        self.copy_button = self.add_button_with_style(
            button_container,
            "Copy All Results",
            self.on_copy_all_click,
            'secondary'
        )

        # Hidden input for clipboard copy (like ComBreakDirect's input fields)
        self.copy_input = gui.Input(input_type='text', style={
            'position': 'absolute',
            'left': '-9999px',
            'width': '1px',
            'height': '1px'
        })
        self.copy_input.attributes['id'] = 'validation_copy_field'
        self.diagnostics_body.append(self.copy_input, 'copy_input')

        # Store validation results for copying
        self.last_validation_results = None

        # Pipeline Status Section
        self.pipeline_section = gui.VBox(style={
            'margin': '20px 10px',
            'padding': '15px',
            'background': 'rgba(0, 30, 60, 0.4)',
            'border': '1px solid rgba(0, 204, 255, 0.3)',
            'border-radius': '5px'
        })
        self.diagnostics_body.append(self.pipeline_section)

        pipeline_title = gui.Label(
            "Pipeline Status",
            style={
                'font-size': '18px',
                'color': '#00ccff',
                'font-weight': 'bold',
                'margin-bottom': '10px'
            }
        )
        self.pipeline_section.append(pipeline_title)

        self.pipeline_status_label = gui.Label(
            "Loading pipeline status...",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'margin': '5px 0',
                'font-family': 'monospace'
            }
        )
        self.pipeline_section.append(self.pipeline_status_label)

        # Steps checklist
        self.steps_container = gui.VBox(style={
            'margin': '10px 0',
            'background': 'transparent'
        })
        self.pipeline_section.append(self.steps_container)

        # Validation Results Section
        self.results_section = gui.VBox(style={
            'margin': '20px 10px',
            'padding': '15px',
            'background': 'rgba(0, 30, 60, 0.4)',
            'border': '1px solid rgba(0, 204, 255, 0.3)',
            'border-radius': '5px',
            'display': 'none'  # Hidden until validation runs
        })
        self.diagnostics_body.append(self.results_section)

        results_title = gui.Label(
            "Validation Results",
            style={
                'font-size': '18px',
                'color': '#00ccff',
                'font-weight': 'bold',
                'margin-bottom': '10px'
            }
        )
        self.results_section.append(results_title)

        self.results_label = gui.Label(
            "",
            style={
                'font-size': '14px',
                'color': '#a5f3fc',
                'margin': '5px 0'
            }
        )
        self.results_section.append(self.results_label)

        # Issues list
        self.issues_container = gui.VBox(style={
            'margin': '10px 0',
            'background': 'transparent',
            'max-height': '400px',
            'overflow-y': 'auto'
        })
        self.results_section.append(self.issues_container)

        # Load initial status
        self.update_pipeline_status()

        # Subscribe to status updates
        self.logic.subscribe_to_status_updates(self.on_status_update)

    def _setup_scrollable_body(self):
        """Create a viewport-aware scroll wrapper for diagnostics content."""
        if hasattr(self, 'diagnostics_body'):
            return

        self.main_container.style.update({
            'width': '100%',
            'max-width': '1200px',
            'align-items': 'stretch',
            'justify-content': 'flex-start',
            'overflow': 'visible'
        })
        if hasattr(self, 'page_title_label'):
            self.page_title_label.style.update({
                'align-self': 'center',
                'text-align': 'center',
                'width': '100%'
            })

        # ScrollArea is not available in all remi builds we run against, so we
        # use a plain Container with overflow settings to behave the same way.
        self.diagnostics_scroll_area = gui.Container(width='100%', height='100%')
        self.diagnostics_scroll_area.style.update({
            'width': '100%',
            'background': 'transparent',
            'overflow-y': 'auto',
            'overflow-x': 'hidden',
            'padding': '0 10px 90px 10px',
            'box-sizing': 'border-box'
        })

        self.diagnostics_body = gui.VBox(style={
            'width': '100%',
            'max-width': '1100px',
            'margin': '0 auto',
            'align-items': 'stretch',
            'background': 'transparent',
            'gap': '10px'
        })
        self.diagnostics_scroll_area.append(self.diagnostics_body)
        self.main_container.append(self.diagnostics_scroll_area)
        self._install_scroll_resizer()

    def _install_scroll_resizer(self):
        if not hasattr(self, 'diagnostics_scroll_area'):
            return

        nav_lookup = f"document.getElementById('{self.nav_bar.identifier}')" if hasattr(self, 'nav_bar') else "null"
        status_lookup = f"document.getElementById('{self.status_bar.identifier}')" if hasattr(self, 'status_bar') else "null"
        scroll_id = self.diagnostics_scroll_area.identifier

        js = """
        (function() {
            function resizeDiagScrollArea() {
                var area = document.getElementById('%s');
                if (!area) return;
                var nav = %s;
                var status = %s;
                var navHeight = nav ? nav.offsetHeight : 0;
                var statusHeight = status ? status.offsetHeight : 0;
                var available = window.innerHeight - navHeight - statusHeight - 80;
                if (available < 280) {
                    available = Math.max(200, window.innerHeight - 120);
                }
                area.style.height = available + 'px';
                area.style.maxHeight = available + 'px';
            }
            window.__resizeDiagScrollArea = resizeDiagScrollArea;
            if (!window.__diagScrollResizeBound) {
                window.addEventListener('resize', resizeDiagScrollArea);
                window.__diagScrollResizeBound = true;
            }
            resizeDiagScrollArea();
        })();
        """ % (scroll_id, nav_lookup, status_lookup)
        self.app.execute_javascript(js)

    def _resize_scroll_area(self):
        if hasattr(self, 'diagnostics_scroll_area'):
            self.app.execute_javascript("""
                if (window.__resizeDiagScrollArea) {
                    window.__resizeDiagScrollArea();
                }
            """)

    def _reset_scroll_position(self):
        if hasattr(self, 'diagnostics_scroll_area'):
            js = """
                (function() {
                    var area = document.getElementById('%s');
                    if (area) area.scrollTop = 0;
                })();
            """ % self.diagnostics_scroll_area.identifier
            self.app.execute_javascript(js)

    def on_status_update(self, status_message):
        """Handle status updates from validation"""
        self.update_status_display(status_message)

    def refresh_platform_info(self):
        """
        Called automatically when the page is shown.
        Refreshes the pipeline status to show current database state.
        """
        self.update_pipeline_status()
        self._resize_scroll_area()
        self._reset_scroll_position()

    def on_validate_click(self, widget):
        """Start full validation"""
        self.update_status_display("Starting validation...")
        self.validate_button.attributes['disabled'] = 'true'
        self.validate_button.set_text("Validating...")

        # Start validation in background
        self.logic.validate_database()

        # Check for results periodically
        def check_results():
            time.sleep(2)  # Wait for validation to start
            max_attempts = 300  # Allow up to 5 minutes for long validations
            for _ in range(max_attempts):
                results = self.logic.get_validation_results()
                if results:
                    self.display_validation_results(results)
                    self.validate_button.attributes.pop('disabled', None)
                    self.validate_button.set_text("Run Full Validation")
                    return
                time.sleep(1)

            # Timeout
            self.validate_button.attributes.pop('disabled', None)
            self.validate_button.set_text("Run Full Validation")
            self.update_status_display("Validation timed out before results were available")

        thread = threading.Thread(target=check_results)
        thread.daemon = True
        thread.start()

    def on_refresh_click(self, widget):
        """Refresh pipeline status"""
        self.update_pipeline_status()
        self.update_status_display("Status refreshed")

    def on_copy_all_click(self, widget):
        """Copy all validation results to clipboard - exact same approach as ComBreakDirect"""
        if not self.last_validation_results:
            self.update_status_display("No validation results to copy. Run validation first.")
            return

        try:
            # Format results as text
            text_output = self._format_results_as_text(self.last_validation_results)

            # Set the value of the hidden input (like ComBreakDirect sets input.value)
            self.copy_input.set_value(text_output)

            # Use EXACT same approach as ComBreakDirect - select the field and copy
            js_code = """
                const input = document.getElementById('validation_copy_field');
                input.select();
                document.execCommand('copy');
            """

            self.app.execute_javascript(js_code)

            # Visual feedback on button (exactly like ComBreakDirect)
            original_text = widget.get_text()
            widget.set_text("Copied!")
            widget.style['color'] = '#00ff00'

            # Reset after 2 seconds (like ComBreakDirect)
            def reset_button():
                try:
                    widget.set_text(original_text)
                    widget.style['color'] = '#00ccff'
                except:
                    pass

            import threading
            timer = threading.Timer(2.0, reset_button)
            timer.start()

            self.update_status_display("Validation results copied to clipboard!")

        except Exception as e:
            self.update_status_display(f"Error copying results: {str(e)}")

    def _format_results_as_text(self, results):
        """Format validation results as plain text"""
        lines = []
        lines.append("=" * 80)
        lines.append("S.A.R.A. DATABASE VALIDATION RESULTS")
        lines.append("=" * 80)

        # Summary
        summary = results.get('summary', {})
        lines.append(f"\n{summary.get('summary_text', 'Validation complete')}")
        lines.append("")

        # Issues grouped by level
        issues = results.get('issues', [])

        if not issues:
            lines.append("✓ No issues found! Database is valid.")
        else:
            # Group by level
            issues_by_level = {'CRITICAL': [], 'ERROR': [], 'WARNING': [], 'INFO': []}
            for issue in issues:
                level = issue.get('level', 'INFO')
                issues_by_level[level].append(issue)

            # Display each level
            for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO']:
                level_issues = issues_by_level[level]
                if not level_issues:
                    continue

                lines.append(f"\n{level} ({len(level_issues)})")
                lines.append("-" * 80)

                for issue in level_issues:
                    step = issue.get('step', 'Unknown')
                    message = issue.get('message', '')
                    details = issue.get('details', '')
                    suggestion = issue.get('suggestion', '')

                    lines.append(f"[{step}] {message}")
                    if details:
                        # Handle multi-line details properly
                        if '\n' in details:
                            lines.append("  Details:")
                            for detail_line in details.split('\n'):
                                lines.append(f"    {detail_line}")
                        else:
                            lines.append(f"  Details: {details}")
                    if suggestion:
                        lines.append(f"  → {suggestion}")
                    lines.append("")  # Blank line between issues

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def update_pipeline_status(self):
        """Update the pipeline status display"""
        try:
            status = self.logic.get_pipeline_status()

            # Update summary label
            completed = len(status.get('completed_steps', []))
            total = status.get('total_steps', 0)
            percentage = status.get('completion_percentage', 0)
            mode = "Cutless" if status.get('is_cutless_mode', False) else "Traditional"
            current = status.get('current_step', 'Unknown')

            summary = f"Progress: {completed}/{total} steps ({percentage:.1f}%) | Mode: {mode}"
            if completed < total:
                summary += f" | Current: {current}"

            self.pipeline_status_label.set_text(summary)

            # Update steps checklist
            self.steps_container.empty()

            completed_steps = set(status.get('completed_steps', []))
            is_cutless = status.get('is_cutless_mode')

            all_steps = [
                "Platform/Folder Setup",
                "ToonamiChecker",
                "LineupPrep",
                "BumpEncoder",
                "UncutEncoder",
                "Multilineup",
                "ShowScheduler/Merger",
                "CommercialBreaker",
                "CommercialInjector/BlockMaker"
            ]

            if is_cutless:
                all_steps.append("CutlessFinalizer")

            all_steps.append("LineupIntegrity")

            for step in all_steps:
                is_completed = step in completed_steps
                symbol = "✓" if is_completed else "○"
                color = "#00ff00" if is_completed else "#666666"

                step_label = gui.Label(
                    f"{symbol} {step}",
                    style={
                        'font-size': '13px',
                        'color': color,
                        'margin': '2px 0',
                        'font-family': 'monospace'
                    }
                )
                self.steps_container.append(step_label)

            self._resize_scroll_area()

        except Exception as e:
            self.pipeline_status_label.set_text(f"Error loading status: {str(e)}")

    def display_validation_results(self, results):
        """Display validation results"""
        try:
            # Store results for copying
            self.last_validation_results = results

            self.results_section.style['display'] = 'block'

            summary = results.get('summary', {})
            summary_text = summary.get('summary_text', 'Validation complete')

            critical_count = summary.get('critical_count', 0)
            error_count = summary.get('error_count', 0)
            warning_count = summary.get('warning_count', 0)

            self.results_label.set_text(summary_text)

            # Clear previous issues
            self.issues_container.empty()

            # Display issues
            issues = results.get('issues', [])

            if not issues:
                no_issues_label = gui.Label(
                    "✓ No issues found! Database is valid.",
                    style={
                        'font-size': '14px',
                        'color': '#00ff00',
                        'margin': '10px 0',
                        'font-weight': 'bold'
                    }
                )
                self.issues_container.append(no_issues_label)
            else:
                # Group issues by level
                issues_by_level = {
                    'CRITICAL': [],
                    'ERROR': [],
                    'WARNING': [],
                    'INFO': []
                }

                for issue in issues:
                    level = issue.get('level', 'INFO')
                    issues_by_level[level].append(issue)

                # Display issues by level
                for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO']:
                    level_issues = issues_by_level[level]
                    if not level_issues:
                        continue

                    # Level header
                    level_color = {
                        'CRITICAL': '#ff0000',
                        'ERROR': '#ff6666',
                        'WARNING': '#ffaa00',
                        'INFO': '#00ccff'
                    }[level]

                    level_header = gui.Label(
                        f"{level} ({len(level_issues)})",
                        style={
                            'font-size': '15px',
                            'color': level_color,
                            'font-weight': 'bold',
                            'margin': '10px 0 5px 0'
                        }
                    )
                    self.issues_container.append(level_header)

                    # Display each issue
                    for issue in level_issues[:10]:  # Limit to 10 per level
                        issue_box = gui.VBox(style={
                            'margin': '5px 0',
                            'padding': '8px',
                            'background': 'rgba(0, 0, 0, 0.3)',
                            'border-left': f'3px solid {level_color}',
                            'border-radius': '3px'
                        })

                        # Issue message
                        msg_label = gui.Label(
                            f"[{issue.get('step', 'Unknown')}] {issue.get('message', '')}",
                            style={
                                'font-size': '13px',
                                'color': '#a5f3fc',
                                'margin': '2px 0'
                            }
                        )
                        issue_box.append(msg_label)

                        # Details
                        if issue.get('details'):
                            details_label = gui.Label(
                                f"Details: {issue.get('details')}",
                                style={
                                    'font-size': '12px',
                                    'color': '#88b0c0',
                                    'margin': '2px 0 2px 10px',
                                    'font-style': 'italic'
                                }
                            )
                            issue_box.append(details_label)

                        # Suggestion
                        if issue.get('suggestion'):
                            suggestion_label = gui.Label(
                                f"→ {issue.get('suggestion')}",
                                style={
                                    'font-size': '12px',
                                    'color': '#66dd88',
                                    'margin': '2px 0 0 10px'
                                }
                            )
                            issue_box.append(suggestion_label)

                        self.issues_container.append(issue_box)

                    if len(level_issues) > 10:
                        more_label = gui.Label(
                            f"... and {len(level_issues) - 10} more {level} issues",
                            style={
                                'font-size': '12px',
                                'color': '#888888',
                                'margin': '5px 0',
                                'font-style': 'italic'
                            }
                        )
                        self.issues_container.append(more_label)

            self._resize_scroll_area()

        except Exception as e:
            self.results_label.set_text(f"Error displaying results: {str(e)}")


class MainApp(App):
    def __init__(self, *args, **kwargs):
        self.default_page_titles = {
            "Page1": "Step 1 - Choose Your Platform - Welcome to the Absolution",
            "Page2": "Step 2 - Login to Plex - Secure Docking",
            "Page3": "Step 2 - Enter Details Manually - A Little Detour",
            "Page4": "Step 3 - Prepare Content - Intruder Alert",
            "Page5": "Step 4 - Commercial Breaker - Toonami Will Be Right Back",
            "Page6": "Step 5 - Create your Toonami Channel - All aboard the Absolution",
            "Page7": "Step 6 - Let's Make Another Channel! - Toonami's Back Bitches",
            "Page8": "S.A.R.A. Database Diagnostics - System Status"
        }
        self.page_titles = dict(self.default_page_titles)
        
        # Track whether Page3 was ever visited
        self.visited_manual_setup = False
        
        # Keep track of navigation history for proper back button behavior
        self.navigation_history = []
        
        # Custom page flow to respect skipping of optional Page3
        self.page_flow = {
            'Page1': None,  # No previous page
            'Page2': 'Page1',
            'Page3': 'Page2',
            'Page4': 'Page2',  # Default if Page3 wasn't used
            'Page5': 'Page4',
            'Page6': 'Page5',
            'Page7': 'Page6'
        }

        # Initialize the LogicController
        from API import LogicController
        self.logic = LogicController()
        self.nav_logic = self.logic
        self.navigation_locked = False
        self.navigation_lock_reason = None
        self.nav_logic.subscribe_to_operation_state(self._handle_operation_state)
        stored_platform_type = self.logic._get_data("platform_type")
        self.current_platform_type = stored_platform_type if stored_platform_type else 'combreakdirect'
        if self.current_platform_type == 'combreakdirect':
            self.page_flow['Page4'] = 'Page1'
            self.page_titles['Page4'] = "Step 2 - Prepare Content - Intruder Alert"
            self.page_titles['Page5'] = "Step 3 - Commercial Breaker - Toonami Will Be Right Back"
            self.page_titles['Page6'] = "Step 4 - Create your Toonami Channel - All aboard the Absolution"
            self.page_titles['Page7'] = "Step 5 - Let's Make Another Channel! - Toonami's Back Bitches"

        super(MainApp, self).__init__(*args, **kwargs)

    def refresh_all_nav_bars(self):
        if hasattr(self, 'pages'):
            for page in self.pages.values():
                if hasattr(page, 'refresh_nav_bar'):
                    page.refresh_nav_bar()

    def _handle_operation_state(self, data):
        try:
            running = False
            operation = None
            if isinstance(data, dict):
                running = bool(data.get('running'))
                operation = data.get('operation')
            else:
                running = bool(data)
            self.set_navigation_locked(running, operation)
        except Exception as exc:
            print(f"Failed to handle operation state: {exc}")

    def set_navigation_locked(self, locked: bool, operation: str | None = None) -> None:
        self.navigation_locked = locked
        self.navigation_lock_reason = operation if locked else None

        if hasattr(self, 'pages'):
            for page in self.pages.values():
                nav = getattr(page, 'nav_bar', None)
                if nav and hasattr(nav, 'set_navigation_enabled'):
                    nav.set_navigation_enabled(not locked)
                for attr in ('continue_button', 'next_button'):
                    button = getattr(page, attr, None)
                    if button and hasattr(button, 'set_enabled'):
                        button.set_enabled(not locked)

        if locked and hasattr(self, 'logic') and hasattr(self.logic, '_broadcast_status_update'):
            message = f"Navigation locked while {operation or 'an operation'} runs"
            self.logic._broadcast_status_update(message)

    def update_platform_type(self, platform_type: str | None) -> None:
        self.current_platform_type = platform_type
        self.visited_manual_setup = False
        self.page_titles = dict(self.default_page_titles)

        if platform_type and hasattr(self, 'logic'):
            self.logic._set_data("platform_type", platform_type)

        if platform_type == 'combreakdirect':
            self.page_flow['Page4'] = 'Page1'
            self.page_titles['Page4'] = "Step 2 - Prepare Content - Intruder Alert"
            self.page_titles['Page5'] = "Step 3 - Commercial Breaker - Toonami Will Be Right Back"
            self.page_titles['Page6'] = "Step 4 - Create your Toonami Channel - All aboard the Absolution"
            self.page_titles['Page7'] = "Step 5 - Let's Make Another Channel! - Toonami's Back Bitches"
        else:
            self.page_flow['Page4'] = 'Page2'

        self.refresh_all_nav_bars()

    def refresh(self):
        """Force UI refresh using JavaScript reflow"""
        self.execute_javascript("""
            setTimeout(function() {
                // Force browser reflow to update UI immediately
                document.body.style.display='none';
                document.body.offsetHeight; // Trigger reflow
                document.body.style.display='';
            }, 10);
        """)

    def main(self):
        container = gui.Container(width='100%', height='100%')
        container.style.update(Styles.default_container_style)
        
        self.container = gui.Container(width='100%', height='100%')
        self.container.style.update(Styles.default_container_style)
        
        # Add custom CSS for the navigation indicators and status bar animations
        self.execute_javascript("""
        var style = document.createElement('style');
        style.innerHTML = `
            @keyframes grid-scroll {
                0% { background-position: 0 0; }
                100% { background-position: 60px 60px; }
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            
            .nav-indicator {
                transition: all 0.3s ease;
            }
            
            .nav-indicator:hover {
                transform: scale(1.2);
            }
            
            .status-bar {
                transition: all 0.3s ease;
            }
            
            .status-active {
                animation: pulse 2s infinite;
            }
        `;
        document.head.appendChild(style);
        """)

        self.pages = {
            'Page1': Page1(self),
            'Page2': Page2(self),
            'Page3': Page3(self),
            'Page4': Page4(self),
            'Page5': Page5(self),
            'Page6': Page6(self),
            'Page7': Page7(self),
            'Page8': Page8(self),
        }
        
        self.set_current_page('Page1')
        return self.container

    def set_current_page(self, page_name, force_refresh: bool = False):
        current_page = self.navigation_history[-1] if self.navigation_history else None
        if getattr(self, 'navigation_locked', False) and current_page and page_name != current_page:
            if hasattr(self, 'logic') and hasattr(self.logic, '_broadcast_status_update'):
                self.logic._broadcast_status_update("Navigation locked while an operation is running")
            return
        if (page_name in self.pages):
            if force_refresh:
                page_obj = self.pages[page_name] = type(self.pages[page_name])(self)
            else:
                page_obj = self.pages[page_name]
            if hasattr(page_obj, 'refresh_platform_info'):
                page_obj.refresh_platform_info()

            # Mark Page3 as visited if we're going there
            if page_name == 'Page3':
                self.visited_manual_setup = True
                
                # Refresh all navigation bars to reflect this change
                self.refresh_all_nav_bars()
            
            # Add to navigation history
            self.navigation_history.append(page_name)
            
            # Clear the container and add the new page
            self.container.empty()
            self.container.append(page_obj)
            
            # Important: Trigger platform type check for specific pages
            if page_name in ['Page6', 'Page7'] and hasattr(self.pages[page_name], 'check_platform_type'):
                # Call the check_platform_type method to update UI based on current platform
                self.pages[page_name].check_platform_type()

            # Allow pages to refresh platform-dependent UI
            if hasattr(self.pages[page_name], 'refresh_platform_type'):
                self.pages[page_name].refresh_platform_type()
            
            # Pass reference to the LogicController if page has it
            if hasattr(self.pages[page_name], 'logic'):
                self.logic = self.pages[page_name].logic
                
            # Broadcast status update and update the status display
            if hasattr(self, 'logic') and hasattr(self.logic, '_broadcast_status_update'):
                status_message = f"Navigated to {self.page_titles.get(page_name, page_name)}"
                self.logic._broadcast_status_update(status_message)
                
                # Update the status display in the current page
                if hasattr(self.pages[page_name], 'update_status_display'):
                    self.pages[page_name].update_status_display(status_message)

            self.refresh_all_nav_bars()
    
    def go_back(self):
        if getattr(self, 'navigation_locked', False):
            if hasattr(self, 'logic') and hasattr(self.logic, '_broadcast_status_update'):
                self.logic._broadcast_status_update("Navigation locked while an operation is running")
            return
        # Must have at least two pages in history to go back
        if len(self.navigation_history) <= 1:
            return
            
        # Remove current page from history
        current_page = self.navigation_history.pop()  
        previous_page = self.navigation_history[-1]  # Get the previous page
        
        # Special handling for Page4 going back
        if current_page == 'Page4' and previous_page == 'Page3' and not self.visited_manual_setup:
            # Skip the optional manual page if it was never completed
            self.navigation_history.pop()  # Remove Page3 from history
            previous_page = 'Page2'
            
        # Reset filter mode if coming from Page5 back to Page4
        if current_page == 'Page5' and previous_page == 'Page4':
            if hasattr(self.pages['Page4'], 'set_filter_mode'):
                # Reset to default move_files mode
                self.pages['Page4'].set_filter_mode('move_files')
                
        # Go to the previous page - we need to pop again since set_current_page will add it
        self.navigation_history.pop()
        self.set_current_page(previous_page)

    def navigate_to_diagnostics(self, widget=None):
        """Hidden panic button callback: Navigate to diagnostics page (Page8)"""
        self.set_current_page('Page8')

    def start_over(self):
        if getattr(self, 'navigation_locked', False):
            if hasattr(self, 'logic') and hasattr(self.logic, '_broadcast_status_update'):
                self.logic._broadcast_status_update("Navigation locked while an operation is running")
            return
        # Reset visited_manual_setup flag
        self.visited_manual_setup = False
        stored_platform_type = self.logic._get_data("platform_type") if hasattr(self, 'logic') else None
        fallback_platform = stored_platform_type or 'combreakdirect'
        self.update_platform_type(fallback_platform)
        
        # Reset filter mode in Page4
        if hasattr(self.pages['Page4'], 'set_filter_mode'):
            self.pages['Page4'].set_filter_mode('move_files')
            
        # Reset input mode in Page5
        if hasattr(self.pages['Page5'], 'cblogic') and hasattr(self.pages['Page5'], 'set_input_mode'):
            # Clear any files in the input handler
            self.pages['Page5'].cblogic.input_handler.clear_all()
            # Reset to default folder mode
            self.pages['Page5'].set_input_mode('folder')
        
        # Clear history and go to Page1
        self.navigation_history = []
        self.set_current_page('Page1', force_refresh=True)

def WebServer():
    # Starts the webserver
    start(MainApp, address='0.0.0.0', port=8081, start_browser=True)

if __name__ == "__main__":
    WebServer()
