#!/usr/bin/env python3
"""
Google Photos Takeout Timestamp Restorer
=========================================

Version: 1.0.0
Author: Your Name
License: MIT (recommended)

Description:
------------
This script restores the correct file system timestamps of media files
exported from Google Photos Takeout.

It prioritizes:
1. Metadata extracted from associated JSON files
2. Date patterns detected in filenames (fallback)

Features:
---------
- Matches media files with their corresponding JSON metadata
- Supports Google supplemental metadata formats
- Intelligent fallback matching logic
- Dry-run mode (safe preview)
- Detailed log.txt output
- Detects orphan JSON files
- Handles duplicate and edited files

Supported media formats:
.jpg, .jpeg, .png, .heic, .mp4, .mov

Usage:
------
Dry run (no changes applied):
    python script.py --dryrun

Apply changes:
    python script.py

Dependency:
    pip install tqdm
"""

import os
import re
import json
import argparse
import unicodedata
from tqdm import tqdm
from datetime import datetime
from pathlib import Path
import time

# ============================================================
# Configuration & Arguments
# ============================================================

VERSION = "1.0.0"

parser = argparse.ArgumentParser(description="Restore timestamps from Google Photos Takeout")
parser.add_argument("--dryrun", action="store_true", help="Preview changes without modifying files")
args = parser.parse_args()

DRYRUN = args.dryrun

# ============================================================
# Initialization
# ============================================================

start_time = time.time()
base_path = Path.cwd()
log_file = base_path / "log.txt"

if log_file.exists():
    log_file.unlink()

def log(message=""):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def log_section(title, items):
    log()
    log("=" * 65)
    log(f"{title} ({len(items)} items)")
    log("=" * 65)
    for item in items:
        log(str(item))

print(f"\nProcessing folder: {base_path}")
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Version: {VERSION}\n")

log(f"Processing folder: {base_path}")
log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log(f"Version: {VERSION}")
log()

# ============================================================
# File Discovery
# ============================================================

MEDIA_EXTENSIONS = (".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov")

media_files = [
    p for p in base_path.rglob("*")
    if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
]

json_files = list(base_path.rglob("*.json"))

# ============================================================
# Utility Functions
# ============================================================

def normalize_text(text):
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_base_name(name):
    name = name.lower()

    # Remove Google metadata suffixes
    name = re.sub(r'\.supplemental-metadata\.json$', '', name)
    name = re.sub(r'\.supp\.json$', '', name)
    name = re.sub(r'\.s\.json$', '', name)
    name = re.sub(r'\.json$', '', name)

    # Remove media extension
    name = re.sub(r'\.(jpg|jpeg|png|heic|mp4|mov)$', '', name)

    # Remove duplicate numbering (1)
    name = re.sub(r'\(\d+\)', '', name)

    return name.strip()

# ============================================================
# JSON Indexing
# ============================================================

json_index_by_folder = {}

for j in json_files:
    base = clean_base_name(j.name)
    folder = str(j.parent).lower()

    if folder not in json_index_by_folder:
        json_index_by_folder[folder] = {}

    json_index_by_folder[folder][base] = j

# ============================================================
# Tracking Collections
# ============================================================

modified_total = 0
modified_from_json = 0
modified_from_name = 0

modified_json_files = []
modified_name_files = []
files_without_date = []
json_used = set()
orphan_json = []
matched_pairs = []

# ============================================================
# JSON Matching Logic
# ============================================================

def find_matching_json(base_name, index):
    if base_name in index:
        return index[base_name]

    stripped_ext = re.sub(r'\.(jpg|jpeg|png|heic|mp4|mov)$', '', base_name, flags=re.IGNORECASE)
    if stripped_ext in index:
        return index[stripped_ext]

    stripped_num = re.sub(r'\(\d+\)', '', base_name)
    if stripped_num in index:
        return index[stripped_num]

    return None

# ============================================================
# Main Processing
# ============================================================

for media in tqdm(media_files, desc="Processing media", unit="file"):

    new_date = None
    source = None

    base_name = clean_base_name(media.name)
    current_folder = str(media.parent).lower()

    json_match = None

    # First search in same folder
    if current_folder in json_index_by_folder:
        json_match = find_matching_json(base_name, json_index_by_folder[current_folder])

    # Process JSON if found
    if json_match:
        try:
            with open(json_match, "r", encoding="utf-8") as f:
                data = json.load(f)

            timestamp = None
            if "photoTakenTime" in data and "timestamp" in data["photoTakenTime"]:
                timestamp = data["photoTakenTime"]["timestamp"]
            elif "creationTime" in data and "timestamp" in data["creationTime"]:
                timestamp = data["creationTime"]["timestamp"]

            if timestamp and str(timestamp).isdigit():
                new_date = datetime.fromtimestamp(int(timestamp))
                source = "JSON"
                json_used.add(str(json_match))

                matched_pairs.append((str(media), str(json_match)))

        except Exception:
            pass

    # Fallback: Extract date from filename
    if not new_date:
        patterns = [
            r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)',              # YYYYMMDD
            r'(\d{4})-(\d{2})-(\d{2})',                        # YYYY-MM-DD
            r'(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})', # YYYYMMDD_HHMMSS
        ]

        for pattern in patterns:
            match = re.search(pattern, media.name)
            if match:
                try:
                    groups = match.groups()
                    year, month, day = map(int, groups[:3])

                    if len(groups) >= 6:
                        hour, minute, second = map(int, groups[3:6])
                        new_date = datetime(year, month, day, hour, minute, second)
                    else:
                        new_date = datetime(year, month, day)

                    source = "FILENAME"
                    break
                except Exception:
                    pass

    # Apply timestamp
    if new_date:
        current_stat = media.stat()
        current_ctime = datetime.fromtimestamp(current_stat.st_ctime)

        if abs((current_ctime - new_date).total_seconds()) > 2:

            if not DRYRUN:
                ts = new_date.timestamp()
                os.utime(media, (ts, ts))

            modified_total += 1

            if source == "JSON":
                modified_from_json += 1
                modified_json_files.append(str(media))
            else:
                modified_from_name += 1
                modified_name_files.append(str(media))
    else:
        files_without_date.append(str(media))

# Detect orphan JSON files
for j in json_files:
    if str(j) not in json_used:
        orphan_json.append(str(j))

# ============================================================
# Summary
# ============================================================

duration = round(time.time() - start_time, 2)

print("\n========== SUMMARY ==========")
print(f"Media files       : {len(media_files)}")
print(f"JSON files        : {len(json_files)}")
print(f"JSON used         : {len(json_used)}")
print(f"Modified files    : {modified_total}")
print(f"  From JSON       : {modified_from_json}")
print(f"  From filename   : {modified_from_name}")
print(f"Without timestamp : {len(files_without_date)}")
print(f"Orphan JSON       : {len(orphan_json)}")
print(f"Duration          : {duration} seconds")
print("=============================\n")

# ============================================================
# Logging
# ============================================================

log_section("Modified from JSON", modified_json_files)
log_section("Modified from filename", modified_name_files)
log_section("Files without detectable date", files_without_date)
log_section("Orphan JSON files", orphan_json)

log("\nMatched media + JSON pairs:")
for media_path, json_path in matched_pairs:
    log(f"Media: {media_path}")
    log(f"JSON : {json_path}\n")

log(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")