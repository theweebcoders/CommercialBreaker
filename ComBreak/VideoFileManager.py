class VideoFile:
    def __init__(self, original_file, dirpath, filename):
        self.original_file = original_file
        self.dirpath = dirpath
        self.filename = filename


class VideoFilesManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VideoFilesManager, cls).__new__(cls)
            cls._instance.video_files = []
        return cls._instance

    def add_file(self, original_file, dirpath, filename):
        video_file = VideoFile(original_file, dirpath, filename)
        self.video_files.append(video_file)

    def remove_file(self, original_file, dirpath, filename):
        file_to_remove = next((file for file in self.video_files if
                               file.original_file == original_file and
                               file.dirpath == dirpath and
                               file.filename == filename), None)
        if file_to_remove:
            self.video_files.remove(file_to_remove)

    def get_files(self, original_file=None, dirpath=None, filename=None):
        return [file.__dict__ for file in self.video_files if
                (original_file is None or file.original_file == original_file) and
                (dirpath is None or file.dirpath == dirpath) and
                (filename is None or file.filename == filename)]

    def clear_files(self):
        self.video_files.clear()
