# Test file for ProgressManager

class ProgressManager:
    def __init__(self, downscale_count, silence_count, frame_count, progress_cb):
        # Calculate the total number of frames to process
        self.total_frames = max(1, frame_count)
        self.processed_frames = 0
        
        # Track operations for logging purposes
        self.silence_total = silence_count
        self.downscale_total = downscale_count
        self.frame_total = frame_count
        self.silence_done = 0
        self.downscale_done = 0
        self.frame_done = 0
        
        # Store callback
        self.cb = progress_cb
        
        # Initial call to set progress to 0
        if self.cb:
            self._update_progress()

    def _update_progress(self):
        # Calculate real percentage based on processed frames
        percent = int((self.processed_frames / self.total_frames) * 100)
        
        # Cap at 99% until force_complete is called
        percent = min(percent, 99)
        
        # Update UI with the real percentage
        if self.cb:
            self.cb(percent, 100)

    def step_downscale(self):
        if self.downscale_done < self.downscale_total:
            self.downscale_done += 1

    def step_silence(self):
        if self.silence_done < self.silence_total:
            self.silence_done += 1

    def step_frame(self):
        # This is the one that affects real progress
        self.processed_frames += 1
        self.frame_done += 1
        self._update_progress()
    
    def update_frame_progress(self, processed_frames, total_frames=None):
        """Update progress based on actual processed/total frames from the detector."""
        # Update our internal counters
        self.processed_frames = processed_frames
        if total_frames is not None and total_frames > 0:
            self.total_frames = total_frames
        
        # Update the progress bar
        self._update_progress()
        
    def force_complete(self):
        """Forces the progress bar to 100% when processing is truly complete."""
        if self.cb:
            self.cb(100, 100)


if __name__ == "__main__":
    # Create a callback function to print progress
    def progress_callback(current, total):
        percent = (current / total) * 100
        print(f'Progress: {current}/{total} = {percent:.1f}%')

    # Create a progress manager with the same ratio as we expect in real use
    print('=== PREVIOUS IMPLEMENTATION (SIMULATED) ===')
    downscale_count = 5  # 5 segments to downscale
    silence_count = 1    # 1 video file
    frame_count = 94     # 94 frames to analyze
    
    # Simulate how it would look before our fix
    print('Initial state:')
    print(f'Progress: 0/100 = 0.0%')
    
    # After silence step - progress remained at 0%
    print('\nAfter silence step:')
    print(f'Progress: 0/100 = 0.0%')
    
    # After downscale steps - still no visible progress
    print('\nAfter downscale steps:')
    print(f'Progress: 0/100 = 0.0%')
    
    # Only after frame processing begins do we see progress
    print('\nAfter first frame:')
    print(f'Progress: 1/100 = 1.0%')
    
    # After 25% frames
    print('\nAfter 25% frames:')
    print(f'Progress: 25/100 = 25.0%')
    
    # After 50% frames
    print('\nAfter 50% frames:')
    print(f'Progress: 50/100 = 50.0%')
    
    # After 99% frames
    print('\nAfter 99% frames:')
    print(f'Progress: 99/100 = 99.0%')
    
    # After 100% frames - overshoots to 100% before complete
    print('\nProblem: After 100% frames - progress shown as complete before actually finished:')
    print(f'Progress: 100/100 = 100.0% (but processing is not complete)')
    
    print('\n=== NEW IMPLEMENTATION ===')
    
    # Test with our new implementation
    pm = ProgressManager(downscale_count, silence_count, frame_count, progress_callback)
    
    print('\nInitial state:')
    print(f'Total frames: {pm.total_frames}')
    
    # Silence detection doesn't directly affect progress
    print('\nAfter silence step:')
    pm.step_silence()
    print(f'Silence phase: {pm.silence_done}/{pm.silence_total} (tracked but no progress update)')
    
    # Downscaling doesn't directly affect progress
    print('\nAfter all downscale steps:')
    for _ in range(pm.downscale_total):
        pm.step_downscale()
    print(f'Downscale phase: {pm.downscale_done}/{pm.downscale_total} (tracked but no progress update)')
    
    # Using update_frame_progress directly from analyzer
    print('\nAfter 10 frames analyzed:')
    pm.update_frame_progress(10)
    print(f'Processed: {pm.processed_frames}/{pm.total_frames} = {(pm.processed_frames/pm.total_frames*100):.1f}%')
    
    # After 25% frames
    print('\nAfter 25% frames:')
    pm.update_frame_progress(pm.total_frames // 4)
    print(f'Processed: {pm.processed_frames}/{pm.total_frames} = {(pm.processed_frames/pm.total_frames*100):.1f}%')
    
    # After 75% frames
    print('\nAfter 75% frames:')
    pm.update_frame_progress(int(pm.total_frames * 0.75))
    print(f'Processed: {pm.processed_frames}/{pm.total_frames} = {(pm.processed_frames/pm.total_frames*100):.1f}%')
    
    # After all frames
    print('\nAfter all frames:')
    pm.update_frame_progress(pm.total_frames)
    print(f'Processed: {pm.processed_frames}/{pm.total_frames} = {(pm.processed_frames/pm.total_frames*100):.1f}%')
    
    # Adding extra frames beyond estimate - progress stays at 99%
    print('\nAdding extra frames beyond estimate:')
    pm.update_frame_progress(pm.total_frames + 10)
    print(f'Processed: {pm.processed_frames}/{pm.total_frames} (progress capped at 99%)')
    
    # After force_complete
    print('\nAfter force_complete:')
    pm.force_complete()
    
    print('\n=== ADVANTAGES OF REAL PROGRESS REPORTING ===')
    print('1. Progress shows real work: directly uses processed_frames/total_frames')
    print('2. No arbitrary weights or phases - just actual frames processed')
    print('3. Progress starts from 0% immediately and increases linearly')
    print('4. Progress never exceeds 100% before truly complete')
    print('5. Simple to understand: % complete = frames processed / total frames')