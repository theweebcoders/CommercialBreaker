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
        'font-size': '16px',
        'padding': '5px',
        'margin': '5px'
    }
    title_label_style = {
        'font-size': '24px',
        'padding': '10px',
        'font-weight': 'bold',
        'margin': '10px'
    }
    default_button_style = {
        'font-size': '16px',
        'padding': '10px',
        'margin': '5px'
    }
    default_input_style = {
        'font-size': '16px',
        'padding': '5px',
        'margin': '5px',
        'width': '100%'
    }
    default_container_style = {
        'display': 'flex',
        'flex-direction': 'column',
        'align-items': 'center',
        'justify-content': 'flex-start',
        'width': '100%',
        'height': '100%',
        'background-color': '#F0F0F0',
        'overflow': 'auto'
    }

class BasePage(gui.Container):
    def __init__(self, app, title_key, *args, **kwargs):
        super(BasePage, self).__init__(*args, **kwargs)
        self.app = app
        self.set_size('100%', '100%')
        self.style.update(Styles.default_container_style)

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
        self.logic = LogicController()
        self.PlexManager = PlexManager(self.logic)
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)
        self.libraries_selected = 0

        # Main container for the page
        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page1', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Label for login instruction
        label = gui.Label("Login with Plex", style=Styles.default_label_style)
        main_container.append(label)

        # Login button
        login_with_plex_button = gui.Button("Login with Plex", width=200, height=30, style=Styles.default_button_style)
        login_with_plex_button.onclick.do(self.login_to_plex)
        main_container.append(login_with_plex_button)

        # Dropdown for Plex Servers
        self.plex_server_dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        self.plex_server_dropdown.append(gui.DropDownItem("Select a Plex Server"))
        self.plex_server_dropdown.onchange.do(self.on_server_selected)
        main_container.append(self.plex_server_dropdown)

        # Dropdown for Anime Library
        self.plex_anime_library_dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        self.plex_anime_library_dropdown.append(gui.DropDownItem("Select your Anime Library"))
        self.plex_anime_library_dropdown.onchange.do(self.add_1_to_libraries_selected)
        main_container.append(self.plex_anime_library_dropdown)

        # Dropdown for Toonami Library
        self.plex_library_dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        self.plex_library_dropdown.append(gui.DropDownItem("Select your Toonami Library"))
        self.plex_library_dropdown.onchange.do(self.add_1_to_libraries_selected)
        main_container.append(self.plex_library_dropdown)

        # DizqueTV URL Entry
        dizquetv_url_label = gui.Label('dizqueTV URL:', style=Styles.default_label_style)
        main_container.append(dizquetv_url_label)
        self.dizquetv_url_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.dizquetv_url_entry.set_value("e.g., http://localhost:17685")
        main_container.append(self.dizquetv_url_entry)

        # Status label
        self.status_label = gui.Label("Status: Idle", style=Styles.default_label_style)
        main_container.append(self.status_label)

        # Continue and Skip buttons
        buttons_container = gui.HBox(style={
            'justify-content': 'center',
            'margin-top': '20px'
        })

        self.continue_button = gui.Button("Continue", width=200, height=30, style=Styles.default_button_style)
        self.continue_button.onclick.do(self.on_continue_button_click)
        self.continue_button.style['display'] = 'none'
        buttons_container.append(self.continue_button)

        self.skip_button = gui.Button("Skip", width=200, height=30, style=Styles.default_button_style)
        self.skip_button.onclick.do(lambda x: self.app.set_current_page('Page2'))
        buttons_container.append(self.skip_button)

        main_container.append(buttons_container)

        self.append(main_container)

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
        dizquetv_url = self.dizquetv_url_entry.get_value()
        self.logic._set_data("selected_anime_library", selected_anime_library)
        self.logic._set_data("selected_toonami_library", selected_toonami_library)
        self.logic._set_data("dizquetv_url", dizquetv_url)
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page3')

    def handle_redis_message(self, channel, data):
        if channel == 'new_server_choices':
            self.update_dropdown()
        elif channel == 'new_library_choices':
            self.update_library_dropdowns()

