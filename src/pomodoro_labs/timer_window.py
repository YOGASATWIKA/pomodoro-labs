"""Jendela timer melayang (Qt)."""
import time
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from . import platform_, sound
from .config import CORNERS
from .settings_window import SettingsWindow
from .style import FLOATING_QSS, STATE_COLORS, polish
from .timing import (PHASE_CLASS, PHASE_NAMES, advance, auto_state, fmt,
                     parse_duration, parse_pomodoro, pomodoro_text)


class FloatingTimer(QWidget):
    def __init__(self, cfg, initial=None, pomodoro=False, auto=True):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("Pomodoro Labs")
        self.setWindowIcon(platform_.app_icon())
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)  # macOS: jangan sembunyi saat app lain aktif
        self.setStyleSheet(FLOATING_QSS)

        self.settings_win = None
        self.auto = False
        self.auto_key = None      # fase otomatis terakhir, untuk mendeteksi pergantian
        self.pomodoro = False
        self.phase = "work"
        self.session = 1          # sesi fokus ke-berapa
        self.durations = parse_pomodoro(pomodoro_text(cfg["pomodoro"]), cfg["pomodoro"])
        self.total = 25 * 60
        self.end_time = None      # waktu selesai saat berjalan (monotonic)
        self.remaining = self.total
        self.blink = False
        self.state = None
        self._drag = None
        self._color = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(4)

        self.phase_label = QLabel()
        self.phase_label.setObjectName("phase")
        self.phase_label.hide()
        outer.addWidget(self.phase_label)

        self.label = QLabel(fmt(self.remaining))
        self.label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.label)

        row = QHBoxLayout()
        row.setSpacing(4)
        outer.addLayout(row)
        self.entry = QLineEdit("25")
        self.entry.setFixedWidth(64)
        self.entry.returnPressed.connect(self.start)
        row.addWidget(self.entry)
        self.btn_start = self.add_button(row, "▶", "Mulai / Jeda", self.toggle)
        self.btn_reset = self.add_button(row, "⟲", "Reset", self.reset)
        self.btn_skip = self.add_button(row, "⏭", "Lewati ke fase berikutnya", self.skip)
        self.btn_mode = self.add_button(row, "🍅", "Mode Pomodoro on/off", self.toggle_mode)
        self.btn_auto = self.add_button(row, "🕘", "Otomatis ikut jadwal kerja / manual",
                                        self.toggle_auto)
        self.add_button(row, "⚙", "Pengaturan", self.open_settings)
        self.add_button(row, "✕", "Tutup", QApplication.quit)
        self.manual_widgets = [self.entry, self.btn_start, self.btn_reset,
                               self.btn_skip, self.btn_mode]

        self.apply_look()
        self.set_auto(auto)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(200)

        if pomodoro:
            self.toggle_mode()
            self.start()
        elif initial:
            self.entry.setText(initial)
            self.start()

    # --- tampilan ---

    def apply_look(self):
        f = QFont("monospace")
        f.setStyleHint(QFont.Monospace)
        f.setBold(True)
        f.setPixelSize(int(self.cfg["look"]["font"]))
        self.label.setFont(f)
        self.paint_state()

    def paint_state(self, color=None):
        color = color or STATE_COLORS.get(self.state, "#ffffff")
        if color != self._color:   # jangan set ulang stylesheet tiap tick
            self._color = color
            self.label.setStyleSheet(f"color: {color};")

    def set_state_class(self, name):
        self.state = name
        self.paint_state()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 20, 24, int(255 * self.cfg["look"]["opacity"] / 100)))
        p.drawRoundedRect(QRectF(self.rect()), 12, 12)

    def place(self):
        self.adjustSize()
        area = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        corner = self.cfg["look"].get("corner", CORNERS[0])
        x = area.x() + 20 if "kiri" in corner else area.x() + area.width() - self.width() - 20
        y = area.y() + area.height() - self.height() - 20 if "bawah" in corner else area.y() + 20
        self.move(x, y)

    def add_button(self, row, label, tooltip, callback):
        btn = QPushButton(label)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda *_: callback())
        row.addWidget(btn)
        return btn

    @staticmethod
    def set_active(btn, on):
        btn.setProperty("active", "true" if on else "false")
        polish(btn)

    # --- input mouse / keyboard ---

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            handle = self.windowHandle()
            if handle is not None and handle.startSystemMove():
                return  # OS yang menggeser (aman di Wayland)
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.RightButton:
            self.open_settings()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            QApplication.quit()
        else:
            super().keyPressEvent(e)

    # --- pengaturan ---

    def open_settings(self):
        if self.settings_win is not None:
            self.settings_win.raise_()
            self.settings_win.activateWindow()
            return
        self.settings_win = SettingsWindow(self.cfg, on_saved=self.apply_config)
        self.settings_win.finished.connect(lambda *_: setattr(self, "settings_win", None))
        self.settings_win.show()

    def apply_config(self):
        self.apply_look()
        self.durations = parse_pomodoro(pomodoro_text(self.cfg["pomodoro"]), self.cfg["pomodoro"])
        if self.auto:
            self.auto_key = None      # hitung ulang fase tanpa membunyikan alarm
            self.tick()
        elif self.pomodoro and self.end_time is None:
            self.entry.setText(pomodoro_text(self.cfg["pomodoro"]))
            self.reset()
        self.update()
        self.place()
        platform_.notify("Pomodoro Labs", "Pengaturan tersimpan ✓")

    # --- fase ---

    def sessions_before_long(self):
        return int(self.cfg["pomodoro"]["sessions"])

    def show_phase(self, phase, session):
        text = PHASE_NAMES[phase]
        if session:
            text += f"  ·  sesi {session}/{self.sessions_before_long()}"
        if self.auto:
            text = "🕘 " + text
        self.phase_label.setText(text)
        self.phase_label.show()

    def update_phase_label(self):
        if self.pomodoro:
            self.show_phase(self.phase, self.session)
        else:
            self.phase_label.hide()

    def running_class(self):
        return PHASE_CLASS[self.phase] if self.pomodoro else None

    # --- mode ---

    def set_auto(self, auto):
        self.auto = auto
        self.auto_key = None
        self.end_time = None
        self.set_active(self.btn_auto, auto)
        for w in self.manual_widgets:
            w.setVisible(not auto)
        self.btn_skip.setVisible(not auto and self.pomodoro)
        self.entry.setToolTip(
            "Fokus/istirahat/istirahat panjang dalam menit (contoh: 25/5/15)"
            if self.pomodoro else "Menit (contoh: 25, 1:30, 1:00:00)")
        if auto:
            self.tick()
        else:
            self.reset()
        self.place()  # kecilkan jendela sesuai isi

    def toggle_auto(self):
        self.set_auto(not self.auto)

    def toggle_mode(self):
        self.pomodoro = not self.pomodoro
        self.set_active(self.btn_mode, self.pomodoro)
        self.entry.setText(pomodoro_text(self.cfg["pomodoro"]) if self.pomodoro else "25")
        self.set_auto(False)

    # --- kontrol manual ---

    def read_entry(self):
        """Durasi untuk fase sekarang dari isian, atau None kalau isian tidak valid."""
        try:
            if self.pomodoro:
                self.durations = parse_pomodoro(self.entry.text(), self.cfg["pomodoro"])
                return self.durations[self.phase]
            secs = parse_duration(self.entry.text())
            return secs if secs > 0 else None
        except ValueError:
            return None

    def run(self, secs):
        self.total = self.remaining = secs
        self.end_time = time.monotonic() + secs
        self.btn_start.setText("⏸")
        self.set_state_class(self.running_class())
        self.update_phase_label()
        self.label.setText(fmt(secs))

    def start(self):
        secs = self.read_entry()
        if secs:
            self.run(secs)

    def toggle(self):
        if self.end_time is not None:          # sedang jalan -> jeda
            self.remaining = self.end_time - time.monotonic()
            self.end_time = None
            self.btn_start.setText("▶")
            self.set_state_class("paused")
        elif 0 < self.remaining < self.total:  # lanjutkan
            self.end_time = time.monotonic() + self.remaining
            self.btn_start.setText("⏸")
            self.set_state_class(self.running_class())
        else:                                  # mulai baru dari isian
            self.start()

    def reset(self):
        self.end_time = None
        if self.pomodoro:
            self.phase, self.session = "work", 1
        secs = self.read_entry()
        if secs:
            self.total = secs
        self.remaining = self.total
        self.btn_start.setText("▶")
        self.set_state_class(None)
        self.update_phase_label()
        self.label.setText(fmt(self.remaining))

    def skip(self):
        if self.pomodoro:
            self.phase, self.session = advance(self.phase, self.session, self.sessions_before_long())
            self.read_entry()
            self.run(self.durations[self.phase])

    # --- bunyi & notifikasi ---

    def alert(self, title, body, event):
        platform_.notify(title, body, self)
        s = self.cfg["sound"]
        sound.play_tits(s.get(event, 1), s["freq"], s["volume"], s["gap"])

    def finish(self):
        if self.pomodoro:
            done = self.phase
            self.phase, self.session = advance(self.phase, self.session, self.sessions_before_long())
            if done == "work":
                self.alert("🍅 Sesi fokus selesai",
                           f"Waktunya {PHASE_NAMES[self.phase].split(' ', 1)[1].lower()} "
                           f"{fmt(self.durations[self.phase])}", self.phase)
            else:
                self.alert("💪 Istirahat selesai", f"Lanjut fokus sesi {self.session}", "work")
            self.run(self.durations[self.phase])   # otomatis lanjut fase berikutnya
            return
        self.end_time = None
        self.remaining = 0
        self.btn_start.setText("▶")
        self.set_state_class("done")
        self.alert("⏰ Timer selesai", f"{fmt(self.total)} sudah habis", "timer")

    # --- mode otomatis ---

    def auto_alert(self, prev_phase, phase, session, end):
        until = end.strftime("%H:%M")
        if phase == "work":
            self.alert("🍅 Waktunya fokus", f"Sesi {session}, sampai {until}", "work")
        elif phase in ("short", "long"):
            self.alert(PHASE_NAMES[phase], f"Istirahat dulu sampai {until}", phase)
        elif phase == "lunch":
            self.alert("🍱 Istirahat siang", f"Selamat makan! Kerja lagi jam {until}", "lunch")
        elif prev_phase != "off":
            self.alert("🏠 Jam kerja selesai", "Kerja bagus hari ini!", "off")

    def tick_auto(self):
        now = datetime.now()
        key, phase, session, end = auto_state(now, self.durations, self.cfg["schedule"],
                                              self.sessions_before_long())
        if key != self.auto_key:
            if self.auto_key is not None:
                self.auto_alert(self.auto_key[0], phase, session, end)
            self.auto_key = key
            self.set_state_class(PHASE_CLASS[phase])
            self.show_phase(phase, session)
        self.label.setText(fmt((end - now).total_seconds()))

    def tick(self):
        if self.auto:
            self.tick_auto()
            return
        if self.end_time is not None:
            self.remaining = self.end_time - time.monotonic()
            if self.remaining <= 0:
                self.finish()
            else:
                self.label.setText(fmt(self.remaining))
        elif self.remaining == 0 and self.state == "done":
            self.blink = not self.blink
            self.paint_state("#7a2e2e" if self.blink else STATE_COLORS["done"])
            return
        self.paint_state()
