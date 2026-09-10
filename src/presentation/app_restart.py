import os
import subprocess
import sys

from PySide6.QtWidgets import QApplication


def restart_app() -> None:
    """Relaunch the app as a new process, then quit the current one.

    Works both for a normal `python src/main.py` dev run and for a
    PyInstaller onefile build (sys.frozen=True, sys.executable is the
    bundled binary itself - it must not also be passed as an argument).
    """
    if getattr(sys, "frozen", False):
        args = [sys.executable] + sys.argv[1:]
    else:
        args = [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:]

    subprocess.Popen(args)

    app = QApplication.instance()
    if app is not None:
        app.quit()
