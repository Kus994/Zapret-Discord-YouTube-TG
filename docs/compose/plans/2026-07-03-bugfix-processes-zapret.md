# Bug Fix: Processes CPU Color Logic & Zapret Worker Usage — Implementation Plan

> [!NOTE]
> This document may not reflect the current implementation.
> See the final report for up-to-date state:
> [Final Report](../reports/processes-redesign.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two isolated bugs — inverted CPU color thresholds in Processes page and unsafe Worker callback usage in Zapret page.

**Architecture:** Two independent single-line fixes in separate files. No cross-file dependencies. No new files created.

**Tech Stack:** Python 3.8.10, PyQt5

## Global Constraints

- Python 3.8.10
- PyQt5 — all Worker lifecycle via BasePage._run_worker
- Russian language UI

---

### Task 1: Fix CPU color thresholds in Processes page table

**Covers:** S1

**Files:**
- Modify: `page_processes.py:441, 443`

**Interfaces:**
- Consumes: `cpu` (float, 0-100 normalized CPU percent)
- Produces: colored QTableWidgetItem foreground

**Rationale:** The current thresholds (`>50` red, `>20` yellow) are too aggressive. Windows 11 Task Manager uses higher thresholds. Raising to `>80` / `>50` reduces visual noise.

- [ ] **Step 1: Read the current lines to confirm context**

Read `page_processes.py` lines 438-445:

```python
                    elif col == 3:
                        c = "#e05252" if cpu > 50 else "#f5c842" if cpu > 20 else "#a0a8b0"
                        item.setForeground(QColor(c))
                        if cpu > 20:
                            item.setFont(bold)
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        item.setData(Qt.UserRole, cpu)
```

- [ ] **Step 2: Apply the fix**

Edit `page_processes.py` line 441 — change thresholds:

```python
# OLD:
c = "#e05252" if cpu > 50 else "#f5c842" if cpu > 20 else "#a0a8b0"
# ...
if cpu > 20:

# NEW:
c = "#e05252" if cpu > 80 else "#f5c842" if cpu > 50 else "#a0a8b0"
# ...
if cpu > 50:
```

Both lines must be changed — the color thresholds AND the bold-font threshold must match.

- [ ] **Step 3: Verify no other references to the old thresholds**

Search `page_processes.py` for `cpu > 50` and `cpu > 20` — confirm the only occurrences are on lines 441 and 443.

- [ ] **Step 4: Commit**

```bash
git add page_processes.py
git commit -m "fix: raise CPU color thresholds in process table from 20/50 to 50/80"
```

---

### Task 2: Fix Worker callback signature in page_zapret.py

**Covers:** S2

**Status:** Already applied in outer `page_zapret.py`. The three `on_done=self._refresh_badge` call sites (lines 1145, 1251, 1256) now use `_run_worker` and `_refresh_badge` already references `self._worker` from BasePage. No code changes needed — this task is reused as-is.

**Files:**
- `page_zapret.py:1145, 1251, 1256` — verified clean

**Verification:** Confirm no direct `Worker(` instantiation remains in the outer file. Only `DownloadWorker(` at line 1216 is expected (download uses a different worker class).

- [ ] **Step 1: Verify outer page_zapret.py has no direct Worker() calls**

Run: `grep "Worker(" page_zapret.py`
Expected: Only `DownloadWorker(` match, no bare `Worker(`

- [ ] **Step 2: Verify _refresh_badge uses self._worker**

Read `page_zapret.py` line 1258-1260:
```python
    def _refresh_badge(self):
        running  = _is_running()
        starting = self._worker is not None and self._worker.isRunning()
```
Expected: Uses `self._worker` (BasePage), not `self._start_w` / `self._stop_w`.

- [ ] **Step 3: No commit needed — verified clean**
