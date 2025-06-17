import requests
import json
from API.utils.ErrorManager import get_error_manager

class DizqueTVManager:
    def __init__(self, platform_url, channel_number, duration, network):
        self.platform_url = platform_url
        self.channel_number = channel_number
        self.duration = duration
        self.network = network
        self.api_url = f'{platform_url}/api'
        self.error_manager = get_error_manager()

    def convert_to_milliseconds(self, time):
        try:
            time = time.split(':')
            if len(time) != 2:
                self.error_manager.send_error_level(
                    source="FlexInjector",
                    operation="convert_to_milliseconds",
                    message="Invalid flex duration format",
                    details=f"Duration '{self.duration}' is not in MM:SS format",
                    suggestion="Flex duration should be in format MM:SS (e.g., 02:30 for 2 minutes 30 seconds)"
                )
                raise ValueError(f"Invalid time format: {self.duration}")
                
            minutes = int(time[0])
            seconds = int(time[1])
            
            if seconds >= 60:
                self.error_manager.send_error_level(
                    source="FlexInjector",
                    operation="convert_to_milliseconds",
                    message="Invalid seconds value in flex duration",
                    details=f"Seconds value {seconds} is greater than 59",
                    suggestion="Seconds should be between 00 and 59. Use minutes for values over 60 seconds"
                )
                raise ValueError(f"Invalid seconds: {seconds}")
                
            return (minutes * 60 + seconds) * 1000
        except (ValueError, IndexError) as e:
            if "Invalid" not in str(e):  # Don't double-report our own errors
                self.error_manager.send_error_level(
                    source="FlexInjector",
                    operation="convert_to_milliseconds",
                    message="Cannot parse flex duration",
                    details=str(e),
                    suggestion="Make sure flex duration is in MM:SS format with numbers only"
                )
            raise
        
    def is_flex_target(self, title):
        return self.network in title if title else False
        
    def insert_flex(self, channel_data):
        flex_length = self.convert_to_milliseconds(self.duration)
        programs_list = channel_data.get('programs', [])
        
        if not programs_list:
            self.error_manager.send_warning(
                source="FlexInjector",
                operation="insert_flex",
                message="Channel has no programs",
                details=f"Channel {self.channel_number} appears to be empty",
                suggestion="Add programs to the channel first before inserting flex breaks"
            )
            return channel_data
            
        new_programs = []
        flex_added_count = 0
        
        for i, program in enumerate(programs_list):
            current_title = program.get('title', '')
            new_programs.append(program)
            
            if i + 1 < len(programs_list):
                next_title = programs_list[i + 1].get('title', '')
                if 'Intro' in next_title:
                    is_offline_entry = {'duration': flex_length, 'isOffline': True}
                    new_programs.append(is_offline_entry)
                elif 'isOffline' not in programs_list[i + 1] and self.is_flex_target(current_title) and self.is_flex_target(next_title):
                    is_offline_entry = {'duration': flex_length, 'isOffline': True}
                    new_programs.append(is_offline_entry)
            elif 'isOffline' in program:
                program['duration'] = flex_length
                
        channel_data['programs'] = new_programs
        return channel_data
        
    def main(self):
        # Validate connection to DizqueTV
        try:
            print(f'Getting channel {self.channel_number} from {self.api_url}')
            response = requests.get(f'{self.api_url}/channel/{self.channel_number}', timeout=10)
        except requests.exceptions.ConnectionError:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Cannot connect to DizqueTV",
                details=f"Failed to reach DizqueTV at {self.platform_url}",
                suggestion="Check that DizqueTV is running and the URL is correct"
            )
            raise
        except requests.exceptions.Timeout:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="DizqueTV connection timed out",
                details=f"No response from {self.platform_url} after 10 seconds",
                suggestion="Check your network connection and that DizqueTV is responding"
            )
            raise
        except Exception as e:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Failed to connect to DizqueTV",
                details=str(e),
                suggestion="Check your DizqueTV URL and network settings"
            )
            raise
            
        if response.status_code == 404:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message=f"Channel {self.channel_number} not found",
                details="The specified channel does not exist in DizqueTV",
                suggestion="Create the channel in DizqueTV first. If you changed the channel number, change it in the GUI as well."
            )
            raise Exception(f'Channel {self.channel_number} not found')
        elif response.status_code != 200:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Failed to retrieve channel data",
                details=f"DizqueTV returned status code {response.status_code}",
                suggestion="Check DizqueTV logs for more information. Also check dizquetv to see if the flex was added successfully."
            )
            raise Exception(f'Failed to get channel: {response.text}')
            
        try:
            channel_data = response.json()
        except json.JSONDecodeError:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Invalid response from DizqueTV",
                details="The channel data returned is not valid JSON",
                suggestion="Check that DizqueTV is functioning correctly"
            )
            raise
            
        print(f'Successfully retrieved channel with {len(channel_data.get("programs", []))} programs')
        
        # Insert flex breaks
        try:
            modified_channel = self.insert_flex(channel_data)
        except Exception as e:
            # Error already logged by insert_flex or convert_to_milliseconds
            raise
            
        print(f'Modified channel now has {len(modified_channel.get("programs", []))} programs')
        
        # Update the channel
        print(f'Updating channel {self.channel_number}...')
        try:
            update_response = requests.post(
                f'{self.api_url}/channel', 
                json=modified_channel,
                timeout=30  # Longer timeout for updates
            )
        except requests.exceptions.ConnectionError:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Lost connection to DizqueTV during update",
                details="The connection was lost while updating the channel",
                suggestion="Check DizqueTV status and try running Flex Injector again"
            )
            raise
        except requests.exceptions.Timeout:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="DizqueTV update timed out",
                details="The channel update took too long to complete",
                suggestion="Check DizqueTV performance and try again"
            )
            raise
        except Exception as e:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="Failed to update channel",
                details=str(e),
                suggestion="Check DizqueTV logs and try again"
            )
            raise
        
        if update_response.status_code not in [200, 204]:
            self.error_manager.send_error_level(
                source="FlexInjector",
                operation="main",
                message="DizqueTV rejected the channel update",
                details=f"Status code {update_response.status_code}: {update_response.text}",
                suggestion="The channel data may be invalid. Check DizqueTV logs for details"
            )
            raise Exception(f'Failed to update channel: {update_response.text}')
            
        print(f'Successfully updated channel {self.channel_number}')
        return True