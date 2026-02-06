#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║              PATH ANALYZER v3.0 — GUI Edition               ║
║         Analizzatore di struttura directory per Windows      ║
║         Supporta percorsi locali e di rete (UNC)            ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import threading
import datetime
import time
import webbrowser
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk


# ─── Costanti Albero ─────────────────────────────────────────────────────────
PIPE   = "│   "
TEE    = "├── "
ELBOW  = "└── "
SPACE  = "    "

# ─── Icone per tipo di file ──────────────────────────────────────────────────
FILE_ICONS = {
    ".pdf": "📄", ".doc": "📝", ".docx": "📝", ".odt": "📝",
    ".xls": "📊", ".xlsx": "📊", ".csv": "📊", ".ods": "📊",
    ".ppt": "📽️", ".pptx": "📽️", ".odp": "📽️",
    ".txt": "📃", ".rtf": "📃", ".md": "📑", ".log": "📃",
    ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️",
    ".bmp": "🖼️", ".svg": "🖼️", ".ico": "🖼️", ".webp": "🖼️",
    ".psd": "🎨", ".ai": "🎨",
    ".mp4": "🎬", ".avi": "🎬", ".mkv": "🎬", ".mov": "🎬",
    ".mp3": "🎵", ".wav": "🎵", ".flac": "🎵", ".ogg": "🎵",
    ".py": "🐍", ".js": "⚡", ".ts": "⚡", ".jsx": "⚡", ".tsx": "⚡",
    ".html": "🌐", ".css": "🎨", ".scss": "🎨",
    ".java": "☕", ".cs": "🔷", ".cpp": "⚙️", ".c": "⚙️", ".h": "⚙️",
    ".rs": "🦀", ".go": "🐹", ".rb": "💎", ".php": "🐘",
    ".sql": "🗃️", ".json": "📋", ".xml": "📋", ".yaml": "📋", ".yml": "📋",
    ".sh": "🐚", ".bat": "🐚", ".ps1": "🐚", ".cmd": "🐚",
    ".zip": "📦", ".rar": "📦", ".7z": "📦", ".tar": "📦", ".gz": "📦",
    ".exe": "⚙️", ".msi": "⚙️", ".dll": "🔧", ".sys": "🔧",
    ".db": "🗄️", ".sqlite": "🗄️", ".mdb": "🗄️", ".accdb": "🗄️",
    ".ttf": "🔤", ".otf": "🔤", ".woff": "🔤", ".woff2": "🔤",
    ".ini": "⚙️", ".cfg": "⚙️", ".conf": "⚙️", ".env": "⚙️",
    ".bak": "💾", ".iso": "💿", ".img": "💿", ".vhd": "💿",
}

FOLDER_ICON = "📁"
UNKNOWN_ICON = "📄"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    name: str
    path: str
    extension: str
    size: int
    modified: float
    path_length: int = 0
    is_hidden: bool = False

@dataclass
class DirInfo:
    name: str
    path: str
    files: list = field(default_factory=list)
    subdirs: list = field(default_factory=list)
    total_files: int = 0
    total_size: int = 0
    depth: int = 0
    path_length: int = 0
    error: Optional[str] = None

@dataclass
class PathLengthStats:
    all_paths: list = field(default_factory=list)
    over_limit: list = field(default_factory=list)
    longest_file_path: str = ""
    longest_file_length: int = 0
    longest_dir_path: str = ""
    longest_dir_length: int = 0
    avg_length: float = 0
    median_length: int = 0
    distribution: dict = field(default_factory=lambda: defaultdict(int))

@dataclass
class ScanStats:
    total_dirs: int = 0
    total_files: int = 0
    total_size: int = 0
    max_depth: int = 0
    extensions: dict = field(default_factory=lambda: defaultdict(int))
    ext_sizes: dict = field(default_factory=lambda: defaultdict(int))
    largest_files: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    path_stats: PathLengthStats = field(default_factory=PathLengthStats)
    scan_start: float = 0
    scan_end: float = 0


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def format_size(size_bytes: int) -> str:
    if size_bytes < 0:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes} {unit}" if unit == 'B' else f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def format_date(timestamp: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")
    except (OSError, ValueError):
        return "N/A"

def is_hidden(filepath: str) -> bool:
    name = os.path.basename(filepath)
    if name.startswith('.'):
        return True
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
        if attrs != -1:
            return bool(attrs & 0x2)
    except (AttributeError, OSError):
        pass
    return False

def get_file_icon(extension: str) -> str:
    return FILE_ICONS.get(extension.lower(), UNKNOWN_ICON)

def safe_stat(path: str) -> Optional[os.stat_result]:
    try:
        return os.stat(path)
    except (OSError, PermissionError):
        return None

