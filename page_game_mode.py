"""
page_game_mode.py — KUS Pro
Страница «Игровой режим»: быстрое переключение между набором фоновых
приложений (закрыть перед игрой / вернуть после) с настраиваемым
списком программ и их путей.

Список приложений и пути хранятся в config.json (секция "game_mode"),
поэтому страница не привязана к чужому диску/имени пользователя —
каждый прописывает свои пути через кнопку «Обзор».
"""

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QCheckBox,
    QPushButton, QFrame, QMessageBox, QFileDialog, QScrollArea,
    QWidget, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer

from base_page import BasePage
from config_manager import load_config, save_config
from qt_compat import *
from modules.game_mode import EXTRA_KILL_ONLY


def _load_game_mode_cfg():
    cfg = load_config()
    gm_cfg = cfg.get("game_mode", {})
    apps = gm_cfg.get("apps")
    if not apps:
        from modules.game_mode import DEFAULT_APPS
        apps = [dict(a) for a in DEFAULT_APPS]
    return {
        "apps": apps,
        "disable_transparency": gm_cfg.get("disable_transparency", True),
        "enable_taskbar_autohide": gm_cfg.get("enable_taskbar_autohide", True),
        "auto_return_enabled": gm_cfg.get("auto_return_enabled", False),
        "auto_return_minutes": gm_cfg.get("auto_return_minutes", 60),
        "hotkey": gm_cfg.get("hotkey", ""),
    }


def _save_game_mode_cfg(gm_cfg):
    cfg = load_config()
    cfg["game_mode"] = gm_cfg
    save_config(cfg)


def _fn_activate(log_func, progress_func, apps, disable_transparency, enable_taskbar_autohide):
    from modules.game_mode import activate_game_mode
    from modules.action_log import log_action
    result = activate_game_mode(
        log_func, progress_func, apps=apps, extra_kill_only=EXTRA_KILL_ONLY,
        disable_transparency=disable_transparency,
        enable_taskbar_autohide=enable_taskbar_autohide,
    )
    closed = result.get("closed", [])
    log_action("game_mode", "Активация игрового режима: закрыто {} приложений".format(len(closed)))
    return result


def _fn_deactivate(log_func, progress_func, apps, enable_transparency, disable_taskbar_autohide):
    from modules.game_mode import deactivate_game_mode
    return deactivate_game_mode(
        log_func, progress_func, apps=apps,
        enable_transparency=enable_transparency,
        disable_taskbar_autohide=disable_taskbar_autohide,
    )


class _AppRow(QFrame):
    """Одна строка настройки приложения: чекбокс + путь + «Обзор»."""

    def __init__(self, app_cfg, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        self._enabled = QCheckBox()
        self._enabled.setChecked(app_cfg.get("enabled", True))
        lay.addWidget(self._enabled)

        lbl = QLabel(app_cfg["label"])
        lbl.setFixedWidth(150)
        lbl.setStyleSheet("color:#e8ddd0; font-size:12px; background:transparent;")
        lay.addWidget(lbl)

        self._path = QLineEdit(app_cfg.get("path", ""))
        self._path.setPlaceholderText("Путь к .exe (не обязателен для закрытия процесса)")
        lay.addWidget(self._path, 1)

        b_browse = QPushButton("…")
        b_browse.setFixedWidth(30)
        b_browse.clicked.connect(self._browse)
        lay.addWidget(b_browse)

        self._process = app_cfg["process"]
        self._label = app_cfg["label"]

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл — {}".format(self._label),
            "", "Исполняемые файлы (*.exe);;Все файлы (*.*)"
        )
        if path:
            self._path.setText(path)

    def to_dict(self):
        return {
            "label": self._label,
            "process": self._process,
            "path": self._path.text().strip(),
            "enabled": self._enabled.isChecked(),
        }


