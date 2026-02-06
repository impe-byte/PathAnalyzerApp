# 📂 PathAnalyzer

**Windows desktop app to scan and analyze directory structures with full path-length auditing.**

Built with Python + CustomTkinter. Compiles to a single standalone `.exe`.

---

## What it does

- Recursively scans any **local** or **network (UNC)** path on Windows
- Generates a **Markdown report** with a clean `tree`-style directory structure
- Detects all paths exceeding a configurable character limit (default: 260 — Windows `MAX_PATH`)
- Shows file distribution by extension, largest files, and detailed path-length statistics
- Modern **dark-mode GUI** with real-time progress, cancel support, and 4 result tabs

## Why

Windows still struggles with paths longer than 260 characters. Before migrating, archiving, or deploying large directory trees, PathAnalyzer gives you a complete picture: which files are at risk, how deep the structure goes, and where the problems are.

## Quick start

```bash
# Run from source
pip install customtkinter
python path_analyzer_gui.py

# Or build a standalone .exe (no Python needed on target machine)
build_exe.bat
```

## Report includes

| Section | Content |
|---------|---------|
| Directory tree | Clean `tree`-style view + detailed view with sizes and path lengths |
| Path analysis | Distribution histogram, all paths over threshold, longest paths by type |
| File stats | Extension breakdown, top N largest files, total size |
| Errors | Permission denied, inaccessible paths |

## Tech

`Python 3.8+` · `CustomTkinter` · `PyInstaller` · Single-file `.exe` · ~20 MB · Windows 10/11

---

*MIT License*
