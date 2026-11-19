"""Bagian yang berbeda per OS: ikon aplikasi, notifikasi, dan pembuatan shortcut."""
import os
import shutil
import subprocess
import sys
import textwrap

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

_tray = None


def app_icon():
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#e0483a"))
    p.drawEllipse(QRectF(10, 22, 108, 100))
    p.setBrush(QColor("#4caf50"))
    p.drawEllipse(QRectF(52, 6, 24, 24))
    p.end()
    return QIcon(pm)


def _get_tray():
    global _tray
    if _tray is None and QSystemTrayIcon.isSystemTrayAvailable():
        _tray = QSystemTrayIcon(app_icon())
        _tray.setToolTip("Pomodoro Labs")
        _tray.show()
    return _tray


def notify(title, body, window=None):
    """Notifikasi sistem lewat tray; kalau tidak ada, kedipkan jendela/ikon taskbar."""
    tray = _get_tray()
    if tray is not None:
        tray.showMessage(title, body, QSystemTrayIcon.Information, 8000)
    if window is not None:
        QApplication.alert(window, 3000)


def launch_command():
    """Perintah untuk menjalankan aplikasi ini dari shortcut."""
    exe = shutil.which("pomodoro-labs")
    return [exe] if exe else [sys.executable, "-m", "pomodoro_labs"]


def install_shortcut():
    """Buat shortcut aplikasi. Mengembalikan teks hasil untuk ditampilkan ke pengguna."""
    cmd = launch_command()
    if sys.platform.startswith("linux"):
        return _shortcut_linux(cmd)
    if sys.platform == "win32":
        return _shortcut_windows(cmd)
    if sys.platform == "darwin":
        return _shortcut_macos(cmd)
    return "OS ini belum didukung untuk pembuatan shortcut."


def _shortcut_linux(cmd):
    line = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    path = os.path.expanduser("~/.local/share/applications/pomodoro-labs.desktop")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
            [Desktop Entry]
            Name=Pomodoro Labs
            Comment=Timer Pomodoro kecil yang selalu di atas jendela lain
            Exec={line}
            Icon=alarm-symbolic
            Terminal=false
            Type=Application
            Categories=Utility;
            Actions=Pomodoro;Manual;

            [Desktop Action Pomodoro]
            Name=Pomodoro manual
            Exec={line} --pomodoro

            [Desktop Action Manual]
            Name=Timer manual
            Exec={line} --manual
            """))
    return f"Shortcut dibuat: {path}"


def _shortcut_windows(cmd):
    menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                        "Start Menu", "Programs")
    lnk = os.path.join(menu, "Pomodoro Labs.lnk")
    target = cmd[0]
    args = " ".join(cmd[1:])
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
          "$s.TargetPath='%s';$s.Arguments='%s';$s.Save()" % (lnk, target, args))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return f"Shortcut dibuat: {lnk}"


def _shortcut_macos(cmd):
    app = os.path.expanduser("~/Applications/Pomodoro Labs.app")
    macos = os.path.join(app, "Contents", "MacOS")
    os.makedirs(macos, exist_ok=True)
    launcher = os.path.join(macos, "pomodoro-labs")
    with open(launcher, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\nexec " + " ".join(f'"{c}"' for c in cmd) + ' "$@"\n')
    os.chmod(launcher, 0o755)
    with open(os.path.join(app, "Contents", "Info.plist"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0"><dict>
            <key>CFBundleName</key><string>Pomodoro Labs</string>
            <key>CFBundleExecutable</key><string>pomodoro-labs</string>
            <key>CFBundleIdentifier</key><string>labs.pomodoro</string>
            <key>CFBundlePackageType</key><string>APPL</string>
            </dict></plist>
            """))
    return f"Aplikasi dibuat: {app}"
