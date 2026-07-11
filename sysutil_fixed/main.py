"""
main.py
-------
Kus — модульная утилита системного администратора для Windows.

Графическая оболочка на CustomTkinter с фоновым изображением,
боковой навигацией по разделам и панелью лога/прогресса.

Запуск: python main.py
Требует: Windows 10/11, Python 3.10+, пакеты из requirements.txt.
"""

import sys
import math
import threading
import queue
import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image

# --- Модули утилиты -------------------------------------------------------
from modules import cleanup, network, processes, updates, monitor, elevation, extra

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
BACKGROUND_PATH = ASSETS_DIR / "background.jpg"

ctk.set_appearance_mode("dark")

COLOR_BG_PANEL       = "#0B1220"
COLOR_BG_PANEL_ALPHA = "#0B1220"
COLOR_ACCENT         = "#5AA9E6"
COLOR_ACCENT_HOVER   = "#3D8FCF"
COLOR_TEXT_MAIN      = "#E7EEF7"
COLOR_TEXT_DIM       = "#8FA3BD"
COLOR_DANGER         = "#E15554"
COLOR_SUCCESS        = "#4CC9A4"
COLOR_WARN           = "#F4A261"
COLOR_LOG_BG         = "#060A12"
FONT_FAMILY          = "Segoe UI"

# ---------------------------------------------------------------------------
# Волновой Canvas-прогресс-бар
# ---------------------------------------------------------------------------

class WaveProgressBar(tk.Frame):
    """
    Замена CTkProgressBar: рисует сложную многослойную синусоидальную волну
    на tk.Canvas — точно такую же логику, что была в JS-примере пользователя,
    но переведённую в Python/Tkinter.
    """

    BAR_COUNT  = 80
    BAR_RATIO  = 1.25   # ширина бара relative to step
    HEIGHT     = 18

    # Цвета волны (HSL-похожий переход по индексу)
    COLORS_WAVE = [
        "#1A3A5C", "#1E4D7A", "#2265A8", "#2E80D8",
        "#5AA9E6", "#7FC4F5", "#A0D8FF", "#5AA9E6",
        "#2E80D8", "#2265A8", "#1E4D7A", "#1A3A5C",
    ]

    def __init__(self, master, height=None, **kwargs):
        h = height or self.HEIGHT
        # Strip ctk-only kwargs so tk.Frame doesn't reject them
        for k in ("fg_color", "corner_radius", "progress_color"):
            kwargs.pop(k, None)
        super().__init__(master, height=h, bg="#060A12", **kwargs)
        self.configure(bg="#060A12")

        self._canvas = tk.Canvas(self, bg="#060A12", bd=0, highlightthickness=0,
                                 height=h)
        self._canvas.pack(fill="x", expand=True)

        self._time   = 0.0
        self._target = 0.0        # 0..1 — логический прогресс
        self._shown  = 0.0
        self._wave_active = False
        self._job    = None
        self._width  = 0

        self._canvas.bind("<Configure>", self._on_resize)
        self._start_loop()

    def set(self, value: float):
        """Устанавливает прогресс без анимации (совместимость с CTkProgressBar)."""
        self._target = max(0.0, min(1.0, value))
        self._shown  = self._target

    def animate_to(self, value: float):
        """Плавно переходит к новому значению."""
        self._target = max(0.0, min(1.0, value))

    def start_wave(self):
        self._wave_active = True

    def stop_wave(self):
        self._wave_active = False

    def _on_resize(self, event):
        self._width = event.width

    def _start_loop(self):
        self._tick()

    def _tick(self):
        self._draw()
        self._job = self._canvas.after(20, self._tick)   # ~50 fps

    def _draw(self):
        canvas = self._canvas
        w = self._width or canvas.winfo_width() or 400
        h = self.HEIGHT

        # Плавно подводим _shown к _target
        diff = self._target - self._shown
        if abs(diff) > 0.002:
            self._shown += diff * 0.12
        else:
            self._shown = self._target

        # Продвигаем фазу времени
        self._time += 0.035

        canvas.delete("all")

        # Фон
        canvas.create_rectangle(0, 0, w, h, fill="#060A12", outline="")

        # Область прогресса — сколько баров рисуем (proportion)
        prog_width = int(w * max(self._shown, 0.0))
        if prog_width <= 0 and not self._wave_active:
            return

        # Параметры баров
        bar_count = self.BAR_COUNT
        step  = w / bar_count
        bw    = step * self.BAR_RATIO

        t  = self._time
        nc = len(self.COLORS_WAVE)

        for i in range(bar_count):
            x = i * step

            # Рисуем только до края прогресса (или всё при wave_active)
            if not self._wave_active and x > prog_width:
                break

            # Три синусоиды — как в JS-примере
            wave1 = (math.sin((i * 0.02 + t)   * 2.0) * 0.5 + 0.5)
            wave2 = (math.sin((i * 0.015 + t * 1.3) * 2.0) * 0.3 + 0.2)
            wave3 = (math.sin((i * 0.03  + t * 0.7) * 2.0) * 0.2 + 0.1)
            bar_h = (wave1 + wave2 + wave3) * h * 0.75

            # Цвет меняется по синусоиде тоже
            col_idx = int((math.sin(i * 0.08 + t * 0.6) * 0.5 + 0.5) * (nc - 1))
            col = self.COLORS_WAVE[col_idx]

            # Прозрачность края — затухание за границей прогресса
            x1 = x
            x2 = x + bw
            y1 = h - bar_h
            y2 = h
            canvas.create_rectangle(x1, y1, x2, y2, fill=col, outline="")

        # Тонкий светящийся край по линии прогресса
        if not self._wave_active and prog_width > 0:
            glow = "#A0D8FF"
            canvas.create_line(prog_width, 0, prog_width, h, fill=glow, width=2)


