#!/usr/bin/env python3
"""
Modul untuk mendownload video dari YouTube menggunakan yt-dlp
"""

import os
import subprocess
import json
from typing import Optional, Dict, Any


def get_video_info(url: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Ambil informasi video dari YouTube tanpa mendownload

    Args:
        url: URL video YouTube
        verbose: Tampilkan output detail

    Returns:
        Dictionary berisi info video atau None jika gagal
    """
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            url
        ]

        if verbose:
            print(f"[DEBUG] Mengambil info video: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            if verbose:
                print(f"[DEBUG] Error: {result.stderr}")
            return None

        info = json.loads(result.stdout)
        return info

    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout saat mengambil info video")
        return None
    except json.JSONDecodeError:
        print("[ERROR] Gagal parse info video")
        return None
    except FileNotFoundError:
        print("[ERROR] yt-dlp tidak ditemukan. Install dengan: pip install yt-dlp")
        return None
    except Exception as e:
        if verbose:
            print(f"[DEBUG] Exception: {str(e)}")
        return None


def download_video(
    url: str,
    output_dir: str = 'output',
    quality: str = 'best',
    verbose: bool = False
) -> Optional[str]:
    """
    Download video dari YouTube

    Args:
        url: URL video YouTube
        output_dir: Folder tujuan download
        quality: Kualitas video (best, worst, atau format spesifik)
        verbose: Tampilkan output detail

    Returns:
        Path ke file video yang didownload atau None jika gagal
    """
    # Pastikan folder output ada
    os.makedirs(output_dir, exist_ok=True)

    # Template nama file output
    output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    # Konfigurasi format berdasarkan quality
    if quality == 'best':
        format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    elif quality == 'worst':
        format_spec = 'worstvideo+worstaudio/worst'
    else:
        # Gunakan format yang diberikan langsung
        format_spec = quality

    try:
        # Command untuk download
        cmd = [
            'yt-dlp',
            '-f', format_spec,
            '-o', output_template,
            '--merge-output-format', 'mp4',
            '--no-playlist',  # Hanya download satu video, bukan playlist
            '--print', 'after_move:filepath',  # Print path file setelah selesai
            url
        ]

        if verbose:
            print(f"[DEBUG] Menjalankan: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 menit timeout untuk download
        )

        if result.returncode != 0:
            print(f"[ERROR] Gagal download: {result.stderr}")
            return None

        # Ambil path file dari output
        output_path = result.stdout.strip().split('\n')[-1]

        if os.path.exists(output_path):
            return output_path

        # Fallback: cari file yang baru dibuat di output_dir
        return _find_latest_video(output_dir)

    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout saat mendownload video")
        return None
    except FileNotFoundError:
        print("[ERROR] yt-dlp tidak ditemukan. Install dengan: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"[ERROR] Gagal download: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None


def _find_latest_video(directory: str) -> Optional[str]:
    """
    Cari file video terbaru di direktori

    Args:
        directory: Path direktori untuk dicari

    Returns:
        Path ke file video terbaru atau None
    """
    video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov']

    latest_file = None
    latest_time = 0

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        # Skip jika bukan file
        if not os.path.isfile(filepath):
            continue

        # Check ekstensi
        _, ext = os.path.splitext(filename)
        if ext.lower() not in video_extensions:
            continue

        # Bandingkan waktu modifikasi
        mtime = os.path.getmtime(filepath)
        if mtime > latest_time:
            latest_time = mtime
            latest_file = filepath

    return latest_file


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Dapatkan durasi video dalam detik menggunakan ffprobe

    Args:
        video_path: Path ke file video

    Returns:
        Durasi dalam detik atau None jika gagal
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        return float(result.stdout.strip())

    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return None


def extract_audio(video_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Ekstrak audio dari video untuk analisis

    Args:
        video_path: Path ke file video
        output_path: Path output untuk audio (opsional)

    Returns:
        Path ke file audio atau None jika gagal
    """
    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_audio.wav"

    try:
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '22050',  # Sample rate untuk librosa
            '-ac', '1',  # Mono
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            return None

        if os.path.exists(output_path):
            return output_path

        return None

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
