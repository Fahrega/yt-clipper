# YouTube Clipper CLI

Tool untuk membuat clip dari video YouTube dalam format TikTok (portrait 9:16).

## Persiapan

Pastikan Anda sudah menginstal *dependencies* yang diperlukan:
```bash
pip install -r requirements.txt
```

## Penggunaan

### 1. Mode Manual (Menentukan Waktu Sendiri)
Gunakan mode ini jika Anda sudah mengetahui bagian video mana yang ingin dijadikan clip.
```bash
python clipper.py --url "URL_VIDEO_YOUTUBE" --start 01:30 --end 02:00
```

### 2. Mode Otomatis (Deteksi Highlight AI)
Biarkan aplikasi mencari bagian menarik dalam video berdasarkan analisis audio dan visual.
```bash
python clipper.py --url "URL_VIDEO_YOUTUBE" --auto --max-clips 3
```

### 3. Opsi Tambahan
*   **Face Tracking:** Menjaga wajah subjek tetap di tengah video (disarankan untuk konten *talking head*).
    *   Tambahkan flag `--face-track` atau `-ft`.
*   **Kualitas Video:** Mengatur kualitas output (low/medium/high).
    *   Contoh: `--quality medium`
*   **Membatasi Pencarian (Mode Auto):** Membatasi deteksi highlight pada rentang waktu tertentu.
    *   Contoh: `python clipper.py --url "URL" --auto --start 05:00 --end 15:00`
*   **Menyimpan File Original:** Jika ingin menyimpan file video asli YouTube setelah proses selesai (defaultnya akan dihapus).
    *   Tambahkan flag `--keep-original`.

## Ringkasan Parameter Utama

| Flag | Deskripsi |
| :--- | :--- |
| `--url` / `-u` | Link video YouTube (Wajib). |
| `--auto` / `-a` | Mengaktifkan deteksi highlight otomatis. |
| `--start` / `-s` | Waktu mulai (format `MM:SS` atau `HH:MM:SS`). |
| `--end` / `-e` | Waktu selesai (format `MM:SS` atau `HH:MM:SS`). |
| `--face-track` / `-ft` | Mengaktifkan AI untuk memposisikan wajah di tengah. |
| `--output` / `-o` | Lokasi folder penyimpanan hasil (Default: `output/`). |
| `--keep-original` | Menyimpan file video asli setelah pemrosesan. |

Untuk bantuan lengkap, jalankan:
```bash
python clipper.py --help
```
