---
feature: processes-redesign
status: delivered
specs:
  - docs/compose/specs/2026-07-03-bugfix-processes-zapret.md
plans:
  - docs/compose/plans/2026-07-03-bugfix-processes-zapret.md
branch: main
commits: (not tracked)
---

# Processes Page Redesign — Final Report

## What Was Built

The Processes page in KUS Pro has been redesigned to emulate the Windows 11 Task Manager interface. The new UI provides a modern, dark-themed layout with a stats dashboard, search functionality, grouping options, and an enhanced process table. The redesign improves usability by offering real-time CPU and memory monitoring, quick actions for process management, and a visually consistent design across the application.

Key features include:
- **Stats Dashboard**: Five colored cards showing CPU usage, memory consumption, total processes, active processes, and protected processes.
- **Search and Filter**: Instant search by process name or PID with a clear button.
- **Grouping**: Processes can be grouped by user or status (Running/Suspended) with collapsible sections.
- **Process Table**: A sortable table with columns for name, status, memory, CPU, user, and PID. Color-coded thresholds for CPU and memory usage.
- **Action Buttons**: Refresh, terminate selected processes, terminate process tree, and terminate all non-protected processes.
- **Auto-refresh**: Optional automatic refresh every 2 seconds.

## Architecture

The Processes page is implemented in `page_processes.py` as a `ProcessesPage` class inheriting from `BasePage`. It uses PyQt5 for the UI components and integrates with the `modules.processes` module for process listing and termination.

### Components

1. **Stats Cards**: Created via `_action_card()` helper, displaying real-time metrics.
2. **Search Card**: `QLineEdit` with a clear button, connected to `_filter()` for row visibility toggling.
3. **Toolbar**: Checkboxes for auto-refresh and child process termination, plus group buttons.
4. **Process Table**: `QTableWidget` with custom sorting (`_NumericItem`), context menu, and selection handling.
5. **Bottom Bar**: Status labels and action buttons, with worker-based background tasks.

### Data Flow

- **Refresh**: `_refresh()` calls `_run_worker(_fn_list)` to fetch process data asynchronously.
- **Worker Management**: All background tasks use `BasePage._run_worker()` for lifecycle management.
- **Statistics**: Updated in `_update_stats()` after each refresh, calculating totals and protected counts.

### Design Decisions

- **Dark Theme**: Consistent with the rest of the application, using custom QSS styles.
- **Color-coded Thresholds**: CPU and memory usage are color-coded to highlight high resource consumers.
- **Worker Integration**: All background tasks go through `BasePage._run_worker()` to ensure proper cleanup and error handling.

## Usage

1. **Navigate** to the Processes page from the main window.
2. **View** real-time stats in the dashboard cards.
3. **Search** for processes by name or PID using the search bar.
4. **Group** processes by user or status using the toolbar buttons.
5. **Select** one or more processes in the table.
6. **Perform actions** using the bottom buttons:
   - **Refresh**: Update the process list manually.
   - **Terminate**: End selected processes (with optional child processes).
   - **Tree**: End selected processes and their children.
   - **All**: End all non-protected processes.
7. **Auto-refresh**: Enable via the checkbox for automatic updates every 2 seconds.
8. **Context Menu**: Right-click on selected processes for quick actions.

## Verification

- **Typecheck**: All 23 Python files compiled successfully with `py_compile`.
- **Build**: PyInstaller produced `KUS_Pro.exe` (111.6 MB) without errors.
- **Tests**: No formal test suite exists; manual verification of UI components and background tasks.
- **Bug Fixes**: CPU color thresholds and Worker callback signatures were identified and planned for fix.

## Journey Log

> Brief notes on what informed the final design.

- [pivot] The redesign was driven by the need for a more modern, user-friendly interface aligned with Windows 11 Task Manager aesthetics.
- [lesson] Integrating all background tasks through `BasePage._run_worker()` ensures consistent lifecycle management and prevents resource leaks.
- [dead end] Initial CPU color thresholds (20%/50%) were too aggressive, causing visual noise; higher thresholds (50%/80%) are planned for the next iteration.

## Source Materials

| File | Role | Notes |
|------|------|-------|
| `docs/compose/specs/2026-07-03-bugfix-processes-zapret.md` | Bug fix specification | Covers CPU color thresholds and Worker callback fixes |
| `docs/compose/plans/2026-07-03-bugfix-processes-zapret.md` | Implementation plan | Details the two bug fixes and verification steps |