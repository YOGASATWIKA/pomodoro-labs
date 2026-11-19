# Pomodoro Labs

Timer kecil yang **melayang di atas jendela lain**, dengan mode Pomodoro dan mode otomatis yang mengikuti jadwal kerja. Bagian dari ekosistem CP Labs.

## Fitur
- Selalu di atas jendela lain, bisa diseret, transparansi dan ukuran font bisa diatur
- Pomodoro (default 25 / 5 / 10 menit, 4 sesi) dan timer manual
- Mode otomatis mengikuti jadwal kerja per hari, termasuk istirahat siang
- Bunyi "tit" per kejadian, dengan nada, volume, dan jeda yang bisa diatur
- Pengaturan lewat klik kanan atau tombol ⚙, disimpan di `~/.config/timer-melayang/config.json`

## Kebutuhan
Linux dengan Python 3 dan GTK 3:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

## Pasang
```bash
git clone https://github.com/YOGASATWIKA/pomodoro-labs.git
cd pomodoro-labs
./install.sh            # salin ke ~/.local/bin
./install.sh --link     # atau symlink, untuk pengembangan
./install.sh --uninstall
```

## Pemakaian
```
pomodoro-labs                 mode otomatis (ikut jadwal kerja)
pomodoro-labs --manual        timer manual
pomodoro-labs [menit]         timer manual langsung mulai, contoh: 25 atau 1:30
pomodoro-labs --pomodoro      Pomodoro manual langsung mulai
```
Seret jendela untuk memindahkan, klik kanan untuk Pengaturan, `Esc` untuk menutup.

## Lisensi
MIT
