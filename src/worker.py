"""
worker.py — KUS Pro
Универсальный фоновый воркер.

Модули cleanup/network/processes/updates ожидают:
    func(log_func, progress_func, **kwargs)

Модули monitor, elevation — вызываются напрямую, не через Worker.
"""

import traceback
from PyQt5.QtCore import QThread, pyqtSignal


class Worker(QThread):
    line_out  = pyqtSignal(str, str)   # (text, level)
    progress  = pyqtSignal(float)
    result    = pyqtSignal(object)
    finished  = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func   = func
        self._args   = args
        self._kwargs = kwargs
        self._cancel_requested = False

    def request_cancel(self):
        """
        Кооперативная отмена: ставим флаг, поток сам должен его проверять
        (через self.is_cancel_requested() внутри длинного цикла) и выйти
        чисто. В отличие от QThread.terminate(), это не убивает поток
        в произвольной точке — а значит не оставляет открытые файлы/
        хендлы/сокеты в подвешенном состоянии.
        """
        self._cancel_requested = True

    def is_cancel_requested(self):
        return self._cancel_requested

    def run(self):
        def log_func(msg, level="INFO"):
            self.line_out.emit(str(msg), level.upper())

        def progress_func(val):
            try:
                self.progress.emit(float(val))
            except Exception:
                pass

        try:
            ret = self._func(log_func, progress_func, *self._args, **self._kwargs)
            progress_func(1.0)
            if ret is not None:
                self.result.emit(ret)
        except SystemExit:
            pass  # не логируем — это штатный выход
        except Exception as exc:
            log_func("[Ошибка] {}: {}".format(type(exc).__name__, exc), "ERR")
            log_func(traceback.format_exc(), "ERR")
        finally:
            self.finished.emit()
