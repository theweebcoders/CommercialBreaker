from collections import namedtuple

VideoFile = namedtuple('VideoFile', ['original_file', 'dirpath', 'filename'])


class VideoFilesManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VideoFilesManager, cls).__new__(cls)
            cls._instance.video_files = []
            # Parallel set keyed by (original_file, dirpath, filename) for O(1) dedup
            cls._instance._seen = set()
        return cls._instance

    def add_file(self, original_file, dirpath, filename):
        """Add a file to the manager, but only if it isn't already present."""
        key = (original_file, dirpath, filename)
        if key in self._seen:
            return
        self._seen.add(key)
        self.video_files.append(VideoFile(original_file, dirpath, filename))

    def remove_file(self, original_file, dirpath, filename):
        key = (original_file, dirpath, filename)
        if key not in self._seen:
            return
        self._seen.discard(key)
        file_to_remove = next((file for file in self.video_files if
                               file.original_file == original_file and
                               file.dirpath == dirpath and
                               file.filename == filename), None)
        if file_to_remove:
            self.video_files.remove(file_to_remove)

    def get_files(self, original_file=None, dirpath=None, filename=None):
        return [file._asdict() for file in self.video_files if
                (original_file is None or file.original_file == original_file) and
                (dirpath is None or file.dirpath == dirpath) and
                (filename is None or file.filename == filename)]

    def clear_files(self):
        self.video_files.clear()
        self._seen.clear()
