"""Logika waktu murni (tanpa GUI): durasi, fase Pomodoro, dan jadwal kerja."""
from datetime import datetime, timedelta

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

PHASE_NAMES = {"work": "🍅 Fokus", "short": "☕ Istirahat", "long": "🌴 Istirahat panjang",
               "lunch": "🍱 Istirahat siang", "off": "🏠 Di luar jam kerja"}
PHASE_CLASS = {"work": "work", "short": "break", "long": "break", "lunch": "break", "off": "off"}


def parse_duration(text):
    """'25' -> 25 menit, '1:30' -> 1 menit 30 detik, '1:00:00' -> 1 jam."""
    parts = [float(p) for p in text.strip().split(":")]
    if len(parts) == 1:
        return int(parts[0] * 60)
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return int(secs)


def pomodoro_text(pomo):
    return f"{pomo['work']}/{pomo['short']}/{pomo['long']}"


def parse_pomodoro(text, pomo):
    """'25/5/15' -> (fokus, istirahat, istirahat panjang) dalam detik."""
    vals = [parse_duration(p) for p in text.split("/")]
    defaults = [pomo["work"] * 60, pomo["short"] * 60, pomo["long"] * 60]
    vals = (vals + defaults[len(vals):])[:3]
    if min(vals) <= 0:
        raise ValueError
    return dict(zip(("work", "short", "long"), vals))


def advance(phase, session, sessions_before_long):
    """Fase Pomodoro berikutnya: fokus -> istirahat -> fokus ..., panjang tiap N sesi."""
    if phase == "work":
        return ("long" if session >= sessions_before_long else "short"), session
    return "work", (1 if phase == "long" else session + 1)


def work_blocks(schedule, day):
    blocks = []
    for start, end in schedule.get(str(day.weekday()), []):
        s = datetime.combine(day, datetime.strptime(start, "%H:%M").time())
        e = datetime.combine(day, datetime.strptime(end, "%H:%M").time())
        blocks.append((s, e))
    return blocks


def auto_state(now, durations, schedule, sessions_before_long):
    """Keadaan menurut jadwal: (kunci unik, fase, sesi, waktu selesai fase)."""
    blocks = work_blocks(schedule, now.date())
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
                phase, session = advance(phase, session, sessions_before_long)
    for d in range(1, 8):  # cari hari kerja berikutnya
        nxt = work_blocks(schedule, now.date() + timedelta(days=d))
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
