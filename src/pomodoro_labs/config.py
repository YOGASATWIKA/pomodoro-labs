"""Pengaturan: nilai bawaan, lokasi berkas per OS, muat/simpan, dan migrasi dari versi GTK."""
import copy
import json
import os
import shutil
import sys

APP = "pomodoro-labs"
LEGACY_APP = "timer-melayang"

DEFAULTS = {
    # hari (0=Senin ... 6=Minggu) -> blok kerja [jam mulai, jam selesai].
    # Jeda di antara blok dianggap istirahat siang.
    "schedule": {
        "0": [["09:00", "12:30"], ["13:30", "18:00"]],
        "1": [["09:00", "12:30"], ["13:30", "18:00"]],
        "2": [["09:00", "12:30"], ["13:30", "18:00"]],
        "3": [["09:00", "12:30"], ["13:30", "18:00"]],
        "4": [["09:00", "12:00"], ["13:00", "18:00"]],
        "5": [],
        "6": [],
    },
    "pomodoro": {"work": 25, "short": 5, "long": 10, "sessions": 4},  # menit
    # jumlah bunyi "tit" per kejadian, plus nada/volume/jeda
    "sound": {"work": 3, "short": 1, "long": 2, "lunch": 2, "off": 1, "timer": 1,
              "freq": 1000, "volume": 70, "gap": 350},
    "look": {"opacity": 85, "font": 34, "corner": "kanan atas"},
}

CORNERS = ["kanan atas", "kiri atas", "kanan bawah", "kiri bawah"]


def _home():
    return os.path.expanduser("~")


def config_dir(app=APP):
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.join(_home(), "AppData", "Roaming"), app)
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Application Support", app)
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(_home(), ".config"), app)


def cache_dir(app=APP):
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.join(_home(), "AppData", "Local"), app, "cache")
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Caches", app)
    return os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(_home(), ".cache"), app)


def config_path():
    return os.path.join(config_dir(), "config.json")


def legacy_config_path():
    # Versi GTK lama selalu memakai ~/.config/timer-melayang
    return os.path.join(_home(), ".config", LEGACY_APP, "config.json")


def migrate_legacy():
    """Salin config lama sekali saja, kalau config baru belum ada."""
    new, old = config_path(), legacy_config_path()
    if os.path.exists(new) or not os.path.exists(old):
        return False
    os.makedirs(os.path.dirname(new), exist_ok=True)
    shutil.copyfile(old, new)
    return True


def load_config():
    migrate_legacy()
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(config_path(), encoding="utf-8") as f:
            data = json.load(f)
        for key, val in cfg.items():
            if isinstance(data.get(key), dict):
                val.update(data[key])
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    os.makedirs(config_dir(), exist_ok=True)
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
