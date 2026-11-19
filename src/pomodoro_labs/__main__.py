"""Titik masuk: `pomodoro-labs` atau `python -m pomodoro_labs`."""
import sys

from . import __version__

USAGE = """Pomodoro Labs - timer kecil yang melayang di atas jendela lain.

Pemakaian:
  pomodoro-labs                  mode otomatis (ikut jadwal kerja)
  pomodoro-labs --manual         timer manual
  pomodoro-labs [menit]          timer manual langsung mulai, contoh: 25 atau 1:30
  pomodoro-labs --pomodoro       Pomodoro manual langsung mulai
  pomodoro-labs --settings       buka Pengaturan saat start
  pomodoro-labs --install-shortcut   buat shortcut aplikasi di OS ini
  pomodoro-labs --version

Seret jendela untuk memindahkan. Klik kanan atau tombol ⚙ untuk Pengaturan.
Esc untuk menutup."""


def _check_linux_deps():
    """Qt 6.5+ di X11 butuh libxcb-cursor0; tanpa itu Qt langsung abort tanpa pesan jelas."""
    import ctypes.util
    import os
    if not sys.platform.startswith("linux"):
        return True
    if os.environ.get("QT_QPA_PLATFORM") not in (None, "", "xcb"):
        return True
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" and os.environ.get("WAYLAND_DISPLAY"):
        return True
    if ctypes.util.find_library("xcb-cursor"):
        return True
    print("Library sistem 'libxcb-cursor0' belum terpasang (dibutuhkan Qt di X11).\n"
          "  Debian/Ubuntu : sudo apt install libxcb-cursor0\n"
          "  Fedora        : sudo dnf install xcb-util-cursor\n"
          "  Arch          : sudo pacman -S xcb-util-cursor", file=sys.stderr)
    return False


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--version" in args:
        print(f"pomodoro-labs {__version__}")
        return 0
    if "--help" in args or "-h" in args:
        print(USAGE)
        return 0

    if "--install-shortcut" in args:
        from . import platform_
        print(platform_.install_shortcut())
        return 0

    if not _check_linux_deps():
        return 1

    from PySide6.QtWidgets import QApplication

    from . import platform_
    from .config import load_config
    from .timer_window import FloatingTimer

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Pomodoro Labs")
    app.setWindowIcon(platform_.app_icon())

    initial = next((a for a in args if not a.startswith("--")), None)
    pomodoro = "--pomodoro" in args
    win = FloatingTimer(load_config(), initial=initial, pomodoro=pomodoro,
                        auto=not (initial or pomodoro or "--manual" in args))
    win.show()
    win.place()
    if "--settings" in args:
        win.open_settings()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