class Page2(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page2, self).__init__(app, 'Page2', *args, **kwargs)

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page2', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Plex URL Entry
        plex_url_label = gui.Label('Plex URL:', style=Styles.default_label_style)
        main_container.append(plex_url_label)
        self.plex_url_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.plex_url_entry.set_value("e.g., http://localhost:32400")
        main_container.append(self.plex_url_entry)

        # Plex Token Entry
        plex_token_label = gui.Label('Plex Token:', style=Styles.default_label_style)
        main_container.append(plex_token_label)
        self.plex_token_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.plex_token_entry.set_value("e.g., xxxxxxxxxxxxxx")
        main_container.append(self.plex_token_entry)

        # Plex Anime Library Entry
        plex_anime_library_label = gui.Label('Plex Anime Library:', style=Styles.default_label_style)
        main_container.append(plex_anime_library_label)
        self.plex_anime_library_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.plex_anime_library_entry.set_value("e.g., Anime")
        main_container.append(self.plex_anime_library_entry)

        # Plex Toonami Library Entry
        plex_toonami_library_label = gui.Label('Plex Toonami Library:', style=Styles.default_label_style)
        main_container.append(plex_toonami_library_label)
        self.plex_toonami_library_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.plex_toonami_library_entry.set_value("e.g., Toonami")
        main_container.append(self.plex_toonami_library_entry)

        # DizqueTV URL Entry
        dizquetv_url_label = gui.Label('dizqueTV URL:', style=Styles.default_label_style)
        main_container.append(dizquetv_url_label)
        self.dizquetv_url_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.dizquetv_url_entry.set_value("e.g., http://localhost:17685")
        main_container.append(self.dizquetv_url_entry)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30, style=Styles.default_button_style)
        self.continue_button.onclick.do(self.on_continue_button_click)
        main_container.append(self.continue_button)

        self.append(main_container)

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

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page3', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Prepare Content button
        label = gui.Label("Prepare my shows and bumps to be cut", style=Styles.default_label_style)
        main_container.append(label)
        self.prepare_button = gui.Button("Prepare Content", width=200, height=30, style=Styles.default_button_style)
        self.prepare_button.onclick.do(self.prepare_content)
        main_container.append(self.prepare_button)

        # Get Plex Timestamps button
        label = gui.Label("Get Plex Timestamps", style=Styles.default_label_style)
        main_container.append(label)
        self.get_plex_timestamps_button = gui.Button("Get Plex Timestamps", width=200, height=30, style=Styles.default_button_style)
        self.get_plex_timestamps_button.onclick.do(self.logic.get_plex_timestamps)
        main_container.append(self.get_plex_timestamps_button)

        # Move Filtered Shows button
        label = gui.Label("Move Filtered Shows", style=Styles.default_label_style)
        main_container.append(label)
        self.move_filtered_shows_button = gui.Button("Move Filtered Shows", width=200, height=30, style=Styles.default_button_style)
        self.move_filtered_shows_button.onclick.do(self.logic.move_filtered)
        main_container.append(self.move_filtered_shows_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", style=Styles.default_label_style)
        main_container.append(self.status_label)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30, style=Styles.default_button_style)
        self.continue_button.onclick.do(self.on_continue_button_click)
        main_container.append(self.continue_button)

        self.append(main_container)

    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page5')

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
        self.selection_container = gui.VBox(style={'align-items': 'center', 'justify-content': 'center', 'margin-top': '20px'})
        self.checkboxes = {}

        for show in unique_show_names:
            checkbox = gui.CheckBox(checked=True, style={'margin-right': '10px'})
            checkbox_label = gui.Label(show, style=Styles.default_label_style)
            self.checkboxes[show] = checkbox
            hbox = gui.HBox(children=[checkbox, checkbox_label], style={'align-items': 'center'})
            self.selection_container.append(hbox)

        done_button = gui.Button("Done", width=200, height=30, style=Styles.default_button_style)
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

    def handle_redis_message(self, channel, data):
        pass

class Page4(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page4, self).__init__(app, 'Page4', *args, **kwargs)

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'center',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page4', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Next button
        self.next_button = gui.Button("Next", width=200, height=30, style=Styles.default_button_style)
        self.next_button.onclick.do(lambda x: self.app.set_current_page('Page5'))
        main_container.append(self.next_button)

        self.append(main_container)
        # TODO: Implement Commercial Breaker functionality here

