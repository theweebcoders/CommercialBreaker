# Test file for ProgressManager

class ProgressManager:
    def __init__(self, downscale_count, silence_count, frame_count, progress_cb):
        # Apply weight factor to downscaling for more immediate feedback
        # This ensures downscaling (which happens first) shows visible progress right away
        downscale_weight = 5  # Weight factor to make downscaling progress more visible
        
        self.downscale_total = downscale_count * downscale_weight
        self.silence_total = silence_count
        self.frame_total = frame_count
        # Ensure total is at least 1 to avoid division by zero if all counts are 0
        self.total = max(1, self.downscale_total + silence_count + frame_count)
        
        self.downscale_done = 0
        self.silence_done = 0
        self.frame_done = 0
        self.done = 0
        
        # Store weight factor for step_downscale to use
        self.downscale_weight = downscale_weight
        
        self.cb = progress_cb
        # Initial call to set progress to 0
        if self.cb:
            self.cb(self.done, self.total)

    def _update_progress(self):
        self.done = self.downscale_done + self.silence_done + self.frame_done
        # Ensure we don't exceed total due to estimations or errors
        # Cap at 99% unless force_complete is called, to prevent visual "jumping back"
        self.done = min(self.done, self.total - 1) 
        if self.cb:
            self.cb(self.done, self.total)

    def step_downscale(self):
        # Only step if we haven't reached the total for this category
        if self.downscale_done < self.downscale_total:
            # Increment by weight factor to reflect the weighted total
            self.downscale_done += self.downscale_weight
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.downscale_done == self.downscale_total:
        #     print("Warning: Tried to step downscale beyond total")

    def step_silence(self):
        # Only step if we haven't reached the total for this category
        if self.silence_done < self.silence_total:
            self.silence_done += 1
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.silence_done == self.silence_total:
        #     print("Warning: Tried to step silence beyond total")

    def step_frame(self):
        # Only step if we're not nearing the total to avoid overshooting
        # Leave room for at least 1% of progress for force_complete
        if self.done < self.total - 1:
            self.frame_done += 1 
            self._update_progress()
        # Otherwise, just increment counter but don't update visible progress
        else:
            self.frame_done += 1
            
    def force_complete(self):
        """Forces the progress bar to 100%."""
        self.done = self.total
        self.downscale_done = self.downscale_total
        self.silence_done = self.silence_total
        self.frame_done = self.frame_total # Set frame done to total estimated
        if self.cb:
            self.cb(self.done, self.total)


if __name__ == "__main__":
    # Create a callback function to print progress
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f'Progress: {current}/{total} = {percent:.1f}%')

    # Create a progress manager with the same ratio as we expect in real use
    print('=== BEFORE FIX (simulated) ===')
    downscale_count = 5  # 5 segments to downscale
    silence_count = 1    # 1 video file
    frame_count = 94     # 94 frames to analyze
    # Total = 100 steps

    # Simulate how it would look before our fix
    print('Initial state:')
    print(f'Downscale: 0/{downscale_count}, Silence: 0/{silence_count}, Frame: 0/{frame_count}')
    print(f'Progress: 0/100 = 0.0%')

    # After silence step (1% complete)
    print('\nAfter silence step:')
    print(f'Downscale: 0/{downscale_count}, Silence: 1/{silence_count}, Frame: 0/{frame_count}')
    print(f'Progress: 1/100 = 1.0%')

    # After downscale steps (6% complete, still early in process)
    print('\nAfter downscale steps:')
    print(f'Downscale: 5/{downscale_count}, Silence: 1/{silence_count}, Frame: 0/{frame_count}')
    print(f'Progress: 6/100 = 6.0%')

    # Midway through frame processing (~50% complete)
    print('\nMidway through frame processing:')
    print(f'Downscale: 5/{downscale_count}, Silence: 1/{silence_count}, Frame: 47/{frame_count}')
    print(f'Progress: 53/100 = 53.0%')


    print('\n=== AFTER FIX (actual) ===')
    # Test with our new weighted implementation
    pm = ProgressManager(downscale_count, silence_count, frame_count, progress_callback)

    print('\nInitial state:')
    print(f'Downscale weight: {pm.downscale_weight}')
    print(f'Total steps: {pm.total}')

    print('\nAfter silence step:')
    pm.step_silence()

    print('\nAfter first downscale step:')
    pm.step_downscale()

    print('\nAfter all downscale steps:')
    for _ in range(downscale_count - 1):
        pm.step_downscale()

    print('\nAfter 25% frame steps:')
    for _ in range(frame_count // 4):
        pm.step_frame()

    print('\nAfter 75% frame steps:')
    for _ in range(frame_count // 2):
        pm.step_frame()

    print('\nAfter all frame steps:')
    for _ in range(frame_count - pm.frame_done):
        pm.step_frame()

    print('\nAfter force_complete:')
    pm.force_complete()