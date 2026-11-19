#!/usr/bin/env python3
"""Timer kecil yang melayang (selalu di atas jendela lain), dengan mode Pomodoro
dan mode otomatis yang mengikuti jadwal kerja.

Pemakaian:
  pomodoro-labs                 mode otomatis (ikut jadwal kerja)
  pomodoro-labs --manual        timer manual
  pomodoro-labs [menit]         timer manual langsung mulai, contoh: 25 atau 1:30
  pomodoro-labs --pomodoro      Pomodoro manual langsung mulai
Seret jendela untuk memindahkan. Klik kanan atau tombol ⚙ untuk Pengaturan.
Esc untuk menutup. Pengaturan disimpan di ~/.config/timer-melayang/config.json
"""
import copy
import json
import math
import os
import struct
import subprocess
import sys
import time
import wave
from datetime import datetime, timedelta

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

CONFIG_PATH = os.path.expanduser("~/.config/timer-melayang/config.json")
CACHE_DIR = os.path.expanduser("~/.cache/timer-melayang")

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

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

SOUND_EVENTS = [
    ("work", "🍅 Mulai kerja / fokus"),
    ("short", "☕ Istirahat pendek"),
    ("long", "🌴 Istirahat panjang"),
    ("lunch", "🍱 Istirahat siang"),
    ("off", "🏠 Jam kerja selesai"),
    ("timer", "⏰ Timer manual selesai"),
]
CORNERS = ["kanan atas", "kiri atas", "kanan bawah", "kiri bawah"]


def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        for key, val in cfg.items():
            if isinstance(data.get(key), dict):
                val.update(data[key])
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


CONFIG = load_config()


# --- suara ---

def tit_file(freq, volume):
    """File bunyi "tit" pendek (0.15 detik) untuk nada & volume tertentu."""
    path = os.path.join(CACHE_DIR, f"tit-{int(freq)}-{int(volume)}.wav")
    if not os.path.exists(path):
        os.makedirs(CACHE_DIR, exist_ok=True)
        rate, n = 44100, int(44100 * 0.15)
        amp = 32000 * volume / 100
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"".join(
                struct.pack("<h", int(amp * min(1, i / 300, (n - i) / 300)
                                      * math.sin(2 * math.pi * freq * i / rate)))
                for i in range(n)))
    return path


def play_tits(count, freq=None, volume=None, gap=None):
    s = CONFIG["sound"]
    path = tit_file(freq or s["freq"], s["volume"] if volume is None else volume)
    gap = gap or s["gap"]
    for i in range(int(count)):
        GLib.timeout_add(i * gap, lambda: subprocess.Popen(["paplay", path]) and False)


def alert(title, body, event):
    subprocess.Popen(["notify-send", "-u", "critical", title, body])
    play_tits(CONFIG["sound"].get(event, 1))


# --- tampilan ---

def build_css():
    look = CONFIG["look"]
    return f"""
#floating {{ background-color: rgba(20, 20, 24, {look['opacity'] / 100:.2f}); border-radius: 12px; }}
#time {{ color: #ffffff; font-size: {look['font']}px; font-weight: bold; font-family: monospace; }}
#time.work {{ color: #ff8a80; }}
#time.break {{ color: #7ee08a; }}
#time.off {{ color: #9a9a9a; }}
#time.paused {{ color: #f5c542; }}
#time.done {{ color: #ff5c5c; }}
#phase {{ color: #cccccc; font-size: 12px; }}
#floating entry {{ min-width: 0; font-size: 13px; }}
#floating button {{ padding: 2px 8px; min-height: 0; font-size: 13px; }}
#floating button.active {{ background: #c0392b; color: white; }}

#settings {{ background-color: #1c1d23; }}
#settings .page {{ padding: 18px 22px; }}
#settings .section {{ color: #ff8a80; font-weight: bold; font-size: 13px; margin-top: 10px; }}
#settings .hint {{ color: #8a8d99; font-size: 11px; }}
#settings list {{ background-color: #262731; border-radius: 10px; border: 1px solid #33343f; }}
#settings list row {{ padding: 8px 12px; border-bottom: 1px solid #2f303b; }}
#settings list row:last-child {{ border-bottom: none; }}
#settings .rowtitle {{ color: #f0f0f0; }}
#settings entry.time {{ font-family: monospace; }}
#settings entry.error {{ border-color: #ff5c5c; color: #ff5c5c; }}
#settings .preview {{ background-color: #14151a; border-radius: 12px; padding: 14px; }}
""".encode()


