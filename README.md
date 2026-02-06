# PathAnalyzer Editor v4.0

> Windows desktop application for scanning directory structures, auditing path lengths, and **bulk-renaming files and folders** to fix paths that exceed configurable character limits — with full preview, rollback, and a guided wizard.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Building the Executable (.exe)](#building-the-executable-exe)
- [Usage Guide](#usage-guide)
- [Rename Wizard — Step by Step](#rename-wizard--step-by-step)
- [Available Rename Rules](#available-rename-rules)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Performance & Scale](#performance--scale)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## The Problem

Windows has a classic path length limit of **260 characters** (`MAX_PATH`). Many legacy applications, backup tools, and sync services fail when paths exceed this limit. Deep folder nesting with long names quickly pushes paths beyond it.

The obvious fix — renaming folders and files to shorter names — has a critical technical challenge: **cascading path invalidation**. When you rename a parent folder, every child path changes instantly. If a tool has already queued rename operations using the old paths, they all fail. With 100,000+ files, this creates a catastrophic chain of errors.

```
Before:  C:\Project\Very_Long_Folder_Name\subfolder\report.txt
Rename parent:  Very_Long_Folder_Name → VLF
After:   C:\Project\VLF\subfolder\report.txt

Problem: Any operation still referencing the old path → ERROR
```

---

## The Solution

PathAnalyzer Editor uses a **3-phase architecture** with **bottom-up execution** to completely eliminate cascading path invalidation:

### Phase 1: SCAN (Read-Only)
Full recursive scan of the directory tree. No filesystem changes. Builds an in-memory model.

### Phase 2: PLAN (In-Memory)
The user configures rename rules through the wizard. The engine computes ALL changes in memory without touching the filesystem. Full preview before execution.

### Phase 3: EXECUTE (Bottom-Up)
Operations are sorted by depth (deepest first) and executed bottom-up:

```
Depth 5:  rename deepest files and folders
Depth 4:  rename one level above
Depth 3:  ...
Depth 2:  ...
Depth 1:  ...
Depth 0:  rename root-level items (if needed)
```

**Why this works:** When a folder is renamed, all its children have ALREADY been processed. The old path is still valid at the moment of rename. No cascading invalidation.

```
Bottom-Up Execution Example:

1. Rename C:\A_Long\B_Long\long_file.txt → C:\A_Long\B_Long\lf.txt     OK (file first)
2. Rename C:\A_Long\B_Long\             → C:\A_Long\BL\                 OK (child done)
3. Rename C:\A_Long\                    → C:\AL\                        OK (all children done)

Final result: C:\AL\BL\lf.txt  ✓
```

---

## Features

### Scanning
- Recursive scan of **local** (`C:\`, `D:\`) and **network UNC** (`\\server\share`) paths
- Configurable max depth, folder exclusions, hidden file filtering
- Cancel scan at any time

### Path Analysis
- Character-level path length measurement for every file and folder
- Configurable threshold (default: 260 = Windows `MAX_PATH`)
- Distribution histogram, top 10 longest paths, average/median stats
- Full list of all paths exceeding the threshold

### Rename Editor (Wizard)
- **8 rename rule types** — find/replace, truncate, regex, smart abbreviation, and more
- Rules apply to files, folders, or both — fully configurable
- **Full preview** of every operation before execution
- **Conflict detection** — catches duplicate names, missing paths
- **Bottom-up execution** — eliminates cascading path invalidation
- **Rollback** — undo all changes with one click
- **Undo log** — JSON file saved automatically for recovery

### Interface
- Modern dark-mode GUI with CustomTkinter
- 4 tabs: Structure (tree view), Statistics, Path Analysis, Log
- Real-time progress bar, cancel support
- Markdown report export

---

## Requirements

### To run from source
- **Python 3.8+** (3.11+ recommended)
- **customtkinter** >= 5.2.0

### To build the executable
- All of the above, plus **PyInstaller** >= 6.0

### To use the compiled executable
- **Windows 10/11** (64-bit) — no other dependencies

---

## Quick Start

### 1. Download the project files

Place all files in the same folder:

```
PathAnalyzerEditor/
├── path_analyzer_editor.py     ← Main application
├── requirements.txt            ← Python dependencies
├── PathAnalyzerEditor.spec     ← PyInstaller config
├── build_exe.bat               ← Automated build script
├── ARCHITECTURE.md             ← Technical architecture (Italian)
└── README.md                   ← This file
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python path_analyzer_editor.py
```

---

## Building the Executable (.exe)

### Automated (Recommended)

**Double-click `build_exe.bat`** — it will:
1. Verify Python installation
2. Install dependencies
3. Compile the executable (including CustomTkinter assets)
4. Clean up temporary files
5. Open the output folder

The executable will be at `dist\PathAnalyzerEditor.exe` (~20-25 MB).

### Manual

```bash
pip install -r requirements.txt
pyinstaller PathAnalyzerEditor.spec --clean --noconfirm
```

### Distribution

The `.exe` file is **fully standalone**:
- Does NOT require Python on the target machine
- Does NOT require any additional libraries
- Works on any Windows 10/11 (64-bit)
- Single file, zero configuration

---

## Usage Guide

### 1. Select the Path

Enter the path manually or click **Browse** to select a folder. Supports both local paths and network UNC paths (`\\server\share\folder`).

### 2. Configure Options

| Option | Description | Default |
|--------|-------------|---------|
| **Path Threshold** | Max path length in characters before flagging | `260` |
| **Max Depth** | Recursion limit (`-1` = unlimited) | `-1` |
| **Hidden Files** | Include/exclude hidden files and folders | Included |
| **Exclude Folders** | Comma-separated list of folders to skip | `.git, node_modules, ...` |

### 3. Run the Scan

Click **Scan** and wait for the analysis to complete. Results populate across 4 tabs:

| Tab | Content |
|-----|---------|
| **Structure** | Clean `tree`-style directory view |
| **Statistics** | Extension breakdown, largest files |
| **Path Analysis** | Length distribution, all paths over threshold |
| **Log** | Timestamped operation log |

### 4. Open the Rename Editor

If paths over the threshold are found, the **Rename Editor** button activates. Click it to open the guided wizard.

### 5. Export Report

Click **Export .md** to save a full Markdown report with all analysis results.

---

## Rename Wizard — Step by Step

### Step 1: Configure Rules

Add one or more rename rules from the left panel. Each rule can target files, folders, or both. Rules are applied in sequence (top to bottom).

### Step 2: Preview

The engine calculates ALL operations in memory and displays:
- Total operations planned
- Estimated character savings
- Conflicts (duplicate names, etc.)
- Full list: old name → new name, with path lengths and savings
- Complete path details for every operation

If conflicts are detected, execution is blocked until resolved.

### Step 3: Confirm

Review the summary and choose error handling behavior:
- **Skip and continue** — skip failed operations, process the rest
- **Stop on error** — halt execution at the first failure

### Step 4: Execute

Operations run bottom-up with real-time progress. After completion:
- A **JSON undo log** is saved automatically
- The **Rollback** button lets you revert ALL changes instantly
- A summary shows successes, errors, and details

---

## Available Rename Rules

| Rule | Description | Example |
|------|-------------|---------|
| **Find & Replace** | Replace text in names (case sensitive or not) | `Old_Project` → `OP` |
| **Truncate** | Cut names to max N characters (extension preserved) | `VeryLongName.txt` → `VeryL.txt` |
| **Remove Characters** | Remove specific characters | `file__name` → `filename` |
| **Remove Prefix** | Strip a prefix from names | `backup_report.txt` → `report.txt` |
| **Remove Suffix** | Strip a suffix (before extension) | `file_old.txt` → `file.txt` |
| **Compress Separators** | Collapse repeated separators | `my___file` → `my_file` |
| **Regex Replace** | Custom pattern matching | `IMG_\d{8}` → `img` |
| **Smart Abbreviate** | Auto-shorten common words (EN + IT) | `Documents` → `Docs`, `Configuration` → `Cfg` |

### Smart Abbreviation Dictionary (partial)

```
documents → docs        configuration → cfg       application → app
development → dev       production → prod         temporary → tmp
library → lib           resource → res            information → info
database → db           screenshot → scrn         repository → repo
administration → admin  management → mgmt         specification → spec
```

Italian words are also supported: `documenti → docs`, `configurazione → cfg`, `progetto → prj`, etc.

---

## Architecture

```
path_analyzer_editor.py
│
├── DATA LAYER
│   ├── FileInfo, DirInfo         → File/directory metadata
│   ├── RenameOperation           → Single planned operation (old → new + depth)
│   ├── RenamePlan                → Ordered list of operations + validation
│   └── RenameRule                → User-configured rule with parameters
│
├── ENGINE
│   ├── PathAnalyzer              → Recursive scanner (os.scandir, thread-safe)
│   ├── RenameEngine              → Rename planner + executor
│   │   ├── create_plan()         → Compute all operations in memory
│   │   ├── execute()             → Bottom-up execution with progress
│   │   ├── rollback()            → Reverse all executed operations
│   │   └── save_undo_log()       → JSON log for recovery
│   │
│   └── RuleProcessor             → Apply rename rules to names
│       ├── find_replace()
│       ├── truncate()
│       ├── smart_abbreviate()
│       └── regex_replace()
│
└── GUI
    ├── PathAnalyzerApp           → Main window (scan + analysis + report)
    └── WizardWindow              → 4-step rename wizard
        ├── Step 1: Rules         → Configure rename rules
        ├── Step 2: Preview       → Full diff preview
        ├── Step 3: Confirm       → Warnings + error handling choice
        └── Step 4: Execute       → Progress + rollback + results
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Bottom-up execution** | Eliminates cascading path invalidation — the core problem |
| **3-phase separation** | Scan/Plan/Execute are fully decoupled; Plan never touches disk |
| **os.walk(topdown=False)** | Native bottom-up traversal, proven and efficient |
| **os.scandir()** | 2-20x faster than os.listdir() for large directories |
| **Single-file app** | Simplifies distribution and PyInstaller bundling |
| **JSON undo log** | Machine-readable rollback data, survives app crashes |
| **Thread-per-operation** | GUI never blocks during scan or execution |

---

## Project Structure

```
PathAnalyzerEditor/
├── path_analyzer_editor.py     # Complete application (1400+ lines)
├── requirements.txt            # customtkinter, pyinstaller
├── PathAnalyzerEditor.spec     # PyInstaller config (bundles CTk assets)
├── build_exe.bat               # One-click build script (pure ASCII)
├── ARCHITECTURE.md             # Detailed technical docs (Italian)
└── README.md                   # This file
```

---

## Performance & Scale

### Tested Scale
- Designed for directories with **100,000+ files**
- Scan uses `os.scandir()` for maximum filesystem performance
- Progress updates every N items (not every single one) to avoid GUI overhead

### Memory Usage
- Only metadata is held in memory (name, path, size) — never file contents
- ~50-100 MB RAM for 100K files
- Rename operations are lightweight string pairs

### Robustness
- Network paths (UNC): handled with error tolerance
- Files in use by other processes: skip + log
- Insufficient permissions: skip + log
- Unicode filenames: full support
- Rollback: reverse execution order (top-down) for safe undo

---

## Troubleshooting

### Antivirus blocks the .exe
PyInstaller-generated executables trigger false positives in some antivirus software. Add an exception for `PathAnalyzerEditor.exe`.

### "ModuleNotFoundError: customtkinter"
```bash
pip install customtkinter --upgrade
```

### Build fails with customtkinter error
Always use the `.spec` file which includes CustomTkinter assets:
```bash
pyinstaller PathAnalyzerEditor.spec --clean --noconfirm
```

### The .exe opens and closes immediately
Run from terminal to see errors:
```bash
cd dist
PathAnalyzerEditor.exe
```

### Network path not working
- Verify the UNC path is reachable: `dir \\server\share\folder`
- Check access permissions
- Network latency may cause timeouts on very large shares

### Scan is slow on huge directories
- Set a **max depth** limit (e.g., 5)
- **Exclude** heavy folders: `node_modules, .git, bin, obj, dist, build`
- The scan runs in a separate thread — the GUI stays responsive

### Rollback doesn't fully restore
- The JSON undo log is saved next to the scanned directory
- If files were modified by other processes after rename, rollback may partially fail
- Always check the log for details

---

## License

Free to use, modify, and redistribute.

---

*PathAnalyzer Editor v4.0 — Built with Python + CustomTkinter*
