import copy
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from pomodoro_labs import config  # noqa: E402
from pomodoro_labs.settings_window import SettingsWindow  # noqa: E402
from pomodoro_labs.timer_window import FloatingTimer  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_home", lambda: str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setattr("pomodoro_labs.platform_.notify", lambda *a, **k: None)
    monkeypatch.setattr("pomodoro_labs.sound.play_tits", lambda *a, **k: None)


def test_manual_start_pause_reset(app):
    w = FloatingTimer(copy.deepcopy(config.DEFAULTS), auto=False)
    w.entry.setText("1:30")
    w.start()
    assert w.end_time is not None and w.label.text() == "01:30"
    w.toggle()
    assert w.end_time is None and w.state == "paused"
    w.reset()
    assert w.remaining == 90 and w.state is None


def test_timer_finishes(app):
    w = FloatingTimer(copy.deepcopy(config.DEFAULTS), auto=False)
    w.entry.setText("0:01")
    w.start()
    w.end_time -= 5
    w.tick()
    assert w.state == "done" and w.remaining == 0


def test_pomodoro_advances_phases(app):
    w = FloatingTimer(copy.deepcopy(config.DEFAULTS), pomodoro=True)
    assert w.phase == "work"
    w.end_time -= 10_000
    w.tick()
    assert w.phase == "short" and w.end_time is not None


def test_auto_mode_shows_phase(app):
    w = FloatingTimer(copy.deepcopy(config.DEFAULTS), auto=True)
    assert w.auto and not w.entry.isVisibleTo(w)
    assert w.phase_label.text().startswith("🕘")


def test_settings_save_roundtrip(app):
    cfg = copy.deepcopy(config.DEFAULTS)
    saved = []
    s = SettingsWindow(cfg, on_saved=lambda: saved.append(1))
    s.sp_work.setValue(40)
    s.sc_opacity.setValue(60)
    s.save()
    assert saved and cfg["pomodoro"]["work"] == 40 and cfg["look"]["opacity"] == 60
    assert config.load_config()["pomodoro"]["work"] == 40


def test_settings_rejects_bad_schedule(app, monkeypatch):
    cfg = copy.deepcopy(config.DEFAULTS)
    s = SettingsWindow(cfg, on_saved=lambda: None)
    monkeypatch.setattr("pomodoro_labs.settings_window.QMessageBox.warning", lambda *a, **k: None)
    s.days[0][1][0].setText("25:99")
    s.save()
    assert cfg["schedule"] == config.DEFAULTS["schedule"]
    assert s.days[0][1][0].property("error") == "true"
