# LiveLeak Archive Search

**Version 1.0.0**  
Created by **HIGHTECHDUDE**

A desktop application for searching historical **LiveLeak.com** pages preserved in the **Internet Archive Wayback Machine** and **Common Crawl**.

The tool is designed for research, OSINT, and historical web analysis. It lets you run Boolean text queries across archived captures, review matching pages in a results table, and export hits to CSV.

---

## Features

- Boolean search: `AND`, `OR`, `NOT`, parentheses, and `"quoted phrases"`
- Date range filtering by year
- Search sources:
  - Wayback Machine (HTML)
  - Common Crawl (HTML)
  - Optional archived images
- Scrollable results table
- Double-click a result to open the archived page
- CSV export
- Optional Elasticsearch indexing
- Dry-run mode
- Progress bar and live log
- Native-style GUI (CustomTkinter)
- Windows and macOS packaging support

---

## Screenshot

<img width="2710" height="1880" alt="image" src="https://github.com/user-attachments/assets/01c308b8-6776-46cc-b7f4-3525e9c6357b" />


---

## Requirements

### Run from source
- Python 3.11 or 3.12 recommended  
  Python 3.14 may work, but packaging is less reliable
- Internet connection

### Optional
- Elasticsearch, if you want to index and query saved hits locally

---

## Installation

### Option A — Download a release (recommended)

Go to the [Releases](../../releases) page and download:

| Platform | File |
|----------|------|
| Windows  | `LiveLeakSearch_Setup_v1.0.0.exe` |
| macOS    | `LiveLeakSearch_v1.0.0.dmg` |

**Windows**
1. Run the installer
2. Launch **LiveLeak Archive Search** from the Start Menu or Desktop shortcut

**macOS**
1. Open the `.dmg`
2. Drag **LiveLeakSearch** into **Applications**
3. Launch the app  
   If macOS blocks it: **System Settings → Privacy & Security → Open Anyway**

---

### Option B — Run from source

```bash
git clone https://github.com/YOUR_USERNAME/liveleak-archive-search.git
cd liveleak-archive-search
pip install -r requirements.txt
python liveleak_gui.py
