#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path Analyzer Editor v4.0
Analizzatore + Editor massivo di path con wizard, preview, e rollback.
Bottom-up execution per evitare cascading path invalidation.
"""

import os
import sys
import re
import json
import threading
import datetime
import time
import shutil
import webbrowser
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Callable
from enum import Enum

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PIPE = "│   "; TEE = "├── "; ELBOW = "└── "; SPACE = "    "

FILE_ICONS = {
    ".pdf":"📄",".doc":"📝",".docx":"📝",".xls":"📊",".xlsx":"📊",".csv":"📊",
    ".ppt":"📽️",".pptx":"📽️",".txt":"📃",".md":"📑",".log":"📃",
    ".jpg":"🖼️",".jpeg":"🖼️",".png":"🖼️",".gif":"🖼️",".bmp":"🖼️",".svg":"🖼️",
    ".mp4":"🎬",".avi":"🎬",".mkv":"🎬",".mp3":"🎵",".wav":"🎵",
    ".py":"🐍",".js":"⚡",".ts":"⚡",".jsx":"⚡",".tsx":"⚡",
    ".html":"🌐",".css":"🎨",".java":"☕",".cs":"🔷",".cpp":"⚙️",".c":"⚙️",
    ".rs":"🦀",".go":"🐹",".rb":"💎",".php":"🐘",
    ".sql":"🗃️",".json":"📋",".xml":"📋",".yaml":"📋",".yml":"📋",
    ".sh":"🐚",".bat":"🐚",".ps1":"🐚",
    ".zip":"📦",".rar":"📦",".7z":"📦",
    ".exe":"⚙️",".dll":"🔧",".db":"🗄️",".sqlite":"🗄️",
    ".ttf":"🔤",".otf":"🔤",".ini":"⚙️",".cfg":"⚙️",".env":"⚙️",
    ".bak":"💾",".iso":"💿",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    name: str; path: str; extension: str; size: int; modified: float
    path_length: int = 0; is_hidden: bool = False

@dataclass
class DirInfo:
    name: str; path: str
    files: list = field(default_factory=list)
    subdirs: list = field(default_factory=list)
    total_files: int = 0; total_size: int = 0; depth: int = 0
    path_length: int = 0; error: Optional[str] = None

@dataclass
class PathLengthStats:
    all_paths: list = field(default_factory=list)
    over_limit: list = field(default_factory=list)
    longest_file_path: str = ""; longest_file_length: int = 0
    longest_dir_path: str = ""; longest_dir_length: int = 0
    avg_length: float = 0; median_length: int = 0
    distribution: dict = field(default_factory=lambda: defaultdict(int))

@dataclass
class ScanStats:
    total_dirs: int = 0; total_files: int = 0; total_size: int = 0
    max_depth: int = 0
    extensions: dict = field(default_factory=lambda: defaultdict(int))
    ext_sizes: dict = field(default_factory=lambda: defaultdict(int))
    largest_files: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    path_stats: PathLengthStats = field(default_factory=PathLengthStats)
    scan_start: float = 0; scan_end: float = 0


class RuleType(Enum):
    FIND_REPLACE = "Trova e Sostituisci"
    TRUNCATE = "Tronca a N caratteri"
    REMOVE_CHARS = "Rimuovi caratteri"
    REMOVE_PREFIX = "Rimuovi prefisso"
    REMOVE_SUFFIX = "Rimuovi suffisso"
    COMPRESS_SEPARATORS = "Comprimi separatori"
    REGEX_REPLACE = "Regex"
    SMART_ABBREVIATE = "Abbreviazione smart"


@dataclass
class RenameRule:
    """Una singola regola di rinomina configurata dall'utente."""
    rule_type: RuleType
    params: dict = field(default_factory=dict)
    apply_to_files: bool = True
    apply_to_dirs: bool = True
    enabled: bool = True

    def describe(self) -> str:
        t = self.rule_type.value
        p = self.params
        if self.rule_type == RuleType.FIND_REPLACE:
            return f'{t}: "{p.get("find","")}" -> "{p.get("replace","")}"'
        elif self.rule_type == RuleType.TRUNCATE:
            return f'{t}: max {p.get("max_chars",50)} caratteri'
        elif self.rule_type == RuleType.REMOVE_CHARS:
            return f'{t}: "{p.get("chars","")}"'
        elif self.rule_type == RuleType.REMOVE_PREFIX:
            return f'{t}: "{p.get("prefix","")}"'
        elif self.rule_type == RuleType.REMOVE_SUFFIX:
            return f'{t}: "{p.get("suffix","")}"'
        elif self.rule_type == RuleType.COMPRESS_SEPARATORS:
            return f'{t}: comprimi ripetizioni di "{p.get("char","_")}"'
        elif self.rule_type == RuleType.REGEX_REPLACE:
            return f'{t}: /{p.get("pattern","")}/ -> "{p.get("replace","")}"'
        elif self.rule_type == RuleType.SMART_ABBREVIATE:
            return f'{t}: abbreviazioni comuni'
        return t


@dataclass
class RenameOperation:
    """Una singola operazione di rinomina pianificata."""
    old_path: str
    new_path: str
    old_name: str
    new_name: str
    depth: int
    is_dir: bool
    old_length: int = 0
    new_length: int = 0
    savings: int = 0
    status: str = "pending"  # pending, done, error, skipped
    error_msg: str = ""

    def __post_init__(self):
        self.old_length = len(self.old_path)
        self.new_length = len(self.new_path)
        self.savings = self.old_length - self.new_length


@dataclass
class RenamePlan:
    """Piano completo di rinomina con tutte le operazioni ordinate."""
    operations: List[RenameOperation] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_savings: int = 0
    paths_fixed: int = 0
    is_valid: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def format_size(b):
    if b < 0: return "N/A"
    for u in ['B','KB','MB','GB','TB']:
        if b < 1024: return f"{b} {u}" if u == 'B' else f"{b:.2f} {u}"
        b /= 1024
    return f"{b:.2f} PB"

def format_date(ts):
    try: return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except: return "N/A"

def is_hidden(fp):
    if os.path.basename(fp).startswith('.'): return True
    try:
        import ctypes
        a = ctypes.windll.kernel32.GetFileAttributesW(str(fp))
        if a != -1: return bool(a & 0x2)
    except: pass
    return False

def get_icon(ext): return FILE_ICONS.get(ext.lower(), "📄")

def safe_stat(p):
    try: return os.stat(p)
    except: return None

def get_range(l):
    if l<=50: return "0-50"
    elif l<=100: return "51-100"
    elif l<=150: return "101-150"
    elif l<=200: return "151-200"
    elif l<=260: return "201-260"
    elif l<=300: return "261-300"
    else: return "300+"


# ═══════════════════════════════════════════════════════════════════════════════
# SMART ABBREVIATIONS
# ═══════════════════════════════════════════════════════════════════════════════