PHASE_NAMES = {"work": "🍅 Fokus", "short": "☕ Istirahat", "long": "🌴 Istirahat panjang",
               "lunch": "🍱 Istirahat siang", "off": "🏠 Di luar jam kerja"}
PHASE_CLASS = {"work": "work", "short": "break", "long": "break", "lunch": "break", "off": "off"}


# --- logika waktu ---

def parse_duration(text):
    """'25' -> 25 menit, '1:30' -> 1 menit 30 detik, '1:00:00' -> 1 jam."""
    parts = [float(p) for p in text.strip().split(":")]
    if len(parts) == 1:
        return int(parts[0] * 60)
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return int(secs)


def pomodoro_text():
    p = CONFIG["pomodoro"]
    return f"{p['work']}/{p['short']}/{p['long']}"


def parse_pomodoro(text):
    """'25/5/15' -> (fokus, istirahat, istirahat panjang) dalam detik."""
    vals = [parse_duration(p) for p in text.split("/")]
    p = CONFIG["pomodoro"]
    defaults = [p["work"] * 60, p["short"] * 60, p["long"] * 60]
    vals = (vals + defaults[len(vals):])[:3]
    if min(vals) <= 0:
        raise ValueError
    return dict(zip(("work", "short", "long"), vals))


def sessions_before_long():
    return int(CONFIG["pomodoro"]["sessions"])


def advance(phase, session):
    """Fase Pomodoro berikutnya: fokus -> istirahat -> fokus ..., panjang tiap N sesi."""
    if phase == "work":
        return ("long" if session >= sessions_before_long() else "short"), session
    return "work", (1 if phase == "long" else session + 1)


def work_blocks(day):
    blocks = []
    for start, end in CONFIG["schedule"].get(str(day.weekday()), []):
        s = datetime.combine(day, datetime.strptime(start, "%H:%M").time())
        e = datetime.combine(day, datetime.strptime(end, "%H:%M").time())
        blocks.append((s, e))
    return blocks


def auto_state(now, durations):
    """Keadaan menurut jadwal: (kunci unik, fase, sesi, waktu selesai fase)."""
    blocks = work_blocks(now.date())
    for i, (s, e) in enumerate(blocks):
        if now < s:
            kind = "off" if i == 0 else "lunch"
            return (kind, s), kind, 0, s
        if now < e:
            # Pomodoro dihitung dari awal blok, jadi selalu sinkron dengan jam
            t, phase, session = s, "work", 1
            while True:
                end = min(t + timedelta(seconds=durations[phase]), e)
                if now < end:
                    return (phase, t), phase, session, end
                t = end
                phase, session = advance(phase, session)
    for d in range(1, 8):  # cari hari kerja berikutnya
        nxt = work_blocks(now.date() + timedelta(days=d))
        if nxt:
            return ("off", nxt[0][0]), "off", 0, nxt[0][0]
    return ("off", None), "off", 0, now


