# Directory Polling Monitor v1.0.0
#### Author: Bocaletto Luca

Self-contained Python tool for Terminal for polling-based directory monitoring.  
Allows you to watch one or more folders, apply advanced filters, and log changes in real time—all from a simple text menu.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=for-the-badge&logo=gnu)](LICENSE) [![Python 3.6+](https://img.shields.io/badge/Python-3.6%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/) [![Linux-Compatible](https://img.shields.io/badge/Linux-Compatible-blue?style=for-the-badge&logo=linux)](https://www.kernel.org/) [![Status: Complete](https://img.shields.io/badge/Status-Complete-brightgreen?style=for-the-badge)](https://github.com/bocaletto-luca/Directory-Monitor)

---

## Features

- Monitor multiple directories at once
- Recursive or non-recursive scanning
- Include or exclude hidden files and folders
- Advanced glob-based include/exclude filters
- Detects creation, deletion, and modification of files & directories
- Real-time logging to console and/or a log file
- Press **ESC** at any time during monitoring to stop and return to the menu
- No external dependencies—runs on Python 3.6+ with the standard library only

---

## Installation

1. Clone this repository or download the script:
   ```bash
   git clone https://github.com/bocaletto-luca/Directory-Polling-Monitor.git
   cd Directory-Polling-Monitor
   ```

2. Ensure you have Python 3.6 or newer installed:
   ```bash
   python3 --version
   ```

3. (Optional) Make the script executable:
   ```bash
   chmod +x monitor_poll.py
   ```

---

## Usage

Run the monitor script directly:
```bash
python3 monitor_poll.py
# or, if executable:
./monitor_poll.py
```

You’ll be greeted by an interactive menu to configure your monitoring session.

---

## Interactive Menu Overview

1. **Add directory**  
   Enter an absolute or `~/` path to include in the watch list.

2. **Remove directory**  
   Remove a previously added path from the list.

3. **Show configured directories**  
   Display all paths currently queued for monitoring.

4. **Polling interval**  
   Set the time (in seconds) between directory scans. Default is **5.0s**.

5. **Recursive scan**  
   Toggle whether subdirectories should be included in the scan.

6. **Include hidden**  
   Toggle whether files/folders starting with `.` are monitored.

7. **Advanced filters**  
   Enter the include/exclude submenu to add or remove glob patterns.  
   - **Include patterns**: Only files/folders matching at least one pattern are monitored.  
   - **Exclude patterns**: Any file/folder matching an exclude pattern is skipped.

8. **Log file path**  
   Specify a filename to capture logs. If left empty, all events print to stdout.

9. **Start monitoring**  
   Begin the polling loop. Press **ESC** anytime to stop and return to the main menu.

0. **Exit**  
   Quit the program.

---

## Advanced Filters Sub-Menu

Within the “Advanced filters” option, you can:  
- **Add INCLUDE pattern** (e.g. `*.log`, `data/**/*.csv`)  
- **Remove INCLUDE pattern**  
- **List current INCLUDE patterns**  
- **Add EXCLUDE pattern** (e.g. `temp/*`, `*/.git/*`)  
- **Remove EXCLUDE pattern**  
- **List current EXCLUDE patterns**  

Patterns use standard Unix glob syntax via Python’s `fnmatch` module.

---

## Press ESC to Stop Monitoring

During an active monitoring session, the script switches the terminal to “cbreak” mode, allowing it to detect single keystrokes. Press the **ESC** key at any time to immediately break out of the loop and return to the configuration menu. The terminal’s original settings are restored automatically upon exit.

---

## Logging Format

Each event is logged with a timestamp and severity level:  
```
2025-07-05 22:58:53,080 INFO     [<base_path>] +Added   FILE: example.txt
2025-07-05 22:59:12,345 INFO     [<base_path>] *Modified DIR : docs/
2025-07-05 22:59:20,123 INFO     [<base_path>] -Removed  FILE: old.log
```

- `+Added`   → created file/dir  
- `*Modified`→ modified timestamp changed  
- `-Removed` → deleted file/dir  

---

## License

Distributed under the GPL License. See [LICENSE](LICENSE) for details.  

---

_Enjoy monitoring your file system with ease!_