def get_path_length_range(length: int) -> str:
    if length <= 50:      return "0-50"
    elif length <= 100:   return "51-100"
    elif length <= 150:   return "101-150"
    elif length <= 200:   return "151-200"
    elif length <= 260:   return "201-260"
    elif length <= 300:   return "261-300"
    else:                 return "300+"


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PathAnalyzer:

    def __init__(self, root_path, max_depth=-1, exclude_dirs=None,
                 show_hidden=True, top_n_files=15, path_limit=260,
                 progress_callback=None):
        self.root_path = os.path.abspath(root_path)
        self.max_depth = max_depth
        self.exclude_dirs = set(exclude_dirs or [])
        self.show_hidden = show_hidden
        self.top_n_files = top_n_files
        self.path_limit = path_limit
        self.progress_callback = progress_callback
        self.stats = ScanStats()
        self.root_dir: Optional[DirInfo] = None
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def scan(self) -> Optional[DirInfo]:
        self.stats.scan_start = time.time()
        self._cancel = False

        if not os.path.exists(self.root_path):
            raise FileNotFoundError(f"Il percorso '{self.root_path}' non esiste.")
        if not os.path.isdir(self.root_path):
            raise NotADirectoryError(f"'{self.root_path}' non è una directory.")

        self.root_dir = self._scan_directory(self.root_path, depth=0)

        if self._cancel:
            return None

        self.stats.scan_end = time.time()
        self.stats.largest_files.sort(key=lambda x: x.size, reverse=True)
        self.stats.largest_files = self.stats.largest_files[:self.top_n_files]
        self._compute_path_stats()
        return self.root_dir

    def _scan_directory(self, dir_path, depth):
        if self._cancel:
            return DirInfo(name="", path="")

        dir_name = os.path.basename(dir_path) or dir_path
        path_len = len(dir_path)
        dir_info = DirInfo(name=dir_name, path=dir_path, depth=depth, path_length=path_len)

        self.stats.total_dirs += 1
        self.stats.max_depth = max(self.stats.max_depth, depth)
        self.stats.path_stats.all_paths.append((dir_path, path_len, "DIR"))
        if path_len > self.path_limit:
            self.stats.path_stats.over_limit.append((dir_path, path_len, "DIR"))

        if self.progress_callback and self.stats.total_dirs % 20 == 0:
            self.progress_callback(self.stats.total_dirs, self.stats.total_files)

        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            dir_info.error = "Accesso negato"
            self.stats.errors.append(f"Accesso negato: {dir_path}")
            return dir_info
        except OSError as e:
            dir_info.error = str(e)
            self.stats.errors.append(f"Errore: {dir_path} → {e}")
            return dir_info

        for entry in entries:
            if self._cancel:
                break
            try:
                if not self.show_hidden and is_hidden(entry.path):
                    continue
                if entry.name in self.exclude_dirs:
                    continue

                if entry.is_dir(follow_symlinks=False):
                    if self.max_depth >= 0 and depth >= self.max_depth:
                        continue
                    subdir = self._scan_directory(entry.path, depth + 1)
                    dir_info.subdirs.append(subdir)
                    dir_info.total_files += subdir.total_files
                    dir_info.total_size += subdir.total_size
                elif entry.is_file(follow_symlinks=False):
                    stat = safe_stat(entry.path)
                    size = stat.st_size if stat else 0
                    modified = stat.st_mtime if stat else 0
                    ext = os.path.splitext(entry.name)[1].lower()
                    file_path_len = len(entry.path)

                    file_info = FileInfo(
                        name=entry.name, path=entry.path, extension=ext,
                        size=size, modified=modified, path_length=file_path_len,
                        is_hidden=is_hidden(entry.path),
                    )
                    dir_info.files.append(file_info)
                    dir_info.total_files += 1
                    dir_info.total_size += size
                    self.stats.total_files += 1
                    self.stats.total_size += size
                    self.stats.extensions[ext if ext else "(nessuna)"] += 1
                    self.stats.ext_sizes[ext if ext else "(nessuna)"] += size
                    self.stats.path_stats.all_paths.append((entry.path, file_path_len, "FILE"))
                    if file_path_len > self.path_limit:
                        self.stats.path_stats.over_limit.append((entry.path, file_path_len, "FILE"))
                    self.stats.largest_files.append(file_info)
                    if len(self.stats.largest_files) > self.top_n_files * 3:
                        self.stats.largest_files.sort(key=lambda x: x.size, reverse=True)
                        self.stats.largest_files = self.stats.largest_files[:self.top_n_files]
            except (PermissionError, OSError):
                continue

        return dir_info

    def _compute_path_stats(self):
        ps = self.stats.path_stats
        if not ps.all_paths:
            return
        lengths = sorted([p[1] for p in ps.all_paths])
        ps.avg_length = sum(lengths) / len(lengths)
        ps.median_length = lengths[len(lengths) // 2]
        for _, length, _ in ps.all_paths:
            ps.distribution[get_path_length_range(length)] += 1
        file_paths = [(p, l) for p, l, t in ps.all_paths if t == "FILE"]
        dir_paths = [(p, l) for p, l, t in ps.all_paths if t == "DIR"]
        if file_paths:
            lf = max(file_paths, key=lambda x: x[1])
            ps.longest_file_path, ps.longest_file_length = lf
        if dir_paths:
            ld = max(dir_paths, key=lambda x: x[1])
            ps.longest_dir_path, ps.longest_dir_length = ld
        ps.over_limit.sort(key=lambda x: x[1], reverse=True)

    # ─── Albero Pulito ───────────────────────────────────────────────────

    def build_clean_tree(self, dir_info, prefix="", is_last=True, is_root=True):
        lines = []
        if is_root:
            lines.append(dir_info.name)
            child_prefix = ""
        else:
            connector = ELBOW if is_last else TEE
            lines.append(f"{prefix}{connector}{dir_info.name}")
            child_prefix = prefix + (SPACE if is_last else PIPE)

        items = [(True, s) for s in dir_info.subdirs] + [(False, f) for f in dir_info.files]
        for i, (is_dir, item) in enumerate(items):
            last = (i == len(items) - 1)
            if is_dir:
                lines.extend(self.build_clean_tree(item, child_prefix, last, False))
            else:
                lines.append(f"{child_prefix}{ELBOW if last else TEE}{item.name}")
        return lines

    # ─── Albero Dettagliato ──────────────────────────────────────────────

    def build_detail_tree(self, dir_info, prefix="", is_last=True, is_root=True):
        lines = []
        if is_root:
            lines.append(f"{FOLDER_ICON} {dir_info.name}/  [{format_size(dir_info.total_size)}] (path: {dir_info.path_length} chars)")
            child_prefix = ""
        else:
            connector = ELBOW if is_last else TEE
            size_str = f"  [{format_size(dir_info.total_size)}]" if dir_info.total_size > 0 else ""
            error_str = f"  ⚠️ {dir_info.error}" if dir_info.error else ""
            warn = " ❌" if dir_info.path_length > self.path_limit else ""
            lines.append(f"{prefix}{connector}{FOLDER_ICON} {dir_info.name}/{size_str}  (path: {dir_info.path_length} chars){warn}{error_str}")
            child_prefix = prefix + (SPACE if is_last else PIPE)

        items = [(True, s) for s in dir_info.subdirs] + [(False, f) for f in dir_info.files]
        for i, (is_dir, item) in enumerate(items):
            last = (i == len(items) - 1)
            if is_dir:
                lines.extend(self.build_detail_tree(item, child_prefix, last, False))
            else:
                connector = ELBOW if last else TEE
                icon = get_file_icon(item.extension)
                warn = " ❌" if item.path_length > self.path_limit else ""
                lines.append(f"{child_prefix}{connector}{icon} {item.name}  ({format_size(item.size)}, path: {item.path_length} chars){warn}")
        return lines

    # ─── Genera Report MD ────────────────────────────────────────────────

    def generate_report(self, output_path):
        if self.root_dir is None:
            return None

        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        elapsed = self.stats.scan_end - self.stats.scan_start
        ps = self.stats.path_stats
        path_type = "🌐 Percorso di rete (UNC)" if self.root_path.startswith("\\\\") else "💻 Percorso locale"

        L = []

        # HEADER
        L.append("# 📂 Path Analyzer Report")
        L.append("")
        L.append(f"> Report generato il **{now}** — Path Analyzer v3.0 GUI")
        L.append("")
        L.append("---")
        L.append("")

        # INFO
        L.append("## ℹ️ Informazioni Percorso")
        L.append("")
        L.append("| Proprietà | Valore |")
        L.append("|-----------|--------|")
        L.append(f"| **Percorso analizzato** | `{self.root_path}` |")
        L.append(f"| **Tipo** | {path_type} |")
        L.append(f"| **Lunghezza percorso root** | {len(self.root_path)} caratteri |")
        L.append(f"| **Tempo di scansione** | {elapsed:.2f} secondi |")
        L.append(f"| **Profondità massima** | {self.stats.max_depth} livelli |")
        L.append(f"| **Soglia lunghezza path** | {self.path_limit} caratteri |")
        if self.max_depth >= 0:
            L.append(f"| **Limite profondità** | {self.max_depth} livelli |")
        if self.exclude_dirs:
            L.append(f"| **Cartelle escluse** | `{'`, `'.join(self.exclude_dirs)}` |")
        L.append(f"| **File nascosti** | {'Inclusi' if self.show_hidden else 'Esclusi'} |")
        L.append("")

        # RIEPILOGO
        L.append("## 📊 Riepilogo Generale")
        L.append("")
        L.append("| Metrica | Valore |")
        L.append("|---------|--------|")
        L.append(f"| 📁 **Cartelle totali** | {self.stats.total_dirs:,} |")
        L.append(f"| 📄 **File totali** | {self.stats.total_files:,} |")
        L.append(f"| 💾 **Dimensione totale** | {format_size(self.stats.total_size)} |")
        L.append(f"| 📏 **Profondità albero** | {self.stats.max_depth} livelli |")
        L.append(f"| 🏷️ **Tipi di file unici** | {len(self.stats.extensions)} estensioni |")
        L.append(f"| 📐 **Path medio** | {ps.avg_length:.0f} caratteri |")
        L.append(f"| 📐 **Path mediano** | {ps.median_length} caratteri |")
        L.append(f"| 🔴 **Path oltre soglia ({self.path_limit})** | **{len(ps.over_limit)}** |")
        L.append("")

        # ANALISI PATH
        L.append("## 📐 Analisi Lunghezza Percorsi")
        L.append("")
        L.append(f"> Soglia: **{self.path_limit} caratteri** (MAX_PATH Windows = 260)")
        L.append("")

        L.append("### Distribuzione")
        L.append("")
        range_order = ["0-50", "51-100", "101-150", "151-200", "201-260", "261-300", "300+"]
        total_paths = len(ps.all_paths) or 1
        L.append("| Range | Conteggio | % | Distribuzione |")
        L.append("|-------|-----------|---|---------------|")
        for r in range_order:
            count = ps.distribution.get(r, 0)
            pct = count / total_paths * 100
            bar = "█" * max(0, int(pct / 2))
            marker = " 🔴" if r in ("261-300", "300+") and count > 0 else ""
            L.append(f"| `{r}` | {count:,} | {pct:.1f}% | {bar}{marker} |")
        L.append("")

        # Top 10 path più lunghi
        all_sorted = sorted(ps.all_paths, key=lambda x: x[1], reverse=True)[:10]
        if all_sorted:
            L.append("### 🏆 Top 10 Percorsi più Lunghi")
            L.append("")
            L.append("| # | Tipo | Lunghezza | Stato | Percorso |")
            L.append("|---|------|-----------|-------|----------|")
            for i, (path, length, ptype) in enumerate(all_sorted, 1):
                tipo = "📁 DIR" if ptype == "DIR" else "📄 FILE"
                stato = "🔴 OLTRE" if length > self.path_limit else "✅ OK"
                try:
                    rel = os.path.relpath(path, self.root_path)
                except ValueError:
                    rel = path
                L.append(f"| {i} | {tipo} | **{length}** | {stato} | `{rel}` |")
            L.append("")

        # Path oltre soglia
        if ps.over_limit:
            L.append(f"### 🔴 Percorsi Oltre la Soglia ({self.path_limit} caratteri)")
            L.append("")
            L.append(f"> **{len(ps.over_limit)}** percorsi problematici trovati.")
            L.append("")
            L.append("| # | Tipo | Lunghezza | Eccesso | Percorso |")
            L.append("|---|------|-----------|---------|----------|")
            for i, (path, length, ptype) in enumerate(ps.over_limit, 1):
                tipo = "📁" if ptype == "DIR" else "📄"
                L.append(f"| {i} | {tipo} | **{length}** | +{length - self.path_limit} | `{path}` |")
            L.append("")
        else:
            L.append("### ✅ Nessun Percorso Oltre la Soglia")
            L.append("")
            L.append(f"> Tutti i {len(ps.all_paths):,} percorsi sono entro {self.path_limit} caratteri.")
            L.append("")

        # Path più lunghi per tipo
        if ps.longest_file_path:
            w = " 🔴" if ps.longest_file_length > self.path_limit else " ✅"
            L.append(f"**File più lungo** ({ps.longest_file_length} chars){w}")
            L.append("```")
            L.append(ps.longest_file_path)
            L.append("```")
            L.append("")
        if ps.longest_dir_path:
            w = " 🔴" if ps.longest_dir_length > self.path_limit else " ✅"
            L.append(f"**Cartella più lunga** ({ps.longest_dir_length} chars){w}")
            L.append("```")
            L.append(ps.longest_dir_path)
            L.append("```")
            L.append("")

        # ESTENSIONI
        L.append("## 🏷️ Distribuzione per Estensione")
        L.append("")
        sorted_exts = sorted(self.stats.extensions.items(), key=lambda x: x[1], reverse=True)
        if sorted_exts:
            L.append("| Estensione | Conteggio | Dimensione | % |")
            L.append("|------------|-----------|------------|---|")
            for ext, count in sorted_exts[:25]:
                size = self.stats.ext_sizes.get(ext, 0)
                pct = (count / self.stats.total_files * 100) if self.stats.total_files > 0 else 0
                icon = get_file_icon(ext) if ext != "(nessuna)" else "❓"
                bar = "█" * max(1, int(pct / 3))
                L.append(f"| {icon} `{ext}` | {count:,} | {format_size(size)} | {bar} {pct:.1f}% |")
            L.append("")

        # FILE PIÙ GRANDI
        if self.stats.largest_files:
            L.append(f"## 📏 Top {len(self.stats.largest_files)} File più Grandi")
            L.append("")
            L.append("| # | File | Dimensione | Path Length | Percorso |")
            L.append("|---|------|------------|------------|----------|")
            for i, f in enumerate(self.stats.largest_files, 1):
                icon = get_file_icon(f.extension)
                try:
                    rel = os.path.relpath(os.path.dirname(f.path), self.root_path)
                    rel = "/" if rel == "." else f"/{rel}/"
                except ValueError:
                    rel = os.path.dirname(f.path)
                w = " 🔴" if f.path_length > self.path_limit else ""
                L.append(f"| {i} | {icon} `{f.name}` | **{format_size(f.size)}** | {f.path_length}{w} | `{rel}` |")
            L.append("")

        # ERRORI
        if self.stats.errors:
            L.append("## ⚠️ Errori")
            L.append("")
            for err in self.stats.errors[:20]:
                L.append(f"- {err}")
            if len(self.stats.errors) > 20:
                L.append(f"- *+{len(self.stats.errors) - 20} altri*")
            L.append("")

        # ALBERO PULITO
        L.append("---")
        L.append("")
        L.append("## 🌳 Struttura Directory")
        L.append("")
        L.append("### Vista Pulita")
        L.append("")
        L.append("```")
        L.extend(self.build_clean_tree(self.root_dir))
        L.append("```")
        L.append("")

        # ALBERO DETTAGLIATO
        L.append("### Vista Dettagliata")
        L.append("")
        L.append("```")
        L.extend(self.build_detail_tree(self.root_dir))
        L.append("```")
        L.append("")
        L.append(f"> ❌ = path oltre {self.path_limit} caratteri")
        L.append("")

        # INDICE FILE
        L.append("---")
        L.append("")
        L.append("## 📋 Indice Completo")
        L.append("")
        self._file_index(self.root_dir, L)
        L.append("")

        # FOOTER
        L.append("---")
        L.append(f"*Path Analyzer v3.0 GUI — {now} — Soglia: {self.path_limit} chars*")
        L.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(L))

        return output_path

    def _file_index(self, dir_info, lines, rel_prefix=""):
        current = os.path.join(rel_prefix, dir_info.name) if rel_prefix else dir_info.name
        if dir_info.files:
            lines.append(f"### {FOLDER_ICON} `{current}/`")
            lines.append("")
            lines.append("| File | Ext | Dimensione | Path Len | Modificato |")
            lines.append("|------|-----|------------|----------|------------|")
            for f in sorted(dir_info.files, key=lambda x: x.name.lower()):
                icon = get_file_icon(f.extension)
                ext = f.extension or "—"
                w = " 🔴" if f.path_length > self.path_limit else ""
                lines.append(f"| {icon} {f.name} | `{ext}` | {format_size(f.size)} | {f.path_length}{w} | {format_date(f.modified)} |")
            lines.append("")
        for sub in dir_info.subdirs:
            self._file_index(sub, lines, current)