SMART_ABBREV = {
    "documents": "docs", "document": "doc", "documentation": "docs",
    "configuration": "cfg", "config": "cfg", "configure": "cfg",
    "application": "app", "applications": "apps",
    "development": "dev", "developer": "dev",
    "production": "prod", "environment": "env",
    "temporary": "tmp", "temp": "tmp",
    "library": "lib", "libraries": "libs",
    "resource": "res", "resources": "res",
    "information": "info", "images": "img", "image": "img",
    "source": "src", "sources": "src",
    "package": "pkg", "packages": "pkgs",
    "component": "cmp", "components": "cmps",
    "database": "db", "backup": "bak", "backups": "bak",
    "directory": "dir", "directories": "dirs",
    "template": "tpl", "templates": "tpls",
    "utilities": "util", "utility": "util",
    "download": "dl", "downloads": "dl",
    "attachment": "att", "attachments": "att",
    "administration": "admin", "administrator": "admin",
    "management": "mgmt", "manager": "mgr",
    "project": "prj", "projects": "prjs",
    "specification": "spec", "specifications": "specs",
    "presentation": "pres", "presentations": "pres",
    "reference": "ref", "references": "refs",
    "description": "desc", "version": "ver",
    "original": "orig", "screenshot": "scrn", "screenshots": "scrn",
    "communication": "comm", "communications": "comms",
    "repository": "repo", "repositories": "repos",
    "attachment": "att", "implementation": "impl",
    "maintenance": "maint", "certificate": "cert", "certificates": "certs",
    "documento": "doc", "documenti": "docs", "documentazione": "docs",
    "configurazione": "cfg", "applicazione": "app", "applicazioni": "apps",
    "sviluppo": "dev", "produzione": "prod", "ambiente": "env",
    "temporaneo": "tmp", "libreria": "lib", "librerie": "libs",
    "risorsa": "res", "risorse": "res", "informazioni": "info",
    "immagine": "img", "immagini": "img", "sorgente": "src",
    "componente": "cmp", "componenti": "cmps",
    "progetto": "prj", "progetti": "prjs",
    "presentazione": "pres", "presentazioni": "pres",
    "amministrazione": "admin", "gestione": "mgmt",
    "archivio": "arch", "comunicazione": "comm", "comunicazioni": "comms",
    "manutenzione": "maint", "certificato": "cert", "certificati": "certs",
}


# ═══════════════════════════════════════════════════════════════════════════════
# RULE PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class RuleProcessor:
    """Applica le regole di rinomina a un nome di file/cartella."""

    @staticmethod
    def apply_rules(name: str, rules: List[RenameRule], is_dir: bool) -> str:
        for rule in rules:
            if not rule.enabled:
                continue
            if is_dir and not rule.apply_to_dirs:
                continue
            if not is_dir and not rule.apply_to_files:
                continue

            # Per i file, separa nome ed estensione
            if not is_dir:
                base, ext = os.path.splitext(name)
            else:
                base, ext = name, ""

            base = RuleProcessor._apply_single(base, rule)

            # Sicurezza: non permettere nomi vuoti
            if not base.strip():
                base = "_renamed"

            name = base + ext

        return name

    @staticmethod
    def _apply_single(base: str, rule: RenameRule) -> str:
        p = rule.params
        rt = rule.rule_type

        if rt == RuleType.FIND_REPLACE:
            find = p.get("find", "")
            repl = p.get("replace", "")
            case_sensitive = p.get("case_sensitive", False)
            if find:
                if case_sensitive:
                    base = base.replace(find, repl)
                else:
                    base = re.sub(re.escape(find), repl, base, flags=re.IGNORECASE)

        elif rt == RuleType.TRUNCATE:
            max_c = p.get("max_chars", 50)
            if len(base) > max_c:
                base = base[:max_c]

        elif rt == RuleType.REMOVE_CHARS:
            chars = p.get("chars", "")
            for c in chars:
                base = base.replace(c, "")

        elif rt == RuleType.REMOVE_PREFIX:
            prefix = p.get("prefix", "")
            if prefix and base.startswith(prefix):
                base = base[len(prefix):]

        elif rt == RuleType.REMOVE_SUFFIX:
            suffix = p.get("suffix", "")
            if suffix and base.endswith(suffix):
                base = base[:-len(suffix)]

        elif rt == RuleType.COMPRESS_SEPARATORS:
            char = p.get("char", "_")
            if char:
                pattern = re.escape(char) + "{2,}"
                base = re.sub(pattern, char, base)
                base = base.strip(char)

        elif rt == RuleType.REGEX_REPLACE:
            pattern = p.get("pattern", "")
            repl = p.get("replace", "")
            if pattern:
                try:
                    base = re.sub(pattern, repl, base)
                except re.error:
                    pass  # Regex invalida, skip

        elif rt == RuleType.SMART_ABBREVIATE:
            words = re.split(r'([_\-\s.]+)', base)
            result = []
            for w in words:
                low = w.lower()
                if low in SMART_ABBREV:
                    abbr = SMART_ABBREV[low]
                    # Mantieni il case originale se era capitalizzato
                    if w[0].isupper() and len(w) > 0:
                        abbr = abbr.capitalize()
                    result.append(abbr)
                else:
                    result.append(w)
            base = "".join(result)

        return base


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNER ENGINE (from v3, compacted)
# ═══════════════════════════════════════════════════════════════════════════════

