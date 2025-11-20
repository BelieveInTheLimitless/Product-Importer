import os
from pathlib import Path
from fastapi import UploadFile
import time
import uuid

UPLOAD_DIR = Path("/app/uploads")

def init_storage():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_csv(file: UploadFile) -> str:
    init_storage()
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    safe_name = f"{suffix}-{os.path.basename(file.filename)}"
    file_path = UPLOAD_DIR / safe_name

    try:
        file.file.seek(0)
    except Exception:
        pass

    with open(file_path, "wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            f.flush()

    return str(file_path)