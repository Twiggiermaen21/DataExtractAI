import os
import time

def _request_id():
    return f"ocr-{int(time.time() * 1000)}"

def _file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None

def _fields_summary(fields):
    if not isinstance(fields, dict):
        return {'type': type(fields).__name__}
    keys = list(fields.keys())
    non_empty = [key for key, value in fields.items() if value not in (None, '', [], {})]
    return {
        'keys_count': len(keys),
        'non_empty_count': len(non_empty),
        'keys': keys[:30],
    }
