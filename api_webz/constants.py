import os
from pathlib import Path
from utils import Helper
utils = Helper()


# __file__ is the current script path (e.g., 'root/app/script.py')
current_file = Path(__file__).resolve()
# .parent gets 'app', and the next .parent gets 'root'
ROOT_DIR = current_file.parent.parent



# .name extracts only the folder string (e.g., 'root')
ROOT_DIR_NAME = ROOT_DIR.name
pth = os.path.join(ROOT_DIR, "paths.json5")

# print(f"ROOT CONFIG PATH: {pth}")
OUTPUT_DIR = os.path.join(ROOT_DIR, "OUTPUTS")
os.makedirs(OUTPUT_DIR, exist_ok=True)

LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

config = utils.load_json5(pth)

AUTH_UTILS = config["auth_utils"]
