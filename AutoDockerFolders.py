import os
from pathlib import Path
from API.FrontEndLogic import LogicController

def auto_docker_folder():
    # Fetch data from environment variables or use the Docker container paths
    anime_folder = os.getenv("ANIME_FOLDER", "/app/anime")
    bump_folder = os.getenv("BUMP_FOLDER", "/app/bump")
    special_bump_folder = os.getenv("SPECIAL_BUMP_FOLDER", "/app/special_bump")
    working_folder = os.getenv("WORKING_FOLDER", "/app/working")
    commercial_folder = os.getenv("COMMERCIAL_FOLDER", "/app/commercials")

    # Create _pre_rendered_breaks folder for ComBreakDirect
    # This ensures the folder exists before the server starts, avoiding race conditions
    pre_rendered_breaks = Path(commercial_folder) / "_pre_rendered_breaks"
    pre_rendered_breaks.mkdir(parents=True, exist_ok=True)
    print(f"[DOCKER_SETUP] Created pre-rendered breaks folder: {pre_rendered_breaks}")

    # Save the fetched data to the database
    logic = LogicController()
    logic._set_data("anime_folder", anime_folder)
    logic._set_data("bump_folder", bump_folder)
    logic._set_data("special_bump_folder", special_bump_folder)
    logic._set_data("working_folder", working_folder)
    logic._set_data("commercial_folder", commercial_folder)

# Run the folder setup when the script is executed
auto_docker_folder()
