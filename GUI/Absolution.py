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
import config

class BasePage(gui.Container):
    def __init__(self, app, title_key, *args, **kwargs):
        super(BasePage, self).__init__(*args, **kwargs)
        self.app = app
        self.set_size(800, 600)
        # Debugging line to check what gets retrieved
        print(f"Retrieving title for {title_key}: {getattr(app, 'page_titles', {}).get(title_key, 'No title found')}")
        title = getattr(app, 'page_titles', {}).get(title_key, "No title found")
        self.lbl = gui.Label(title)
        self.append(self.lbl)

class RedisListenerMixin:
    def after(self, time_ms, callback):
        # Wait for time in milliseconds then call callback
        threading.Timer(time_ms / 1000, callback).start()

    def process_redis_messages(self):
        while not self.redis_queue.empty():
            message = self.redis_queue.get()
            channel = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')

            if channel == 'status_updates':
                self.update_status_label(data)
            elif hasattr(self, 'handle_redis_message'):
                # Allow pages to handle additional messages
                self.handle_redis_message(channel, data)

        self.after(100, self.process_redis_messages)

    def listen_for_redis_updates(self, redis_queue):
        redis_client = self.logic.redis_client
        pubsub = redis_client.pubsub()
        pubsub.subscribe('status_updates', 'new_server_choices', 'new_library_choices', 'plex_servers', 'plex_libraries')

        for message in pubsub.listen():
            if message['type'] == 'message':
                redis_queue.put(message)

    def start_redis_listener_thread(self, redis_queue):
        threading.Thread(target=self.listen_for_redis_updates, args=(redis_queue,), daemon=True).start()

    def update_status_label(self, status):
        self.status_label.set_text(f"Status: {status}")

class Page1(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page1, self).__init__(app, 'Page1', *args, **kwargs)
        # Label for login instruction
        label = gui.Label("Login with Plex", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.logic = LogicController()
        self.PlexManager = PlexManager(self.logic)
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)
        self.libraries_selected = 0

        # Login button
        login_with_plex_button = gui.Button("Login with Plex", width=200, height=30)
        login_with_plex_button.onclick.do(self.login_to_plex)
        self.append(login_with_plex_button)

        # Dropdown for Plex Servers
        self.plex_server_dropdown = gui.DropDown(width='100%')
        self.plex_server_dropdown.append(gui.DropDownItem("Select a Plex Server"))
        self.plex_server_dropdown.onchange.do(self.on_server_selected)
        self.append(self.plex_server_dropdown)

        # Dropdown for Anime Library
        self.plex_anime_library_dropdown = gui.DropDown(width='100%')
        self.plex_anime_library_dropdown.append(gui.DropDownItem("Select your Anime Library"))
        self.plex_anime_library_dropdown.onchange.do(self.add_1_to_libraries_selected)
        self.append(self.plex_anime_library_dropdown)

        # Dropdown for Toonami Library
        self.plex_library_dropdown = gui.DropDown(width='100%')
        self.plex_library_dropdown.append(gui.DropDownItem("Select your Toonami Library"))
        self.plex_library_dropdown.onchange.do(self.add_1_to_libraries_selected)
        self.append(self.plex_library_dropdown)

        # DizqueTV URL Entry
        dizquetv_url_label = gui.Label('dizqueTV URL:', width='100%')
        self.append(dizquetv_url_label)
        self.dizquetv_url_entry = gui.Input(input_type='text', width='100%')
        self.dizquetv_url_entry.set_value("eg. http://localhost:17685")
        self.append(self.dizquetv_url_entry)

        # Status label
        self.status_label = gui.Label("Status: Idle", width='100%')
        self.append(self.status_label)

        # Continue and Skip buttons
        self.continue_button = gui.Button("Continue", width=200, height=30)
        self.continue_button.onclick.do(self.on_continue_button_click)
        self.continue_button.style['display'] = 'none'  # Initially hide continue button
        self.append(self.continue_button)

        self.skip_button = gui.Button("Skip", width=200, height=30)
        self.skip_button.onclick.do(lambda x: self.app.set_current_page('Page2'))
        self.append(self.skip_button)

    def login_to_plex(self, widget):
        self.logic.login_to_plex()
        self.PlexManager._wait_for_servers()
        self.update_dropdown()

    def on_server_selected(self, widget, value):
        self.selected_server = self.plex_server_dropdown.get_value()
        print(f"Selected server: {self.selected_server}")
        self.logic.on_server_selected(self.selected_server)
        self.PlexManager._wait_for_libraries()
        self.update_library_dropdowns()

    def add_1_to_libraries_selected(self, widget, value):
        self.libraries_selected += 1
        if self.libraries_selected == 2:
            self.show_continue_button()

    def show_continue_button(self):
        self.continue_button.style['display'] = 'block'
        self.skip_button.style['display'] = 'none'

    def update_dropdown(self):
        try:
            # Attempt to get the message without blocking
            message = self.redis_queue.get_nowait()
            if message['channel'].decode('utf-8') == 'plex_servers':
                # Decode and load data from the message
                server_list = json.loads(message['data'].decode('utf-8'))
                for server in server_list:
                    self.plex_server_dropdown.append(gui.DropDownItem(server))
            else:
                # If the message is not the one we are looking for, put it back
                self.redis_queue.put(message)
        except Empty:
            # If no messages, reschedule to try again in 100 milliseconds
            self.after(100, self.update_dropdown)

    def update_library_dropdowns(self):
        try:
            # Attempt to get the message without blocking
            message = self.redis_queue.get_nowait()
            if message['channel'].decode('utf-8') == 'plex_libraries':
                # Decode and load data from the message
                library_list = json.loads(message['data'].decode('utf-8'))
                for library in library_list:
                    self.plex_anime_library_dropdown.append(gui.DropDownItem(library))
                    self.plex_library_dropdown.append(gui.DropDownItem(library))
            else:
                # If the message is not the one we are looking for, put it back
                self.redis_queue.put(message)
        except Empty:
            # If no messages, reschedule to try again in 100 milliseconds
            self.after(100, self.update_library_dropdowns)

    def on_continue_button_click(self, widget):
        selected_anime_library = self.plex_anime_library_dropdown.get_value()
        selected_toonami_library = self.plex_library_dropdown.get_value()
        dizquetv_url = self.dizquetv_url_entry.get_value()
        self.logic._set_data("selected_anime_library", selected_anime_library)
        self.logic._set_data("selected_toonami_library", selected_toonami_library)
        self.logic._set_data("dizquetv_url", dizquetv_url)
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page3')

    # Optional: Handle additional Redis messages specific to this page
    def handle_redis_message(self, channel, data):
        if channel == 'new_server_choices':
            self.update_dropdown()
        elif channel == 'new_library_choices':
            self.update_library_dropdowns()

