import pytest
from pathlib import Path, PurePosixPath
import time
import bisect # Added for optimized directory detection


@pytest.fixture(scope="session")
def fixture_dirs(tmp_path_factory):
    """
    Materialise every entry found in tests/fixtures/sample.txt underneath a
    temporary root and return (anime_dir, bumps_dir, working_dir).
    """
    print(f"\n{'='*60}")
    print("FIXTURE IS RUNNING! Starting fixture setup...")
    start_time = time.time()
    
    root = tmp_path_factory.mktemp("from_tree")
    print(f"Created temp root: {root}")
    
    tree_file = Path(__file__).parent / "fixtures" / "sample.txt"
    print(f"Reading tree file: {tree_file}")
    print(f"Tree file exists: {tree_file.exists()}")

    # --- load & clean -------------------------------------------------------
    rel_paths: list[str] = []
    print("Loading and cleaning paths...")
    for raw in tree_file.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw or raw == ".":                 # skip blanks and the root dot
            continue
        rel = raw[2:] if raw.startswith("./") else raw
        rel_paths.append(rel)
    
    print(f"Loaded {len(rel_paths)} paths from sample.txt")

    # --- detect which of them are directories -------------------------------
    print("Detecting directories...")
    
    rel_paths_set = set(rel_paths) # Ensure unique paths
    
    print("Optimized directory detection starting...")
    unique_sorted_rel_paths = sorted(list(rel_paths_set))
    dir_set: set[str] = set()
    num_paths = len(unique_sorted_rel_paths)
    
    # Keep track of the overall fixture start time for progress reporting
    fixture_start_time = start_time 

    for i, p_candidate in enumerate(unique_sorted_rel_paths):
        if i % 5000 == 0 and i > 0: # Progress reporting
            elapsed_detection = time.time() - fixture_start_time
            print(f"  Dir detection progress: {i}/{num_paths} ({i/num_paths*100:.1f}%) - {elapsed_detection:.1f}s elapsed")
        
        p_prefix_to_check = p_candidate + "/"
        
        # Find the insertion point for p_prefix_to_check in the remainder of the sorted list
        # lo=i+1 ensures we don't match p_candidate with itself or check paths before it.
        idx = bisect.bisect_left(unique_sorted_rel_paths, p_prefix_to_check, lo=i + 1)
        
        # If a path is found at idx and it starts with p_prefix_to_check, then p_candidate is a directory
        if idx < num_paths and unique_sorted_rel_paths[idx].startswith(p_prefix_to_check):
            dir_set.add(p_candidate)
            
    print("Optimized directory detection finished.")
    print(f"Found {len(dir_set)} directories")
    print(f"Will create {len(rel_paths_set) - len(dir_set)} files (based on unique paths)") # Clarified count

    # --- materialise --------------------------------------------------------
    print("Creating directories and files...")
    dirs_created = 0
    files_created = 0
    
    for i, rel in enumerate(rel_paths):
        if i % 1000 == 0 and i > 0:
            elapsed = time.time() - start_time
            print(f"  Progress: {i}/{len(rel_paths)} ({i/len(rel_paths)*100:.1f}%) - {elapsed:.1f}s elapsed")
        
        target = root / PurePosixPath(rel)        # keep forward-slash semantics
        
        try:
            if rel in dir_set:
                if target.exists() and not target.is_dir():
                    print(f"WARNING: {target} exists as file, can't create directory!")
                    continue
                target.mkdir(parents=True, exist_ok=True)
                dirs_created += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch(exist_ok=True)
                files_created += 1
        except Exception as e:
            print(f"ERROR creating {target}: {e}")
            print(f"  rel: {rel}")
            print(f"  in dir_set: {rel in dir_set}")
            print(f"  target exists: {target.exists()}")
            if target.exists():
                print(f"  is_file: {target.is_file()}")
                print(f"  is_dir: {target.is_dir()}")
            raise

    # Final summary
    elapsed = time.time() - start_time
    print(f"\nFixture setup complete!")
    print(f"  Directories created: {dirs_created}")
    print(f"  Files created: {files_created}")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  Average: {len(rel_paths)/elapsed:.0f} items/second")

    # extra working directory
    working_dir = root / "working"
    if working_dir.is_file(): # Check if 'working' exists as a file
        print(f"WARNING: '{working_dir}' exists as a file. Removing it to create a directory.")
        working_dir.unlink() # Remove the file
    working_dir.mkdir(exist_ok=True)

    # common sub-folders used by the code under test
    anime_dir = root / "Anime"                    # will exist thanks to sample.txt
    bumps_dir = root / "Bumps"                    # may not exist → create
    bumps_dir.mkdir(parents=True, exist_ok=True)

    print(f"Returning directories:")
    print(f"  anime_dir: {anime_dir}")
    print(f"  bumps_dir: {bumps_dir}")
    print(f"  working_dir: {working_dir}")
    print(f"{'='*60}")

    return anime_dir, bumps_dir, working_dir
