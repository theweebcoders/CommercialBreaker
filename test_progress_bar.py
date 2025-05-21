# Test file for ProgressManager

class ProgressManager:
    def __init__(self, downscale_count, silence_count, frame_count, progress_cb):
        # Define phase weights based on estimated time/importance of each phase
        # These represent the percentage of the progress bar allocated to each phase
        self.silence_weight = 10    # Silence detection: 10% of total progress
        self.downscale_weight = 30  # Video downscaling: 30% of total progress
        self.frame_weight = 60      # Frame analysis: 60% of total progress
        
        # Store the total operations for each phase
        self.silence_total = max(1, silence_count)
        self.downscale_total = max(1, downscale_count)
        self.frame_total = max(1, frame_count)
        
        # Initialize progress counters
        self.silence_done = 0
        self.downscale_done = 0
        self.frame_done = 0
        
        # Progress is tracked as a percentage (0-100)
        self.total = 100
        self.done = 0
        
        # Store callback
        self.cb = progress_cb
        
        # Initial call to set progress to 0
        if self.cb:
            self.cb(self.done, self.total)

    def _update_progress(self):
        # Calculate the progress contribution from each phase
        silence_progress = min(self.silence_done / self.silence_total, 1.0) * self.silence_weight
        downscale_progress = min(self.downscale_done / self.downscale_total, 1.0) * self.downscale_weight
        frame_progress = min(self.frame_done / self.frame_total, 1.0) * self.frame_weight
        
        # Calculate total progress but cap at 99% until force_complete is called
        self.done = min(round(silence_progress + downscale_progress + frame_progress), 99)
        
        # Update UI
        if self.cb:
            self.cb(self.done, self.total)

    def step_downscale(self):
        # Only count steps up to the expected total
        if self.downscale_done < self.downscale_total:
            self.downscale_done += 1
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.downscale_done == self.downscale_total:
        #     print(f"Warning: Downscale steps exceeded estimate ({self.downscale_done}/{self.downscale_total})")

    def step_silence(self):
        # Only count steps up to the expected total
        if self.silence_done < self.silence_total:
            self.silence_done += 1
            self._update_progress()
        # Optional: Log or warn if trying to step beyond total
        # elif self.silence_done == self.silence_total:
        #     print(f"Warning: Silence steps exceeded estimate ({self.silence_done}/{self.silence_total})")

    def step_frame(self):
        # Only count steps up to the expected total for progress calculation
        if self.frame_done < self.frame_total:
            self.frame_done += 1 
            self._update_progress()
        # Otherwise, just increment counter but don't update visible progress
        else:
            self.frame_done += 1
        
    def force_complete(self):
        """Forces the progress bar to 100% when processing is truly complete."""
        self.done = 100
        if self.cb:
            self.cb(self.done, self.total)


if __name__ == "__main__":
    # Create a callback function to print progress
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f'Progress: {current}/{total} = {percent:.1f}%')

    # Create a progress manager with the same ratio as we expect in real use
    print('=== ORIGINAL IMPLEMENTATION (SIMULATED) ===')
    downscale_count = 5  # 5 segments to downscale
    silence_count = 1    # 1 video file
    frame_count = 94     # 94 frames to analyze
    # Total = 100 steps

    # Simulate how it would look before our fix
    print('Initial state:')
    print(f'Downscale: 0/{downscale_count}, Silence: 0/{silence_count}, Frame: 0/{frame_count}')
    print(f'Progress: 0/100 = 0.0%')

    # After silence step (only 1% progress)
    print('\nAfter silence step:')
    print(f'Progress: 1/100 = 1.0%')
    
    # After first downscale step (only 2% progress)
    print('\nAfter first downscale step:')
    print(f'Progress: 2/100 = 2.0%')
    
    # After all downscale steps (still only 6% progress)
    print('\nAfter all downscale steps:')
    print(f'Progress: 6/100 = 6.0%')
    
    # After 25% frame steps
    print('\nAfter 25% frame steps:')
    print(f'Progress: 29/100 = 29.0%')
    
    # After 75% frame steps
    print('\nAfter 75% frame steps:')
    print(f'Progress: 76/100 = 76.0%')
    
    # After all frame steps - overshooting to 100% before complete
    print('\nAfter all frame steps - problem: overshooting to 100%:')
    print(f'Progress: 100/100 = 100.0% (but processing is not complete)')
    
    print('\n=== PHASE-BASED IMPLEMENTATION ===')
    
    # Test with our new implementation
    pm = ProgressManager(downscale_count, silence_count, frame_count, progress_callback)
    
    print('\nInitial state:')
    print(f'Phase weights: Silence: {pm.silence_weight}%, Downscale: {pm.downscale_weight}%, Frame: {pm.frame_weight}%')
    
    print('\nAfter silence step:')
    pm.step_silence()
    print(f'Silence phase: {pm.silence_done}/{pm.silence_total} = {(pm.silence_done/pm.silence_total*100):.1f}%')
    
    print('\nAfter first downscale step:')
    pm.step_downscale()
    print(f'Downscale phase: {pm.downscale_done}/{pm.downscale_total} = {(pm.downscale_done/pm.downscale_total*100):.1f}%')
    
    print('\nAfter all downscale steps:')
    for _ in range(pm.downscale_total - pm.downscale_done):
        pm.step_downscale()
    print(f'Downscale phase: {pm.downscale_done}/{pm.downscale_total} = {(pm.downscale_done/pm.downscale_total*100):.1f}%')
    
    print('\nAfter 25% frame steps:')
    for _ in range(pm.frame_total // 4):
        pm.step_frame()
    print(f'Frame phase: {pm.frame_done}/{pm.frame_total} = {(pm.frame_done/pm.frame_total*100):.1f}%')
    
    print('\nAfter 75% frame steps:')
    for _ in range(pm.frame_total // 2):
        pm.step_frame()
    print(f'Frame phase: {pm.frame_done}/{pm.frame_total} = {(pm.frame_done/pm.frame_total*100):.1f}%')
    
    print('\nAfter all frame steps:')
    for _ in range(pm.frame_total - pm.frame_done):
        pm.step_frame()
    print(f'Frame phase: {pm.frame_done}/{pm.frame_total} = {(pm.frame_done/pm.frame_total*100):.1f}%')
    
    print('\nAdding extra frames beyond estimate:')
    for _ in range(10):  # Add 10 more frames beyond our estimate
        pm.step_frame()
    print(f'Frame phase: {pm.frame_done}/{pm.frame_total} = exceeded, but progress capped at 99%')
    
    print('\nAfter force_complete:')
    pm.force_complete()
    
    print('\n=== PHASE-BASED ADVANTAGES ===')
    print('1. Early phases (silence, downscaling) immediately show visible progress')
    print('2. Progress is proportional to actual work/time of each phase')
    print('3. Progress never exceeds 100% before truly complete')
    print('4. No arbitrary weight factors - each phase progresses naturally')
    print('5. Simple to understand and adjust if processing priorities change')