class PathAnalyzer:

    def __init__(self, root_path, max_depth=-1, exclude_dirs=None,
                 show_hidden=True, top_n_files=15, path_limit=260,
                 progress_cb=None):
        self.root_path = os.path.abspath(root_path)
        self.max_depth = max_depth
        self.exclude_dirs = set(exclude_dirs or [])
        self.show_hidden = show_hidden
        self.top_n_files = top_n_files
        self.path_limit = path_limit
        self.progress_cb = progress_cb
        self.stats = ScanStats()
        self.root_dir = None
        self._cancel = False

    def cancel(self): self._cancel = True

    def scan(self):
        self.stats.scan_start = time.time()
        self._cancel = False
        if not os.path.exists(self.root_path):
            raise FileNotFoundError(f"Percorso non trovato: {self.root_path}")
        if not os.path.isdir(self.root_path):
            raise NotADirectoryError(f"Non e' una directory: {self.root_path}")
        self.root_dir = self._scan_dir(self.root_path, 0)
        if self._cancel: return None
        self.stats.scan_end = time.time()
        self.stats.largest_files.sort(key=lambda x: x.size, reverse=True)
        self.stats.largest_files = self.stats.largest_files[:self.top_n_files]
        self._compute_path_stats()
        return self.root_dir

    def _scan_dir(self, dir_path, depth):
        if self._cancel: return DirInfo(name="", path="")
        dn = os.path.basename(dir_path) or dir_path
        pl = len(dir_path)
        di = DirInfo(name=dn, path=dir_path, depth=depth, path_length=pl)
        self.stats.total_dirs += 1
        self.stats.max_depth = max(self.stats.max_depth, depth)
        self.stats.path_stats.all_paths.append((dir_path, pl, "DIR"))
        if pl > self.path_limit:
            self.stats.path_stats.over_limit.append((dir_path, pl, "DIR"))
        if self.progress_cb and self.stats.total_dirs % 50 == 0:
            self.progress_cb(self.stats.total_dirs, self.stats.total_files)
        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            di.error = "Accesso negato"; self.stats.errors.append(f"Accesso negato: {dir_path}"); return di
        except OSError as e:
            di.error = str(e); self.stats.errors.append(f"Errore: {dir_path}: {e}"); return di
        for entry in entries:
            if self._cancel: break
            try:
                if not self.show_hidden and is_hidden(entry.path): continue
                if entry.name in self.exclude_dirs: continue
                if entry.is_dir(follow_symlinks=False):
                    if self.max_depth >= 0 and depth >= self.max_depth: continue
                    sub = self._scan_dir(entry.path, depth + 1)
                    di.subdirs.append(sub); di.total_files += sub.total_files; di.total_size += sub.total_size
                elif entry.is_file(follow_symlinks=False):
                    st = safe_stat(entry.path); sz = st.st_size if st else 0; mt = st.st_mtime if st else 0
                    ext = os.path.splitext(entry.name)[1].lower(); fpl = len(entry.path)
                    fi = FileInfo(name=entry.name, path=entry.path, extension=ext, size=sz,
                                  modified=mt, path_length=fpl, is_hidden=is_hidden(entry.path))
                    di.files.append(fi); di.total_files += 1; di.total_size += sz
                    self.stats.total_files += 1; self.stats.total_size += sz
                    self.stats.extensions[ext or "(nessuna)"] += 1; self.stats.ext_sizes[ext or "(nessuna)"] += sz
                    self.stats.path_stats.all_paths.append((entry.path, fpl, "FILE"))
                    if fpl > self.path_limit: self.stats.path_stats.over_limit.append((entry.path, fpl, "FILE"))
                    self.stats.largest_files.append(fi)
                    if len(self.stats.largest_files) > self.top_n_files * 3:
                        self.stats.largest_files.sort(key=lambda x: x.size, reverse=True)
                        self.stats.largest_files = self.stats.largest_files[:self.top_n_files]
            except: continue
        return di

    def _compute_path_stats(self):
        ps = self.stats.path_stats
        if not ps.all_paths: return
        lengths = sorted([p[1] for p in ps.all_paths])
        ps.avg_length = sum(lengths) / len(lengths)
        ps.median_length = lengths[len(lengths) // 2]
        for _, l, _ in ps.all_paths: ps.distribution[get_range(l)] += 1
        fps = [(p,l) for p,l,t in ps.all_paths if t == "FILE"]
        dps = [(p,l) for p,l,t in ps.all_paths if t == "DIR"]
        if fps: lf = max(fps, key=lambda x:x[1]); ps.longest_file_path,ps.longest_file_length = lf
        if dps: ld = max(dps, key=lambda x:x[1]); ps.longest_dir_path,ps.longest_dir_length = ld
        ps.over_limit.sort(key=lambda x: x[1], reverse=True)

    def build_clean_tree(self, di, prefix="", is_last=True, is_root=True):
        lines = []
        if is_root: lines.append(di.name); cp = ""
        else:
            lines.append(f"{prefix}{ELBOW if is_last else TEE}{di.name}")
            cp = prefix + (SPACE if is_last else PIPE)
        items = [(True,s) for s in di.subdirs] + [(False,f) for f in di.files]
        for i,(d,it) in enumerate(items):
            last = i == len(items) - 1
            if d: lines.extend(self.build_clean_tree(it, cp, last, False))
            else: lines.append(f"{cp}{ELBOW if last else TEE}{it.name}")
        return lines


# ═══════════════════════════════════════════════════════════════════════════════
# RENAME ENGINE — Il cuore del sistema
# ═══════════════════════════════════════════════════════════════════════════════

class RenameEngine:
    """
    Motore di rinomina con esecuzione bottom-up.

    STRATEGIA CHIAVE:
    1. Raccoglie tutti i path problematici
    2. Applica le regole IN MEMORIA per calcolare i nuovi nomi
    3. Ordina le operazioni per profondita DECRESCENTE (bottom-up)
    4. Esegue le rinominazioni dal piu profondo al meno profondo
    5. In questo modo, quando rinomini una cartella, tutti i suoi figli
       sono gia stati rinominati e il vecchio path e' ancora valido
    """

    def __init__(self, root_path: str, path_limit: int = 260):
        self.root_path = root_path
        self.path_limit = path_limit
        self.plan = RenamePlan()
        self.executed_ops: List[RenameOperation] = []  # Per rollback

    def create_plan(self, rules: List[RenameRule],
                    only_over_limit: bool = True,
                    progress_cb: Callable = None) -> RenamePlan:
        """
        Crea il piano di rinomina senza toccare il filesystem.
        Scansiona il tree e applica le regole in memoria.
        """
        self.plan = RenamePlan()
        ops = []

        # Raccoglie tutti gli elementi con os.walk bottom-up
        # Bottom-up garantisce che le cartelle figlio vengano PRIMA dei genitori
        all_entries = []

        for dirpath, dirnames, filenames in os.walk(self.root_path, topdown=False):
            depth = dirpath.replace(self.root_path, "").count(os.sep)

            # File in questa directory
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if only_over_limit and len(full_path) <= self.path_limit:
                    continue
                all_entries.append((full_path, fname, depth, False))

            # La directory stessa (solo se non e' la root)
            if os.path.abspath(dirpath) != os.path.abspath(self.root_path):
                dname = os.path.basename(dirpath)
                if only_over_limit and len(dirpath) <= self.path_limit:
                    continue
                all_entries.append((dirpath, dname, depth, True))

        if progress_cb:
            progress_cb(0, len(all_entries))

        # Per ogni entry, calcola il nuovo nome applicando le regole
        # IMPORTANTE: calcoliamo i nuovi path tenendo conto delle rinominazioni
        # gia pianificate per le cartelle padre. Usiamo una mappa di sostituzione.
        dir_renames = {}  # old_dir_path -> new_dir_name

        for idx, (full_path, name, depth, is_dir) in enumerate(all_entries):
            if progress_cb and idx % 100 == 0:
                progress_cb(idx, len(all_entries))

            new_name = RuleProcessor.apply_rules(name, rules, is_dir)

            if new_name == name:
                continue  # Nessun cambiamento

            # Calcola il nuovo path completo
            parent = os.path.dirname(full_path)
            new_path = os.path.join(parent, new_name)

            # Controlla conflitti
            if os.path.exists(new_path) and new_path.lower() != full_path.lower():
                self.plan.conflicts.append(
                    f"Conflitto: '{new_name}' esiste gia in {parent}"
                )
                continue

            op = RenameOperation(
                old_path=full_path, new_path=new_path,
                old_name=name, new_name=new_name,
                depth=depth, is_dir=is_dir
            )
            ops.append(op)

            if is_dir:
                dir_renames[full_path] = new_name

        # Ordina per profondita DECRESCENTE (bottom-up)
        # A parita di profondita, i file prima delle cartelle
        ops.sort(key=lambda o: (-o.depth, not o.is_dir))

        self.plan.operations = ops
        self.plan.total_savings = sum(o.savings for o in ops)
        self.plan.paths_fixed = len(ops)
        self.plan.is_valid = len(self.plan.conflicts) == 0

        # Warnings
        if not ops:
            self.plan.warnings.append("Nessuna modifica necessaria con le regole attuali.")

        # Verifica duplicati nello stesso folder
        by_folder = defaultdict(list)
        for op in ops:
            parent = os.path.dirname(op.old_path)
            by_folder[parent].append(op.new_name.lower())
        for folder, names in by_folder.items():
            dupes = [n for n in names if names.count(n) > 1]
            if dupes:
                self.plan.is_valid = False
                self.plan.conflicts.append(
                    f"Nomi duplicati in {folder}: {set(dupes)}"
                )

        return self.plan

    def execute(self, on_error: str = "skip",
                progress_cb: Callable = None) -> Tuple[int, int, List[str]]:
        """
        Esegue il piano di rinomina.
        Le operazioni sono GIA ordinate bottom-up dal create_plan().

        on_error: "skip" = continua, "stop" = ferma tutto

        Returns: (successi, errori, lista_errori)
        """
        self.executed_ops = []
        success = 0
        errors = 0
        error_list = []
        total = len(self.plan.operations)

        for idx, op in enumerate(self.plan.operations):
            if progress_cb and idx % 10 == 0:
                progress_cb(idx, total, success, errors)

            try:
                # Verifica che il path sorgente esista ancora
                if not os.path.exists(op.old_path):
                    # Il path potrebbe essere cambiato da un'operazione precedente
                    # su una cartella genitore. Ma con bottom-up non dovrebbe succedere.
                    op.status = "skipped"
                    op.error_msg = "Path non trovato (possibile rinomina genitore)"
                    error_list.append(f"SKIP: {op.old_path} non trovato")
                    errors += 1
                    if on_error == "stop":
                        break
                    continue

                # Verifica che il target non esista
                if os.path.exists(op.new_path) and op.new_path.lower() != op.old_path.lower():
                    op.status = "skipped"
                    op.error_msg = "Destinazione gia esistente"
                    error_list.append(f"SKIP: {op.new_path} esiste gia")
                    errors += 1
                    if on_error == "stop":
                        break
                    continue

                # Esegui la rinomina
                os.rename(op.old_path, op.new_path)
                op.status = "done"
                self.executed_ops.append(op)
                success += 1

            except PermissionError:
                op.status = "error"
                op.error_msg = "Permesso negato"
                error_list.append(f"ERRORE permesso: {op.old_path}")
                errors += 1
                if on_error == "stop": break

            except OSError as e:
                op.status = "error"
                op.error_msg = str(e)
                error_list.append(f"ERRORE: {op.old_path}: {e}")
                errors += 1
                if on_error == "stop": break

        if progress_cb:
            progress_cb(total, total, success, errors)

        return success, errors, error_list

    def rollback(self, progress_cb: Callable = None) -> Tuple[int, int]:
        """
        Annulla le operazioni eseguite in ordine INVERSO (top-down).
        Questo e' l'opposto dell'esecuzione: prima le cartelle piu alte,
        poi quelle piu profonde, poi i file.
        """
        # Inverti l'ordine: le ultime eseguite (le piu alte) vanno rollbackate per prime
        to_undo = list(reversed(self.executed_ops))
        success = 0
        errors = 0
        total = len(to_undo)

        for idx, op in enumerate(to_undo):
            if progress_cb and idx % 10 == 0:
                progress_cb(idx, total)

            try:
                if os.path.exists(op.new_path):
                    os.rename(op.new_path, op.old_path)
                    success += 1
            except:
                errors += 1

        self.executed_ops.clear()
        return success, errors

    def save_undo_log(self, path: str):
        """Salva il log delle operazioni per undo futuro."""
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "root_path": self.root_path,
            "operations": [
                {"old": op.old_path, "new": op.new_path, "is_dir": op.is_dir,
                 "depth": op.depth, "status": op.status}
                for op in self.executed_ops
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# GUI — MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class PathAnalyzerApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Path Analyzer Editor v4.0")
        self.geometry("1100x780")
        self.minsize(900, 650)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.analyzer = None
        self.rename_engine = None
        self._scan_thread = None
        self._last_report = None

        self._build_ui()

    def _build_ui(self):
        # ── TOP BAR ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkLabel(top, text="Path Analyzer Editor", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkLabel(top, text="v4.0", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=6, pady=(4,0))

        # ── PATH INPUT ──
        pf = ctk.CTkFrame(self, fg_color="transparent")
        pf.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(pf, text="Percorso:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.path_var = ctk.StringVar()
        self.path_entry = ctk.CTkEntry(pf, textvariable=self.path_var, placeholder_text=r"C:\... o \\server\share\...", height=34)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(8,4))
        ctk.CTkButton(pf, text="Sfoglia", width=80, height=34, command=self._browse).pack(side="left")

        # ── OPTIONS ROW ──
        of = ctk.CTkFrame(self)
        of.pack(fill="x", padx=16, pady=4)
        r1 = ctk.CTkFrame(of, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8,4))

        ctk.CTkLabel(r1, text="Soglia Path:").pack(side="left")
        self.limit_var = ctk.StringVar(value="260")
        ctk.CTkEntry(r1, textvariable=self.limit_var, width=70, height=28).pack(side="left", padx=(4,12))

        ctk.CTkLabel(r1, text="Profondita:").pack(side="left")
        self.depth_var = ctk.StringVar(value="-1")
        ctk.CTkEntry(r1, textvariable=self.depth_var, width=50, height=28).pack(side="left", padx=(4,12))

        self.hidden_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(r1, text="File nascosti", variable=self.hidden_var).pack(side="left", padx=(0,12))

        ctk.CTkLabel(r1, text="Escludi:").pack(side="left")
        self.exclude_var = ctk.StringVar(value=".git, node_modules, __pycache__, .vs")
        ctk.CTkEntry(r1, textvariable=self.exclude_var, height=28).pack(side="left", fill="x", expand=True, padx=(4,0))

        # ── ACTION BUTTONS ──
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=4)

        self.scan_btn = ctk.CTkButton(bf, text="Scansione", height=36, font=ctk.CTkFont(weight="bold"), command=self._start_scan)
        self.scan_btn.pack(side="left", padx=(0,6))

        self.cancel_btn = ctk.CTkButton(bf, text="Annulla", height=36, fg_color="#c0392b", hover_color="#e74c3c", state="disabled", command=self._cancel_scan)
        self.cancel_btn.pack(side="left", padx=(0,6))

        self.edit_btn = ctk.CTkButton(bf, text="Editor Rinomina", height=36, fg_color="#e67e22", hover_color="#f39c12", state="disabled", command=self._open_wizard)
        self.edit_btn.pack(side="left", padx=(0,6))

        self.export_btn = ctk.CTkButton(bf, text="Esporta .md", height=36, fg_color="#27ae60", hover_color="#2ecc71", state="disabled", command=self._export)
        self.export_btn.pack(side="left")

        # ── PROGRESS ──
        pgf = ctk.CTkFrame(self, fg_color="transparent")
        pgf.pack(fill="x", padx=16, pady=(4,0))
        self.progress = ctk.CTkProgressBar(pgf, mode="indeterminate")
        self.progress.pack(fill="x"); self.progress.set(0)
        self.status_var = ctk.StringVar(value="Pronto. Seleziona un percorso e avvia la scansione.")
        ctk.CTkLabel(pgf, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(2,0))

        # ── TABS ──
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(6,12))

        for name in ["Struttura", "Statistiche", "Analisi Path", "Log"]:
            tab = self.tabs.add(name)
            txt = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=12), wrap="none")
            txt.pack(fill="both", expand=True)
            setattr(self, f"txt_{name.lower().replace(' ','_')}", txt)

    # ─── ACTIONS ─────────────────────────────────────────────────────────

    def _browse(self):
        f = filedialog.askdirectory(title="Seleziona cartella")
        if f: self.path_var.set(f)

    def _start_scan(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Attenzione", "Inserisci un percorso.")
            return
        try:
            limit = int(self.limit_var.get()); depth = int(self.depth_var.get())
        except ValueError:
            messagebox.showerror("Errore", "Valori numerici non validi."); return

        excl = [e.strip() for e in self.exclude_var.get().split(",") if e.strip()]

        for t in [self.txt_struttura, self.txt_statistiche, self.txt_analisi_path, self.txt_log]:
            t.configure(state="normal"); t.delete("1.0","end")

        self._log("Avvio scansione: " + path)
        self.scan_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.edit_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Scansione in corso...")

        self.analyzer = PathAnalyzer(root_path=path, max_depth=depth, exclude_dirs=excl,
                                     show_hidden=self.hidden_var.get(), path_limit=limit,
                                     progress_cb=self._on_progress)
        self._scan_thread = threading.Thread(target=self._run_scan, daemon=True)
        self._scan_thread.start()

    def _run_scan(self):
        try:
            r = self.analyzer.scan()
            if r is None: self.after(0, self._on_cancelled)
            else: self.after(0, self._on_complete)
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _cancel_scan(self):
        if self.analyzer: self.analyzer.cancel()

    def _on_progress(self, d, f):
        self.after(0, lambda: self.status_var.set(f"Scansione... {d:,} cartelle, {f:,} file"))

    def _on_cancelled(self):
        self.progress.stop(); self.progress.set(0)
        self.scan_btn.configure(state="normal"); self.cancel_btn.configure(state="disabled")
        self.status_var.set("Annullata."); self._log("Scansione annullata.")

    def _on_error(self, e):
        self.progress.stop(); self.progress.set(0)
        self.scan_btn.configure(state="normal"); self.cancel_btn.configure(state="disabled")
        self.status_var.set(f"Errore: {e}"); messagebox.showerror("Errore", e)

    def _on_complete(self):
        self.progress.stop(); self.progress.set(1)
        self.scan_btn.configure(state="normal"); self.cancel_btn.configure(state="disabled")
        self.export_btn.configure(state="normal")

        a = self.analyzer; s = a.stats; ps = s.path_stats
        el = s.scan_end - s.scan_start

        # Abilita editor solo se ci sono path oltre soglia
        if ps.over_limit:
            self.edit_btn.configure(state="normal")

        self.status_var.set(
            f"Completata in {el:.2f}s - {s.total_dirs:,} dir, {s.total_files:,} file, "
            f"{format_size(s.total_size)}, {len(ps.over_limit)} path oltre soglia")

        # Popola tab Struttura
        self.txt_struttura.delete("1.0","end")
        self.txt_struttura.insert("1.0", "\n".join(a.build_clean_tree(a.root_dir)))

        # Popola tab Statistiche
        self.txt_statistiche.delete("1.0","end")
        lines = [
            f"{'='*60}", "  RIEPILOGO", f"{'='*60}",
            f"  Percorso:     {a.root_path}",
            f"  Tempo:        {el:.2f}s",
            f"  Cartelle:     {s.total_dirs:,}",
            f"  File:         {s.total_files:,}",
            f"  Dimensione:   {format_size(s.total_size)}",
            f"  Profondita:   {s.max_depth}", "",
            f"{'='*60}", "  ESTENSIONI (Top 20)", f"{'='*60}",
        ]
        for ext,cnt in sorted(s.extensions.items(), key=lambda x:x[1], reverse=True)[:20]:
            sz = s.ext_sizes.get(ext,0)
            pct = cnt/s.total_files*100 if s.total_files else 0
            lines.append(f"  {ext:<12} {cnt:>6,}  {format_size(sz):>10}  {'#'*max(1,int(pct/2))} {pct:.1f}%")
        self.txt_statistiche.insert("1.0", "\n".join(lines))

        # Popola tab Analisi Path
        self.txt_analisi_path.delete("1.0","end")
        pl = [
            f"{'='*60}", f"  ANALISI PATH (soglia: {a.path_limit})", f"{'='*60}",
            f"  Percorsi:   {len(ps.all_paths):,}",
            f"  Media:      {ps.avg_length:.0f} chars",
            f"  Mediana:    {ps.median_length} chars",
            f"  Max file:   {ps.longest_file_length} chars",
            f"  Max dir:    {ps.longest_dir_length} chars",
            f"  Oltre:      {len(ps.over_limit)}", "",
        ]
        if ps.over_limit:
            pl.append(f"{'='*60}")
            pl.append(f"  PERCORSI OLTRE SOGLIA ({len(ps.over_limit)})")
            pl.append(f"{'='*60}")
            for i,(p,l,t) in enumerate(ps.over_limit, 1):
                pl.append(f"  {i:>4}. [{t:>4}] {l} chars (+{l-a.path_limit})")
                pl.append(f"        {p}")
        self.txt_analisi_path.insert("1.0", "\n".join(pl))

        self._log(f"Scansione completata: {s.total_dirs:,} dir, {s.total_files:,} file, {len(ps.over_limit)} oltre soglia")

    def _export(self):
        if not self.analyzer or not self.analyzer.root_dir: return
        path = filedialog.asksaveasfilename(title="Salva Report", defaultextension=".md",
                                            filetypes=[("Markdown","*.md")])
        if not path: return
        # Usa il generatore report dalla v3 (semplificato qui)
        self._log(f"Export report: {path}")
        try:
            self._generate_md_report(path)
            self._last_report = path
            messagebox.showinfo("OK", f"Report salvato:\n{path}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def _generate_md_report(self, output_path):
        a = self.analyzer; s = a.stats; ps = s.path_stats
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        L = ["# Path Analyzer Report","",f"> {now} - Path Analyzer Editor v4.0","","---",""]
        L.append("## Riepilogo\n")
        L.append(f"| Metrica | Valore |\n|---|---|\n| Cartelle | {s.total_dirs:,} |\n| File | {s.total_files:,} |")
        L.append(f"| Dimensione | {format_size(s.total_size)} |\n| Path oltre soglia | **{len(ps.over_limit)}** |\n")
        if ps.over_limit:
            L.append(f"## Percorsi oltre soglia ({a.path_limit} chars)\n")
            L.append("| # | Tipo | Lunghezza | Eccesso | Percorso |")
            L.append("|---|------|-----------|---------|----------|")
            for i,(p,l,t) in enumerate(ps.over_limit, 1):
                L.append(f"| {i} | {t} | **{l}** | +{l-a.path_limit} | `{p}` |")
            L.append("")
        L.append("## Struttura\n\n```")
        L.extend(a.build_clean_tree(a.root_dir))
        L.append("```\n")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(L))

    # ─── WIZARD ──────────────────────────────────────────────────────────

    def _open_wizard(self):
        if not self.analyzer or not self.analyzer.stats.path_stats.over_limit:
            messagebox.showinfo("Info", "Nessun path oltre soglia. Non serve l'editor.")
            return
        WizardWindow(self, self.analyzer)

    def _log(self, text):
        self.txt_log.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_log.insert("end", f"[{ts}] {text}\n")
        self.txt_log.see("end")


# ═══════════════════════════════════════════════════════════════════════════════
# GUI — WIZARD WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class WizardWindow(ctk.CTkToplevel):
    """Finestra wizard per configurare e applicare le rinominazioni."""

    def __init__(self, parent: PathAnalyzerApp, analyzer: PathAnalyzer):
        super().__init__(parent)
        self.parent_app = parent
        self.analyzer = analyzer
        self.engine = RenameEngine(analyzer.root_path, analyzer.path_limit)
        self.rules: List[RenameRule] = []
        self.current_step = 0

        self.title("Editor Rinomina - Wizard")
        self.geometry("950x650")
        self.minsize(800, 550)
        self.transient(parent)
        self.grab_set()

        self._build()
        self._show_step(0)

    def _build(self):
        # Title
        tf = ctk.CTkFrame(self, fg_color="transparent")
        tf.pack(fill="x", padx=16, pady=(12,4))
        self.step_label = ctk.CTkLabel(tf, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.step_label.pack(side="left")
        self.step_info = ctk.CTkLabel(tf, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.step_info.pack(side="left", padx=8, pady=(4,0))

        ps = self.analyzer.stats.path_stats
        info = ctk.CTkFrame(self)
        info.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(info, text=f"  {len(ps.over_limit)} percorsi oltre la soglia di {self.analyzer.path_limit} caratteri  ",
                     font=ctk.CTkFont(size=12), text_color="#e74c3c").pack(padx=10, pady=6)

        # Content area
        self.content = ctk.CTkFrame(self)
        self.content.pack(fill="both", expand=True, padx=16, pady=4)

        # Bottom buttons
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(4,12))
        self.btn_back = ctk.CTkButton(bf, text="< Indietro", width=100, height=36, state="disabled", command=self._prev_step)
        self.btn_back.pack(side="left")
        self.btn_next = ctk.CTkButton(bf, text="Avanti >", width=100, height=36, command=self._next_step)
        self.btn_next.pack(side="right")

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _show_step(self, step):
        self.current_step = step
        self._clear_content()
        self.btn_back.configure(state="normal" if step > 0 else "disabled")

        if step == 0: self._step_rules()
        elif step == 1: self._step_preview()
        elif step == 2: self._step_confirm()
        elif step == 3: self._step_execute()

    def _prev_step(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _next_step(self):
        if self.current_step == 0:
            # Valida che ci siano regole
            if not self.rules:
                messagebox.showwarning("Attenzione", "Aggiungi almeno una regola.")
                return
            self._show_step(1)
        elif self.current_step == 1:
            if not self.engine.plan.operations:
                messagebox.showinfo("Info", "Nessuna operazione da eseguire.")
                return
            self._show_step(2)
        elif self.current_step == 2:
            self._show_step(3)

    # ─── STEP 0: CONFIGURAZIONE REGOLE ───────────────────────────────────

    def _step_rules(self):
        self.step_label.configure(text="Step 1: Configura Regole")
        self.step_info.configure(text="Definisci le regole per abbreviare i nomi")
        self.btn_next.configure(text="Avanti: Preview >", state="normal")

        # Split: left = add rule, right = rule list
        left = ctk.CTkFrame(self.content)
        left.pack(side="left", fill="both", expand=True, padx=(0,4))

        right = ctk.CTkFrame(self.content)
        right.pack(side="right", fill="both", expand=True, padx=(4,0))

        # Left: Add rule form
        ctk.CTkLabel(left, text="Aggiungi Regola", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=(10,4))

        self.rule_type_var = ctk.StringVar(value=RuleType.FIND_REPLACE.value)
        ctk.CTkLabel(left, text="Tipo:").pack(anchor="w", padx=10)
        ctk.CTkOptionMenu(left, variable=self.rule_type_var,
                          values=[rt.value for rt in RuleType],
                          command=self._on_rule_type_change,
                          width=280).pack(padx=10, pady=(0,8))

        # Dynamic params frame
        self.params_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.params_frame.pack(fill="x", padx=10)
        self.param_vars = {}
        self._on_rule_type_change(self.rule_type_var.get())

        # Checkboxes
        self.apply_files_var = ctk.BooleanVar(value=True)
        self.apply_dirs_var = ctk.BooleanVar(value=True)
        cf = ctk.CTkFrame(left, fg_color="transparent")
        cf.pack(fill="x", padx=10, pady=8)
        ctk.CTkCheckBox(cf, text="Applica ai file", variable=self.apply_files_var).pack(side="left", padx=(0,10))
        ctk.CTkCheckBox(cf, text="Applica alle cartelle", variable=self.apply_dirs_var).pack(side="left")

        ctk.CTkButton(left, text="+ Aggiungi Regola", height=36,
                      fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._add_rule).pack(padx=10, pady=8)

        # Right: Rule list
        ctk.CTkLabel(right, text="Regole Attive", font=ctk.CTkFont(size=14, weight="bold")).pack(padx=10, pady=(10,4))

        self.rules_list = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=11))
        self.rules_list.pack(fill="both", expand=True, padx=10, pady=(0,4))

        ctk.CTkButton(right, text="Rimuovi Ultima", height=30,
                      fg_color="#c0392b", hover_color="#e74c3c",
                      command=self._remove_last_rule).pack(padx=10, pady=(0,8))

        self._refresh_rules_display()

    def _on_rule_type_change(self, value):
        for w in self.params_frame.winfo_children(): w.destroy()
        self.param_vars = {}

        if value == RuleType.FIND_REPLACE.value:
            ctk.CTkLabel(self.params_frame, text="Cerca:").pack(anchor="w")
            v1 = ctk.StringVar(); self.param_vars["find"] = v1
            ctk.CTkEntry(self.params_frame, textvariable=v1, height=28).pack(fill="x", pady=(0,4))
            ctk.CTkLabel(self.params_frame, text="Sostituisci con:").pack(anchor="w")
            v2 = ctk.StringVar(); self.param_vars["replace"] = v2
            ctk.CTkEntry(self.params_frame, textvariable=v2, height=28).pack(fill="x", pady=(0,4))
            v3 = ctk.BooleanVar(value=False); self.param_vars["case_sensitive"] = v3
            ctk.CTkCheckBox(self.params_frame, text="Case sensitive", variable=v3).pack(anchor="w")

        elif value == RuleType.TRUNCATE.value:
            ctk.CTkLabel(self.params_frame, text="Max caratteri (solo il nome, senza estensione):").pack(anchor="w")
            v = ctk.StringVar(value="40"); self.param_vars["max_chars"] = v
            ctk.CTkEntry(self.params_frame, textvariable=v, width=80, height=28).pack(anchor="w")

        elif value == RuleType.REMOVE_CHARS.value:
            ctk.CTkLabel(self.params_frame, text="Caratteri da rimuovere:").pack(anchor="w")
            v = ctk.StringVar(value="_ -"); self.param_vars["chars"] = v
            ctk.CTkEntry(self.params_frame, textvariable=v, height=28).pack(fill="x")

        elif value == RuleType.REMOVE_PREFIX.value:
            ctk.CTkLabel(self.params_frame, text="Prefisso da rimuovere:").pack(anchor="w")
            v = ctk.StringVar(); self.param_vars["prefix"] = v
            ctk.CTkEntry(self.params_frame, textvariable=v, height=28).pack(fill="x")

        elif value == RuleType.REMOVE_SUFFIX.value:
            ctk.CTkLabel(self.params_frame, text="Suffisso da rimuovere (prima dell'estensione):").pack(anchor="w")
            v = ctk.StringVar(); self.param_vars["suffix"] = v
            ctk.CTkEntry(self.params_frame, textvariable=v, height=28).pack(fill="x")

        elif value == RuleType.COMPRESS_SEPARATORS.value:
            ctk.CTkLabel(self.params_frame, text="Carattere separatore da comprimere:").pack(anchor="w")
            v = ctk.StringVar(value="_"); self.param_vars["char"] = v
            ctk.CTkEntry(self.params_frame, textvariable=v, width=60, height=28).pack(anchor="w")

        elif value == RuleType.REGEX_REPLACE.value:
            ctk.CTkLabel(self.params_frame, text="Pattern Regex:").pack(anchor="w")
            v1 = ctk.StringVar(); self.param_vars["pattern"] = v1
            ctk.CTkEntry(self.params_frame, textvariable=v1, height=28).pack(fill="x", pady=(0,4))
            ctk.CTkLabel(self.params_frame, text="Sostituisci con:").pack(anchor="w")
            v2 = ctk.StringVar(); self.param_vars["replace"] = v2
            ctk.CTkEntry(self.params_frame, textvariable=v2, height=28).pack(fill="x")

        elif value == RuleType.SMART_ABBREVIATE.value:
            ctk.CTkLabel(self.params_frame, text="Abbrevia automaticamente parole comuni\n(Documents->Docs, Configuration->Cfg, ecc.)",
                        font=ctk.CTkFont(size=11)).pack(anchor="w")

    def _add_rule(self):
        rt_str = self.rule_type_var.get()
        rt = next(r for r in RuleType if r.value == rt_str)

        params = {}
        for k, v in self.param_vars.items():
            val = v.get()
            if k == "max_chars":
                try: val = int(val)
                except: val = 50
            elif k == "case_sensitive":
                val = bool(val)
            params[k] = val

        rule = RenameRule(
            rule_type=rt, params=params,
            apply_to_files=self.apply_files_var.get(),
            apply_to_dirs=self.apply_dirs_var.get()
        )
        self.rules.append(rule)
        self._refresh_rules_display()

    def _remove_last_rule(self):
        if self.rules:
            self.rules.pop()
            self._refresh_rules_display()

    def _refresh_rules_display(self):
        if hasattr(self, 'rules_list'):
            self.rules_list.configure(state="normal")
            self.rules_list.delete("1.0", "end")
            if not self.rules:
                self.rules_list.insert("1.0", "Nessuna regola configurata.\n\nAggiungi regole dal pannello a sinistra.")
            else:
                for i, r in enumerate(self.rules, 1):
                    scope = []
                    if r.apply_to_files: scope.append("file")
                    if r.apply_to_dirs: scope.append("cartelle")
                    self.rules_list.insert("end", f"{i}. {r.describe()}\n")
                    self.rules_list.insert("end", f"   Applica a: {', '.join(scope)}\n\n")

    # ─── STEP 1: PREVIEW ────────────────────────────────────────────────

    def _step_preview(self):
        self.step_label.configure(text="Step 2: Preview Modifiche")
        self.step_info.configure(text="Verifica le modifiche prima di applicarle")
        self.btn_next.configure(text="Avanti: Conferma >", state="normal")

        self.preview_text = ctk.CTkTextbox(self.content, font=ctk.CTkFont(family="Consolas", size=11), wrap="none")
        self.preview_text.pack(fill="both", expand=True, padx=4, pady=4)

        self.preview_text.insert("1.0", "Calcolo preview in corso...\n")

        threading.Thread(target=self._calc_preview, daemon=True).start()

    def _calc_preview(self):
        plan = self.engine.create_plan(self.rules, only_over_limit=True)
        self.after(0, lambda: self._show_preview(plan))

    def _show_preview(self, plan: RenamePlan):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")

        lines = []
        lines.append(f"{'='*80}")
        lines.append(f"  PREVIEW PIANO DI RINOMINA")
        lines.append(f"{'='*80}")
        lines.append(f"  Operazioni pianificate:  {len(plan.operations)}")
        lines.append(f"  Risparmio totale:        ~{plan.total_savings} caratteri")
        lines.append(f"  Conflitti:               {len(plan.conflicts)}")
        lines.append(f"  Warnings:                {len(plan.warnings)}")
        lines.append(f"  Piano valido:            {'SI' if plan.is_valid else 'NO'}")
        lines.append("")

        if plan.conflicts:
            lines.append(f"{'!'*80}")
            lines.append(f"  CONFLITTI (devono essere risolti)")
            lines.append(f"{'!'*80}")
            for c in plan.conflicts:
                lines.append(f"  ! {c}")
            lines.append("")

        if plan.warnings:
            for w in plan.warnings:
                lines.append(f"  AVVISO: {w}")
            lines.append("")

        if plan.operations:
            lines.append(f"{'='*80}")
            lines.append(f"  OPERAZIONI (ordinate bottom-up per esecuzione sicura)")
            lines.append(f"{'='*80}")
            lines.append(f"  {'#':>5}  {'Tipo':<5}  {'Depth':<6}  {'Vecchio':^30}  ->  {'Nuovo':^30}  {'Risparmio'}")
            lines.append(f"  {'-'*5}  {'-'*5}  {'-'*6}  {'-'*30}  --  {'-'*30}  {'-'*9}")

            for i, op in enumerate(plan.operations, 1):
                t = "DIR" if op.is_dir else "FILE"
                old = op.old_name[:30]
                new = op.new_name[:30]
                lines.append(f"  {i:>5}  {t:<5}  d={op.depth:<4}  {old:<30}  ->  {new:<30}  -{op.savings} chars")

            lines.append("")
            lines.append(f"  Totale: {len(plan.operations)} operazioni, ~{plan.total_savings} caratteri risparmiati")

            # Mostra anche il dettaglio dei path completi
            lines.append("")
            lines.append(f"{'='*80}")
            lines.append(f"  DETTAGLIO PATH COMPLETI")
            lines.append(f"{'='*80}")
            for i, op in enumerate(plan.operations, 1):
                t = "DIR " if op.is_dir else "FILE"
                lines.append(f"  {i}. [{t}] depth={op.depth}")
                lines.append(f"     PRIMA:  {op.old_path}")
                lines.append(f"             ({op.old_length} chars)")
                lines.append(f"     DOPO:   {op.new_path}")
                lines.append(f"             ({op.new_length} chars, -{op.savings})")
                lines.append("")

        self.preview_text.insert("1.0", "\n".join(lines))

        if not plan.is_valid:
            self.btn_next.configure(state="disabled")

    # ─── STEP 2: CONFERMA ───────────────────────────────────────────────

    def _step_confirm(self):
        self.step_label.configure(text="Step 3: Conferma")
        self.step_info.configure(text="Conferma l'esecuzione delle modifiche")
        self.btn_next.configure(text="ESEGUI MODIFICHE", state="normal",
                                fg_color="#c0392b", hover_color="#e74c3c")

        f = ctk.CTkFrame(self.content, fg_color="transparent")
        f.pack(expand=True)

        plan = self.engine.plan
        lines = [
            f"Stai per eseguire {len(plan.operations)} operazioni di rinomina.",
            "",
            f"  - File da rinominare:    {sum(1 for o in plan.operations if not o.is_dir)}",
            f"  - Cartelle da rinominare: {sum(1 for o in plan.operations if o.is_dir)}",
            f"  - Risparmio stimato:     ~{plan.total_savings} caratteri",
            "",
            "Le operazioni verranno eseguite in ordine bottom-up",
            "(dal livello piu profondo al piu alto) per evitare",
            "l'invalidazione dei percorsi.",
            "",
            "Verra creato un file di log per il rollback.",
        ]
        for line in lines:
            ctk.CTkLabel(f, text=line, font=ctk.CTkFont(family="Consolas", size=13)).pack(anchor="w", padx=20)

        ctk.CTkLabel(f, text="\nATTENZIONE: questa operazione modifica il filesystem!",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#e74c3c").pack(pady=(16,4))

        self.on_error_var = ctk.StringVar(value="skip")
        ef = ctk.CTkFrame(f, fg_color="transparent")
        ef.pack(pady=8)
        ctk.CTkLabel(ef, text="In caso di errore:").pack(side="left", padx=(0,8))
        ctk.CTkRadioButton(ef, text="Salta e continua", variable=self.on_error_var, value="skip").pack(side="left", padx=4)
        ctk.CTkRadioButton(ef, text="Ferma tutto", variable=self.on_error_var, value="stop").pack(side="left", padx=4)

    # ─── STEP 3: ESECUZIONE ─────────────────────────────────────────────

    def _step_execute(self):
        self.step_label.configure(text="Step 4: Esecuzione")
        self.step_info.configure(text="Operazioni in corso...")
        self.btn_next.configure(state="disabled", text="In corso...")
        self.btn_back.configure(state="disabled")

        self.exec_text = ctk.CTkTextbox(self.content, font=ctk.CTkFont(family="Consolas", size=11))
        self.exec_text.pack(fill="both", expand=True, padx=4, pady=4)

        btn_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_frame.pack(fill="x", padx=4, pady=4)

        self.rollback_btn = ctk.CTkButton(btn_frame, text="ROLLBACK (Annulla Tutto)",
                                          fg_color="#c0392b", hover_color="#e74c3c",
                                          state="disabled", command=self._do_rollback)
        self.rollback_btn.pack(side="left", padx=(0,8))

        self.close_btn = ctk.CTkButton(btn_frame, text="Chiudi", state="disabled",
                                       command=self.destroy)
        self.close_btn.pack(side="right")

        self.exec_text.insert("1.0", "Avvio esecuzione...\n\n")

        threading.Thread(target=self._run_execute, daemon=True).start()

    def _run_execute(self):
        on_err = self.on_error_var.get()

        def progress(idx, total, ok, err):
            self.after(0, lambda: self._exec_progress(idx, total, ok, err))

        success, errors, error_list = self.engine.execute(on_error=on_err, progress_cb=progress)

        # Salva undo log
        undo_path = os.path.join(os.path.dirname(self.analyzer.root_path),
                                 f"path_analyzer_undo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            self.engine.save_undo_log(undo_path)
        except:
            undo_path = None

        self.after(0, lambda: self._exec_done(success, errors, error_list, undo_path))

    def _exec_progress(self, idx, total, ok, err):
        self.exec_text.configure(state="normal")
        pct = idx / total * 100 if total else 100
        self.exec_text.delete("1.0", "end")
        self.exec_text.insert("1.0",
            f"Progresso: {idx}/{total} ({pct:.0f}%)\n"
            f"Successi: {ok}\n"
            f"Errori: {err}\n")
        self.step_info.configure(text=f"Operazione {idx}/{total}...")

    def _exec_done(self, success, errors, error_list, undo_path):
        self.exec_text.configure(state="normal")
        self.exec_text.delete("1.0", "end")

        lines = [
            "=" * 60,
            "  ESECUZIONE COMPLETATA",
            "=" * 60,
            f"  Operazioni riuscite:  {success}",
            f"  Errori:               {errors}",
            "",
        ]

        if undo_path:
            lines.append(f"  Log rollback salvato in:")
            lines.append(f"  {undo_path}")
            lines.append("")

        if error_list:
            lines.append("-" * 60)
            lines.append("  ERRORI:")
            lines.append("-" * 60)
            for e in error_list:
                lines.append(f"  {e}")

        lines.append("")
        if success > 0:
            lines.append("  Per annullare le modifiche, usa il pulsante ROLLBACK.")

        self.exec_text.insert("1.0", "\n".join(lines))

        self.step_info.configure(text=f"Completato: {success} ok, {errors} errori")
        self.btn_next.configure(text="Completato", state="disabled")
        self.close_btn.configure(state="normal")

        if success > 0:
            self.rollback_btn.configure(state="normal")

        self.parent_app._log(f"Editor: {success} rinominati, {errors} errori")

    def _do_rollback(self):
        if not messagebox.askyesno("Conferma Rollback",
                                   "Vuoi annullare TUTTE le modifiche effettuate?"):
            return

        self.rollback_btn.configure(state="disabled")
        ok, err = self.engine.rollback()

        self.exec_text.configure(state="normal")
        self.exec_text.insert("end", f"\n\n{'='*60}\n  ROLLBACK: {ok} ripristinati, {err} errori\n{'='*60}\n")
        self.parent_app._log(f"Rollback: {ok} ripristinati, {err} errori")

        if err == 0:
            messagebox.showinfo("Rollback", f"Rollback completato: {ok} elementi ripristinati.")
        else:
            messagebox.showwarning("Rollback", f"Rollback parziale: {ok} ok, {err} errori.")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = PathAnalyzerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
