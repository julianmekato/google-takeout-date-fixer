# Google Takeout Date Fixer

Restore the correct creation dates of photos and videos exported from **Google Takeout**.

When exporting from Google Photos, many files lose their original timestamps and inherit the download date instead.  
Google provides the real date inside `.json` metadata files — but it is not automatically applied.

This script fixes that.

---

## 🚀 What This Script Does

- Restores file timestamps from `.supplemental-metadata.json`
- Falls back to extracting dates from filenames when JSON is missing
- Works recursively across subfolders
- Handles thousands of files efficiently
- Idempotent (safe to run multiple times)
- Generates detailed `log.txt`
- Supports dry-run mode

---

## 📂 Supported File Types

- `.jpg`
- `.jpeg`
- `.png`
- `.heic`
- `.mp4`
- `.mov`

---

## 🧠 Smart Date Detection

### 1️⃣ Priority: JSON Metadata

Extracts:
- `photoTakenTime.timestamp`
- `creationTime.timestamp`

Fully supports:
- `.supplemental-metadata.json`
- `.supp.json`
- `.s.json`
- Duplicate filenames like `(1)`
- Edited versions like `-editada`
- WhatsApp naming inconsistencies

---

### 2️⃣ Fallback: Filename Date Extraction

Automatically detects dates from patterns like:
IMG-20221221-WA0158.jpg
VID-20220730-WA0161.mp4
null-20231004-WA0156.jpg
Screenshot_2022-11-16-20-16-26.png
Screenrecorder-2022-12-07-14-37-31.mp4
PXL_20230115_153045123.jpg

The script uses generic date detection (`YYYYMMDD` or `YYYY-MM-DD`)  
so it works regardless of file prefix.

---

## 🛡 Idempotent & Safe

The script:
- Only updates files if timestamp differs by more than 2 seconds
- Can be run multiple times safely
- Tracks JSON files used
- Reports orphan JSON files

---

## 📊 Output Summary Example

Multimedia : 8527
JSON total : 8366
JSON used : 6970
Modified : 7099 (JSON: 6970 | Filename: 129)
Without date : 1428
Orphan JSON : 396
Duration : 12.06 seconds

---

## 📝 Log File

Generates a `log.txt` containing:

- Files modified via JSON
- Files modified via filename
- Files without detectable date
- Orphan JSON files
- Matched multimedia + JSON pairs

---

## ⚙️ Installation

Requires Python 3.8+
Install dependency:
bash
pip install tqdm

▶ Usage
Dry run (recommended first)
python cambiar_fecha_v8.py --dryrun

Apply changes
python cambiar_fecha_v8.py