# ---------------------------------------------------------------------------
# LogConsole
# ---------------------------------------------------------------------------

class LogConsole(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COLOR_BG_PANEL, corner_radius=14)

        self._queue: "queue.Queue[tuple[str, object]]" = queue.Queue()

        header = ctk.CTkLabel(
            self, text="Журнал выполнения",
            font=(FONT_FAMILY, 14, "bold"), text_color=COLOR_TEXT_MAIN,
        )
        header.pack(anchor="w", padx=16, pady=(12, 4))

        # Волновой прогресс-бар вместо CTkProgressBar
        self.progress = WaveProgressBar(self, height=18)
        self.progress.pack(fill="x", padx=16, pady=(0, 6))

        self._progress_target = 0.0
        self._progress_shown  = 0.0
        self._animating_progress = False

        self.status_label = ctk.CTkLabel(
            self, text="Ожидание команды...",
            font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM, anchor="w",
        )
        self.status_label.pack(fill="x", padx=16)

        self.textbox = ctk.CTkTextbox(
            self, fg_color=COLOR_LOG_BG, text_color=COLOR_TEXT_MAIN,
            font=("Consolas", 12), corner_radius=10, wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self.textbox.configure(state="disabled")

        self.after(80, self._drain_queue)

    def log(self, text: str):
        self._queue.put(("log", text))

    def set_progress(self, value: float):
        self._queue.put(("progress", max(0.0, min(1.0, value))))

    def set_status(self, text: str):
        self._queue.put(("status", text))

    def clear(self):
        self._queue.put(("clear", None))

    def _drain_queue(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self.textbox.configure(state="normal")
                    self.textbox.insert("end", f"{payload}\n")
                    self.textbox.see("end")
                    self.textbox.configure(state="disabled")
                elif kind == "progress":
                    self._progress_target = payload
                    self.progress.animate_to(payload)
                    # Включаем волну пока прогресс не дошёл до 1.0
                    if payload < 0.98:
                        self.progress.start_wave()
                    else:
                        self.progress.stop_wave()
                elif kind == "status":
                    self.status_label.configure(text=payload)
                elif kind == "clear":
                    self.textbox.configure(state="normal")
                    self.textbox.delete("1.0", "end")
                    self.textbox.configure(state="disabled")
                    self._progress_target = 0.0
                    self._progress_shown  = 0.0
                    self.progress.set(0)
                    self.progress.stop_wave()
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)


# ---------------------------------------------------------------------------
# ActionRunner
# ---------------------------------------------------------------------------

class ActionRunner:
    def __init__(self, console: LogConsole):
        self.console = console
        self._busy   = False

    @property
    def busy(self) -> bool:
        return self._busy

    def run(self, label: str, target, *args, on_done=None, **kwargs):
        if self._busy:
            self.console.log(f"[!] Подождите завершения текущей операции, прежде чем запускать «{label}».")
            return

        def wrapper():
            self._busy = True
            self.console.set_status(f"Выполняется: {label}")
            self.console.log(f"\n--- {label} ---")
            try:
                result = target(*args, log_func=self.console.log,
                                progress_func=self.console.set_progress, **kwargs)
            except Exception as exc:
                self.console.log(f"[Ошибка] {exc}")
                result = None
            finally:
                self._busy = False
                self.console.set_status("Готово. Ожидание команды...")
                self.console.set_progress(1.0)
                if on_done:
                    on_done(result)

        threading.Thread(target=wrapper, daemon=True).start()


# ---------------------------------------------------------------------------
# NavButton
# ---------------------------------------------------------------------------

class NavButton(ctk.CTkButton):
    def __init__(self, master, text, command):
        super().__init__(
            master, text=text, command=command,
            fg_color="transparent", hover_color="#16243B",
            text_color=COLOR_TEXT_MAIN, anchor="w",
            font=(FONT_FAMILY, 14), height=42, corner_radius=10,
        )

    def set_active(self, active: bool):
        if active:
            self.configure(fg_color=COLOR_ACCENT, text_color="#08111F",
                           hover_color=COLOR_ACCENT_HOVER)
        else:
            self.configure(fg_color="transparent", text_color=COLOR_TEXT_MAIN,
                           hover_color="#16243B")


# ---------------------------------------------------------------------------
# Базовый класс секции
# ---------------------------------------------------------------------------

class SectionFrame(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(
            self, text=title, font=(FONT_FAMILY, 22, "bold"), text_color=COLOR_TEXT_MAIN,
        ).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(
            self, text=subtitle, font=(FONT_FAMILY, 13), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", pady=(0, 16))


def styled_button(master, text, command, kind="default"):
    palette = {
        "default": (COLOR_ACCENT,   COLOR_ACCENT_HOVER, "#08111F"),
        "danger":  (COLOR_DANGER,   "#C23F3F",          "#FFFFFF"),
        "success": (COLOR_SUCCESS,  "#3AA886",          "#08111F"),
        "warn":    (COLOR_WARN,     "#D4874A",          "#08111F"),
    }
    fg, hover, txt = palette[kind]
    return ctk.CTkButton(
        master, text=text, command=command,
        fg_color=fg, hover_color=hover, text_color=txt,
        font=(FONT_FAMILY, 13, "bold"), height=38, corner_radius=10,
    )


# ---------------------------------------------------------------------------
# AnimatedProgressBar (для монитора)
# ---------------------------------------------------------------------------

class AnimatedProgressBar(ctk.CTkProgressBar):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._shown    = 0.0
        self._target   = 0.0
        self._anim_job = None
        self.set(0)

    def animate_to(self, value: float):
        self._target = max(0.0, min(1.0, value))
        if self._anim_job is None:
            self._step()

    def _step(self):
        diff = self._target - self._shown
        if abs(diff) < 0.004:
            self._shown    = self._target
            super().set(self._shown)
            self._anim_job = None
            return
        self._shown   += diff * 0.18
        super().set(self._shown)
        self._anim_job = self.after(16, self._step)


# ---------------------------------------------------------------------------
# Разделы
# ---------------------------------------------------------------------------

class CleanupSection(SectionFrame):
    def __init__(self, master, runner: ActionRunner):
        super().__init__(master, "Очистка системы",
                         "Temp-файлы, кэш обновлений Windows, корзина и мусор на всех дисках")
        self.runner = runner

        self.include_cache_var    = ctk.BooleanVar(value=True)
        self.include_all_disks_var = ctk.BooleanVar(value=True)
        self.clean_prefetch_var   = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            self, text="Очистить кэш загруженных обновлений Windows",
            variable=self.include_cache_var, text_color=COLOR_TEXT_MAIN,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkCheckBox(
            self, text="Очистить Temp-папки на всех дисках (не только C:\\)",
            variable=self.include_all_disks_var, text_color=COLOR_TEXT_MAIN,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkCheckBox(
            self, text="Очистить Prefetch (ускоряет первый запуск приложений после чистки)",
            variable=self.clean_prefetch_var, text_color=COLOR_TEXT_MAIN,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 16))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w")
        styled_button(row, "🧹  Запустить полную очистку", self._run).pack(side="left", padx=(0, 10))
        styled_button(row, "📊  Оценить объём мусора", self._estimate, kind="warn").pack(side="left")

    def _run(self):
        self.runner.run(
            "Очистка системы",
            cleanup.run_full_cleanup,
            include_update_cache=self.include_cache_var.get(),
            include_all_disks=self.include_all_disks_var.get(),
            clean_prefetch=self.clean_prefetch_var.get(),
        )

    def _estimate(self):
        self.runner.run("Оценка мусора", cleanup.estimate_junk_size)


class NetworkSection(SectionFrame):
    def __init__(self, master, runner: ActionRunner):
        super().__init__(master, "Сетевая диагностика",
                         "Активные соединения, сброс DNS-кэша и стека TCP/IP")
        self.runner = runner

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 16))
        styled_button(row, "Показать соединения",   self._show_connections).pack(side="left", padx=(0, 10))
        styled_button(row, "Сбросить DNS",           self._flush_dns).pack(side="left", padx=(0, 10))
        styled_button(row, "Сбросить стек TCP/IP",   self._reset_stack, kind="danger").pack(side="left")

        self.table = ctk.CTkTextbox(
            self, fg_color=COLOR_LOG_BG, text_color=COLOR_TEXT_MAIN,
            font=("Consolas", 12), corner_radius=10, height=260,
        )
        self.table.pack(fill="both", expand=True)
        self.table.configure(state="disabled")

    def _show_connections(self):
        self.runner.run("Активные соединения", self._fetch_connections)

    def _fetch_connections(self, log_func, progress_func):
        lines = network.list_connections(log_func, progress_func)
        self.after(0, lambda: self._fill_table(lines))

    def _fill_table(self, lines):
        self.table.configure(state="normal")
        self.table.delete("1.0", "end")
        self.table.insert("end", "\n".join(lines) if lines else "Нет данных")
        self.table.configure(state="disabled")

    def _flush_dns(self):
        self.runner.run("Сброс DNS", network.flush_dns)

    def _reset_stack(self):
        self.runner.run("Сброс стека TCP/IP", network.reset_tcp_stack)


class ProcessesSection(SectionFrame):
    def __init__(self, master, runner: ActionRunner):
        super().__init__(master, "Менеджер процессов",
                         "Список запущенных процессов, завершение по PID")
        self.runner = runner

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 10))

        styled_button(row, "🔄  Обновить список", self._refresh).pack(side="left", padx=(0, 10))

        pid_row = ctk.CTkFrame(self, fg_color="transparent")
        pid_row.pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(pid_row, text="PID для завершения:", font=(FONT_FAMILY, 13),
                     text_color=COLOR_TEXT_MAIN).pack(side="left", padx=(0, 8))
        self.pid_entry = ctk.CTkEntry(pid_row, width=100, fg_color=COLOR_LOG_BG,
                                      text_color=COLOR_TEXT_MAIN, border_color=COLOR_ACCENT)
        self.pid_entry.pack(side="left", padx=(0, 10))
        styled_button(pid_row, "⛔  Завершить процесс", self._kill, kind="danger").pack(side="left")

        self.table = ctk.CTkTextbox(
            self, fg_color=COLOR_LOG_BG, text_color=COLOR_TEXT_MAIN,
            font=("Consolas", 11), corner_radius=10, height=240,
        )
        self.table.pack(fill="both", expand=True)
        self.table.configure(state="disabled")

    def _refresh(self):
        self.runner.run("Список процессов", self._fetch)

    def _fetch(self, log_func, progress_func):
        lines = processes.list_processes(log_func, progress_func)
        self.after(0, lambda: self._fill(lines))

    def _fill(self, lines):
        self.table.configure(state="normal")
        self.table.delete("1.0", "end")
        self.table.insert("end", "\n".join(lines) if lines else "Нет данных")
        self.table.configure(state="disabled")

    def _kill(self):
        pid = self.pid_entry.get().strip()
        if not pid.isdigit():
            self.runner.console.log("[!] Введите корректный PID.")
            return
        self.runner.run("Завершение процесса", processes.kill_process, pid=int(pid))


