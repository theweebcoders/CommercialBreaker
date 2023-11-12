import paramiko
import json
import tempfile
import os


class DizqueTVManager:
    def __init__(self, ssh_host, ssh_username, ssh_password, docker_container_name, channel_number, duration):
        self.ssh_host = ssh_host
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.docker_container_name = docker_container_name
        self.channel_number = channel_number
        self.duration = duration

    def ssh_connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.ssh_host, username=self.ssh_username, password=self.ssh_password)
        return ssh

    #convert minutes:seconds to milliseconds
    def convert_to_milliseconds(self, time):
        time = time.split(":")
        minutes = int(time[0])
        seconds = int(time[1])
        return (minutes * 60 + seconds) * 1000

    def execute_command(self, ssh, command):
        print(f"Executing command: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        if error:
            raise Exception(f"Command failed with error: {error}")
        return output

    def is_flex_target(self, title):
        target_keywords = ['Toonami']
        return any(keyword in title for keyword in target_keywords)

    def insert_flex(self, json_data):
        flex_length = self.convert_to_milliseconds(self.duration)
        data = json.loads(json_data)
        programs_list = data.get('programs', [])
        new_programs = []
        for i, program in enumerate(programs_list):
            current_title = program.get('title', '')
            new_programs.append(program)
            if i + 1 < len(programs_list):
                next_title = programs_list[i + 1].get('title', '')
                if 'Intro' in next_title:
                    is_offline_entry = {"duration": flex_length, "isOffline": True}
                    new_programs.append(is_offline_entry)
                elif 'isOffline' not in programs_list[i + 1] and self.is_flex_target(current_title) and self.is_flex_target(next_title):
                    is_offline_entry = {"duration": flex_length, "isOffline": True}
                    new_programs.append(is_offline_entry)
            elif 'isOffline' in program:
                program['duration'] = flex_length
        data['programs'] = new_programs
        return json.dumps(data, indent=4)

    def main(self):
        ssh = self.ssh_connect()

        # Check if the directory exists
        check_dir_command = f"docker exec {self.docker_container_name} ls /home/node/app/.dizquetv/channels/"
        print("Checking if directory exists...")
        print(self.execute_command(ssh, check_dir_command))

        docker_exec_command = f"docker exec {self.docker_container_name} cat /home/node/app/.dizquetv/channels/{self.channel_number}.json"
        existing_json_str = self.execute_command(ssh, docker_exec_command)

        modified_json_str = self.insert_flex(existing_json_str)

        # Create a temporary file to store the modified JSON
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(modified_json_str.encode('utf-8'))

        fetch_container_id_command = f"docker ps -q --filter name={self.docker_container_name}"
        container_id = self.execute_command(ssh, fetch_container_id_command).strip()

        try:
            # Upload the temporary file to a known location on the SSH server
            with ssh.open_sftp() as sftp:
                sftp.put(temp_file.name, f"/tmp/{self.channel_number}.json")

            # Check if the file exists on the SSH server
            check_file_command = f"ls /tmp/{self.channel_number}.json"
            print("Checking if temporary file exists on SSH server...")
            print(self.execute_command(ssh, check_file_command))
            docker_cp_command = f"docker cp /tmp/{self.channel_number}.json {container_id}:/home/node/app/.dizquetv/channels/{self.channel_number}.json"
            self.execute_command(ssh, docker_cp_command)
            # Remove the temporary file from your system
            os.unlink(temp_file.name)

            # Remove the temporary file from the SSH server
            self.execute_command(ssh, f"rm /tmp/{self.channel_number}.json")

        except Exception as e:
            print(f"Failed to upload: {e}")

        container_restart_command = f"docker restart {self.docker_container_name}"
        self.execute_command(ssh, container_restart_command)
