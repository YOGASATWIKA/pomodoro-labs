# Pomodoro Labs

Timer kecil yang **melayang di atas jendela lain**, dengan mode Pomodoro dan mode otomatis yang mengikuti jadwal kerja. Jalan di **Linux, macOS, dan Windows**. Bagian dari ekosistem CP Labs.

## Fitur
- Selalu di atas jendela lain, bisa diseret, transparansi dan ukuran angka bisa diatur
- Pomodoro (default 25 / 5 / 10 menit, 4 sesi) dan timer manual
- Mode otomatis mengikuti jadwal kerja per hari, termasuk istirahat siang
- Bunyi "tit" per kejadian, dengan nada, volume, dan jeda yang bisa diatur
- Notifikasi sistem saat fase berganti
- Pengaturan lewat klik kanan atau tombol ⚙

## Pasang
Butuh Python 3.9+ dan [pipx](https://pipx.pypa.io):

```bash
pipx install git+https://github.com/YOGASATWIKA/pomodoro-labs.git
pomodoro-labs
```

Opsional, buat shortcut di menu aplikasi (Linux `.desktop`, Windows Start Menu, macOS `~/Applications`):

```bash
pomodoro-labs --install-shortcut
```

> PySide6 (Qt) berukuran cukup besar (~100 MB+) saat diunduh pertama kali.

### Catatan per OS
| OS | Catatan |
|---|---|
| **Linux (X11)** | Qt 6.5+ butuh `libxcb-cursor0`: `sudo apt install libxcb-cursor0` (Fedora: `xcb-util-cursor`, Arch: `xcb-util-cursor`). |
| **Linux (Wayland)** | Sebagian compositor mengabaikan "selalu di atas". Jika terjadi, jalankan dengan `QT_QPA_PLATFORM=xcb pomodoro-labs` (XWayland). |
| **macOS** | Notifikasi muncul lewat ikon di menu bar. Belum diuji di perangkat sungguhan. |
| **Windows** | Belum diuji di perangkat sungguhan. Laporan hasil sangat dihargai. |

## Pemakaian
```
pomodoro-labs                      mode otomatis (ikut jadwal kerja)
pomodoro-labs --manual             timer manual
pomodoro-labs [menit]              timer manual langsung mulai, contoh: 25 atau 1:30
pomodoro-labs --pomodoro           Pomodoro manual langsung mulai
pomodoro-labs --settings           buka Pengaturan saat start
pomodoro-labs --install-shortcut   buat shortcut aplikasi
```
Seret jendela untuk memindahkan, klik kanan untuk Pengaturan, `Esc` untuk menutup.

Pengaturan disimpan di:
- Linux: `~/.config/pomodoro-labs/config.json`
- macOS: `~/Library/Application Support/pomodoro-labs/config.json`
- Windows: `%APPDATA%\pomodoro-labs\config.json`

Config dari versi lama (`~/.config/timer-melayang`) disalin otomatis satu kali.

## Pengembangan
```bash
git clone https://github.com/YOGASATWIKA/pomodoro-labs.git
cd pomodoro-labs
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen pytest
```
Struktur: `timing.py` (logika waktu murni), `config.py` (pengaturan & path per OS), `sound.py`, `platform_.py` (notifikasi & shortcut), `timer_window.py`, `settings_window.py`.

## Lisensi
MIT
