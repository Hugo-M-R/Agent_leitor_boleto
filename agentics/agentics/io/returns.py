import os
from typing import Optional


def next_extraction_path(base_dir: str) -> str:
    n = 1
    while True:
        candidate = os.path.join(base_dir, f"extracao_{n}.json")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def next_transcription_path(base_dir: str) -> str:
    n = 1
    while True:
        candidate = os.path.join(base_dir, f"transcricao_{n}.json")
        if not os.path.exists(candidate):
            return candidate
        n += 1


def last_transcription_path(base_dir: str) -> Optional[str]:
    last = None
    n = 1
    while True:
        candidate = os.path.join(base_dir, f"transcricao_{n}.json")
        if not os.path.exists(candidate):
            break
        last = candidate
        n += 1
    return last


def is_duplicate_transcription(base_dir: str, new_text: str) -> bool:
    try:
        import json as _json
        idx = 1
        while True:
            path = os.path.join(base_dir, f"transcricao_{idx}.json")
            if not os.path.exists(path):
                break
            with open(path, "r", encoding="utf-8") as f:
                obj = _json.load(f)
                if isinstance(obj, dict) and obj.get("transcricao", "") == new_text:
                    return True
            idx += 1
    except Exception:
        return False
    return False


