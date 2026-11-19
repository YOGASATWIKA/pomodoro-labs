"""Bunyi "tit": buat WAV pendek sendiri (stdlib) lalu putar lewat Qt di semua OS."""
import math
import os
import struct
import wave

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QSoundEffect

from .config import cache_dir

_effects = {}


def tit_file(freq, volume):
    """File bunyi "tit" pendek (0.15 detik) untuk nada & volume tertentu."""
    path = os.path.join(cache_dir(), f"tit-{int(freq)}-{int(volume)}.wav")
    if not os.path.exists(path):
        os.makedirs(cache_dir(), exist_ok=True)
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


def _effect(path):
    eff = _effects.get(path)
    if eff is None:
        eff = QSoundEffect()
        eff.setSource(QUrl.fromLocalFile(path))
        _effects[path] = eff
    return eff


def play_tits(count, freq, volume, gap):
    """Bunyikan `count` kali, berjeda `gap` ms."""
    eff = _effect(tit_file(freq, volume))
    for i in range(int(count)):
        QTimer.singleShot(int(i * gap), eff.play)
