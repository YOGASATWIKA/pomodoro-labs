import json
import os

from pomodoro_labs import config


def _home(tmp_path, monkeypatch):
    # Windows membaca ~ dari USERPROFILE, jadi patch _home() langsung agar sama di semua OS
    monkeypatch.setattr(config, "_home", lambda: str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setattr(config.sys, "platform", "linux")


def test_defaults_when_no_file(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert config.load_config() == config.DEFAULTS


def test_migrate_legacy_once(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    old = tmp_path / ".config" / "timer-melayang" / "config.json"
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"pomodoro": {"work": 50}}))
    cfg = config.load_config()
    assert cfg["pomodoro"]["work"] == 50 and cfg["pomodoro"]["short"] == 5
    assert os.path.exists(config.config_path())
    old.write_text(json.dumps({"pomodoro": {"work": 10}}))   # config lama berubah lagi
    assert config.load_config()["pomodoro"]["work"] == 50     # tidak ditimpa ulang


def test_save_roundtrip_and_bad_json(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    cfg = config.load_config()
    cfg["look"]["font"] = 50
    config.save_config(cfg)
    assert config.load_config()["look"]["font"] == 50
    open(config.config_path(), "w").write("{bukan json")
    assert config.load_config() == config.DEFAULTS


def test_paths_per_os(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_home", lambda: str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setattr(config.sys, "platform", "win32")
    assert config.config_dir() == os.path.join(str(tmp_path), "AppData", "pomodoro-labs")
    monkeypatch.setattr(config.sys, "platform", "darwin")
    assert "Application Support" in config.config_dir()
