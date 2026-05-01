import questionary
import sys
import os

# Menambahkan path project agar bisa mengimpor modul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from processor import process_clip
from clipper import download_video, run_auto_mode, run_manual_mode

def main():
    print("=== YouTube Clipper Interactive ===")
    
    url = questionary.text("Masukkan URL Video YouTube:").ask()
    if not url:
        return

    mode = questionary.select(
        "Pilih Mode Potongan Video:",
        choices=["Full Screen (Crop)", "Blur Background"]
    ).ask()
    blur_mode = (mode == "Blur Background")

    face_tracking = questionary.confirm("Aktifkan Face Tracking?").ask()
    auto_highlight = questionary.confirm("Gunakan Auto Generate (AI Highlight)?").ask()

    clips = []
    if auto_highlight:
        max_clips = int(questionary.text("Jumlah maksimal klip (AI Highlight):", default="3").ask())
        min_dur = int(questionary.text("Durasi minimum klip (detik):", default="15").ask())
        max_dur = int(questionary.text("Durasi maksimum klip (detik):", default="60").ask())
    else:
        batch_mode = questionary.confirm("Ingin melakukan Batch Processing (banyak klip sekaligus)?").ask()
        if batch_mode:
            print("Masukkan rentang waktu (Contoh: 00:10-00:30, 01:00-01:30)")
            ranges = questionary.text("Rentang waktu (dipisah koma):").ask()
            if ranges:
                ranges_list = [r.strip() for r in ranges.split(',')]
                for r in ranges_list:
                    start, end = r.split('-')
                    clips.append((start, end))
        else:
            start = questionary.text("Waktu mulai (MM:SS):").ask()
            end = questionary.text("Waktu selesai (MM:SS):").ask()
            clips.append((start, end))

    # Download
    print("Mengunduh video...")
    video_path = download_video(url, output_dir="output")
    
    if not video_path:
        print("[ERROR] Gagal mengunduh video")
        return

    # Proses
    if auto_highlight:
        print("Menjalankan AI Auto Highlight...")
        run_auto_mode(
            video_path=video_path,
            output_dir="output",
            max_clips=max_clips,
            min_duration=min_dur,
            max_duration=max_dur,
            quality='high',
            use_face_tracking=face_tracking
        )
    else:
        for i, (s, e) in enumerate(clips):
            print(f"Memproses klip {i+1}: {s} - {e}")
            s_sec = sum(x * int(t) for x, t in zip([60, 1], s.split(':')))
            e_sec = sum(x * int(t) for x, t in zip([60, 1], e.split(':')))
            
            process_clip(
                input_path=video_path,
                start_time=s_sec,
                end_time=e_sec,
                output_dir="output",
                clip_index=i+1,
                use_face_tracking=face_tracking,
                blur_background=blur_mode,
                verbose=True
            )
    
    print("Selesai!")

if __name__ == "__main__":
    main()