class UpdatesSection(SectionFrame):
    def __init__(self, master, runner: ActionRunner):
        super().__init__(master, "Обновления Windows",
                         "Поиск и установка системных обновлений через Windows Update")
        self.runner = runner

        self.auto_install_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self, text="Автоматически устанавливать найденные обновления",
            variable=self.auto_install_var, text_color=COLOR_TEXT_MAIN,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
        ).pack(anchor="w", pady=(0, 16))

        styled_button(self, "🔍  Проверить обновления", self._run).pack(anchor="w")

    def _run(self):
        self.runner.run(
            "Обновления Windows",
            updates.search_and_install_windows_updates,
            auto_install=self.auto_install_var.get(),
        )


class MonitorSection(SectionFrame):
    def __init__(self, master):
        super().__init__(master, "Мониторинг ресурсов",
                         "Использование CPU, оперативной памяти и дисков в реальном времени")

        self.cpu_label = ctk.CTkLabel(self, text="CPU: —%", font=(FONT_FAMILY, 14),
                                      text_color=COLOR_TEXT_MAIN)
        self.cpu_label.pack(anchor="w", pady=(0, 4))
        self.cpu_bar = AnimatedProgressBar(self, progress_color=COLOR_ACCENT, height=12)
        self.cpu_bar.pack(fill="x", pady=(0, 12))

        self.ram_label = ctk.CTkLabel(self, text="RAM: —%", font=(FONT_FAMILY, 14),
                                      text_color=COLOR_TEXT_MAIN)
        self.ram_label.pack(anchor="w", pady=(0, 4))
        self.ram_bar = AnimatedProgressBar(self, progress_color=COLOR_SUCCESS, height=12)
        self.ram_bar.pack(fill="x", pady=(0, 12))

        self.disks_frame  = ctk.CTkFrame(self, fg_color="transparent")
        self.disks_frame.pack(fill="x", pady=(8, 0))
        self._disk_widgets = {}

        self._running = True
        self._tick()

    def _tick(self):
        if not self._running:
            return
        threading.Thread(target=self._collect_and_update, daemon=True).start()
        self.after(1500, self._tick)

    def _collect_and_update(self):
        snap = monitor.get_snapshot()
        if self._running:
            self.after(0, lambda: self._apply_snapshot(snap))

    def _apply_snapshot(self, snap):
        if not self._running:
            return
        self.cpu_label.configure(text=f"CPU: {snap['cpu_percent']:.0f}%")
        self.cpu_bar.animate_to(snap["cpu_percent"] / 100)
        self.ram_label.configure(
            text=f"RAM: {snap['ram_percent']:.0f}%  ({snap['ram_used_gb']} / {snap['ram_total_gb']} ГБ)"
        )
        self.ram_bar.animate_to(snap["ram_percent"] / 100)
        for disk in snap["disks"]:
            dev = disk["device"]
            if dev not in self._disk_widgets:
                label = ctk.CTkLabel(self.disks_frame, text="", font=(FONT_FAMILY, 13),
                                     text_color=COLOR_TEXT_MAIN)
                label.pack(anchor="w", pady=2)
                bar = AnimatedProgressBar(self.disks_frame, progress_color=COLOR_ACCENT, height=10)
                bar.pack(fill="x", pady=(0, 8))
                self._disk_widgets[dev] = (label, bar)
            label, bar = self._disk_widgets[dev]
            label.configure(text=f"Диск {dev}  {disk['percent']:.0f}%  "
                                  f"({disk['used_gb']:.0f} / {disk['total_gb']:.0f} ГБ)")
            bar.animate_to(disk["percent"] / 100)

    def stop(self):
        self._running = False


