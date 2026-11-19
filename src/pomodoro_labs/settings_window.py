"""Dialog Pengaturan (Qt): Jadwal, Pomodoro, Suara, Tampilan."""
import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
                               QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from . import sound
from .config import CORNERS, DEFAULTS, save_config
from .style import SETTINGS_QSS, polish
from .timing import DAY_NAMES, valid_time

SOUND_EVENTS = [
    ("work", "🍅 Mulai kerja / fokus"),
    ("short", "☕ Istirahat pendek"),
    ("long", "🌴 Istirahat panjang"),
    ("lunch", "🍱 Istirahat siang"),
    ("off", "🏠 Jam kerja selesai"),
    ("timer", "⏰ Timer manual selesai"),
]


def label(text, name=None, wrap=False):
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    lbl.setWordWrap(wrap)
    return lbl


def spin(lo, hi, step=1):
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setMinimumWidth(72)
    return s


def slider(lo, hi, step, width=220):
    """Slider dengan angka di kanan. Mengembalikan (widget gabungan, slider)."""
    s = QSlider(Qt.Horizontal)
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setPageStep(step)
    s.setFixedWidth(width)
    val = QLabel(str(lo))
    val.setFixedWidth(36)
    s.valueChanged.connect(lambda v: val.setText(str(v)))
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(s)
    lay.addWidget(val)
    return box, s


def time_entry():
    e = QLineEdit()
    e.setMaxLength(5)
    e.setFixedWidth(64)
    e.setAlignment(Qt.AlignCenter)
    e.setPlaceholderText("--:--")
    e.setProperty("error", "false")
    return e