def fmt(secs):
    secs = max(0, int(round(secs)))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def valid_time(text):
    try:
        return datetime.strptime(text.strip(), "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


# --- jendela pengaturan ---

class SettingsWindow(Gtk.Window):
    def __init__(self, timer):
        super().__init__(title="Pengaturan Timer")
        self.timer = timer
        self.set_name("settings")
        self.set_default_size(720, 560)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_icon_name("alarm-symbolic")

        header = Gtk.HeaderBar(show_close_button=True)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
                               transition_duration=180)
        header.set_custom_title(Gtk.StackSwitcher(stack=self.stack))
        btn_save = Gtk.Button(label="Simpan")
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", lambda *_: self.save())
        header.pack_end(btn_save)
        btn_default = Gtk.Button(label="Default")
        btn_default.set_tooltip_text("Kembalikan semua pengaturan ke bawaan")
        btn_default.connect("clicked", lambda *_: self.load(copy.deepcopy(DEFAULTS)))
        header.pack_start(btn_default)
        self.set_titlebar(header)
        self.add(self.stack)

        self.build_schedule_page()
        self.build_pomodoro_page()
        self.build_sound_page()
        self.build_look_page()
        self.load(copy.deepcopy(CONFIG))
        self.show_all()

    # helper tampilan

    def page(self, name, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("page")
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.add(box)
        self.stack.add_titled(scroll, name, title)
        return box

    def section(self, parent, title, hint=None):
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.get_style_context().add_class("section")
        parent.pack_start(lbl, False, False, 0)
        if hint:
            h = Gtk.Label(label=hint, xalign=0, wrap=True)
            h.get_style_context().add_class("hint")
            parent.pack_start(h, False, False, 0)
        lst = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        parent.pack_start(lst, False, False, 0)
        return lst

    def row(self, lst, title, widget, hint=None):
        r = Gtk.Box(spacing=12)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0)
        t.get_style_context().add_class("rowtitle")
        texts.pack_start(t, False, False, 0)
        if hint:
            h = Gtk.Label(label=hint, xalign=0)
            h.get_style_context().add_class("hint")
            texts.pack_start(h, False, False, 0)
        r.pack_start(texts, True, True, 0)
        widget.set_valign(Gtk.Align.CENTER)
        r.pack_end(widget, False, False, 0)
        lst.add(r)

    @staticmethod
    def spin(lo, hi, step=1):
        s = Gtk.SpinButton.new_with_range(lo, hi, step)
        s.set_numeric(True)
        return s

    @staticmethod
    def scale(lo, hi, step, width=220):
        s = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, step)
        s.set_size_request(width, -1)
        s.set_value_pos(Gtk.PositionType.RIGHT)
        s.set_digits(0)
        return s

    @staticmethod
    def time_entry():
        e = Gtk.Entry(width_chars=5, max_length=5, placeholder_text="--:--")
        e.set_alignment(0.5)
        e.get_style_context().add_class("time")
        return e

    # halaman

    def build_schedule_page(self):
        box = self.page("jadwal", "🗓  Jadwal")
        lst = self.section(box, "Jadwal kerja mingguan",
                           "Format jam HH:MM. Kosongkan kolom istirahat kalau hari itu "
                           "tanpa istirahat siang. Matikan saklar untuk hari libur.")
        self.days = []
        for i, name in enumerate(DAY_NAMES):
            r = Gtk.Box(spacing=8)
            sw = Gtk.Switch(valign=Gtk.Align.CENTER)
            lbl = Gtk.Label(label=name, xalign=0, width_chars=7)
            lbl.get_style_context().add_class("rowtitle")
            r.pack_start(sw, False, False, 0)
            r.pack_start(lbl, False, False, 4)
            entries = [self.time_entry() for _ in range(4)]
            fields = Gtk.Box(spacing=6)
            for text, e in zip(["Masuk", "Istirahat", "–", "Pulang"], entries):
                h = Gtk.Label(label=text)
                h.get_style_context().add_class("hint")
                fields.pack_start(h, False, False, 0)
                fields.pack_start(e, False, False, 0)
            r.pack_end(fields, False, False, 0)
            sw.connect("notify::active", lambda s, _p, f=fields: f.set_sensitive(s.get_active()))
            lst.add(r)
            self.days.append((sw, entries))

        btn = Gtk.Button(label="Samakan Selasa–Jumat dengan Senin", halign=Gtk.Align.START)
        btn.connect("clicked", lambda *_: self.copy_monday())
        box.pack_start(btn, False, False, 4)

    def copy_monday(self):
        sw0, e0 = self.days[0]
        for sw, entries in self.days[1:5]:
            sw.set_active(sw0.get_active())
            for src, dst in zip(e0, entries):
                dst.set_text(src.get_text())

    def build_pomodoro_page(self):
        box = self.page("pomodoro", "🍅  Pomodoro")
        lst = self.section(box, "Durasi (menit)",
                           "Dipakai di mode otomatis maupun Pomodoro manual.")
        self.sp_work = self.spin(1, 180)
        self.sp_short = self.spin(1, 60)
        self.sp_long = self.spin(1, 120)
        self.sp_sessions = self.spin(1, 12)
        self.row(lst, "Fokus / kerja", self.sp_work)
        self.row(lst, "Istirahat pendek", self.sp_short)
        self.row(lst, "Istirahat panjang", self.sp_long)
        lst2 = self.section(box, "Siklus")
        self.row(lst2, "Sesi fokus sebelum istirahat panjang", self.sp_sessions,
                 "Contoh 4: fokus·istirahat ×3, lalu istirahat panjang")

    def build_sound_page(self):
        box = self.page("suara", "🔔  Suara")
        lst = self.section(box, "Jumlah bunyi \"tit\"",
                           "Atur berapa kali berbunyi untuk tiap kejadian (0 = diam). "
                           "Tekan ▶ untuk mencoba.")
        self.sp_tits = {}
        for key, title in SOUND_EVENTS:
            sp = self.spin(0, 6)
            play = Gtk.Button(label="▶")
            play.set_tooltip_text("Coba bunyi")
            play.connect("clicked", lambda *_, s=sp: self.test_sound(s.get_value_as_int()))
            w = Gtk.Box(spacing=6)
            w.pack_start(sp, False, False, 0)
            w.pack_start(play, False, False, 0)
            self.row(lst, title, w)
            self.sp_tits[key] = sp

        lst2 = self.section(box, "Karakter bunyi")
        self.sc_freq = self.scale(300, 3000, 50)
        self.sc_vol = self.scale(5, 100, 5)
        self.sp_gap = self.spin(120, 1500, 10)
        self.row(lst2, "Nada (Hz)", self.sc_freq, "Rendah = berat, tinggi = nyaring")
        self.row(lst2, "Volume (%)", self.sc_vol)
        self.row(lst2, "Jeda antar tit (ms)", self.sp_gap)
        test = Gtk.Button(label="▶  Coba tit-tit-tit", halign=Gtk.Align.START)
        test.connect("clicked", lambda *_: self.test_sound(3))
        box.pack_start(test, False, False, 4)

    def test_sound(self, count):
        play_tits(count, self.sc_freq.get_value(), self.sc_vol.get_value(),
                  self.sp_gap.get_value_as_int())

    def build_look_page(self):
        box = self.page("tampilan", "🎨  Tampilan")
        lst = self.section(box, "Jendela timer")
        self.sc_opacity = self.scale(30, 100, 5)
        self.sp_font = self.spin(16, 96, 2)
        self.cb_corner = Gtk.ComboBoxText()
        for c in CORNERS:
            self.cb_corner.append(c, c.capitalize())
        self.row(lst, "Kepekatan latar (%)", self.sc_opacity, "Makin kecil makin transparan")
        self.row(lst, "Ukuran angka (px)", self.sp_font)
        self.row(lst, "Posisi awal", self.cb_corner, "Dipakai saat timer dibuka / disimpan")

        hint = Gtk.Label(label="Pratinjau warna fase", xalign=0)
        hint.get_style_context().add_class("section")
        box.pack_start(hint, False, False, 0)
        prev = Gtk.Box(spacing=24, halign=Gtk.Align.START)
        prev.get_style_context().add_class("preview")
        for text, cls in [("Fokus", "#ff8a80"), ("Istirahat", "#7ee08a"),
                          ("Jeda", "#f5c542"), ("Libur", "#9a9a9a")]:
            l = Gtk.Label()
            l.set_markup(f'<span foreground="{cls}" font_family="monospace" '
                         f'weight="bold" size="x-large">25:00</span>\n'
                         f'<span foreground="#aaaaaa" size="small">{text}</span>')
            l.set_justify(Gtk.Justification.CENTER)
            prev.pack_start(l, False, False, 0)
        box.pack_start(prev, False, False, 0)

    # muat & simpan

    def load(self, cfg):
        for i, (sw, entries) in enumerate(self.days):
            blocks = cfg["schedule"].get(str(i), [])
            if len(blocks) >= 2:
                vals = [blocks[0][0], blocks[0][1], blocks[1][0], blocks[-1][1]]
            elif len(blocks) == 1:
                vals = [blocks[0][0], "", "", blocks[0][1]]
            else:
                vals = ["09:00", "12:00", "13:00", "17:00"]
            for e, v in zip(entries, vals):
                e.set_text(v)
            sw.set_active(bool(blocks))
            entries[0].get_parent().set_sensitive(bool(blocks))
        p = cfg["pomodoro"]
        self.sp_work.set_value(p["work"])
        self.sp_short.set_value(p["short"])
        self.sp_long.set_value(p["long"])
        self.sp_sessions.set_value(p["sessions"])
        s = cfg["sound"]
        for key, sp in self.sp_tits.items():
            sp.set_value(s[key])
        self.sc_freq.set_value(s["freq"])
        self.sc_vol.set_value(s["volume"])
        self.sp_gap.set_value(s["gap"])
        lk = cfg["look"]
        self.sc_opacity.set_value(lk["opacity"])
        self.sp_font.set_value(lk["font"])
        self.cb_corner.set_active_id(lk["corner"] if lk["corner"] in CORNERS else CORNERS[0])

    def read_schedule(self):
        schedule, errors = {}, []
        for i, (sw, entries) in enumerate(self.days):
            for e in entries:
                e.get_style_context().remove_class("error")
            if not sw.get_active():
                schedule[str(i)] = []
                continue
            t_in, l_start, l_end, t_out = (valid_time(e.get_text()) if e.get_text().strip()
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
                    e.get_style_context().add_class("error")
                errors.append(DAY_NAMES[i])
                continue
            schedule[str(i)] = ([[t_in, l_start], [l_end, t_out]] if l_start
                                else [[t_in, t_out]])
        return schedule, errors

    def save(self):
        schedule, errors = self.read_schedule()
        if errors:
            self.stack.set_visible_child_name("jadwal")
            dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                    message_type=Gtk.MessageType.WARNING,
                                    buttons=Gtk.ButtonsType.OK,
                                    text="Jadwal belum benar")
            dlg.format_secondary_text(
                f"Periksa hari: {', '.join(errors)}.\nPakai format HH:MM dan pastikan "
                "urutannya Masuk < Istirahat < selesai istirahat < Pulang.")
            dlg.run()
            dlg.destroy()
            return
        CONFIG["schedule"] = schedule
        CONFIG["pomodoro"] = {"work": self.sp_work.get_value_as_int(),
                              "short": self.sp_short.get_value_as_int(),
                              "long": self.sp_long.get_value_as_int(),
                              "sessions": self.sp_sessions.get_value_as_int()}
        sound = {k: sp.get_value_as_int() for k, sp in self.sp_tits.items()}
        sound.update(freq=int(self.sc_freq.get_value()), volume=int(self.sc_vol.get_value()),
                     gap=self.sp_gap.get_value_as_int())
        CONFIG["sound"] = sound
        CONFIG["look"] = {"opacity": int(self.sc_opacity.get_value()),
                          "font": self.sp_font.get_value_as_int(),
                          "corner": self.cb_corner.get_active_id()}
        save_config(CONFIG)
        self.timer.apply_config()
        subprocess.Popen(["notify-send", "Timer Melayang", "Pengaturan tersimpan ✓"])
        self.destroy()


