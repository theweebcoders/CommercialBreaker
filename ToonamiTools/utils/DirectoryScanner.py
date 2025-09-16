import os
import re
import time


def fast_video_scan(folder_path, progress_callback=None):
    """
    Optimized video file scanner for large directory trees on slow storage.

    Uses a chunked approach that processes one show directory at a time,
    providing better progress feedback and error isolation compared to os.walk().

    Args:
        folder_path (str): Path to scan for video files
        progress_callback (callable, optional): Function to call with progress updates
                                              Should accept (current, total, message)

    Returns:
        tuple: (episode_files dict, total_file_count)
    """
    episode_files = {}
    file_count = 0

    start_time = time.time()
    print(f"Fast scanning directory: {folder_path}")

    try:
        # Get top-level show directories first
        top_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
        total_dirs = len(top_dirs)
        print(f"Found {total_dirs} show directories to scan")

        # Process each show directory individually (much faster on network/FUSE filesystems)
        for i, show_dir in enumerate(top_dirs):
            if i % 100 == 0 and i > 0:
                elapsed = time.time() - start_time
                print(f"Progress: {i}/{total_dirs} shows processed, {file_count} files found in {elapsed:.1f}s")
                if progress_callback:
                    progress_callback(i, total_dirs, f"Processed {i} shows, {file_count} files")

            show_path = os.path.join(folder_path, show_dir)
            try:
                # Scan this specific show's directory tree
                for root, dirs, files in os.walk(show_path):
                    for file in files:
                        if file.endswith(('.mkv', '.mp4', '.avi', '.flv')):
                            full_file_path = os.path.join(root, file)
                            # Check if file actually exists (handles broken symlinks)
                            if os.path.exists(full_file_path):
                                file_count += 1
                                # Extract show title from filename
                                if matched_title := re.findall(
                                    r'^(.*?)(?: - S\d{1,2}E\d{1,2})', file, re.IGNORECASE
                                ):
                                    show_title = matched_title[0].strip()
                                    episode = file
                                    rel_path = os.path.relpath(root, folder_path)
                                    if show_title in episode_files:
                                        episode_files[show_title].append(os.path.join(rel_path, episode))
                                    else:
                                        episode_files[show_title] = [os.path.join(rel_path, episode)]
            except Exception as show_error:
                print(f"Warning: Could not scan {show_dir}: {show_error}")
                continue

        elapsed = time.time() - start_time
        print(f"Finished scanning {total_dirs} shows in {elapsed:.1f} seconds")
        if progress_callback:
            progress_callback(total_dirs, total_dirs, f"Completed: {file_count} files found")

    except Exception as e:
        print(f"Error during directory scan: {e}")
        raise

    return episode_files, file_count


def legacy_video_scan(folder_path):
    """
    Original os.walk() based scanning - kept for fallback/comparison.

    Args:
        folder_path (str): Path to scan for video files

    Returns:
        tuple: (episode_files dict, total_file_count)
    """
    episode_files = {}
    file_count = 0

    print(f"Starting to walk through directory: {folder_path}")

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.mkv', '.mp4', '.avi', '.flv')):
                full_file_path = os.path.join(root, file)
                # Check if file actually exists (handles broken symlinks)
                if os.path.exists(full_file_path):
                    file_count += 1
                    if matched_title := re.findall(
                        r'^(.*?)(?: - S\d{1,2}E\d{1,2})', file, re.IGNORECASE
                    ):
                        show_title = matched_title[0].strip()
                        episode = file
                        rel_path = os.path.relpath(root, folder_path)
                        if show_title in episode_files:
                            episode_files[show_title].append(os.path.join(rel_path, episode))
                        else:
                            episode_files[show_title] = [os.path.join(rel_path, episode)]

    return episode_files, file_count