class Page5(BasePage, RedisListenerMixin):
    def __init__(self, app, *args, **kwargs):
        super(Page5, self).__init__(app, 'Page5', *args, **kwargs)
        self.logic = LogicController()
        self.redis_queue = Queue()
        self.start_redis_listener_thread(self.redis_queue)
        self.after(100, self.process_redis_messages)

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page5', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Toonami version selection
        label = gui.Label("What Toonami Version are you making today?", style=Styles.default_label_style)
        main_container.append(label)
        options = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        self.toonami_version_dropdown.append(gui.DropDownItem("Select a Toonami Version"))
        for option in options:
            self.toonami_version_dropdown.append(gui.DropDownItem(option))
        main_container.append(self.toonami_version_dropdown)

        # Channel number entry
        label = gui.Label("What channel number do you want to use?", style=Styles.default_label_style)
        main_container.append(label)
        self.channel_number_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.channel_number_entry.set_value("e.g., 60")
        main_container.append(self.channel_number_entry)

        # Prepare Cut Anime for Lineup button
        label = gui.Label("Prepare Cut Anime for Lineup", style=Styles.default_label_style)
        main_container.append(label)
        self.prepare_cut_anime_button = gui.Button("Prepare Cut Anime for Lineup", width=200, height=30, style=Styles.default_button_style)
        self.prepare_cut_anime_button.onclick.do(self.logic.prepare_cut_anime)
        main_container.append(self.prepare_cut_anime_button)

        # Add Special Bumps to Sheet button
        label = gui.Label("Add Special Bumps to Sheet", style=Styles.default_label_style)
        main_container.append(label)
        self.add_special_bumps_button = gui.Button("Add Special Bumps to Sheet", width=200, height=30, style=Styles.default_button_style)
        self.add_special_bumps_button.onclick.do(self.logic.add_special_bumps)
        main_container.append(self.add_special_bumps_button)

        # Prepare Plex button
        label = gui.Label("Prepare Plex", style=Styles.default_label_style)
        main_container.append(label)
        self.prepare_plex_button = gui.Button("Prepare Plex", width=200, height=30, style=Styles.default_button_style)
        self.prepare_plex_button.onclick.do(self.logic.create_prepare_plex)
        main_container.append(self.prepare_plex_button)

        # Create Toonami Channel button
        label = gui.Label("Create Toonami Channel", style=Styles.default_label_style)
        main_container.append(label)
        self.create_toonami_channel_button = gui.Button("Create Toonami Channel", width=200, height=30, style=Styles.default_button_style)
        self.create_toonami_channel_button.onclick.do(self.create_toonami_channel)
        main_container.append(self.create_toonami_channel_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", style=Styles.default_label_style)
        main_container.append(self.status_label)

        # Continue button
        self.continue_button = gui.Button("Continue", width=200, height=30, style=Styles.default_button_style)
        self.continue_button.onclick.do(self.on_continue_button_click)
        main_container.append(self.continue_button)

        self.append(main_container)

    def on_continue_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page6')

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

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

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page6', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Toonami version selection
        label = gui.Label("What Toonami Version are you making today?", style=Styles.default_label_style)
        main_container.append(label)
        options = ["OG", "2", "3", "Mixed", "Uncut OG", "Uncut 2", "Uncut 3", "Uncut Mixed"]
        self.toonami_version_dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        self.toonami_version_dropdown.append(gui.DropDownItem("Select a Toonami Version"))
        for option in options:
            self.toonami_version_dropdown.append(gui.DropDownItem(option))
        main_container.append(self.toonami_version_dropdown)

        # Channel number entry
        label = gui.Label("What channel number do you want to use?", style=Styles.default_label_style)
        main_container.append(label)
        self.channel_number_entry = gui.Input(input_type='text', style=Styles.default_input_style)
        self.channel_number_entry.set_value("e.g., 60")
        main_container.append(self.channel_number_entry)

        # Start from last episode checkbox
        label = gui.Label("Start from last episode?", style=Styles.default_label_style)
        main_container.append(label)
        self.start_from_last_episode_checkbox = gui.CheckBox(style={'margin': '5px'})
        self.start_from_last_episode_checkbox.set_value(False)
        main_container.append(self.start_from_last_episode_checkbox)

        # Prepare Toonami Channel button
        label = gui.Label("Prepare Toonami Channel", style=Styles.default_label_style)
        main_container.append(label)
        self.prepare_toonami_channel_button = gui.Button("Prepare Toonami Channel", width=200, height=30, style=Styles.default_button_style)
        self.prepare_toonami_channel_button.onclick.do(self.prepare_toonami_channel)
        main_container.append(self.prepare_toonami_channel_button)

        # Create Toonami Channel button
        label = gui.Label("Create Toonami Channel", style=Styles.default_label_style)
        main_container.append(label)
        self.create_toonami_channel_button = gui.Button("Create Toonami Channel", width=200, height=30, style=Styles.default_button_style)
        self.create_toonami_channel_button.onclick.do(self.create_toonami_channel)
        main_container.append(self.create_toonami_channel_button)

        # Status label
        self.status_label = gui.Label("Status: Idle", style=Styles.default_label_style)
        main_container.append(self.status_label)

        # Next button
        self.next_button = gui.Button("Next", width=200, height=30, style=Styles.default_button_style)
        self.next_button.onclick.do(self.on_next_button_click)
        main_container.append(self.next_button)

        self.append(main_container)

    def on_next_button_click(self, widget):
        self.logic._broadcast_status_update("Idle")
        self.app.set_current_page('Page7')

    def prepare_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        start_from_last_episode = self.start_from_last_episode_checkbox.get_value()
        self.logic.prepare_toonami_channel(start_from_last_episode, toonami_version)

    def create_toonami_channel(self, widget):
        toonami_version = self.toonami_version_dropdown.get_value()
        channel_number = self.channel_number_entry.get_value()
        self.logic.create_toonami_channel(toonami_version, channel_number)

    def handle_redis_message(self, channel, data):
        pass

class Page7(BasePage):
    def __init__(self, app, *args, **kwargs):
        super(Page7, self).__init__(app, 'Page7', *args, **kwargs)
        self.logic = LogicController()
        self.logic._broadcast_status_update("Idle")

        main_container = gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'center',
            'margin': 'auto',
            'padding': '20px'
        })

        # Page title
        page_title = gui.Label(self.app.page_titles.get('Page7', ''), style=Styles.title_label_style)
        main_container.append(page_title)

        # Flex Your Toonami Channel label
        label = gui.Label("Flex Your Toonami Channel", style=Styles.default_label_style)
        main_container.append(label)

        # TODO: Implement functionality for flexing the Toonami channel

        self.append(main_container)

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
        self.container = gui.Container(width='100%', height='100%', style=Styles.default_container_style)
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
