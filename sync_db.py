import shutil
import os
from datetime import datetime

# Customize these paths
SOURCE_DB = "\PycharmProjects\PythonProject\pc_info.db"
DEST_DB = "\PycharmProjects\Web App\pc_info.db"
LOG_FILE = "\PycharmProjects\Web App\sync_log.txt"

try:
    os.makedirs(os.path.dirname(DEST_DB), exist_ok=True)
    shutil.copy2(SOURCE_DB, DEST_DB)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} - DB copied successfully.\n")
except Exception as e:
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} - Failed to copy DB: {e}\n")
