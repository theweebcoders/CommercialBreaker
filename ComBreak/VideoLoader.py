import cv2
from config import *

class VideoLoader:
    """A class that represents a video loader."""

    def __init__(self, video_file):
        self.cap = cv2.VideoCapture(video_file)
        self.frame_count = 0

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                raise StopIteration
            self.frame_count += 1
            if self.frame_count % FRAME_RATE == 0:
                return frame

    def get_frame_count(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / FRAME_RATE)

    def release(self):
        self.cap.release()