class Page2(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page2, self).__init__(app, 'Page2', *args, **kwargs)
        # plex url entry
        plex_url_label = gui.Label('Plex URL:', width='100%')
        self.append(plex_url_label)
        self.plex_url_entry = gui.Input(input_type='text', width='100%')
        self.plex_url_entry.set_value("eg. http://localhost:32400")
        self.append(self.plex_url_entry)

        # plex token entry
        plex_token_label = gui.Label('Plex Token:', width='100%')
        self.append(plex_token_label)
        self.plex_token_entry = gui.Input(input_type='text', width='100%')
        self.plex_token_entry.set_value("eg. xxxxxxxxxxxxxx")
        self.append(self.plex_token_entry)

        # plex anime library entry
        plex_anime_library_label = gui.Label('Plex Anime Library:', width='100%')
        self.append(plex_anime_library_label)
        self.plex_anime_library_entry = gui.Input(input_type='text', width='100%')
        self.plex_anime_library_entry.set_value("eg. Anime")
        self.append(self.plex_anime_library_entry)

        # plex toonami library entry
        plex_toonami_library_label = gui.Label('Plex Toonami Library:', width='100%')
        self.append(plex_toonami_library_label)
        self.plex_toonami_library_entry = gui.Input(input_type='text', width='100%')
        self.plex_toonami_library_entry.set_value("eg. Toonami")
        self.append(self.plex_toonami_library_entry)

        # dizquetv url entry
        dizquetv_url_label = gui.Label('dizqueTV URL:', width='100%')
        self.append(dizquetv_url_label)
        self.dizquetv_url_entry = gui.Input(input_type='text', width='100%')
        self.dizquetv_url_entry.set_value("eg. http://localhost:17685")
        self.append(self.dizquetv_url_entry)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30)
        self.continue_button.onclick.do(self.on_continue_button_click)
        self.append(self.continue_button)

    def on_continue_button_click(self, widget):
        self.logic = LogicController()
        plex_url = self.plex_url_entry.get_value()
        plex_token = self.plex_token_entry.get_value()
        plex_anime_library = self.plex_anime_library_entry.get_value()
        plex_toonami_library = self.plex_toonami_library_entry.get_value()
        dizquetv_url = self.dizquetv_url_entry.get_value()
        self.logic.on_continue_second(plex_url, plex_token, plex_anime_library, plex_toonami_library, dizquetv_url)
        self.app.set_current_page('Page3')

