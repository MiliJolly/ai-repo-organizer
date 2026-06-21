#!/usr/bin/env python3
"""
repo_organizer.py
=================
Automatically organizes a messy repository into a clean folder structure.

Features
--------
  - Classifies every root-level file by extension + name/content patterns
  - Creates destination folders only when needed
  - Moves files safely; never silently overwrites (renames on collision)
  - Detects exact duplicates by MD5 hash and skips them
  - Logs every action to  organizer.log  (appends across runs)
  - Builds a searchable JSON index at  file_index.json  after each run
  - Writes cron / Task Scheduler config to  cron_config.txt
  - Fully idempotent: safe to run repeatedly

Usage
-----
  python repo_organizer.py               # organize the repo
  python repo_organizer.py --dry-run     # preview changes, nothing is moved
  python repo_organizer.py --index-only  # rebuild index only, skip file moves
"""

import os
import re
import sys
import json
import shutil
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.resolve()

# These files always stay in the repo root; never moved.
ROOT_ONLY = {
    "readme.md",
    "license",
    "license.md",
    ".gitignore",
    ".gitattributes",
    ".env",
    "repo_organizer.py",
    "organizer.log",
    "file_index.json",
    "cron_config.txt",
}

LOG_FILE   = REPO_ROOT / "organizer.log"
INDEX_FILE = REPO_ROOT / "file_index.json"
CRON_FILE  = REPO_ROOT / "cron_config.txt"

# ---------------------------------------------------------------------------
# CLASSIFICATION RULES
# ---------------------------------------------------------------------------
# Each rule is a tuple:
#   (destination_folder, extensions_set, name_patterns, content_patterns)
#
# Matching logic (evaluated in order; first match wins):
#   1. File extension must be in extensions_set.
#   2. If name_patterns is non-empty  → check regex against filename stem (case-insensitive).
#   3. If content_patterns is non-empty → check regex against first 40 lines of file.
#   4. If both pattern lists are empty   → extension alone is enough to match.
#   5. name_patterns OR content_patterns matching is sufficient (either/or).
#   6. If name_patterns exist but NONE match, fall through to content_patterns.
# ---------------------------------------------------------------------------