class GameModePage(BasePage):
    PAGE_TITLE = "🎮  Игровой режим"
    PAGE_SUB   = "Быстрое закрытие фоновых программ перед игрой и их возврат после"

    def build_ui(self):
        cfg = _load_game_mode_cfg()

        info = QLabel(
            "Включение игрового режима закроет отмеченные ниже приложения,\n"
            "отключит прозрачность окон и включит авто-скрытие панели задач.\n"
            "«Обычный режим» запустит их обратно по указанным путям."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#6a6258; font-size:11px; background:transparent;")
        self._content.addWidget(info)

        # ── Список приложений (со скроллом, на случай если их много) ── #
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setFixedHeight(230)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(6)
        inner_lay.setContentsMargins(0, 0, 4, 0)

        self._rows = []
        for app_cfg in cfg["apps"]:
            row = _AppRow(app_cfg)
            inner_lay.addWidget(row)
            self._rows.append(row)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        self._content.addWidget(scroll)

        # ── Доп. опции ──────────────────────────────────────────────── #
        from widgets import GalahhadToggle
        opt_row = QHBoxLayout()
        self._cb_transparency = GalahhadToggle("Управлять прозрачностью окон")
        self._cb_transparency.setChecked(cfg["disable_transparency"])
        opt_row.addWidget(self._cb_transparency)

        self._cb_taskbar = GalahhadToggle("Управлять авто-скрытием панели задач")
        self._cb_taskbar.setChecked(cfg["enable_taskbar_autohide"])
        opt_row.addWidget(self._cb_taskbar)
        opt_row.addStretch()
        self._content.addLayout(opt_row)

        # ── Таймер автовозврата ─────────────────────────────────────── #
        timer_row = QHBoxLayout()
        self._cb_auto_return = GalahhadToggle("Автоматически вернуть обычный режим через")
        self._cb_auto_return.setChecked(cfg.get("auto_return_enabled", False))
        self._cb_auto_return.stateChanged.connect(self._on_auto_return_toggled)
        timer_row.addWidget(self._cb_auto_return)

        self._auto_return_minutes = QSpinBox()
        self._auto_return_minutes.setRange(5, 360)
        self._auto_return_minutes.setSingleStep(5)
        self._auto_return_minutes.setValue(cfg.get("auto_return_minutes", 60))
        self._auto_return_minutes.setSuffix(" мин")
        timer_row.addWidget(self._auto_return_minutes)
        timer_row.addStretch()
        self._content.addLayout(timer_row)

        self._auto_return_status = QLabel("")
        self._auto_return_status.setStyleSheet("color:#f5a623; font-size:11px; background:transparent;")
        self._content.addWidget(self._auto_return_status)

        self._auto_return_timer = QTimer(self)
        self._auto_return_timer.setSingleShot(True)
        self._auto_return_timer.timeout.connect(self._on_auto_return_fired)

        # ── Глобальная горячая клавиша ──────────────────────────────── #
        hotkey_row = QHBoxLayout()
        hotkey_row.addWidget(QLabel("Глобальная горячая клавиша (переключение режима):"))
        self._hotkey_edit = QLineEdit(cfg.get("hotkey", ""))
        self._hotkey_edit.setPlaceholderText("например: Ctrl+Alt+G")
        self._hotkey_edit.setFixedWidth(160)
        hotkey_row.addWidget(self._hotkey_edit)

        hk_hint = QLabel("Требует перезапуска приложения после изменения.")
        hk_hint.setStyleSheet("color:#6a6258; font-size:10px; background:transparent;")
        hotkey_row.addWidget(hk_hint)
        hotkey_row.addStretch()
        self._content.addLayout(hotkey_row)

        # Отслеживает, активен ли сейчас игровой режим — используется
        # глобальным хоткеем (MainWindow), чтобы понять, что переключать.
        self._is_active = False

        # ── Кнопки сохранения и запуска ─────────────────────────────── #
        btn_row = QHBoxLayout()
        b_save = self.btn("💾  Сохранить настройки", obj="btn_sec")
        b_save.clicked.connect(self._save)
        btn_row.addWidget(b_save)
        btn_row.addStretch()
        self._content.addLayout(btn_row)

        action_row = QHBoxLayout()
        b_on = self._reg_btn(self.btn("🎮  Включить игровой режим"))
        b_on.setStyleSheet(
            "background: #00ff88; color: #0a0e14; font-weight: 700; "
            "font-size: 14px; border-radius: 10px; border: none; padding: 12px 32px;"
        )
        b_on.clicked.connect(self._activate)
        action_row.addWidget(b_on)

        b_off = self._reg_btn(self.btn("🖥  Вернуть обычный режим"))
        b_off.setStyleSheet(
            "background: rgba(0,255,136,0.15); color: #00ff88; font-weight: 700; "
            "font-size: 13px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.25); padding: 10px 24px;"
        )
        b_off.clicked.connect(self._deactivate)
        action_row.addWidget(b_off)
        action_row.addStretch()
        self._content.addLayout(action_row)
        self._content.addStretch()

    def _collect_apps(self, only_enabled=True):
        apps = [r.to_dict() for r in self._rows]
        if only_enabled:
            apps = [a for a in apps if a.get("enabled", True)]
        return apps

    def _save(self):
        apps_all = [r.to_dict() for r in self._rows]
        hotkey = self._hotkey_edit.text().strip()

        if hotkey:
            from modules.hotkeys import parse_hotkey

            if parse_hotkey(hotkey) is None:
                self.log(
                    "Горячая клавиша «{}» не распознана и не будет сохранена. "
                    "Используйте формат вида Ctrl+Alt+G.".format(hotkey), "WARN"
                )
                hotkey = ""

        _save_game_mode_cfg({
            "apps": apps_all,
            "disable_transparency": self._cb_transparency.isChecked(),
            "enable_taskbar_autohide": self._cb_taskbar.isChecked(),
            "auto_return_enabled": self._cb_auto_return.isChecked(),
            "auto_return_minutes": self._auto_return_minutes.value(),
            "hotkey": hotkey,
        })
        self.log("Настройки игрового режима сохранены.", "OK")

    def _activate(self):
        if QMessageBox.question(
            self, "Игровой режим",
            "Закрыть отмеченные приложения и включить игровой режим?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._do_activate()

    def _do_activate(self):
        """Включает игровой режим без диалога подтверждения — используется
        и кнопкой (после явного QMessageBox.question выше), и глобальным
        хоткеем (где модальный диалог сделал бы хоткей бесполезным —
        пользователь жмёт комбинацию именно чтобы не лезть в окно)."""
        apps = self._collect_apps(only_enabled=True)
        self._save()
        self._run_worker(
            _fn_activate, apps,
            disable_transparency=self._cb_transparency.isChecked(),
            enable_taskbar_autohide=self._cb_taskbar.isChecked(),
        )
        self._arm_auto_return()
        self._is_active = True

    def _deactivate(self):
        if QMessageBox.question(
            self, "Обычный режим",
            "Вернуть обычный режим?\nЗапустить отмеченные приложения обратно.",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self._do_deactivate()

    def _do_deactivate(self):
        apps = self._collect_apps(only_enabled=True)
        missing_paths = [a["label"] for a in apps if not a.get("path")]
        if missing_paths:
            self.log(
                "Без указанного пути не будут запущены: {}".format(", ".join(missing_paths)),
                "WARN"
            )
        self._save()
        self._run_worker(
            _fn_deactivate, apps,
            enable_transparency=self._cb_transparency.isChecked(),
            disable_taskbar_autohide=self._cb_taskbar.isChecked(),
        )
        self._disarm_auto_return()
        self._is_active = False

    # ── Таймер автовозврата ─────────────────────────────────────────── #
    def _on_auto_return_toggled(self, _state):
        if self._is_active:
            if self._cb_auto_return.isChecked():
                self._arm_auto_return()
            else:
                self._disarm_auto_return()

    def _arm_auto_return(self):
        if not self._cb_auto_return.isChecked():
            self._auto_return_status.setText("")
            return
        minutes = self._auto_return_minutes.value()
        self._auto_return_timer.start(minutes * 60 * 1000)
        self._auto_return_status.setText(
            "⏱  Обычный режим будет включён автоматически через {} мин.".format(minutes)
        )

    def _disarm_auto_return(self):
        if self._auto_return_timer.isActive():
            self._auto_return_timer.stop()
        self._auto_return_status.setText("")

    def _on_auto_return_fired(self):
        self.log("Время истекло — автоматическое возвращение в обычный режим.", "OK")
        self._auto_return_status.setText("")
        self._do_deactivate()