# ---------------------------------------------------------------------------
# ExtraSection — Обход блокировок (Zapret)
# ---------------------------------------------------------------------------

class ExtraSection(SectionFrame):
    def __init__(self, master, runner: ActionRunner):
        super().__init__(master, "Обход блокировок (Zapret)",
                         "Управление сервисом Zapret — обход блокировок Discord, YouTube и других сайтов")
        self.runner = runner

        # ── Версии ────────────────────────────────────────────────────
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", pady=(0, 10))

        versions = extra.list_available_versions()
        self.version_combo = ctk.CTkComboBox(
            row, values=versions or ["нет версий"], width=260,
            fg_color=COLOR_LOG_BG, text_color=COLOR_TEXT_MAIN,
            border_color=COLOR_ACCENT, button_color=COLOR_ACCENT,
        )
        current = extra.get_current_version_dir()
        if current:
            self.version_combo.set(current.name)
        self.version_combo.pack(side="left", padx=(0, 10))
        styled_button(row, "Сделать активной", self._switch_version,
                      kind="success").pack(side="left", padx=(0, 10))

        # ── Кнопки управления ────────────────────────────────────────
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(anchor="w", pady=(0, 16))

        self.btn_run  = styled_button(row2, "▶  Запустить",   self._run,  kind="success")
        self.btn_run.pack(side="left", padx=(0, 10))

        self.btn_stop = styled_button(row2, "⏹  Остановить", self._stop, kind="danger")
        self.btn_stop.pack(side="left", padx=(0, 10))
        self.btn_stop.configure(state="disabled")

        self.status_lbl = ctk.CTkLabel(
            row2, text="● Сервис не запущен",
            font=(FONT_FAMILY, 13), text_color=COLOR_TEXT_DIM,
        )
        self.status_lbl.pack(side="left", padx=(10, 0))

        # ── Инструкция ───────────────────────────────────────────────
        guide_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_PANEL, corner_radius=10)
        guide_frame.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(
            guide_frame, text="📋  Как обновить Zapret до новой версии",
            font=(FONT_FAMILY, 13, "bold"), text_color=COLOR_ACCENT, anchor="w",
        ).pack(anchor="w", padx=14, pady=(10, 4))

        steps = (
            "1. Скачайте новую версию с https://github.com/Flowseal/zapret-discord-youtube",
            "2. Распакуйте архив в папку  sysutil/zapret/<имя-новой-версии>/",
            "3. Убедитесь, что в папке есть файл  service.bat",
            "4. Откройте файл  sysutil/zapret/current_version.txt",
            "5. Замените содержимое на точное имя новой папки и сохраните файл",
            "6. Выберите новую версию в списке выше → «Сделать активной» → «Запустить»",
        )
        for step in steps:
            ctk.CTkLabel(
                guide_frame, text=step,
                font=(FONT_FAMILY, 12), text_color=COLOR_TEXT_DIM, anchor="w",
                wraplength=700, justify="left",
            ).pack(anchor="w", padx=14, pady=1)
        ctk.CTkLabel(guide_frame, text="", height=8).pack()

    def _switch_version(self):
        extra.set_current_version(self.version_combo.get(), self.runner.console.log)

    def _run(self):
        self._set_running(True)
        self.runner.run("Запуск Zapret", extra.run_service_bat,
                        on_done=lambda _: self._set_running(False))

    def _stop(self):
        extra.stop_service(self.runner.console.log)
        self._set_running(False)

    def _set_running(self, running: bool):
        if running:
            self.btn_run.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.status_lbl.configure(text="● Сервис работает", text_color=COLOR_SUCCESS)
        else:
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.status_lbl.configure(text="● Сервис не запущен", text_color=COLOR_TEXT_DIM)


