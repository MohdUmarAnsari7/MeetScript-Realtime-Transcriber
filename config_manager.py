import os
import json
from datetime import datetime


def get_config_path():
    """Locate config.json, checking local directory and parent directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_cfg = os.path.join(current_dir, "config.json")
    parent_cfg = os.path.join(os.path.dirname(current_dir), "config.json")

    if os.path.exists(local_cfg):
        return local_cfg
    if os.path.exists(parent_cfg):
        return parent_cfg
    return local_cfg


def read_config():
    """Read configuration dictionary from JSON file."""
    cfg_file = get_config_path()
    try:
        if os.path.exists(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def write_config(data):
    """Write configuration dictionary to JSON file."""
    cfg_file = get_config_path()
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_saved_folders():
    """Return (saved_paths_list, selected_path)."""
    data = read_config()
    paths = [p for p in data.get("saved_paths", []) if isinstance(p, str) and p.strip()]
    selected = data.get("selected_path", "")
    if selected and selected not in paths:
        paths.insert(0, selected)
    return paths, selected


def save_folder_selection(path):
    """Save selected folder and maintain up to 10 recent folders."""
    path = path.strip() if path else ""
    data = read_config()
    if path:
        paths = [p for p in data.get("saved_paths", []) if isinstance(p, str) and p.strip() and p != path]
        paths.insert(0, path)
        paths = paths[:10]
        data["selected_path"] = path
        data["saved_paths"] = paths
    else:
        data["selected_path"] = ""
    write_config(data)


def get_saved_meeting_name():
    """Return persisted meeting name or empty string."""
    data = read_config()
    return data.get("meeting_name", "")


def save_meeting_name(name):
    """Persist meeting name into config."""
    data = read_config()
    data["meeting_name"] = name.strip() if name else ""
    write_config(data)


def sanitize_filename_part(name, default="Transcript"):
    """Remove illegal filesystem characters from a name."""
    sanitized = (name or "").strip()
    for ch in r'\/:*?"<>|':
        sanitized = sanitized.replace(ch, "-")
    return sanitized if sanitized else default


def build_unique_filepath(folder, meeting_name, date_format="%m-%d-%Y"):
    """
    Generate unique filepath: <Meeting Name> MM-DD-YYYY.txt
    Adds (1), (2), etc. if file already exists.
    """
    clean_name = sanitize_filename_part(meeting_name)
    date_str = datetime.now().strftime(date_format)
    base_filename = f"{clean_name} {date_str}"
    filepath = os.path.join(folder, f"{base_filename}.txt")

    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(folder, f"{base_filename} ({counter}).txt")
        counter += 1

    return filepath


def write_transcript_to_file(filepath, lines):
    """Write timestamped lines to given file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for stamp, text in lines:
            f.write(f"[{stamp}] {text}\n")