class Page3(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page3, self).__init__(app, 'Page3', *args, **kwargs)
        self.logic = LogicController()
        self.ToonamiChecker = ToonamiTools.ToonamiChecker
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

        # Label for content preparation
        label = gui.Label("Prepare my shows and bumps to be cut", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.prepare_button = gui.Button("Prepare Content", width=200, height=30)
        self.prepare_button.onclick.do(self.prepare_content)
        self.append(self.prepare_button)

        # Label for content get plex timestamps
        label = gui.Label("Get Plex Timestamps", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.get_plex_timestamps_button = gui.Button("Get Plex Timestamps", width=200, height=30)
        self.get_plex_timestamps_button.onclick.do(self.logic.get_plex_timestamps)
        self.append(self.get_plex_timestamps_button)

        # Label for move filtered shows
        label = gui.Label("Move Filtered Shows", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.move_filtered_shows_button = gui.Button("Move Filtered Shows", width=200, height=30)
        self.move_filtered_shows_button.onclick.do(self.logic.move_filtered)
        self.append(self.move_filtered_shows_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", width='100%')
        self.append(self.status_label)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30)
        self.continue_button.onclick.do(lambda x: self.app.set_current_page('Page5'))
        self.continue_button.onclick.do(lambda x: self.logic._broadcast_status_update("Idle"))
        self.append(self.continue_button)

    def prepare_content(self, widget):
        self.logic = LogicController()
        self.logic._broadcast_status_update("Preparing bumps...")
        working_folder = self.logic._get_data("working_folder")
        anime_folder = self.logic._get_data("anime_folder")
        fmaker = ToonamiTools.FolderMaker(working_folder)
        easy_checker = self.ToonamiChecker(anime_folder)
        fmaker.run()
        # Run easy_checker with retries
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
        self.logic._broadcast_status_update("Preparing uncut lineup...")
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
        self.logic._broadcast_status_update("Content preparation complete")

    def display_show_selection(self, unique_show_names, easy_checker, toonami_episodes):
        self.selection_container = gui.VBox()
        self.checkboxes = {}

        for show in unique_show_names:
            checkbox = gui.CheckBox(checked=True)  # Set the checkbox to be checked by default
            checkbox_label = gui.Label(show)
            self.checkboxes[show] = checkbox
            self.selection_container.append(gui.HBox(children=[checkbox, checkbox_label]))

        done_button = gui.Button("Done", width=200, height=30)
        done_button.onclick.do(self.on_done_button_clicked, easy_checker, toonami_episodes)
        self.selection_container.append(done_button)
        self.append(self.selection_container)
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
        self.remove_child(self.selection_container)
        self.prepare_content_continue()

    # Optional: Handle additional Redis messages specific to this page
    def handle_redis_message(self, channel, data):
        pass  # No additional messages to handle in this page

class Page4(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page4, self).__init__(app, 'Page4', *args, **kwargs)
        self.next_button = gui.Button("Next", width=200, height=30)
        self.next_button.onclick.do(lambda x: self.app.set_current_page('Page5'))
        self.append(self.next_button)

        # Commercial Breaker goes here

class Page5(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page5, self).__init__(app, 'Page5', *args, **kwargs)
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

        # Drop-down menu with options
        label = gui.Label("What Toonami Version are you making today?", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        options = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = gui.DropDown(width='100%')
        self.toonami_version_dropdown.append(gui.DropDownItem("Select a Toonami Version"))
        for option in options:
            self.toonami_version_dropdown.append(gui.DropDownItem(option))
        self.append(self.toonami_version_dropdown)

        # Channel number entry
        label = gui.Label("What channel number do you want to use?", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.channel_number_entry = gui.Input(input_type='text', width='100%')
        self.channel_number_entry.set_value("eg. 60")
        self.append(self.channel_number_entry)

        # Prepare cut anime for lineup
        label = gui.Label("Prepare Cut Anime for Lineup", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.prepare_cut_anime_button = gui.Button("Prepare Cut Anime for Lineup", width=200, height=30)
        self.prepare_cut_anime_button.onclick.do(self.logic.prepare_cut_anime)
        self.append(self.prepare_cut_anime_button)

        # Add special bumps to sheet
        label = gui.Label("Add Special Bumps to Sheet", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.add_special_bumps_button = gui.Button("Add Special Bumps to Sheet", width=200, height=30)
        self.add_special_bumps_button.onclick.do(self.logic.add_special_bumps)
        self.append(self.add_special_bumps_button)

        # Prepare Plex
        label = gui.Label("Prepare Plex", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.prepare_plex_button = gui.Button("Prepare Plex", width=200, height=30)
        self.prepare_plex_button.onclick.do(self.logic.create_prepare_plex)
        self.append(self.prepare_plex_button)

        # Create Toonami Channel
        label = gui.Label("Create Toonami Channel", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.create_toonami_channel_button = gui.Button("Create Toonami Channel", width=200, height=30)
        self.create_toonami_channel_button.onclick.do(self.create_toonami_channel)
        self.append(self.create_toonami_channel_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", width='100%')
        self.append(self.status_label)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30)
        self.continue_button.onclick.do(lambda x: self.app.set_current_page('Page6'))
        self.continue_button.onclick.do(lambda x: self.logic._broadcast_status_update("Idle"))
        self.append(self.continue_button)

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    # Optional: Handle additional Redis messages specific to this page
    def handle_redis_message(self, channel, data):
        pass  # No additional messages to handle in this page

class Page6(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page6, self).__init__(app, 'Page6', *args, **kwargs)
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)
        self.logic._broadcast_status_update("Idle")

        # Toonami version selection
        label = gui.Label("What Toonami Version are you making today?", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        options = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = gui.DropDown(width='100%')
        self.toonami_version_dropdown.append(gui.DropDownItem("Select a Toonami Version"))
        for option in options:
            self.toonami_version_dropdown.append(gui.DropDownItem(option))
        self.append(self.toonami_version_dropdown)

        # Channel number entry
        label = gui.Label("What channel number do you want to use?", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.channel_number_entry = gui.Input(input_type='text', width='100%')
        self.channel_number_entry.set_value("eg. 60")
        self.append(self.channel_number_entry)

        # Start from last episode checkbox
        label = gui.Label("Start from last episode?", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.start_from_last_episode_checkbox = gui.CheckBox()
        self.start_from_last_episode_checkbox.set_value(False)
        self.append(self.start_from_last_episode_checkbox)

        # Prepare toonami channel
        label = gui.Label("Prepare Toonami Channel", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.prepare_toonami_channel_button = gui.Button("Prepare Toonami Channel", width=200, height=30)
        self.prepare_toonami_channel_button.onclick.do(self.prepare_toonami_channel)
        self.append(self.prepare_toonami_channel_button)

        # Create toonami channel
        label = gui.Label("Create Toonami Channel", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)
        self.create_toonami_channel_button = gui.Button("Create Toonami Channel", width=200, height=30)
        self.create_toonami_channel_button.onclick.do(self.create_toonami_channel)
        self.append(self.create_toonami_channel_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", width='100%')
        self.append(self.status_label)

        # Next button
        self.next_button = gui.Button("Next", width=200, height=30)
        self.next_button.onclick.do(lambda x: self.app.set_current_page('Page7'))
        self.next_button.onclick.do(lambda x: self.logic._broadcast_status_update("Idle"))
        self.append(self.next_button)

    def prepare_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        start_from_last_episode = self.start_from_last_episode_checkbox.get_value()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    # Optional: Handle additional Redis messages specific to this page
    def handle_redis_message(self, channel, data):
        pass  # No additional messages to handle in this page

class Page7(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page7, self).__init__(app, 'Page7', *args, **kwargs)
        self.logic = LogicController()
        self.logic._broadcast_status_update("Idle")

        # Flex your toonami channel
        label = gui.Label("Flex Your Toonami Channel", style={'font-size': '24px', 'padding': '10px'})
        self.append(label)

        # TODO: Implement functionality for flexing the Toonami channel

class MainApp(App):
    def __init__(self, *args, **kwargs):
        self.page_titles = {
            "Page1": "Step 1 - Login to Plex - Welcome to the Absolution",
            "Page2": "Step 1 - Enter Details - A Little Detour",
            "Page3": "Step 2 - Prepare Content - Intruder Alert",
            "Page4": "Step 3 - Commercial Breaker - Toonami Will Be Right Back",
            "Page5": "Step 4 - Create your Toonami Channel - All aboard the Absolution",
            "Page6": "Step 5 - Let's Make Another Channel! - Toonami's Back Bitches",
            "Page7": "Step 6 - Flex Your Toonami Channel - Commercial Break"
        }
        super(MainApp, self).__init__(*args, **kwargs)

    def main(self):
        self.container = gui.Container(width='100%', height='100%')
        self.pages = {
            'Page1': Page1(self),
            'Page2': Page2(self),
            'Page3': Page3(self),
            'Page4': Page4(self),
            'Page5': Page5(self),
            'Page6': Page6(self),
            'Page7': Page7(self),
        }
        self.set_current_page('Page1')
        return self.container

    def set_current_page(self, page_name):
        if page_name in self.pages:
            self.container.empty()
            self.container.append(self.pages[page_name])

def WebServer():
    # Starts the webserver
    start(MainApp, address='0.0.0.0', port=8081, start_browser=True)

if __name__ == "__main__":
    WebServer()