# ---------------------------------------------------------------------------
# Главное окно
# ---------------------------------------------------------------------------

class SysUtilApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kus — утилита системного администратора")
        self.geometry("1180x720")
        self.minsize(1000, 640)

        self._setup_background()

        self.overlay = ctk.CTkFrame(self, fg_color="#0A1018", corner_radius=0)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.sidebar = self._build_sidebar(self.overlay)
        self.sidebar.pack(side="left", fill="y")

        self.content = ctk.CTkFrame(self.overlay, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=24, pady=24)

        self.body = ctk.CTkFrame(self.content, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        self.console_holder = ctk.CTkFrame(self.content, fg_color="transparent", height=230)
        self.console_holder.pack(fill="x", pady=(16, 0))
        self.console = LogConsole(self.console_holder)
        self.console.pack(fill="both", expand=True)

        self.runner = ActionRunner(self.console)

        self.sections: dict[str, SectionFrame] = {}
        self._build_sections()
        self._show_section("cleanup")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_background(self):
        if BACKGROUND_PATH.exists():
            self._bg_source = Image.open(BACKGROUND_PATH)
            self._bg_image  = ctk.CTkImage(
                light_image=self._bg_source, dark_image=self._bg_source,
                size=(1180, 720),
            )
            self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_image)
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._resize_job = None
            self.bind("<Configure>", self._on_configure)
        else:
            self.bg_label = None

    def _on_configure(self, event):
        if self.bg_label is None:
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(
            150, lambda: self._resize_background(event.width, event.height)
        )

    def _resize_background(self, width, height):
        w, h = max(width, 100), max(height, 100)
        self._bg_image = ctk.CTkImage(
            light_image=self._bg_source, dark_image=self._bg_source, size=(w, h)
        )
        self.bg_label.configure(image=self._bg_image)
        self._resize_job = None

    def _build_sidebar(self, master):
        sidebar = ctk.CTkFrame(master, width=240, fg_color=COLOR_BG_PANEL, corner_radius=0)

        ctk.CTkLabel(
            sidebar, text="Kus",
            font=(FONT_FAMILY, 24, "bold"), text_color=COLOR_TEXT_MAIN,
        ).pack(anchor="w", padx=20, pady=(24, 0))
        ctk.CTkLabel(
            sidebar, text="Панель сетевого администратора",
            font=(FONT_FAMILY, 11), text_color=COLOR_TEXT_DIM,
        ).pack(anchor="w", padx=20, pady=(0, 24))

        self.nav_buttons: dict[str, NavButton] = {}
        nav_items = [
            ("cleanup",   "🧹  Очистка системы"),
            ("network",   "🌐  Сетевая диагностика"),
            ("processes", "⚙️  Менеджер процессов"),
            ("updates",   "🔄  Обновления Windows"),
            ("monitor",   "📊  Мониторинг ресурсов"),
            ("extra",     "🛡️  Обход блокировок"),
        ]

        for key, label in nav_items:
            btn = NavButton(sidebar, label, command=lambda k=key: self._show_section(k))
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[key] = btn

        ctk.CTkLabel(
            sidebar, text="🛡 Запущено с правами администратора",
            font=(FONT_FAMILY, 10), text_color=COLOR_SUCCESS,
            wraplength=200, justify="left",
        ).pack(side="bottom", padx=20, pady=20, anchor="w")

        return sidebar

    def _build_sections(self):
        self.sections["cleanup"]   = CleanupSection(self.body, self.runner)
        self.sections["network"]   = NetworkSection(self.body, self.runner)
        self.sections["processes"] = ProcessesSection(self.body, self.runner)
        self.sections["updates"]   = UpdatesSection(self.body, self.runner)
        self.sections["monitor"]   = MonitorSection(self.body)
        self.sections["extra"]     = ExtraSection(self.body, self.runner)

    def _show_section(self, key: str):
        for k, frame in self.sections.items():
            frame.pack_forget()
            self.nav_buttons[k].set_active(k == key)
        target = self.sections[key]
        target.pack(fill="both", expand=True)
        self._animate_section_in(target)

    def _animate_section_in(self, frame, step=0):
        steps = 6
        if step > steps:
            frame.pack_configure(pady=0)
            return
        offset = int((steps - step) * 4)
        frame.pack_configure(pady=(offset, 0))
        self.after(18, lambda: self._animate_section_in(frame, step + 1))

    def _on_close(self):
        mon = self.sections.get("monitor")
        if mon:
            mon.stop()
        self.destroy()


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    if "--silent-update-check" in sys.argv:
        def _noop(_): pass
        updates.search_and_install_windows_updates(_noop, _noop, auto_install=True)
        return

    app = SysUtilApp()
    app.mainloop()


if __name__ == "__main__":
    if "--silent-update-check" not in sys.argv and not elevation.is_admin():
        try:
            elevation.relaunch_as_admin()
        except OSError:
            print("Пользователь отклонил запрос прав администратора.")
    main()
