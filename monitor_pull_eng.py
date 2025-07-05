#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor_poll_menu.py v1.3.0

Self-contained Python stdlib tool for polling-based directory monitoring.
Features:
  • multiple directories
  • recursive or non-recursive scan
  • include/exclude hidden entries
  • advanced filters (glob include/exclude patterns)
  • logging to console and/or file
  • detects file and folder creation, deletion, modification
  • press ESC to stop monitoring and return to menu

No external dependencies are required.
"""

import os
import sys
import time
import select
import logging
import fnmatch
import termios
import tty
from pathlib import Path

def scan_dirs(bases, recursive, include_hidden, include_pats, exclude_pats):
    """
    Walk through each base directory and return a snapshot dict:
      { "base|relative_path": last_modification_time }
    Applies glob filters and handles hidden entries per settings.
    """
    snapshot = {}
    for base in bases:
        base = base.resolve()
        if recursive:
            for root, dirs, files in os.walk(base):
                # filter out hidden entries if needed
                if not include_hidden:
                    dirs[:]  = [d for d in dirs  if not d.startswith('.')]
                    files[:] = [f for f in files if not f.startswith('.')]
                # record directories
                for d in dirs:
                    full = Path(root) / d
                    rel = full.relative_to(base).as_posix() + '/'
                    if _filter_match(rel, include_pats, exclude_pats):
                        snapshot[f"{base}|{rel}"] = full.stat().st_mtime
                # record files
                for f in files:
                    full = Path(root) / f
                    rel = full.relative_to(base).as_posix()
                    if _filter_match(rel, include_pats, exclude_pats):
                        snapshot[f"{base}|{rel}"] = full.stat().st_mtime
        else:
            for child in base.iterdir():
                name = child.name
                # skip hidden if not included
                if not include_hidden and name.startswith('.'):
                    continue
                rel = name + ('/' if child.is_dir() else '')
                if _filter_match(rel, include_pats, exclude_pats):
                    snapshot[f"{base}|{rel}"] = child.stat().st_mtime
    return snapshot

def _filter_match(name, includes, excludes):
    """
    Return True if `name` passes include/exclude glob patterns.
    """
    if includes and not any(fnmatch.fnmatch(name, pat) for pat in includes):
        return False
    if excludes and any(fnmatch.fnmatch(name, pat) for pat in excludes):
        return False
    return True

def compare_snapshots(old, new):
    """
    Compare two snapshots, return sets of added, removed, modified keys.
    """
    added   = set(new) - set(old)
    removed = set(old) - set(new)
    modified= {k for k in (set(old) & set(new)) if old[k] != new[k]}
    return added, removed, modified

def setup_logging(logfile):
    """
    Configure logging to stdout and optional file.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding='utf-8'))
    fmt = "%(asctime)s %(levelname)-8s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)
    logging.info("Logging initialized")

