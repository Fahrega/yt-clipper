#!/usr/bin/env python3
"""
YouTube Clipper CLI - Entry Point
Tool untuk membuat clip dari video YouTube dalam format TikTok (portrait 9:16)
"""

import argparse
import sys
import os
from typing import Optional, List, Tuple

from downloader import download_video
from detector import detect_highlights
from processor import process_clip
from utils import validate_url, parse_time, format_time, ensure_output_dir


def parse_arguments() -> argparse.Namespace:
    """
    Parse argumen command line untuk CLI
    """
    parser = argparse.ArgumentParser(
        description='YouTube Clipper - Buat clip TikTok dari video YouTube',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Contoh penggunaan:
  # Mode manual
  python clipper.py --url "https://youtube.com/watch?v=..." --start 01:30 --end 02:00

  # Mode otomatis
  python clipper.py --url "https://youtube.com/watch?v=..." --auto --max-clips 5

  # Mode otomatis dalam rentang waktu tertentu
  python clipper.py --url "https://youtube.com/watch?v=..." --auto --start 05:00 --end 15:00
        '''
    )

    # Argumen wajib
    parser.add_argument(
        '--url', '-u',
        type=str,
        required=True,
        help='URL video YouTube yang akan di-clip'
    )

    # Mode selection
    parser.add_argument(
        '--auto', '-a',
        action='store_true',
        help='Mode otomatis: deteksi highlight berdasarkan audio dan visual'
    )

    # Time range (untuk mode manual atau membatasi mode auto)
    parser.add_argument(
        '--start', '-s',
        type=str,
        default=None,
        help='Waktu mulai clip (format: MM:SS atau HH:MM:SS)'
    )

    parser.add_argument(
        '--end', '-e',
        type=str,
        default=None,
        help='Waktu akhir clip (format: MM:SS atau HH:MM:SS)'
    )

    # Opsi mode otomatis
    parser.add_argument(
        '--max-clips', '-m',
        type=int,
        default=5,
        help='Jumlah maksimal clip yang dihasilkan dalam mode auto (default: 5)'
    )

    parser.add_argument(
        '--min-duration',
        type=int,
        default=15,
        help='Durasi minimum clip dalam detik (default: 15)'
    )

    parser.add_argument(
        '--max-duration',
        type=int,
        default=60,
        help='Durasi maksimum clip dalam detik (default: 60)'
    )

    # Output options
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output',
        help='Folder output untuk menyimpan hasil clip (default: output)'
    )

    parser.add_argument(
        '--quality', '-q',
        type=str,
        choices=['low', 'medium', 'high'],
        default='high',
        help='Kualitas output video (default: high)'
    )

    # Face Tracking options
    parser.add_argument(
        '--face-track', '-ft',
        action='store_true',
        help='Gunakan AI face tracking (memprioritaskan wajah di tengah)'
    )

    # Debug options
    parser.add_argument(
        '--keep-original',
        action='store_true',
        help='Simpan video original yang didownload'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Tampilkan output detail untuk debugging'
    )

    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> Tuple[bool, str]:
    """
    Validasi argumen yang diberikan user
    Returns: (is_valid, error_message)
    """
    # Validasi URL
    if not validate_url(args.url):
        return False, f"URL tidak valid: {args.url}"

    # Validasi mode manual: harus ada start dan end
    if not args.auto:
        if args.start is None or args.end is None:
            return False, "Mode manual membutuhkan --start dan --end"

        start_seconds = parse_time(args.start)
        end_seconds = parse_time(args.end)

        if start_seconds is None:
            return False, f"Format waktu start tidak valid: {args.start}"
        if end_seconds is None:
            return False, f"Format waktu end tidak valid: {args.end}"
        if start_seconds >= end_seconds:
            return False, "Waktu start harus lebih kecil dari waktu end"

    # Validasi durasi
    if args.min_duration < 5:
        return False, "Durasi minimum tidak boleh kurang dari 5 detik"
    if args.max_duration > 180:
        return False, "Durasi maksimum tidak boleh lebih dari 180 detik"
    if args.min_duration > args.max_duration:
        return False, "Durasi minimum tidak boleh lebih besar dari durasi maksimum"

    # Validasi max clips
    if args.max_clips < 1:
        return False, "Jumlah maksimal clip minimal 1"
    if args.max_clips > 20:
        return False, "Jumlah maksimal clip tidak boleh lebih dari 20"

    return True, ""


def run_manual_mode(
    video_path: str,
    start_time: str,
    end_time: str,
    output_dir: str,
    quality: str,
    use_face_tracking: bool = False,
    verbose: bool = False
) -> Optional[str]:
    """
    Jalankan mode manual: clip video dari start ke end time
    Returns: path ke file output atau None jika gagal
    """
    start_seconds = parse_time(start_time)
    end_seconds = parse_time(end_time)

    if verbose:
        print(f"[INFO] Mode Manual: {start_time} - {end_time}")
        print(f"[INFO] Durasi: {end_seconds - start_seconds} detik")

    # Proses clip
    output_path = process_clip(
        input_path=video_path,
        start_time=start_seconds,
        end_time=end_seconds,
        output_dir=output_dir,
        quality=quality,
        use_face_tracking=use_face_tracking,
        verbose=verbose
    )

    return output_path


def run_auto_mode(
    video_path: str,
    output_dir: str,
    max_clips: int,
    min_duration: int,
    max_duration: int,
    quality: str,
    use_face_tracking: bool = False,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    verbose: bool = False
) -> List[str]:
    """
    Jalankan mode otomatis: deteksi highlight dan buat clip
    Returns: list path ke file output
    """
    # Parse time range jika ada
    start_seconds = parse_time(start_time) if start_time else None
    end_seconds = parse_time(end_time) if end_time else None

    if verbose:
        print(f"[INFO] Mode Otomatis: max {max_clips} clips")
        print(f"[INFO] Durasi: {min_duration}-{max_duration} detik per clip")
        if start_seconds is not None:
            print(f"[INFO] Rentang pencarian: {start_time} - {end_time}")

    # Deteksi highlight
    highlights = detect_highlights(
        video_path=video_path,
        max_highlights=max_clips,
        min_duration=min_duration,
        max_duration=max_duration,
        start_time=start_seconds,
        end_time=end_seconds,
        verbose=verbose
    )

    if not highlights:
        print("[WARNING] Tidak ditemukan highlight yang signifikan")
        return []

    if verbose:
        print(f"[INFO] Ditemukan {len(highlights)} highlight")

    # Proses setiap highlight menjadi clip
    output_paths = []
    for i, (hl_start, hl_end, score) in enumerate(highlights):
        if verbose:
            print(f"\n[INFO] Memproses clip {i+1}/{len(highlights)}")
            print(f"[INFO] Waktu: {format_time(hl_start)} - {format_time(hl_end)}")
            print(f"[INFO] Skor highlight: {score:.2f}")

        output_path = process_clip(
            input_path=video_path,
            start_time=hl_start,
            end_time=hl_end,
            output_dir=output_dir,
            quality=quality,
            clip_index=i+1,
            use_face_tracking=use_face_tracking,
            verbose=verbose
        )

        if output_path:
            output_paths.append(output_path)

    return output_paths


def main() -> int:
    """
    Fungsi utama CLI
    Returns: exit code (0 = sukses, 1 = error)
    """
    # Parse argumen
    args = parse_arguments()

    # Validasi argumen
    is_valid, error_msg = validate_arguments(args)
    if not is_valid:
        print(f"[ERROR] {error_msg}")
        return 1

    # Pastikan folder output ada
    output_dir = ensure_output_dir(args.output)
    if args.verbose:
        print(f"[INFO] Output folder: {output_dir}")

    try:
        # Download video
        print(f"[INFO] Mengunduh video dari: {args.url}")
        video_path = download_video(
            url=args.url,
            output_dir=output_dir,
            verbose=args.verbose
        )

        if not video_path:
            print("[ERROR] Gagal mengunduh video")
            return 1

        print(f"[INFO] Video berhasil diunduh: {video_path}")

        # Tanya user soal face tracking jika belum ditentukan via flag
        use_face_tracking = args.face_track
        if not use_face_tracking:
            try:
                choice = input("\nGunakan AI Face Tracking? (Mengikuti wajah agar selalu di tengah) [y/N]: ").lower()
                if choice == 'y':
                    use_face_tracking = True
            except EOFError:
                # Handle non-interactive environments
                use_face_tracking = False

        # Jalankan mode yang dipilih
        if args.auto:
            # Mode otomatis
            output_paths = run_auto_mode(
                video_path=video_path,
                output_dir=output_dir,
                max_clips=args.max_clips,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                quality=args.quality,
                use_face_tracking=use_face_tracking,
                start_time=args.start,
                end_time=args.end,
                verbose=args.verbose
            )

            if output_paths:
                print(f"\n[SUCCESS] Berhasil membuat {len(output_paths)} clip:")
                for path in output_paths:
                    print(f"  - {path}")
            else:
                print("[WARNING] Tidak ada clip yang dihasilkan")

        else:
            # Mode manual
            output_path = run_manual_mode(
                video_path=video_path,
                start_time=args.start,
                end_time=args.end,
                output_dir=output_dir,
                quality=args.quality,
                use_face_tracking=use_face_tracking,
                verbose=args.verbose
            )

            if output_path:
                print(f"\n[SUCCESS] Clip berhasil dibuat: {output_path}")
            else:
                print("[ERROR] Gagal membuat clip")
                return 1

        # Cleanup: hapus video original jika tidak diminta untuk disimpan
        if not args.keep_original and os.path.exists(video_path):
            os.remove(video_path)
            if args.verbose:
                print(f"[INFO] Video original dihapus: {video_path}")

        return 0

    except KeyboardInterrupt:
        print("\n[INFO] Proses dibatalkan oleh user")
        return 1
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