# --- jendela timer ---

class FloatingTimer(Gtk.Window):
    def __init__(self, initial=None, pomodoro=False, auto=True):
        super().__init__(title="Timer Melayang")
        self.set_name("floating")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.stick()  # tampil di semua workspace
        self.set_resizable(False)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
        self.css = Gtk.CssProvider()
        self.css.load_from_data(build_css())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.settings_win = None
        self.auto = False
        self.auto_key = None      # fase otomatis terakhir, untuk mendeteksi pergantian
        self.pomodoro = False
        self.phase = "work"
        self.session = 1          # sesi fokus ke-berapa
        self.durations = parse_pomodoro(pomodoro_text())
        self.total = 25 * 60
        self.end_time = None      # waktu selesai saat berjalan
        self.remaining = self.total
        self.blink = False

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_border_width(10)
        self.add(box)

        self.phase_label = Gtk.Label()
        self.phase_label.set_name("phase")
        self.phase_label.set_no_show_all(True)
        box.pack_start(self.phase_label, False, False, 0)

        self.label = Gtk.Label(label=fmt(self.remaining))
        self.label.set_name("time")
        box.pack_start(self.label, False, False, 0)

        row = Gtk.Box(spacing=4)
        box.pack_start(row, False, False, 0)
        self.entry = Gtk.Entry(text="25", width_chars=6)
        self.entry.connect("activate", lambda *_: self.start())
        row.pack_start(self.entry, False, False, 0)
        self.btn_start = self.add_button(row, "▶", "Mulai / Jeda", self.toggle)
        self.btn_reset = self.add_button(row, "⟲", "Reset", self.reset)
        self.btn_skip = self.add_button(row, "⏭", "Lewati ke fase berikutnya", self.skip)
        self.btn_mode = self.add_button(row, "🍅", "Mode Pomodoro on/off", self.toggle_mode)
        self.btn_auto = self.add_button(row, "🕘", "Otomatis ikut jadwal kerja / manual",
                                        self.toggle_auto)
        self.add_button(row, "⚙", "Pengaturan", self.open_settings)
        self.add_button(row, "✕", "Tutup", Gtk.main_quit)
        self.manual_widgets = [self.entry, self.btn_start, self.btn_reset,
                               self.btn_skip, self.btn_mode]
        for w in self.manual_widgets:
            w.set_no_show_all(True)

        # Seret untuk memindahkan jendela, klik kanan untuk pengaturan
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", self.on_press)
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", Gtk.main_quit)

        self.show_all()
        self.set_auto(auto)
        GLib.idle_add(self.place)

        GLib.timeout_add(200, self.tick)
        if pomodoro:
            self.toggle_mode()
            self.start()
        elif initial:
            self.entry.set_text(initial)
            self.start()

    def place(self):
        display = Gdk.Display.get_default()
        area = (display.get_primary_monitor() or display.get_monitor(0)).get_workarea()
        w, h = self.get_size()
        corner = CONFIG["look"].get("corner", "kanan atas")
        x = area.x + 20 if "kiri" in corner else area.x + area.width - w - 20
        y = area.y + area.height - h - 20 if "bawah" in corner else area.y + 20
        self.move(x, y)
        return False

    def add_button(self, row, label, tooltip, callback):
        btn = Gtk.Button(label=label)
        btn.set_tooltip_text(tooltip)
        btn.connect("clicked", lambda *_: callback())
        row.pack_start(btn, False, False, 0)
        return btn

    def on_press(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        elif event.button == 3:
            self.open_settings()
        return False

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    # --- pengaturan ---

    def open_settings(self):
        if self.settings_win:
            self.settings_win.present()
            return
        self.settings_win = SettingsWindow(self)
        self.settings_win.connect("destroy", lambda *_: setattr(self, "settings_win", None))

    def apply_config(self):
        self.css.load_from_data(build_css())
        self.durations = parse_pomodoro(pomodoro_text())
        if self.auto:
            self.auto_key = None      # hitung ulang fase tanpa membunyikan alarm
            self.tick()
        elif self.pomodoro and self.end_time is None:
            self.entry.set_text(pomodoro_text())
            self.reset()
        self.resize(1, 1)
        GLib.idle_add(self.place)

    def set_state_class(self, name):
        ctx = self.label.get_style_context()
        for c in ("done", "paused", "work", "break", "off"):
            ctx.remove_class(c)
        if name:
            ctx.add_class(name)

    def running_class(self):
        if not self.pomodoro:
            return None
        return PHASE_CLASS[self.phase]

    def show_phase(self, phase, session):
        text = PHASE_NAMES[phase]
        if session:
            text += f"  ·  sesi {session}/{sessions_before_long()}"
        if self.auto:
            text = "🕘 " + text
        self.phase_label.set_text(text)
        self.phase_label.show()

    def update_phase_label(self):
        if self.pomodoro:
            self.show_phase(self.phase, self.session)
        else:
            self.phase_label.hide()

    # --- mode ---

    def set_auto(self, auto):
        self.auto = auto
        self.auto_key = None
        self.end_time = None
        ctx = self.btn_auto.get_style_context()
        (ctx.add_class if auto else ctx.remove_class)("active")
        for w in self.manual_widgets:
            w.set_visible(not auto)
        self.btn_skip.set_visible(not auto and self.pomodoro)
        self.entry.set_tooltip_text(
            "Fokus/istirahat/istirahat panjang dalam menit (contoh: 25/5/15)"
            if self.pomodoro else "Menit (contoh: 25, 1:30, 1:00:00)")
        if auto:
            self.tick()
        else:
            self.reset()
        self.resize(1, 1)  # kecilkan jendela sesuai isi

    def toggle_auto(self):
        self.set_auto(not self.auto)

    def toggle_mode(self):
        self.pomodoro = not self.pomodoro
        ctx = self.btn_mode.get_style_context()
        if self.pomodoro:
            ctx.add_class("active")
            self.entry.set_text(pomodoro_text())
        else:
            ctx.remove_class("active")
            self.entry.set_text("25")
        self.set_auto(False)

    # --- kontrol manual ---

    def read_entry(self):
        """Durasi untuk fase sekarang dari isian, atau None kalau isian tidak valid."""
        try:
            if self.pomodoro:
                self.durations = parse_pomodoro(self.entry.get_text())
                return self.durations[self.phase]
            secs = parse_duration(self.entry.get_text())
            return secs if secs > 0 else None
        except ValueError:
            return None

    def run(self, secs):
        self.total = self.remaining = secs
        self.end_time = time.monotonic() + secs
        self.btn_start.set_label("⏸")
        self.set_state_class(self.running_class())
        self.update_phase_label()
        self.label.set_text(fmt(secs))

    def start(self):
        secs = self.read_entry()
        if secs:
            self.run(secs)

    def toggle(self):
        if self.end_time is not None:          # sedang jalan -> jeda
            self.remaining = self.end_time - time.monotonic()
            self.end_time = None
            self.btn_start.set_label("▶")
            self.set_state_class("paused")
        elif 0 < self.remaining < self.total:  # lanjutkan
            self.end_time = time.monotonic() + self.remaining
            self.btn_start.set_label("⏸")
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
        self.btn_start.set_label("▶")
        self.set_state_class(None)
        self.update_phase_label()
        self.label.set_text(fmt(self.remaining))

    def skip(self):
        if self.pomodoro:
            self.phase, self.session = advance(self.phase, self.session)
            self.read_entry()
            self.run(self.durations[self.phase])

    def finish(self):
        if self.pomodoro:
            done = self.phase
            self.phase, self.session = advance(self.phase, self.session)
            if done == "work":
                alert("🍅 Sesi fokus selesai",
                      f"Waktunya {PHASE_NAMES[self.phase].split(' ', 1)[1].lower()} "
                      f"{fmt(self.durations[self.phase])}", self.phase)
            else:
                alert("💪 Istirahat selesai", f"Lanjut fokus sesi {self.session}", "work")
            self.run(self.durations[self.phase])   # otomatis lanjut fase berikutnya
            return
        self.end_time = None
        self.remaining = 0
        self.btn_start.set_label("▶")
        self.set_state_class("done")
        alert("⏰ Timer selesai", f"{fmt(self.total)} sudah habis", "timer")

    # --- mode otomatis ---

    def auto_alert(self, prev_phase, phase, session, end):
        until = end.strftime("%H:%M")
        if phase == "work":
            alert("🍅 Waktunya fokus", f"Sesi {session}, sampai {until}", "work")
        elif phase in ("short", "long"):
            alert(f"{PHASE_NAMES[phase]}", f"Istirahat dulu sampai {until}", phase)
        elif phase == "lunch":
            alert("🍱 Istirahat siang", f"Selamat makan! Kerja lagi jam {until}", "lunch")
        elif prev_phase != "off":
            alert("🏠 Jam kerja selesai", "Kerja bagus hari ini!", "off")

    def tick_auto(self):
        now = datetime.now()
        key, phase, session, end = auto_state(now, self.durations)
        if key != self.auto_key:
            if self.auto_key is not None:
                self.auto_alert(self.auto_key[0], phase, session, end)
            self.auto_key = key
            self.set_state_class(PHASE_CLASS[phase])
            self.show_phase(phase, session)
        self.label.set_text(fmt((end - now).total_seconds()))

    def tick(self):
        if self.auto:
            self.tick_auto()
            self.label.set_opacity(1.0)
            return True
        if self.end_time is not None:
            self.remaining = self.end_time - time.monotonic()
            if self.remaining <= 0:
                self.finish()
            else:
                self.label.set_text(fmt(self.remaining))
        elif self.remaining == 0 and self.label.get_style_context().has_class("done"):
            self.blink = not self.blink
            self.label.set_opacity(0.3 if self.blink else 1.0)
            return True
        self.label.set_opacity(1.0)
        return True


if __name__ == "__main__":
    args = sys.argv[1:]
    initial = next((a for a in args if not a.startswith("--")), None)
    pomodoro = "--pomodoro" in args
    win = FloatingTimer(initial=initial, pomodoro=pomodoro,
                        auto=not (initial or pomodoro or "--manual" in args))
    if "--settings" in args:
        win.open_settings()
    Gtk.main()
