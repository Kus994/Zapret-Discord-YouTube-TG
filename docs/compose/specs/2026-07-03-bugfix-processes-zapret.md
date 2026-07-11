# Bug Fix: Processes CPU Color Logic & Zapret Worker Usage

> [!NOTE]
> This document may not reflect the current implementation.
> See the final report for up-to-date state:
> [Final Report](../reports/processes-redesign.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix inverted CPU color thresholds in the Processes page table and eliminate direct Worker instantiation in page_zapret.py, ensuring all background tasks go through the BasePage._run_worker management layer.

**Architecture:** Two isolated bug fixes — one threshold tweak in a UI color expression, one callback-signature fix across three call sites in page_zapret.py.

**Tech Stack:** Python 3.8.10, PyQt5, psutil

---

## Global Constraints

- Python 3.8.10 — no walrus operator in places where it hurts readability, no f-string `=` debugging
- PyQt5 — all Worker lifecycle managed via `BasePage._run_worker`
- Russian language UI (all user-facing strings in Russian)

---

## S1. Bug: CPU color thresholds in page_processes.py are too aggressive

**Location:** `page_processes.py:441`

**Problem:** The CPU column color in the process table uses thresholds `>50` for red and `>20` for yellow. This means any process using >20% CPU shows yellow and >50% shows red. Normal desktop usage triggers these colors constantly, making the table visually noisy and misleading.

**Fix:** Raise thresholds to `>80` (red) and `>50` (yellow). Low CPU stays green-ish gray.

```python
# BEFORE (line 441):
c = "#e05252" if cpu > 50 else "#f5c842" if cpu > 20 else "#a0a8b0"

# AFTER:
c = "#e05252" if cpu > 80 else "#f5c842" if cpu > 50 else "#a0a8b0"
```

## S2. Bug: page_zapret.py passes on_done callbacks that don't match Worker.finished signature

**Location:** `page_zapret.py:1145, 1251, 1256`

**Problem:** `_run_worker` connects `Worker.finished` → `on_done`. `Worker.finished` is `pyqtSignal()` (zero arguments). `_refresh_badge(self)` expects zero args — but `on_done` must accept one arg because `finished` emits nothing and Python/Qt signal dispatch can pass `None`. If the signal machinery sends anything, `_refresh_badge` crashes with a TypeError.

**Fix:** Wrap `_refresh_badge` with `lambda: self._refresh_badge()` at all three call sites:

- Line 1145: `on_done=self._refresh_badge` → `on_done=lambda: self._refresh_badge()`
- Line 1251: `on_done=self._refresh_badge` → `on_done=lambda: self._refresh_badge()`
- Line 1256: `on_done=self._refresh_badge` → `on_done=lambda: self._refresh_badge()`

---

## Appendix: Files Affected

| File | Change |
|------|--------|
| `page_processes.py:441` | CPU color thresholds `50/20` → `80/50` |
| `page_zapret.py:1145` | Wrap `on_done` callback |
| `page_zapret.py:1251` | Wrap `on_done` callback |
| `page_zapret.py:1256` | Wrap `on_done` callback |

## Appendix: Other Pages Reviewed (No Bugs Found)

| Page | Status |
|------|--------|
| `page_tg_proxy.py` | Clean — uses BasePage._run_worker correctly |
| `page_network.py` | Clean — uses BasePage._run_worker correctly |
| `page_monitor.py` | Clean — uses QTimer directly, no Worker |
| `page_cleanup.py` | Clean — uses BasePage._run_worker correctly |
| `page_updates.py` | Clean — uses BasePage._run_worker correctly |
| `page_game_mode.py` | Clean — uses BasePage._run_worker correctly |
| `page_security.py` | Clean — uses BasePage._run_worker correctly |
| `page_timetrack.py` | Clean — uses QTimer directly, no Worker |
| `page_settings.py` | Clean — no background tasks |