def _enable_raw_mode():
    """
    Enable cbreak mode on stdin to read single characters (for ESC).
    Returns original termios attributes.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return old

def _restore_mode(old):
    """
    Restore original termios attributes.
    """
    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, old)

def menu():
    """
    Display textual menu for configuration.
    Returns tuple of settings when monitoring is started.
    """
    dirs = []
    interval = 5.0
    recursive = False
    include_hidden = False
    include_pats, exclude_pats = [], []
    logfile = None

    while True:
        print("\n" + "="*60)
        print("   DIRECTORY POLLING MONITOR – VERSION 1.3.0")
        print("="*60)
        print("1) Add directory")
        print("2) Remove directory")
        print("3) Show configured directories")
        print(f"4) Polling interval:       {interval:.1f}s")
        print(f"5) Recursive scan:         {'YES' if recursive else 'NO'}")
        print(f"6) Include hidden:         {'YES' if include_hidden else 'NO'}")
        print("7) Advanced filters (include/exclude)")
        print(f"8) Log file path:          {logfile or 'stdout'}")
        print("9) Start monitoring")
        print("0) Exit")
        print("-"*60)
        choice = input("Select [0-9]: ").strip()

        if choice == '1':
            p = input("   Enter directory to add: ").strip()
            d = Path(p).expanduser().resolve()
            if d.is_dir() and d not in dirs:
                dirs.append(d)
                print("   + Added:", d)
            else:
                print("   ! Invalid or duplicate directory")
        elif choice == '2':
            if not dirs:
                print("   ! No directories to remove")
            else:
                for i, d in enumerate(dirs, 1):
                    print(f"   {i}) {d}")
                sel = input("   Select number to remove: ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(dirs):
                    removed = dirs.pop(int(sel)-1)
                    print("   - Removed:", removed)
                else:
                    print("   ! Invalid selection")
        elif choice == '3':
            if not dirs:
                print("   ! No directories configured")
            else:
                print("   Configured directories:")
                for d in dirs:
                    print("    -", d)
        elif choice == '4':
            val = input("   Set interval (seconds): ").strip()
            try:
                interval = float(val)
            except ValueError:
                print("   ! Invalid number")
        elif choice == '5':
            recursive = not recursive
            print("   Recursive scan:", "YES" if recursive else "NO")
        elif choice == '6':
            include_hidden = not include_hidden
            print("   Include hidden:", "YES" if include_hidden else "NO")
        elif choice == '7':
            _submenu_filters(include_pats, exclude_pats)
        elif choice == '8':
            v = input("   Enter log file path (empty=stdout): ").strip()
            logfile = Path(v).expanduser().resolve() if v else None
        elif choice == '9':
            if not dirs:
                print("   ! At least one directory must be added")
                continue
            return dirs, interval, recursive, include_hidden, include_pats, exclude_pats, logfile
        elif choice == '0':
            sys.exit(0)
        else:
            print("   ! Invalid choice")

def _submenu_filters(includes, excludes):
    """
    Sub-menu to manage include/exclude glob patterns.
    """
    while True:
        print("\n  > ADVANCED FILTERS")
        print("  a) Add INCLUDE pattern")
        print("  b) Remove INCLUDE pattern")
        print("  c) Show INCLUDE patterns")
        print("  d) Add EXCLUDE pattern")
        print("  e) Remove EXCLUDE pattern")
        print("  f) Show EXCLUDE patterns")
        print("  x) Return to main menu")
        sel = input("  Select [a-f,x]: ").strip().lower()
        if sel == 'a':
            pat = input("    Enter INCLUDE pattern: ").strip()
            if pat and pat not in includes:
                includes.append(pat)
                print("    +", pat)
        elif sel == 'b':
            for i, pat in enumerate(includes, 1):
                print(f"    {i}) {pat}")
            v = input("    Select number: ").strip()
            if v.isdigit() and 1 <= int(v) <= len(includes):
                includes.pop(int(v)-1)
        elif sel == 'c':
            print("    INCLUDE patterns:", includes or ["(none)"])
        elif sel == 'd':
            pat = input("    Enter EXCLUDE pattern: ").strip()
            if pat and pat not in excludes:
                excludes.append(pat)
                print("    +", pat)
        elif sel == 'e':
            for i, pat in enumerate(excludes, 1):
                print(f"    {i}) {pat}")
            v = input("    Select number: ").strip()
            if v.isdigit() and 1 <= int(v) <= len(excludes):
                excludes.pop(int(v)-1)
        elif sel == 'f':
            print("    EXCLUDE patterns:", excludes or ["(none)"])
        elif sel == 'x':
            break
        else:
            print("    ! Invalid choice")

def monitor_loop(paths, interval, recursive, include_hidden,
                 include_pats, exclude_pats, logfile):
    """
    Main monitoring loop. Press ESC to interrupt and return to menu.
    """
    setup_logging(logfile)
    logging.info("==== Monitoring started (press ESC to return) ====")
    logging.info(f"Directories: {', '.join(str(p) for p in paths)}")
    logging.info(f"Interval: {interval}s | Recursive: {recursive} | Include hidden: {include_hidden}")
    logging.info(f"Include patterns: {include_pats or '---'}")
    logging.info(f"Exclude patterns: {exclude_pats or '---'}")

    old_attrs = _enable_raw_mode()
    old_snapshot = scan_dirs(paths, recursive, include_hidden, include_pats, exclude_pats)
    try:
        while True:
            # wait for interval or keypress
            ready, _, _ = select.select([sys.stdin], [], [], interval)
            if ready:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # ESC
                    logging.info("ESC pressed: returning to menu.")
                    break

            new_snapshot = scan_dirs(paths, recursive, include_hidden, include_pats, exclude_pats)
            added, removed, modified = compare_snapshots(old_snapshot, new_snapshot)

            for key in sorted(added):
                base, rel = key.split("|", 1)
                typ = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] +Added   {typ}: {rel.rstrip('/')}")
            for key in sorted(removed):
                base, rel = key.split("|", 1)
                typ = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] -Removed {typ}: {rel.rstrip('/')}")
            for key in sorted(modified):
                base, rel = key.split("|", 1)
                typ = "DIR" if rel.endswith("/") else "FILE"
                logging.info(f"[{base}] *Modified{typ}: {rel.rstrip('/')}")

            old_snapshot = new_snapshot

    finally:
        _restore_mode(old_attrs)
        logging.info("==== Monitoring stopped ====")

def main():
    """
    Loop: show menu, then start monitoring until ESC.
    """
    while True:
        params = menu()
        monitor_loop(*params)

if __name__ == "__main__":
    main()
