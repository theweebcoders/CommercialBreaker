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
        self.main_container = self.create_main_container()
        self.append(self.main_container)
        self.add_page_title(self.main_container, self.app.page_titles.get(title_key, ''))

    def create_main_container(self):
        return gui.VBox(width='80%', style={
            'align-items': 'center',
            'justify-content': 'flex-start',
            'margin': 'auto',
            'padding': '20px'
        })

    def add_page_title(self, container, title_text):
        page_title = gui.Label(title_text, style=Styles.title_label_style)
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

    def add_dropdown(self, container, options, onchange_handler=None):
        dropdown = gui.DropDown(width='100%', style=Styles.default_input_style)
        for option in options:
            dropdown.append(gui.DropDownItem(option))
        if onchange_handler:
            dropdown.onchange.do(onchange_handler)
        container.append(dropdown)
        return dropdown

    def add_checkbox(self, container, label_text, default_value=False):
        hbox = gui.HBox(style={'align-items': 'center', 'margin': '5px'})
        checkbox = gui.CheckBox()
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

        # Build the page using helper methods
        self.add_label(self.main_container, "Login with Plex")
        self.login_with_plex_button = self.add_button(self.main_container, "Login with Plex", self.login_to_plex)

        # Plex Servers Dropdown
        self.add_label(self.main_container, "Select a Plex Server")
        self.plex_server_dropdown = self.add_dropdown(self.main_container, ["Select a Plex Server"], self.on_server_selected)

        # Anime Library Dropdown
        self.add_label(self.main_container, "Select your Anime Library")
        self.plex_anime_library_dropdown = self.add_dropdown(self.main_container, ["Select your Anime Library"], self.add_1_to_libraries_selected)

        # Toonami Library Dropdown
        self.add_label(self.main_container, "Select your Toonami Library")
        self.plex_library_dropdown = self.add_dropdown(self.main_container, ["Select your Toonami Library"], self.add_1_to_libraries_selected)

        # DizqueTV URL Entry
        self.dizquetv_url_entry = self.add_labeled_input(self.main_container, "dizqueTV URL:", "e.g., http://localhost:17685")

        # Status label
        self.status_label = self.add_label(self.main_container, "Status: Idle")

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

        self.main_container.append(buttons_container)

    def login_to_plex(self, widget):
        print("You pressed the login button")
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

        # Plex URL Entry
        self.plex_url_entry = self.add_labeled_input(self.main_container, 'Plex URL:', "e.g., http://localhost:32400")

        # Plex Token Entry
        self.plex_token_entry = self.add_labeled_input(self.main_container, 'Plex Token:', "e.g., xxxxxxxxxxxxxx")

        # Plex Anime Library Entry
        self.plex_anime_library_entry = self.add_labeled_input(self.main_container, 'Plex Anime Library:', "e.g., Anime")

        # Plex Toonami Library Entry
        self.plex_toonami_library_entry = self.add_labeled_input(self.main_container, 'Plex Toonami Library:', "e.g., Toonami")

        # DizqueTV URL Entry
        self.dizquetv_url_entry = self.add_labeled_input(self.main_container, 'dizqueTV URL:', "e.g., http://localhost:17685")

        # Continue button
        self.continue_button = self.add_button(self.main_container, "Continue", self.on_continue_button_click)

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

        # Prepare Content button
        self.add_label(self.main_container, "Prepare my shows and bumps to be cut")
        self.prepare_button = self.add_button(self.main_container, "Prepare Content", self.prepare_content)

        # Get Plex Timestamps button
        self.add_label(self.main_container, "Get Plex Timestamps")
        self.get_plex_timestamps_button = self.add_button(self.main_container, "Get Plex Timestamps", self.get_plex_timestamps)

        # Move Filtered Shows button
        self.add_label(self.main_container, "Move Filtered Shows")
        self.move_filtered_shows_button = self.add_button(self.main_container, "Move Filtered Shows", self.move_filtered)

        # Status label
        self.status_label = self.add_label(self.main_container, "Status: Idle")

        # Continue button
        self.continue_button = self.add_button(self.main_container, "Continue", self.on_continue_button_click)

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
        # Sort the list alphabetically (case-insensitive)
        unique_show_names_sorted = sorted(unique_show_names, key=lambda s: s.lower())

        self.selection_container = gui.VBox(style={
            'align-items': 'flex-start',
            'justify-content': 'flex-start',
            'margin-top': '20px',
            'width': '100%',
        })
        self.checkboxes = {}

        label_width = '200px'

        for show in unique_show_names_sorted:
            checkbox = gui.CheckBox(checked=True, style={'margin-right': '10px'})
            checkbox_label = gui.Label(show, style={
                **Styles.default_label_style,
                'width': label_width,
                'text-align': 'left',
            })
            self.checkboxes[show] = checkbox
            hbox = gui.HBox(children=[checkbox, checkbox_label], style={
                'align-items': 'center',
                'justify-content': 'flex-start',
                'width': '100%',
            })
            self.selection_container.append(hbox)

        done_button = self.add_button(
            self.selection_container, "Done",
            lambda w: self.on_done_button_clicked(w, easy_checker, toonami_episodes)
        )
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
        self.main_container.remove_child(self.selection_container)
        self.prepare_content_continue()

    def handle_redis_message(self, channel, data):
        pass

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
        checkbox_container = gui.HBox(style={'justify-content': 'flex-start', 'margin': '10px'})

        # Destructive Mode checkbox
        self.destructive_checkbox = gui.CheckBoxLabel('Destructive Mode', False)
        self.destructive_checkbox.onchange.do(self.on_destructive_mode_changed)
        checkbox_container.append(self.destructive_checkbox)

        # Fast Mode checkbox
        self.fast_checkbox = gui.CheckBoxLabel('Fast Mode', False)
        self.fast_checkbox.onchange.do(self.on_fast_mode_changed)
        checkbox_container.append(self.fast_checkbox)

        # Low Power Mode checkbox
        self.low_power_checkbox = gui.CheckBoxLabel('Low Power Mode', False)
        self.low_power_checkbox.onchange.do(self.on_low_power_mode_changed)
        checkbox_container.append(self.low_power_checkbox)

        self.main_container.append(checkbox_container)

        # Progress bar and status label
        progress_container = gui.VBox(style={'align-items': 'center', 'margin-top': '20px'})

        progress_label = gui.Label("Progress:", style=Styles.default_label_style)
        progress_container.append(progress_label)

        self.progress_bar = gui.Progress(0, 100, style={'width': '80%', 'height': '20px'})
        progress_container.append(self.progress_bar)

        self.status_label = gui.Label("Idle", style=Styles.default_label_style)
        progress_container.append(self.status_label)

        self.main_container.append(progress_container)

        # Action buttons
        buttons_container = gui.HBox(style={'justify-content': 'center', 'margin-top': '20px'})

        detect_button = self.add_button(buttons_container, "Detect", self.detect_commercials)
        cut_button = self.add_button(buttons_container, "Cut", self.cut_videos)
        delete_button = self.add_button(buttons_container, "Delete", self.delete_txt_files)

        self.main_container.append(buttons_container)

        # Continue button to go to the next page
        self.next_button = self.add_button(self.main_container, "Continue", self.on_continue_button_click)

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

    def update_progress(self, current, total):
        self.progress_value = current / total * 100
        self.app.execute_javascript(f"document.getElementById('{self.progress_bar.identifier}').value = {self.progress_value}")
        print(f"Progress: {self.progress_value}%")

    def reset_progress_bar(self):
        self.progress_value = 0
        self.app.execute_javascript(f"document.getElementById('{self.progress_bar.identifier}').value = {self.progress_value}")
        print("Progress reset")

    def update_status(self, text):
        self.logic._broadcast_status_update(text)
        #refresh the status label
        self.status_label.set_text(text)

    def _run_and_notify(self, task, done_callback, task_name, destructive_mode=False, low_power_mode=False, fast_mode=False, reset_callback=None):
        self.update_status(f"Started task: {task_name}")
        if task_name == "Detect Black Frames":
            task(self.input_path, self.output_path, self.update_progress, self.update_status, low_power_mode, fast_mode, reset_callback)
        elif task_name == "Cut Video":
            self.reset_progress_bar()
            task(self.input_path, self.output_path, self.update_progress, self.update_status, destructive_mode)
        self.update_status(f"Finished task: {task_name}")
        done_callback(task_name)

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

        # Prepare Cut Anime for Lineup button
        self.add_label(self.main_container, "Prepare Cut Anime for Lineup")
        self.prepare_cut_anime_button = self.add_button(self.main_container, "Prepare Cut Anime for Lineup", self.prepare_cut_anime)

        # Add Special Bumps to Sheet button
        self.add_label(self.main_container, "Add Special Bumps to Sheet")
        self.add_special_bumps_button = self.add_button(self.main_container, "Add Special Bumps to Sheet", self.add_special_bumps)

        # Prepare Plex button
        self.add_label(self.main_container, "Prepare Plex")
        self.prepare_plex_button = self.add_button(self.main_container, "Prepare Plex", self.create_prepare_plex)

        # Create Toonami Channel button
        self.add_label(self.main_container, "Create Toonami Channel")
        self.create_toonami_channel_button = self.add_button(self.main_container, "Create Toonami Channel", self.create_toonami_channel)

        # Status label
        self.status_label = self.add_label(self.main_container, "Status: Idle")

        # Continue button
        self.continue_button = self.add_button(self.main_container, "Continue", self.on_continue_button_click)

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

        # Start from last episode checkbox
        self.start_from_last_episode_checkbox = self.add_checkbox(self.main_container, "Start from last episode?", default_value=False)

        # Prepare Toonami Channel button
        self.add_label(self.main_container, "Prepare Toonami Channel")
        self.prepare_toonami_channel_button = self.add_button(self.main_container, "Prepare Toonami Channel", self.prepare_toonami_channel)

        # Create Toonami Channel button
        self.add_label(self.main_container, "Create Toonami Channel")
        self.create_toonami_channel_button = self.add_button(self.main_container, "Create Toonami Channel", self.create_toonami_channel)

        # Status label
        self.status_label = self.add_label(self.main_container, "Status: Idle")

        # Next button
        self.next_button = self.add_button(self.main_container, "Next", self.on_next_button_click)

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

        # Flex Your Toonami Channel label
        self.add_label(self.main_container, "Flex Your Toonami Channel")

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