# ═══════════════════════════════════════════════════════════════════════════════
# GUI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class PathAnalyzerApp(ctk.CTk):

    APP_NAME = "Path Analyzer v3.0"
    APP_SIZE = "1000x720"

    def __init__(self):
        super().__init__()

        self.title(self.APP_NAME)
        self.geometry(self.APP_SIZE)
        self.minsize(800, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.analyzer: Optional[PathAnalyzer] = None
        self._scan_thread: Optional[threading.Thread] = None

        self._build_ui()

    def _build_ui(self):
        # ── Top Bar ──────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(top, text="📂 Path Analyzer", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkLabel(top, text="v3.0 GUI", font=ctk.CTkFont(size=12), text_color="gray").pack(side="left", padx=(8, 0), pady=(6, 0))

        # ── Percorso ─────────────────────────────────────────────────────
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(path_frame, text="Percorso:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        self.path_var = ctk.StringVar()
        self.path_entry = ctk.CTkEntry(path_frame, textvariable=self.path_var, placeholder_text="C:\\Users\\... oppure \\\\server\\share\\...", height=36)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(8, 4))

        ctk.CTkButton(path_frame, text="📁 Sfoglia", width=100, height=36, command=self._browse_folder).pack(side="left", padx=(4, 0))

        # ── Opzioni ──────────────────────────────────────────────────────
        opts_frame = ctk.CTkFrame(self)
        opts_frame.pack(fill="x", padx=16, pady=8)

        # Riga 1
        row1 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(row1, text="Soglia Path (chars):").pack(side="left")
        self.limit_var = ctk.StringVar(value="260")
        ctk.CTkEntry(row1, textvariable=self.limit_var, width=80, height=30).pack(side="left", padx=(4, 16))

        ctk.CTkLabel(row1, text="Profondità max:").pack(side="left")
        self.depth_var = ctk.StringVar(value="-1")
        ctk.CTkEntry(row1, textvariable=self.depth_var, width=60, height=30).pack(side="left", padx=(4, 16))

        ctk.CTkLabel(row1, text="Top file:").pack(side="left")
        self.topn_var = ctk.StringVar(value="15")
        ctk.CTkEntry(row1, textvariable=self.topn_var, width=60, height=30).pack(side="left", padx=(4, 16))

        # Riga 2
        row2 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 10))

        self.hidden_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Mostra file nascosti", variable=self.hidden_var).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Escludi cartelle:").pack(side="left")
        self.exclude_var = ctk.StringVar(value=".git, node_modules, __pycache__, .vs, .vscode")
        ctk.CTkEntry(row2, textvariable=self.exclude_var, height=30).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ── Bottoni Azione ───────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=4)

        self.scan_btn = ctk.CTkButton(btn_frame, text="🔍 Avvia Scansione", height=40, font=ctk.CTkFont(size=14, weight="bold"), command=self._start_scan)
        self.scan_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(btn_frame, text="⏹ Annulla", height=40, fg_color="#c0392b", hover_color="#e74c3c", state="disabled", command=self._cancel_scan)
        self.cancel_btn.pack(side="left", padx=(0, 8))

        self.export_btn = ctk.CTkButton(btn_frame, text="💾 Esporta Report .md", height=40, fg_color="#27ae60", hover_color="#2ecc71", state="disabled", command=self._export_report)
        self.export_btn.pack(side="left", padx=(0, 8))

        self.open_btn = ctk.CTkButton(btn_frame, text="📂 Apri Report", height=40, fg_color="#8e44ad", hover_color="#9b59b6", state="disabled", command=self._open_report)
        self.open_btn.pack(side="left")

        # ── Progress ─────────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=16, pady=(4, 0))

        self.progress = ctk.CTkProgressBar(prog_frame, mode="indeterminate")
        self.progress.pack(fill="x")
        self.progress.set(0)

        self.status_var = ctk.StringVar(value="Pronto. Seleziona un percorso e avvia la scansione.")
        ctk.CTkLabel(prog_frame, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(2, 0))

        # ── Tabs Risultati ───────────────────────────────────────────────
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        tab_tree = self.tabs.add("🌳 Struttura")
        tab_stats = self.tabs.add("📊 Statistiche")
        tab_paths = self.tabs.add("📐 Analisi Path")
        tab_log = self.tabs.add("📋 Log")

        # Tree tab
        self.tree_text = ctk.CTkTextbox(tab_tree, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.tree_text.pack(fill="both", expand=True)

        # Stats tab
        self.stats_text = ctk.CTkTextbox(tab_stats, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.stats_text.pack(fill="both", expand=True)

        # Path analysis tab
        self.path_text = ctk.CTkTextbox(tab_paths, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
        self.path_text.pack(fill="both", expand=True)

        # Log tab
        self.log_text = ctk.CTkTextbox(tab_log, font=ctk.CTkFont(family="Consolas", size=11), wrap="none")
        self.log_text.pack(fill="both", expand=True)

        self._last_report_path = None

    # ─── Azioni ──────────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Seleziona la cartella da analizzare")
        if folder:
            self.path_var.set(folder)

    def _start_scan(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Attenzione", "Inserisci un percorso da analizzare.")
            return

        try:
            limit = int(self.limit_var.get())
            depth = int(self.depth_var.get())
            topn = int(self.topn_var.get())
        except ValueError:
            messagebox.showerror("Errore", "I valori numerici non sono validi.")
            return

        exclude_raw = self.exclude_var.get().strip()
        exclude = [e.strip() for e in exclude_raw.split(",") if e.strip()] if exclude_raw else []

        # Pulisci UI
        for txt in (self.tree_text, self.stats_text, self.path_text, self.log_text):
            txt.configure(state="normal")
            txt.delete("1.0", "end")

        self._log("─" * 60)
        self._log(f"🔍 Avvio scansione: {path}")
        self._log(f"   Soglia path: {limit} | Profondità: {depth} | Esclusi: {exclude}")
        self._log("─" * 60)

        self.scan_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.export_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Scansione in corso...")

        self.analyzer = PathAnalyzer(
            root_path=path,
            max_depth=depth,
            exclude_dirs=exclude,
            show_hidden=self.hidden_var.get(),
            top_n_files=topn,
            path_limit=limit,
            progress_callback=self._on_progress,
        )

        self._scan_thread = threading.Thread(target=self._run_scan, daemon=True)
        self._scan_thread.start()

    def _run_scan(self):
        try:
            result = self.analyzer.scan()
            if result is None:
                self.after(0, self._on_scan_cancelled)
            else:
                self.after(0, self._on_scan_complete)
        except Exception as e:
            self.after(0, lambda: self._on_scan_error(str(e)))

    def _cancel_scan(self):
        if self.analyzer:
            self.analyzer.cancel()
        self.status_var.set("Annullamento in corso...")

    def _on_progress(self, dirs, files):
        self.after(0, lambda: self.status_var.set(f"Scansione... {dirs:,} cartelle, {files:,} file"))

    def _on_scan_cancelled(self):
        self.progress.stop()
        self.progress.set(0)
        self.scan_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.status_var.set("Scansione annullata.")
        self._log("⏹ Scansione annullata dall'utente.")

    def _on_scan_error(self, error):
        self.progress.stop()
        self.progress.set(0)
        self.scan_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.status_var.set(f"Errore: {error}")
        self._log(f"❌ Errore: {error}")
        messagebox.showerror("Errore", error)

    def _on_scan_complete(self):
        self.progress.stop()
        self.progress.set(1)
        self.scan_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.export_btn.configure(state="normal")

        a = self.analyzer
        s = a.stats
        ps = s.path_stats
        elapsed = s.scan_end - s.scan_start

        self.status_var.set(
            f"✅ Completata in {elapsed:.2f}s — "
            f"{s.total_dirs:,} cartelle, {s.total_files:,} file, "
            f"{format_size(s.total_size)}, "
            f"{len(ps.over_limit)} path oltre soglia"
        )

        # ── Popola Tab Struttura ─────────────────────────────────────────
        self.tree_text.configure(state="normal")
        self.tree_text.delete("1.0", "end")
        clean_lines = a.build_clean_tree(a.root_dir)
        self.tree_text.insert("1.0", "\n".join(clean_lines))

        # ── Popola Tab Statistiche ───────────────────────────────────────
        self.stats_text.configure(state="normal")
        self.stats_text.delete("1.0", "end")
        stats_lines = []
        stats_lines.append(f"{'='*60}")
        stats_lines.append(f"  RIEPILOGO SCANSIONE")
        stats_lines.append(f"{'='*60}")
        stats_lines.append(f"  Percorso:          {a.root_path}")
        stats_lines.append(f"  Tempo:             {elapsed:.2f}s")
        stats_lines.append(f"  Cartelle:          {s.total_dirs:,}")
        stats_lines.append(f"  File:              {s.total_files:,}")
        stats_lines.append(f"  Dimensione:        {format_size(s.total_size)}")
        stats_lines.append(f"  Profondità:        {s.max_depth} livelli")
        stats_lines.append(f"  Estensioni uniche: {len(s.extensions)}")
        stats_lines.append("")
        stats_lines.append(f"{'─'*60}")
        stats_lines.append(f"  DISTRIBUZIONE ESTENSIONI (Top 20)")
        stats_lines.append(f"{'─'*60}")
        sorted_exts = sorted(s.extensions.items(), key=lambda x: x[1], reverse=True)
        for ext, count in sorted_exts[:20]:
            size = s.ext_sizes.get(ext, 0)
            pct = (count / s.total_files * 100) if s.total_files > 0 else 0
            bar = "█" * max(1, int(pct / 2))
            stats_lines.append(f"  {ext:<12} {count:>6,}  {format_size(size):>10}  {bar} {pct:.1f}%")
        stats_lines.append("")
        stats_lines.append(f"{'─'*60}")
        stats_lines.append(f"  FILE PIÙ GRANDI (Top {len(s.largest_files)})")
        stats_lines.append(f"{'─'*60}")
        for i, f in enumerate(s.largest_files, 1):
            stats_lines.append(f"  {i:>2}. {format_size(f.size):>10}  {f.name}")
        if s.errors:
            stats_lines.append("")
            stats_lines.append(f"{'─'*60}")
            stats_lines.append(f"  ERRORI ({len(s.errors)})")
            stats_lines.append(f"{'─'*60}")
            for err in s.errors[:15]:
                stats_lines.append(f"  • {err}")

        self.stats_text.insert("1.0", "\n".join(stats_lines))

        # ── Popola Tab Analisi Path ──────────────────────────────────────
        self.path_text.configure(state="normal")
        self.path_text.delete("1.0", "end")
        path_lines = []
        path_lines.append(f"{'='*60}")
        path_lines.append(f"  ANALISI LUNGHEZZA PERCORSI")
        path_lines.append(f"  Soglia: {a.path_limit} caratteri")
        path_lines.append(f"{'='*60}")
        path_lines.append(f"  Percorsi analizzati:  {len(ps.all_paths):,}")
        path_lines.append(f"  Lunghezza media:      {ps.avg_length:.1f} chars")
        path_lines.append(f"  Lunghezza mediana:    {ps.median_length} chars")
        if ps.longest_file_path:
            path_lines.append(f"  File più lungo:       {ps.longest_file_length} chars")
        if ps.longest_dir_path:
            path_lines.append(f"  Cartella più lunga:   {ps.longest_dir_length} chars")
        path_lines.append(f"  Oltre soglia:         {len(ps.over_limit)}")
        path_lines.append("")

        path_lines.append(f"{'─'*60}")
        path_lines.append(f"  DISTRIBUZIONE")
        path_lines.append(f"{'─'*60}")
        range_order = ["0-50", "51-100", "101-150", "151-200", "201-260", "261-300", "300+"]
        tp = len(ps.all_paths) or 1
        for r in range_order:
            count = ps.distribution.get(r, 0)
            pct = count / tp * 100
            bar = "█" * max(0, int(pct / 2))
            warn = " ⚠️" if r in ("261-300", "300+") and count > 0 else ""
            path_lines.append(f"  {r:>8}  {count:>6,}  ({pct:5.1f}%)  {bar}{warn}")
        path_lines.append("")

        if ps.over_limit:
            path_lines.append(f"{'─'*60}")
            path_lines.append(f"  ⚠️  PERCORSI OLTRE SOGLIA ({len(ps.over_limit)})")
            path_lines.append(f"{'─'*60}")
            for i, (path, length, ptype) in enumerate(ps.over_limit, 1):
                tipo = "DIR " if ptype == "DIR" else "FILE"
                path_lines.append(f"  {i:>3}. [{tipo}] {length} chars (+{length - a.path_limit})")
                path_lines.append(f"       {path}")
        else:
            path_lines.append(f"  ✅ Tutti i percorsi sono entro la soglia di {a.path_limit} caratteri.")

        path_lines.append("")
        if ps.longest_file_path:
            path_lines.append(f"{'─'*60}")
            path_lines.append(f"  FILE CON PATH PIÙ LUNGO ({ps.longest_file_length} chars):")
            path_lines.append(f"  {ps.longest_file_path}")
        if ps.longest_dir_path:
            path_lines.append("")
            path_lines.append(f"  CARTELLA CON PATH PIÙ LUNGO ({ps.longest_dir_length} chars):")
            path_lines.append(f"  {ps.longest_dir_path}")

        self.path_text.insert("1.0", "\n".join(path_lines))

        self._log(f"✅ Scansione completata in {elapsed:.2f}s")
        self._log(f"   {s.total_dirs:,} cartelle | {s.total_files:,} file | {format_size(s.total_size)}")
        self._log(f"   Path oltre soglia: {len(ps.over_limit)}")

    def _export_report(self):
        if not self.analyzer or not self.analyzer.root_dir:
            return

        path = filedialog.asksaveasfilename(
            title="Salva Report",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Tutti i file", "*.*")],
            initialfile=f"path_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        if not path:
            return

        try:
            self.analyzer.generate_report(path)
            self._last_report_path = path
            self.open_btn.configure(state="normal")
            self._log(f"💾 Report salvato: {path}")
            self.status_var.set(f"Report salvato: {path}")
            messagebox.showinfo("Successo", f"Report salvato in:\n{path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il report:\n{e}")

    def _open_report(self):
        if self._last_report_path and os.path.exists(self._last_report_path):
            webbrowser.open(self._last_report_path)

    def _log(self, text):
        self.log_text.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {text}\n")
        self.log_text.see("end")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = PathAnalyzerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
