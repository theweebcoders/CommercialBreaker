import os

class CutFileRenamer:
    def __init__(self, input_dir):
        self.input_dir = input_dir

    def rename_files(self):
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(".mp4"):
                    parts = file.split("Part ")
                    if len(parts) > 1 and parts[1].split(".")[0].isdigit():
                        old_name = os.path.join(root, file)
                        part_number = int(parts[1].split(".")[0])  # Extracting part number
                        new_name = file.replace(f"Part {str(part_number).zfill(3)}", f"Part {part_number + 1}")
                        new_path = os.path.join(root, new_name)
                        os.rename(old_name, new_path)  # This line is commented out to prevent renaming
                        print(f"Would Rename: {old_name} -> {new_name}")
                    else:
                        print(f"Skipped: {file} (does not follow expected pattern)")


input_dir = r"M:\Cut"
renamer = CutFileRenamer(input_dir)
renamer.rename_files()