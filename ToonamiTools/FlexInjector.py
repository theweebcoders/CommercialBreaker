import requests
import json

class DizqueTVManager:
    def __init__(self, platform_url, channel_number, duration, network):
        self.platform_url = platform_url
        self.channel_number = channel_number
        self.duration = duration
        self.network = network
        self.api_url = f'{platform_url}/api'

    def convert_to_milliseconds(self, time):
        time = time.split(':')
        minutes = int(time[0])
        seconds = int(time[1])
        return (minutes * 60 + seconds) * 1000
        
    def is_flex_target(self, title):
        return self.network in title if title else False
        
    def insert_flex(self, channel_data):
        flex_length = self.convert_to_milliseconds(self.duration)
        programs_list = channel_data.get('programs', [])
        new_programs = []
        
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
        print(f'Getting channel {self.channel_number} from {self.api_url}')
        response = requests.get(f'{self.api_url}/channel/{self.channel_number}')
        if response.status_code != 200:
            raise Exception(f'Failed to get channel: {response.text}')
            
        channel_data = response.json()
        print(f'Successfully retrieved channel with {len(channel_data.get("programs", []))} programs')
        
        modified_channel = self.insert_flex(channel_data)
        print(f'Modified channel now has {len(modified_channel.get("programs", []))} programs')
        
        print(f'Updating channel {self.channel_number}...')
        update_response = requests.post(
            f'{self.api_url}/channel', 
            json=modified_channel
        )
        
        if update_response.status_code not in [200, 204]:
            raise Exception(f'Failed to update channel: {update_response.text}')
            
        print(f'Successfully updated channel {self.channel_number}')
        return True