FOLDER_RULES = [
    # ── Tests ────────────────────────────────────────────────────────────────
    (
        "tests",
        {".py"},
        [r"^test_", r"_test$"],
        [r"import pytest", r"@pytest\.fixture", r"def test_"],
    ),
    # ── Logs ─────────────────────────────────────────────────────────────────
    (
        "logs",
        {".log"},
        [],
        [],
    ),
    # ── Results / metrics JSON  (before generic config JSON) ─────────────────
    (
        "results",
        {".json"},
        [r"result", r"metric", r"output", r"report", r"prediction"],
        [],
    ),
    # ── Raw / processed data files ───────────────────────────────────────────
    (
        "data",
        {".csv", ".xlsx", ".tsv", ".parquet", ".feather"},
        [],
        [],
    ),
    # ── Data preprocessing / ETL scripts ─────────────────────────────────────
    (
        "data",
        {".py"},
        [r"preprocess", r"^etl", r"ingest", r"clean_data"],
        [r"RENAME_MAP", r"generate_synthetic", r"raw_customers"],
    ),
    # ── One-off / temporary scripts  (before generic ML so temp_*.py wins) ───
    (
        "scripts",
        {".py"},
        [r"^temp_", r"^run_", r"^setup_", r"export"],
        [],
    ),
    # ── Machine-learning scripts ──────────────────────────────────────────────
    (
        "ml",
        {".py"},
        [
            r"model",
            r"train",
            r"predict",
            r"segment",
            r"recommend",
            r"experiment",
            r"cluster",
            r"dbscan",
        ],
        [
            r"from sklearn",
            r"import sklearn",
            r"RandomForest",
            r"GradientBoosting",
            r"KMeans",
            r"pickle\.dump",
            r"pickle\.load",
        ],
    ),
    # ── Shell / PowerShell scripts ────────────────────────────────────────────
    (
        "scripts",
        {".sh", ".bash", ".ps1"},
        [],
        [],
    ),
    # ── Backend API / server code ─────────────────────────────────────────────
    (
        "backend",
        {".py"},
        [r"^app", r"api", r"server", r"route", r"endpoint", r"middleware"],
        [r"Flask\(", r"@app\.route", r"FastAPI\(", r"APIRouter"],
    ),
    # ── Frontend ──────────────────────────────────────────────────────────────
    (
        "frontend",
        {".html", ".css", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"},
        [],
        [],
    ),
    # ── Config / dependency files ─────────────────────────────────────────────
    (
        "config",
        {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"},
        [],
        [],
    ),
    (
        "config",
        {".txt"},
        [r"^requirements", r"^setup", r"^pip"],
        [],
    ),
    # ── Docs / notes / markdown ───────────────────────────────────────────────
    (
        "docs",
        {".md", ".txt", ".rst", ".pdf"},
        [],
        [],
    ),
]

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------

def setup_logging(dry_run: bool) -> logging.Logger:
    """Configure a logger that writes to both the log file and stdout."""
    logger = logging.getLogger("repo_organizer")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # File handler (always write; the file persists across runs)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

# ---------------------------------------------------------------------------
# FILE UTILITIES
# ---------------------------------------------------------------------------

def md5_hash(path: Path) -> str:
    """Return the MD5 hex-digest of a file (chunked to handle large files)."""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def peek_content(path: Path, max_lines: int = 40) -> str:
    """Return the first `max_lines` lines of a text file, or '' on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = []
            for _ in range(max_lines):
                line = fh.readline()
                if not line:
                    break
                lines.append(line)
        return "".join(lines)
    except OSError:
        return ""

# ---------------------------------------------------------------------------
# CLASSIFICATION ENGINE
# ---------------------------------------------------------------------------

def classify(path: Path) -> str | None:
    """
    Return the destination folder name for `path`, or None if the file
    should remain in the root.

    Decision order:
      1. Name is in ROOT_ONLY → None (keep in root)
      2. Walk FOLDER_RULES in sequence; return folder on first match
      3. No rule matched → 'misc'  (catch-all)
    """
    if path.name.lower() in ROOT_ONLY:
        return None

    ext  = path.suffix.lower()
    stem = path.stem.lower()

    # Peek content only for text-based extensions (avoid reading binary files)
    TEXT_EXTS = {".py", ".js", ".ts", ".json", ".yaml", ".yml",
                 ".sh", ".txt", ".md", ".html", ".css", ".cfg", ".ini"}
    content = peek_content(path) if ext in TEXT_EXTS else ""

    for folder, exts, name_pats, content_pats in FOLDER_RULES:
        if ext not in exts:
            continue

        # Extension matched → now check name / content
        if not name_pats and not content_pats:
            # Extension alone is sufficient
            return folder

        name_hit = any(re.search(p, stem, re.IGNORECASE) for p in name_pats)
        if name_hit:
            return folder

        if content_pats and content:
            content_hit = any(re.search(p, content) for p in content_pats)
            if content_hit:
                return folder

    return "misc"

# ---------------------------------------------------------------------------
# SAFE MOVE
# ---------------------------------------------------------------------------

def safe_move(
    src: Path,
    dest_dir: Path,
    dry_run: bool,
    logger: logging.Logger,
) -> tuple[str, Path]:
    """
    Move `src` into `dest_dir`.

    Returns (action_label, final_destination):
      'moved'          – file moved successfully
      'moved_renamed'  – file moved but renamed to avoid a name collision
      'skipped_dup'    – identical file already exists in destination
      'skipped_self'   – file is already in the correct location

    In dry-run mode, no filesystem changes are made.
    """
    dest = dest_dir / src.name

    # Already in the right place (shouldn't normally happen for root-level
    # files, but guards against accidental double-processing)
    if dest.resolve() == src.resolve():
        return "skipped_self", dest

    if dest.exists():
        if md5_hash(src) == md5_hash(dest):
            # Exact duplicate – nothing to do
            return "skipped_dup", dest

        # Different content with the same name → rename before moving
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        action = "moved_renamed"
    else:
        action = "moved"

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    return action, dest

# ---------------------------------------------------------------------------
# FILE INDEX
# ---------------------------------------------------------------------------

def build_index(repo_root: Path) -> list[dict]:
    """
    Walk the entire repository and return a list of dicts suitable for
    writing to file_index.json.

    Each entry contains: name, relative path, folder, extension,
    size in bytes, MD5 hash, and timestamp.
    """
    index = []
    for path in sorted(repo_root.rglob("*")):
        # Skip directories and anything inside .git
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue

        rel = path.relative_to(repo_root)
        folder = str(rel.parent) if str(rel.parent) != "." else "root"

        try:
            stat = path.stat()
            size = stat.st_size
            mtime = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
            digest = md5_hash(path)
        except OSError:
            size, mtime, digest = 0, "", ""

        index.append({
            "name":        path.name,
            "path":        str(rel).replace("\\", "/"),
            "folder":      folder,
            "extension":   path.suffix.lower(),
            "size_bytes":  size,
            "md5":         digest,
            "modified_at": mtime,
            "indexed_at":  datetime.utcnow().isoformat(),
        })

    return index

# ---------------------------------------------------------------------------
# CRON / TASK SCHEDULER CONFIG
# ---------------------------------------------------------------------------

def generate_cron_config(script_path: Path) -> str:
    """
    Return the contents of cron_config.txt, covering both Unix/macOS
    (crontab) and Windows (schtasks) scheduling options.
    """
    python  = sys.executable
    script  = str(script_path)
    now     = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""# ============================================================
# repo_organizer – Scheduling Configuration
# Generated: {now}
# ============================================================

# ------------------------------------------------------------
# OPTION 1: Unix / macOS / Linux – crontab
# Run every Sunday at 02:00 AM
# ------------------------------------------------------------
# Add this line with: crontab -e
#
0 2 * * 0  {python} {script} >> {REPO_ROOT / "organizer.log"} 2>&1

# To run daily at 03:30 AM instead:
# 30 3 * * *  {python} {script} >> {REPO_ROOT / "organizer.log"} 2>&1

# ------------------------------------------------------------
# OPTION 2: Windows – Task Scheduler (schtasks)
# Run every Sunday at 02:00 AM
# ------------------------------------------------------------
# Run this command once in an elevated PowerShell / CMD:
#
# schtasks /Create /TN "RepoOrganizer" /TR "{python} {script}" /SC WEEKLY /D SUN /ST 02:00 /F
#
# To delete the task:
# schtasks /Delete /TN "RepoOrganizer" /F
#
# To run it immediately (test):
# schtasks /Run /TN "RepoOrganizer"

# ------------------------------------------------------------
# OPTION 3: GitHub Actions – run on a schedule (add to .github/workflows/)
# ------------------------------------------------------------
# name: Organize Repo
# on:
#   schedule:
#     - cron: "0 2 * * 0"   # every Sunday at 02:00 UTC
#   workflow_dispatch:        # allow manual trigger
# jobs:
#   organize:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - uses: actions/setup-python@v5
#         with:
#           python-version: "3.11"
#       - run: python repo_organizer.py
#       - uses: stefanzweifel/git-auto-commit-action@v5
#         with:
#           commit_message: "chore: auto-organize repo [skip ci]"
"""

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organize repository files into labelled sub-folders."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all planned moves without touching the filesystem.",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Rebuild file_index.json without moving any files.",
    )
    args = parser.parse_args()

    logger = setup_logging(dry_run=args.dry_run)

    mode = "DRY RUN" if args.dry_run else ("INDEX ONLY" if args.index_only else "LIVE")
    logger.info("=" * 60)
    logger.info(f"repo_organizer  started  [{mode}]  {datetime.utcnow().isoformat()}")
    logger.info(f"Repository root: {REPO_ROOT}")
    logger.info("=" * 60)

    # ── Index-only mode ────────────────────────────────────────────────────
    if args.index_only:
        index = build_index(REPO_ROOT)
        INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False))
        logger.info(f"Index rebuilt: {len(index)} files → {INDEX_FILE.name}")
        return

    # ── Collect root-level files to process ───────────────────────────────
    root_files = [
        p for p in sorted(REPO_ROOT.iterdir())
        if p.is_file() and p.name.lower() not in ROOT_ONLY
    ]
    logger.info(f"Found {len(root_files)} root-level file(s) to evaluate.")

    stats = {"moved": 0, "moved_renamed": 0, "skipped": 0, "errors": 0}

    for src in root_files:
        folder = classify(src)

        if folder is None:
            logger.info(f"  KEEP      {src.name!s:<35}  (root-protected)")
            stats["skipped"] += 1
            continue

        dest_dir = REPO_ROOT / folder
        try:
            action, dest = safe_move(src, dest_dir, args.dry_run, logger)
            rel_dest = dest.relative_to(REPO_ROOT)

            if action == "moved":
                logger.info(f"  MOVE      {src.name!s:<35}  →  {rel_dest}")
                stats["moved"] += 1
            elif action == "moved_renamed":
                logger.warning(
                    f"  RENAME    {src.name!s:<35}  →  {rel_dest}  "
                    f"(name collision in {folder}/)"
                )
                stats["moved_renamed"] += 1
            elif action == "skipped_dup":
                logger.info(
                    f"  SKIP-DUP  {src.name!s:<35}  (identical file already in {folder}/)"
                )
                stats["skipped"] += 1
            elif action == "skipped_self":
                logger.info(f"  SKIP-SELF {src.name!s:<35}  (already in correct location)")
                stats["skipped"] += 1

        except Exception as exc:
            logger.error(f"  ERROR     {src.name}: {exc}")
            stats["errors"] += 1

    # ── Rebuild index ──────────────────────────────────────────────────────
    logger.info("-" * 60)
    index = build_index(REPO_ROOT)
    if not args.dry_run:
        INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False))
        logger.info(f"Index written: {len(index)} files → {INDEX_FILE.name}")
    else:
        logger.info(f"[DRY RUN] Index would contain {len(index)} files (not written).")

    # ── Write cron config ──────────────────────────────────────────────────
    cron_text = generate_cron_config(Path(__file__).resolve())
    if not args.dry_run:
        CRON_FILE.write_text(cron_text, encoding="utf-8")
        logger.info(f"Cron config written → {CRON_FILE.name}")

    # ── Summary ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        f"Done.  moved={stats['moved']}  renamed={stats['moved_renamed']}  "
        f"skipped={stats['skipped']}  errors={stats['errors']}"
    )
    if args.dry_run:
        logger.info("DRY RUN complete — no files were moved.")
    logger.info("=" * 60)

    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
