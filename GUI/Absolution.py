from ComBreak import CommercialBreakerLogic
from GUI import LogicController
from CLI import PlexManager
import config
import threading
import os
import psutil
import json
import ToonamiTools
from queue import Queue, Empty
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
        'overflow': 'auto'
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
    }
    
    status_label_style = {
        'font-size': '18px',
        'font-weight': 'bold',
        'color': '#0ff',
        'text-shadow': '0 0 5px #00ccff',
        'padding': '5px',
        'text-align': 'center',
        'flex-grow': '1'  # Changed to flex-grow instead of width
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
        self.title_key = title_key  # Store the title key for later reference
        self.set_size('100%', '100%')
        self.style.update(Styles.default_container_style)
        
        # Add the navigation bar at the top
        self.nav_bar = NavigationBar(app, title_key)
        self.append(self.nav_bar)
        
        # Create the main content container
        self.main_container = self.create_main_container()
        self.append(self.main_container)
        self.add_page_title(self.main_container, self.app.page_titles.get(title_key, ''))
        
        # Add status bar at the bottom
        self.status_bar = self.create_status_bar()
        self.append(self.status_bar)
        
        # Set initial status to idle
        self.update_status_display("Idle")
        
        # Track progress value
        self.global_progress_value = 0

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
            'overflow-y': 'auto'  # Added to enable scrolling if content is too large
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
    
    def update_status_display(self, status_text, show_progress=False, progress_value=None):
        """Update the status display with appropriate styling based on content"""
        if not hasattr(self, 'status_label'):
            return
            
        # Add "Status: " prefix if not present
        if not status_text.startswith("Status: "):
            status_text = f"Status: {status_text}"
            
        self.status_label.set_text(status_text)
        
        # Apply appropriate styling based on status content
        if "error" in status_text.lower() or "failed" in status_text.lower():
            self.status_label.style.update(Styles.status_label_style)
            self.status_label.style.update(Styles.status_error_style)
        elif status_text.lower() == "status: idle":
            self.status_label.style.update(Styles.status_label_style)
            self.status_label.style.update(Styles.status_idle_style)
            # Hide progress bar when idle
            show_progress = False
        else:
            self.status_label.style.update(Styles.status_label_style)
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

    def add_page_title(self, container, title_text):
        page_title = gui.Label(title_text, style=Styles.title_label_style)
        page_title.add_class('main-title') 
        container.append(page_title)

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
        return checkbox

class RedisListenerMixin:
    def after(self, time_ms, callback):
        threading.Timer(time_ms / 1000, callback).start()

    def process_redis_messages(self):
        while not self.redis_queue.empty():
            message = self.redis_queue.get()
            channel = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')

            if channel == 'status_updates':
                self.update_status_label(data)
            elif hasattr(self, 'handle_redis_message'):
                self.handle_redis_message(channel, data)

        self.after(100, self.process_redis_messages)

    def listen_for_redis_updates(self, redis_queue):
        redis_client = self.logic.redis_client
        pubsub = redis_client.pubsub()
        pubsub.subscribe('status_updates', 'new_server_choices', 'new_library_choices', 'plex_servers', 'plex_libraries', 'plex_auth_url')

        for message in pubsub.listen():
            if message['type'] == 'message':
                redis_queue.put(message)

    def start_redis_listener_thread(self, redis_queue):
        threading.Thread(target=self.listen_for_redis_updates, args=(redis_queue,), daemon=True).start()

    def update_status_label(self, status):
        # Use the new method from BasePage
        if hasattr(self, 'update_status_display'):
            self.update_status_display(status)
        else:
            # Fallback for backward compatibility
            if hasattr(self, 'status_label'):
                self.status_label.set_text(f"Status: {status}")

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
        back_button = self.add_button(left_container, "← Back", self.on_back_button_click)
        # Apply navigation style manually
        back_button.style.update(Styles.navigation_button_style)
        
        # Right container for home/start over button
        right_container = gui.HBox(style={
            'align-items': 'center',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        
        # Home/Start Over button - using add_button instead of add_button_with_style
        home_button = self.add_button(right_container, "↻ Start Over", self.on_home_button_click)
        # Apply navigation style manually
        home_button.style.update(Styles.navigation_button_style)
        
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
    
    def create_page_indicators(self, container):
        # Use the app's visited_page2 flag to determine if we show Page2
        show_page2 = self.current_page == 'Page2' or self.app.visited_page2
        
        # Define all pages in sequence with their titles and visual number
        pages = []
        
        # Always add Page1
        pages.append({
            'id': 'Page1', 
            'title': 'Login', 
            'optional': False, 
            'visual_num': 1
        })
        
        # Only add Page2 if we're on it or have visited it
        if show_page2:
            pages.append({
                'id': 'Page2', 
                'title': 'Manual Setup', 
                'optional': True, 
                'visual_num': 2
            })
        
        # Add remaining pages with dynamic visual numbers
        offset = 1 if not show_page2 else 0
        pages.append({
            'id': 'Page3', 
            'title': 'Content Prep', 
            'optional': False, 
            'visual_num': 3 - offset
        })
        pages.append({
            'id': 'Page4', 
            'title': 'Commercial Breaker', 
            'optional': False, 
            'visual_num': 4 - offset
        })
        pages.append({
            'id': 'Page5', 
            'title': 'Channel Creation', 
            'optional': False, 
            'visual_num': 5 - offset
        })
        pages.append({
            'id': 'Page6', 
            'title': 'Additional Channels', 
            'optional': False, 
            'visual_num': 6 - offset
        })
        
        # Display page indicators
        for i, page in enumerate(pages):
            # Create indicator style based on current page
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
            
            # Create text style
            text_style = {
                'font-size': '14px',
                'color': '#0ff' if is_current else '#a5f3fc',
                'margin': '0 5px',
                'font-weight': 'bold' if is_current else 'normal',
                'text-shadow': '0 0 5px #00ccff' if is_current else 'none'
            }
            
            # Create page indicator
            indicator_container = gui.HBox(style={
                'align-items': 'center',
                'margin': '0 8px',
                'background': 'transparent',
                'background-color': 'transparent'
            })
            
            # Add dot indicator
            dot = gui.Container(width=12, height=12, style=indicator_style)
            dot.attributes['page_id'] = page['id']
            dot.onclick.do(self.on_indicator_click)
            indicator_container.append(dot)
            
            # Add page number and title
            label_text = f"{page['visual_num']} - {page['title']}"
            if page['optional']:
                label_text += " (Optional)"
                
            label = gui.Label(label_text, style=text_style)
            indicator_container.append(label)
            
            # Add to container
            container.append(indicator_container)
            
            # Add separator if not the last page
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
    
    def on_indicator_click(self, widget):
        # Navigate to the clicked page
        page_id = widget.attributes.get('page_id')
        if page_id:
            self.app.set_current_page(page_id)
    
    # Add the add_button method to NavigationBar (similar to the one in BasePage)
    def add_button(self, container, text, onclick_handler):
        button = gui.Button(text, width=200, height=30, style=Styles.default_button_style)
        button.onclick.do(onclick_handler)
        container.append(button)
        return button

class Page1(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page1, self).__init__(app, 'Page1', *args, **kwargs)
        self.logic = LogicController()
        self.PlexManager = PlexManager(self.logic)
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)
        self.libraries_selected = 0

        # Build the page using helper methods
        self.add_label(self.main_container, "Login with Plex")
        self.login_with_plex_button = self.add_button_with_style(self.main_container, "Login with Plex", self.login_to_plex, 'primary')

        # Plex Servers Dropdown
        self.add_label(self.main_container, "Select a Plex Server")
        self.plex_server_dropdown = self.add_dropdown(self.main_container, ["Select a Plex Server"], self.on_server_selected)

        # Anime Library Dropdown
        self.add_label(self.main_container, "Select your Anime Library")
        self.plex_anime_library_dropdown = self.add_dropdown(self.main_container, ["Select your Anime Library"], self.add_1_to_libraries_selected)

        # Toonami Library Dropdown
        self.add_label(self.main_container, "Select your Toonami Library")
        self.plex_library_dropdown = self.add_dropdown(self.main_container, ["Select your Toonami Library"], self.add_1_to_libraries_selected)

        # Platform Selection
        platform_container = gui.HBox(style={
            'justify-content': 'center',
            'margin': '20px',
            'gap': '20px',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        self.add_label(platform_container, "Select Platform:")
        
        # Create platform selection buttons
        self.dizquetv_button = gui.Button("DizqueTV", width=150, height=40, style=Styles.selected_button_style)
        self.tunarr_button = gui.Button("Tunarr", width=150, height=40, style=Styles.unselected_button_style)
        
        self.dizquetv_button.onclick.do(lambda w: self.on_platform_change('dizquetv'))
        self.tunarr_button.onclick.do(lambda w: self.on_platform_change('tunarr'))
        
        platform_container.append([self.dizquetv_button, self.tunarr_button])
        
        self.main_container.append(platform_container)
        self.selected_platform = 'dizquetv'  # Default selection

        # Platform URL Entry
        self.url_label = self.add_label(self.main_container, "Platform URL:")
        self.platform_url_entry = self.add_input(self.main_container, "e.g., http://localhost:17685")

        # Remove individual status label since we now use the global one in BasePage

        # Continue and Skip buttons
        buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '20px',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        self.continue_button = self.add_button_with_style(buttons_container, "Continue", self.on_continue_button_click, 'secondary')
        self.continue_button.style['display'] = 'none'
        buttons_container.append(self.continue_button)

        self.skip_button = self.add_button_with_style(buttons_container, "Skip", self.on_skip_button_click, 'secondary')
        buttons_container.append(self.skip_button)

        self.main_container.append(buttons_container)

        self.app.execute_javascript("""
            window.pywebview.api.open_plex_auth_url = function(url) {
                window.open(url, '_blank');
            }
        """)

    def on_platform_change(self, platform):
        """Handle platform selection button clicks"""
        self.selected_platform = platform
        if platform == 'dizquetv':
            self.dizquetv_button.style.update(Styles.selected_button_style)
            self.tunarr_button.style.update(Styles.unselected_button_style)
            self.platform_url_entry.set_value("e.g., http://localhost:17685")
        else:
            self.dizquetv_button.style.update(Styles.unselected_button_style)
            self.tunarr_button.style.update(Styles.selected_button_style)
            self.platform_url_entry.set_value("e.g., http://localhost:8000")

    def login_to_plex(self, widget):
        print("You pressed the login button")
        self.logic.login_to_plex()
        self.PlexManager._wait_for_servers()
        self.update_dropdown()

    def on_server_selected(self, widget, value):
        self.selected_server = self.plex_server_dropdown.get_value()
        print(f"Selected server: {self.selected_server}")
        self.logic.on_server_selected(self.selected_server)
        
        # Run library fetching in a separate thread to prevent UI freezing
        def fetch_libraries_thread():
            self.PlexManager._wait_for_libraries()
            
        threading.Thread(target=fetch_libraries_thread).start()

    def add_1_to_libraries_selected(self, widget, value):
        self.libraries_selected += 1
        if self.libraries_selected == 2:
            self.show_continue_button()

    def show_continue_button(self):
        self.continue_button.style['display'] = 'block'
        self.skip_button.style['display'] = 'none'

    def update_dropdown(self):
        try:
            message = self.redis_queue.get_nowait()
            if message['channel'].decode('utf-8') == 'plex_servers':
                server_list = json.loads(message['data'].decode('utf-8'))
                for server in server_list:
                    self.plex_server_dropdown.append(gui.DropDownItem(server))
            else:
                self.redis_queue.put(message)
        except Empty:
            self.after(100, self.update_dropdown)

    def update_library_dropdowns(self):
        try:
            message = self.redis_queue.get_nowait()
            if message['channel'].decode('utf-8') == 'plex_libraries':
                library_list = json.loads(message['data'].decode('utf-8'))
                for library in library_list:
                    self.plex_anime_library_dropdown.append(gui.DropDownItem(library))
                    self.plex_library_dropdown.append(gui.DropDownItem(library))
            else:
                self.redis_queue.put(message)
        except Empty:
            self.after(100, self.update_library_dropdowns)

    def on_continue_button_click(self, widget):
        selected_anime_library = self.plex_anime_library_dropdown.get_value()
        selected_toonami_library = self.plex_library_dropdown.get_value()
        platform_url = self.platform_url_entry.get_value()
        
        self.logic._set_data("selected_anime_library", selected_anime_library)
        self.logic._set_data("selected_toonami_library", selected_toonami_library)
        self.logic._set_data("platform_url", platform_url)
        self.logic._set_data("platform_type", self.selected_platform)
        self.logic._broadcast_status_update("Idle")
        self.app.visited_page2 = False
        self.app.set_current_page('Page3')

    def handle_redis_message(self, channel, data):
        if channel == 'plex_auth_url':
            #open the Plex auth URL via javascript
            self.app.execute_javascript(f"window.open('{data}', '_blank')")
            print(f"Opening Plex auth URL: {data}")
        elif channel == 'new_server_choices':
            self.update_dropdown()
        elif channel == 'new_library_choices':
            self.update_library_dropdowns()

    def on_skip_button_click(self, widget):
        # Skip button should take us to Manual Setup (Page2)
        self.app.visited_page2 = True
        self.app.set_current_page('Page2')

class Page2(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page2, self).__init__(app, 'Page2', *args, **kwargs)
        self.logic = LogicController()
        self.selected_platform = 'dizquetv'  # Default selection

        # Plex URL Entry
        self.plex_url_entry = self.add_labeled_input(self.main_container, 'Plex URL:', "e.g., http://localhost:32400")

        # Plex Token Entry
        self.plex_token_entry = self.add_labeled_input(self.main_container, 'Plex Token:', "e.g., xxxxxxxxxxxxxx")

        # Plex Anime Library Entry
        self.plex_anime_library_entry = self.add_labeled_input(self.main_container, 'Plex Anime Library:', "e.g., Anime")

        # Plex Toonami Library Entry
        self.plex_toonami_library_entry = self.add_labeled_input(self.main_container, 'Plex Toonami Library:', "e.g., Toonami")

        # Platform Selection
        platform_container = gui.HBox(style={
            'justify-content': 'center',
            'margin': '20px',
            'gap': '20px',
            'background': 'transparent',
            'background-color': 'transparent'
        })
        self.add_label(platform_container, "Select Platform:")
        
        # Create platform selection buttons
        self.dizquetv_button = gui.Button("DizqueTV", width=150, height=40, style=Styles.selected_button_style)
        self.tunarr_button = gui.Button("Tunarr", width=150, height=40, style=Styles.unselected_button_style)
        
        self.dizquetv_button.onclick.do(lambda w: self.on_platform_change('dizquetv'))
        self.tunarr_button.onclick.do(lambda w: self.on_platform_change('tunarr'))
        
        platform_container.append([self.dizquetv_button, self.tunarr_button])
        
        self.main_container.append(platform_container)

        # Platform URL Entry
        self.platform_url_entry = self.add_labeled_input(self.main_container, 'Platform URL:', "e.g., http://localhost:17685")

        # Continue button
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')

    def on_platform_change(self, platform):
        """Handle platform selection button clicks"""
        self.selected_platform = platform
        if platform == 'dizquetv':
            self.dizquetv_button.style.update(Styles.selected_button_style)
            self.tunarr_button.style.update(Styles.unselected_button_style)
            self.platform_url_entry.set_value("e.g., http://localhost:17685")
        else:
            self.dizquetv_button.style.update(Styles.unselected_button_style)
            self.tunarr_button.style.update(Styles.selected_button_style)
            self.platform_url_entry.set_value("e.g., http://localhost:8000")

    def on_continue_button_click(self, widget):
        self.logic = LogicController()
        plex_url = self.plex_url_entry.get_value()
        plex_token = self.plex_token_entry.get_value()
        plex_anime_library = self.plex_anime_library_entry.get_value()
        plex_toonami_library = self.plex_toonami_library_entry.get_value()
        platform_url = self.platform_url_entry.get_value()
        platform_type = self.selected_platform        
        self.logic.on_continue_second(plex_url, plex_token, plex_anime_library, plex_toonami_library, platform_url, platform_type)
        self.app.visited_page2 = True
        self.app.set_current_page('Page3')

class Page3(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page3, self).__init__(app, 'Page3', *args, **kwargs)
        self.logic = LogicController()
        self.ToonamiChecker = ToonamiTools.ToonamiChecker
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

        # Prepare Content button
        self.add_label(self.main_container, "Prepare my shows and bumps to be cut")
        self.prepare_button = self.add_button_with_style(self.main_container, "Prepare Content", self.prepare_content, 'primary')

        # Get Plex Timestamps button
        self.add_label(self.main_container, "Get Plex Timestamps")
        self.get_plex_timestamps_button = self.add_button_with_style(self.main_container, "Get Plex Timestamps", self.get_plex_timestamps, 'primary')

        # Move Filtered Shows button
        self.add_label(self.main_container, "Move Filtered Shows")
        self.move_filtered_shows_button = self.add_button_with_style(self.main_container, "Move Filtered Shows", self.move_filtered, 'primary')

        # Remove individual status label since we now use the global one in BasePage

        # Continue button
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')

    def get_plex_timestamps(self, widget):
        self.logic.get_plex_timestamps()

    def move_filtered(self, widget):
        self.logic.move_filtered()

    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page4')

    def prepare_content(self, widget):
        self.logic = LogicController()
        self.logic._broadcast_status_update("Preparing bumps...")
        working_folder = self.logic._get_data("working_folder")
        anime_folder = self.logic._get_data("anime_folder")
        fmaker = ToonamiTools.FolderMaker(working_folder)
        easy_checker = self.ToonamiChecker(anime_folder)
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
            self.logic._broadcast_status_update("Prepare content failed. Please try again.")
            raise Exception("Failed to run easy_checker")

    def prepare_content_continue(self):
        self.logic = LogicController()
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
        merger_bumps_list_1 = 'multibumps_v2_data_reordered'
        merger_bumps_list_2 = 'multibumps_v3_data_reordered'
        merger_bumps_list_3 = 'multibumps_v9_data_reordered'
        merger_bumps_list_4 = 'multibumps_v8_data_reordered'
        merger_out_1 = 'lineup_v2_uncut'
        merger_out_2 = 'lineup_v3_uncut'
        merger_out_3 = 'lineup_v9_uncut'
        merger_out_4 = 'lineup_v8_uncut'
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
        merger.run(merger_bumps_list_1, uncut_encoder_out, merger_out_1)
        merger.run(merger_bumps_list_2, uncut_encoder_out, merger_out_2)
        merger.run(merger_bumps_list_3, uncut_encoder_out, merger_out_3)
        merger.run(merger_bumps_list_4, uncut_encoder_out, merger_out_4)
        
        # Update status when complete
        self.logic._broadcast_status_update("Content preparation complete")

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

    def handle_redis_message(self, channel, data):
        pass

    def toggle_all_checkboxes(self, state):
        for checkbox in self.checkboxes.values():
            checkbox.set_value(state)

class Page4(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page4, self).__init__(app, 'Page4', *args, **kwargs)
        self.cblogic = CommercialBreakerLogic()
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

        # Initialize the working folder and default directories
        self.working_folder = self.logic._get_data("working_folder")
        self.default_input_folder = f"{self.working_folder}/toonami_filtered"
        self.default_output_folder = f"{self.working_folder}/cut"

        # Create variables for input and output directories with defaults
        self.input_path = self.default_input_folder
        self.output_path = self.default_output_folder

        # Initialize input fields with default values pre-filled
        self.input_path_input = self.add_labeled_input(self.main_container, "Input directory:", self.default_input_folder)
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
        buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '20px',
            'background': 'transparent',
            'background-color': 'transparent'
        })

        detect_button = self.add_button_with_style(buttons_container, "Detect", self.detect_commercials, 'primary')
        cut_button = self.add_button_with_style(buttons_container, "Cut", self.cut_videos, 'primary')
        delete_button = self.add_button_with_style(buttons_container, "Delete", self.delete_txt_files, 'primary')

        self.main_container.append(buttons_container)

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

    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page5')

    # Checkbox event handlers
    def on_destructive_mode_changed(self, widget, value):
        self.destructive_mode = value

    def on_fast_mode_changed(self, widget, value):
        if value:
            self.low_power_checkbox.set_value(False)
            self.low_power_mode = False
        self.fast_mode = value

    def on_low_power_mode_changed(self, widget, value):
        if value:
            self.fast_checkbox.set_value(False)
            self.fast_mode = False
        self.low_power_mode = value

    # Methods for action buttons
    def detect_commercials(self, widget):
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(
                self.cblogic.detect_commercials,
                self.done_detect_commercials,
                "Detect Black Frames",
                False,
                self.low_power_mode,
                self.fast_mode,
                self.reset_progress_bar
            )).start()

    def cut_videos(self, widget):
        if self.validate_input_output_dirs():
            threading.Thread(target=self._run_and_notify, args=(
                self.cblogic.cut_videos,
                self.done_cut_videos,
                "Cut Video",
                self.destructive_mode
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
        # Forward status update to Redis if applicable
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
        self.input_path = self.input_path_input.get_value()
        self.output_path = self.output_path_input.get_value()
        if not (self.input_path and self.output_path):
            self.update_status("Please specify an input and output directory.")
            return False
        if not os.path.isdir(self.input_path):
            self.update_status("Input directory does not exist.")
            return False
        if not os.access(self.output_path, os.W_OK):
            self.update_status("Output directory is not writable.")
            return False
        return True

    def _run_and_notify(self, task, done_callback, task_name, destructive_mode=False, low_power_mode=False, fast_mode=False, reset_callback=None):
        """Run a task and update UI with progress"""
        # Reset progress before starting
        self.reset_progress_bar()
        
        # Update status display with task start info
        self.update_status(f"Started task: {task_name}")
        
        # Get current values from input fields
        current_input_path = self.input_path_input.get_value()
        current_output_path = self.output_path_input.get_value()
        
        try:
            # Run the appropriate task with progress callback
            if task_name == "Detect Black Frames":
                task(current_input_path, current_output_path, self.update_progress, 
                     self.update_status, low_power_mode, fast_mode, reset_callback)
            elif task_name == "Cut Video":
                task(current_input_path, current_output_path, self.update_progress, 
                     self.update_status, destructive_mode)
            
            # Task completed successfully
            self.update_status(f"Finished task: {task_name}")
            done_callback(task_name)
        except Exception as e:
            # Handle errors
            error_message = f"Error in {task_name}: {str(e)}"
            self.update_status(error_message)
            print(error_message)

    def done_cut_videos(self, task_name):
        self.update_status(f"{task_name} - Done!")

    def done_detect_commercials(self, task_name):
        self.update_status(f"{task_name} - Done!")

    def execute_in_main_thread(self, func, *args):
        self.app.execute_javascript(f"window.pywebview.api.{func.__name__}({args})")

class Page5(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page5, self).__init__(app, 'Page5', *args, **kwargs)
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

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
        self.add_label(self.main_container, "Prepare Plex")
        self.prepare_plex_button = self.add_button_with_style(self.main_container, "Prepare Plex", self.create_prepare_plex, 'primary')

        # Create Toonami Channel button
        self.add_label(self.main_container, "Create Toonami Channel")
        self.create_toonami_channel_button = self.add_button_with_style(self.main_container, "Create Toonami Channel", self.create_toonami_channel, 'primary')

        # Add Flex button
        self.add_label(self.main_container, "Add Flex")
        self.add_flex_button = self.add_button_with_style(self.main_container, "Add Flex", self.add_flex, 'primary')

        # Remove individual status label since we now use the global one in BasePage

        # Continue button
        self.continue_button = self.add_button_with_style(self.main_container, "Continue", self.on_continue_button_click, 'secondary')

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
        self.app.set_current_page('Page6')

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    def add_flex(self, widget):
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.add_flex(channel_number, flex_duration)

    def handle_redis_message(self, channel, data):
        pass

class Page6(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page6, self).__init__(app, 'Page6', *args, **kwargs)
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)
        self.logic._broadcast_status_update("Idle")

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

    def prepare_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        start_from_last_episode = self.start_from_last_episode_checkbox.get_value()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    def add_flex(self, widget):
        channel_number = self.channel_number_entry.get_value()
        flex_duration = self.flex_duration_entry.get_value()
        self.logic.add_flex(channel_number, flex_duration)

    def handle_redis_message(self, channel, data):
        pass

class MainApp(App):
    def __init__(self, *args, **kwargs):
        self.page_titles = {
            "Page1": "Step 1 - Login to Plex - Welcome to the Absolution",
            "Page2": "Step 1 - Enter Details - A Little Detour",
            "Page3": "Step 2 - Prepare Content - Intruder Alert",
            "Page4": "Step 3 - Commercial Breaker - Toonami Will Be Right Back",
            "Page5": "Step 4 - Create your Toonami Channel - All aboard the Absolution",
            "Page6": "Step 5 - Let's Make Another Channel! - Toonami's Back Bitches"
        }
        
        # Track whether Page2 was ever visited
        self.visited_page2 = False
        
        # Keep track of navigation history for proper back button behavior
        self.navigation_history = []
        
        # Custom page flow to respect skipping of optional Page2
        self.page_flow = {
            'Page1': None,  # No previous page
            'Page2': 'Page1',
            'Page3': 'Page1',  # Default if Page2 wasn't used
            'Page4': 'Page3',
            'Page5': 'Page4',
            'Page6': 'Page5'
        }
        
        super(MainApp, self).__init__(*args, **kwargs)

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
        }
        
        self.set_current_page('Page1')
        return self.container

    def set_current_page(self, page_name):
        if page_name in self.pages:
            # Mark Page2 as visited if we're going there
            if page_name == 'Page2':
                self.visited_page2 = True
                
                # Refresh all navigation bars to reflect this change
                for page_id, page in self.pages.items():
                    if hasattr(page, 'refresh_nav_bar'):
                        page.refresh_nav_bar()
            
            # Add to navigation history
            self.navigation_history.append(page_name)
            
            # Clear the container and add the new page
            self.container.empty()
            self.container.append(self.pages[page_name])
            
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
    
    def go_back(self):
        # Must have at least two pages in history to go back
        if len(self.navigation_history) <= 1:
            return
            
        # Remove current page from history
        current_page = self.navigation_history.pop()  
        previous_page = self.navigation_history[-1]  # Get the previous page
        
        # Special handling for Page3 going back
        if current_page == 'Page3' and previous_page == 'Page2' and not self.visited_page2:
            # Skip back to Page1 if we never actually visited Page2
            self.navigation_history.pop()  # Remove Page2 from history
            previous_page = 'Page1'
            
        # Go to the previous page - we need to pop again since set_current_page will add it
        self.navigation_history.pop()
        self.set_current_page(previous_page)
    
    def start_over(self):
        # Reset visited_page2 flag
        self.visited_page2 = False
        
        # Refresh all navigation bars to reflect this change
        for page_id, page in self.pages.items():
            if hasattr(page, 'refresh_nav_bar'):
                page.refresh_nav_bar()
        
        # Clear history and go to Page1
        self.navigation_history = []
        self.set_current_page('Page1')

def WebServer():
    # Starts the webserver
    start(MainApp, address='0.0.0.0', port=8081, start_browser=True)

if __name__ == "__main__":
    WebServer()