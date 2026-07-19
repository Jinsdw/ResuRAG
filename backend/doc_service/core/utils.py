import hashlib
import re


def compute_md5(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()[:8]


def sanitize_filename(filename: str) -> str:
    name = re.sub(r"[^\w\-_.]", "_", filename)
    return name[:30]