class Card(QFrame):
    """Daftar baris berkotak (pengganti GtkListBox)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(12, 6, 12, 6)
        self.lay.setSpacing(0)

    def add(self, widget):
        widget.setContentsMargins(0, 8, 0, 8)
        self.lay.addWidget(widget)

    def row(self, title, widget, hint=None):
        r = QWidget()
        lay = QHBoxLayout(r)
        lay.setContentsMargins(0, 0, 0, 0)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(label(title))
        if hint:
            texts.addWidget(label(hint, "hint"))
        lay.addLayout(texts, 1)
        lay.addWidget(widget)
        self.add(r)


class SettingsWindow(QDialog):
    def __init__(self, cfg, on_saved):
        super().__init__()
        self.cfg = cfg
        self.on_saved = on_saved
        self.setWindowTitle("Pengaturan Pomodoro Labs")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setStyleSheet(SETTINGS_QSS)
        self.resize(740, 600)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.build_schedule_page()
        self.build_pomodoro_page()
        self.build_sound_page()
        self.build_look_page()

        bar = QHBoxLayout()
        btn_default = QPushButton("Default")
        btn_default.setToolTip("Kembalikan semua pengaturan ke bawaan")
        btn_default.clicked.connect(lambda: self.load(copy.deepcopy(DEFAULTS)))
        btn_save = QPushButton("Simpan")
        btn_save.setObjectName("primary")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.save)
        bar.addWidget(btn_default)
        bar.addStretch(1)
        bar.addWidget(btn_save)
        root.addLayout(bar)

        self.load(copy.deepcopy(cfg))

    # --- helper halaman ---

    def page(self, title):
        body = QWidget()
        body.setObjectName("page")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        self.tabs.addTab(scroll, title)
        return lay

    @staticmethod
    def section(parent, title, hint=None):
        parent.addWidget(label(title, "section"))
        if hint:
            parent.addWidget(label(hint, "hint", wrap=True))
        card = Card()
        parent.addWidget(card)
        return card

    # --- halaman ---

    def build_schedule_page(self):
        box = self.page("🗓  Jadwal")
        card = self.section(box, "Jadwal kerja mingguan",
                            "Format jam HH:MM. Kosongkan kolom istirahat kalau hari itu "
                            "tanpa istirahat siang. Hilangkan centang untuk hari libur.")
        self.days = []
        for i, name in enumerate(DAY_NAMES):
            r = QWidget()
            lay = QHBoxLayout(r)
            lay.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(name)
            cb.setMinimumWidth(90)
            lay.addWidget(cb)
            lay.addStretch(1)
            entries = [time_entry() for _ in range(4)]
            fields = QWidget()
            flay = QHBoxLayout(fields)
            flay.setContentsMargins(0, 0, 0, 0)
            for text, e in zip(["Masuk", "Istirahat", "–", "Pulang"], entries):
                flay.addWidget(label(text, "hint"))
                flay.addWidget(e)
            lay.addWidget(fields)
            cb.toggled.connect(fields.setEnabled)
            card.add(r)
            self.days.append((cb, entries, fields))

        btn = QPushButton("Samakan Selasa–Jumat dengan Senin")
        btn.clicked.connect(self.copy_monday)
        box.addWidget(btn, 0, Qt.AlignLeft)

    def copy_monday(self):
        cb0, e0, _ = self.days[0]
        for cb, entries, _f in self.days[1:5]:
            cb.setChecked(cb0.isChecked())
            for src, dst in zip(e0, entries):
                dst.setText(src.text())

    def build_pomodoro_page(self):
        box = self.page("🍅  Pomodoro")
        card = self.section(box, "Durasi (menit)",
                            "Dipakai di mode otomatis maupun Pomodoro manual.")
        self.sp_work, self.sp_short = spin(1, 180), spin(1, 60)
        self.sp_long, self.sp_sessions = spin(1, 120), spin(1, 12)
        card.row("Fokus / kerja", self.sp_work)
        card.row("Istirahat pendek", self.sp_short)
        card.row("Istirahat panjang", self.sp_long)
        card2 = self.section(box, "Siklus")
        card2.row("Sesi fokus sebelum istirahat panjang", self.sp_sessions,
                  "Contoh 4: fokus·istirahat ×3, lalu istirahat panjang")

    def build_sound_page(self):
        box = self.page("🔔  Suara")
        card = self.section(box, 'Jumlah bunyi "tit"',
                            "Atur berapa kali berbunyi untuk tiap kejadian (0 = diam). "
                            "Tekan ▶ untuk mencoba.")
        self.sp_tits = {}
        for key, title in SOUND_EVENTS:
            sp = spin(0, 6)
            play = QPushButton("▶")
            play.setToolTip("Coba bunyi")
            play.clicked.connect(lambda _=False, s=sp: self.test_sound(s.value()))
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(sp)
            lay.addWidget(play)
            card.row(title, w)
            self.sp_tits[key] = sp

        card2 = self.section(box, "Karakter bunyi")
        w1, self.sc_freq = slider(300, 3000, 50)
        w2, self.sc_vol = slider(5, 100, 5)
        self.sp_gap = spin(120, 1500, 10)
        card2.row("Nada (Hz)", w1, "Rendah = berat, tinggi = nyaring")
        card2.row("Volume (%)", w2)
        card2.row("Jeda antar tit (ms)", self.sp_gap)
        test = QPushButton("▶  Coba tit-tit-tit")
        test.clicked.connect(lambda: self.test_sound(3))
        box.addWidget(test, 0, Qt.AlignLeft)

    def test_sound(self, count):
        sound.play_tits(count, self.sc_freq.value(), self.sc_vol.value(), self.sp_gap.value())

    def build_look_page(self):
        box = self.page("🎨  Tampilan")
        card = self.section(box, "Jendela timer")
        w1, self.sc_opacity = slider(30, 100, 5)
        self.sp_font = spin(16, 96, 2)
        self.cb_corner = QComboBox()
        for c in CORNERS:
            self.cb_corner.addItem(c.capitalize(), c)
        card.row("Kepekatan latar (%)", w1, "Makin kecil makin transparan")
        card.row("Ukuran angka (px)", self.sp_font)
        card.row("Posisi awal", self.cb_corner, "Dipakai saat timer dibuka / disimpan")

        box.addWidget(label("Pratinjau warna fase", "section"))
        prev = QFrame()
        prev.setObjectName("preview")
        lay = QHBoxLayout(prev)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(24)
        for text, color in [("Fokus", "#ff8a80"), ("Istirahat", "#7ee08a"),
                            ("Jeda", "#f5c542"), ("Libur", "#9a9a9a")]:
            l = QLabel(f'<div align="center"><span style="color:{color};font-family:monospace;'
                       f'font-weight:bold;font-size:18px">25:00</span><br>'
                       f'<span style="color:#aaaaaa;font-size:11px">{text}</span></div>')
            lay.addWidget(l)
        lay.addStretch(1)
        box.addWidget(prev, 0, Qt.AlignLeft)

    # --- muat & simpan ---

    def load(self, cfg):
        for i, (cb, entries, fields) in enumerate(self.days):
            blocks = cfg["schedule"].get(str(i), [])
            if len(blocks) >= 2:
                vals = [blocks[0][0], blocks[0][1], blocks[1][0], blocks[-1][1]]
            elif len(blocks) == 1:
                vals = [blocks[0][0], "", "", blocks[0][1]]
            else:
                vals = ["09:00", "12:00", "13:00", "17:00"]
            for e, v in zip(entries, vals):
                e.setText(v)
            cb.setChecked(bool(blocks))
            fields.setEnabled(bool(blocks))
        p = cfg["pomodoro"]
        self.sp_work.setValue(p["work"])
        self.sp_short.setValue(p["short"])
        self.sp_long.setValue(p["long"])
        self.sp_sessions.setValue(p["sessions"])
        s = cfg["sound"]
        for key, sp in self.sp_tits.items():
            sp.setValue(s[key])
        self.sc_freq.setValue(s["freq"])
        self.sc_vol.setValue(s["volume"])
        self.sp_gap.setValue(s["gap"])
        lk = cfg["look"]
        self.sc_opacity.setValue(lk["opacity"])
        self.sp_font.setValue(lk["font"])
        idx = self.cb_corner.findData(lk["corner"])
        self.cb_corner.setCurrentIndex(max(idx, 0))

    @staticmethod
    def mark(entry, bad):
        entry.setProperty("error", "true" if bad else "false")
        polish(entry)

    def read_schedule(self):
        schedule, errors = {}, []
        for i, (cb, entries, _f) in enumerate(self.days):
            for e in entries:
                self.mark(e, False)
            if not cb.isChecked():
                schedule[str(i)] = []
                continue
            t_in, l_start, l_end, t_out = (valid_time(e.text()) if e.text().strip()
                                           else "" for e in entries)
            bad = [e for e, v in zip(entries, (t_in, l_start, l_end, t_out))
                   if v is None or (v == "" and e in (entries[0], entries[3]))]
            if bool(l_start) != bool(l_end):
                bad += [entries[1], entries[2]]
            times = [t for t in (t_in, l_start, l_end, t_out) if t]
            if not bad and times != sorted(set(times)):
                bad = list(entries)
            if bad:
                for e in bad:
                    self.mark(e, True)
                errors.append(DAY_NAMES[i])
                continue
            schedule[str(i)] = ([[t_in, l_start], [l_end, t_out]] if l_start
                                else [[t_in, t_out]])
        return schedule, errors

    def save(self):
        schedule, errors = self.read_schedule()
        if errors:
            self.tabs.setCurrentIndex(0)
            QMessageBox.warning(
                self, "Jadwal belum benar",
                f"Periksa hari: {', '.join(errors)}.\nPakai format HH:MM dan pastikan "
                "urutannya Masuk < Istirahat < selesai istirahat < Pulang.")
            return
        cfg = self.cfg
        cfg["schedule"] = schedule
        cfg["pomodoro"] = {"work": self.sp_work.value(), "short": self.sp_short.value(),
                           "long": self.sp_long.value(), "sessions": self.sp_sessions.value()}
        snd = {k: sp.value() for k, sp in self.sp_tits.items()}
        snd.update(freq=self.sc_freq.value(), volume=self.sc_vol.value(), gap=self.sp_gap.value())
        cfg["sound"] = snd
        cfg["look"] = {"opacity": self.sc_opacity.value(), "font": self.sp_font.value(),
                       "corner": self.cb_corner.currentData()}
        save_config(cfg)
        self.on_saved()
        self.close()
