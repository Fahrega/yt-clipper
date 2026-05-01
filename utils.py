"""
utils.py - Helper functions untuk YouTube Clipper CLI

Berisi fungsi-fungsi utilitas seperti validasi URL, parsing waktu,
dan generate nama file output.
"""

import re
import os
from datetime import datetime
from typing import Optional, Tuple


def validate_youtube_url(url: str) -> bool:
    """
    Validasi apakah URL adalah URL YouTube yang valid.

    Args:
        url: String URL yang akan divalidasi

    Returns:
        True jika URL valid, False jika tidak

    Examples:
        >>> validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        True
        >>> validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        True
        >>> validate_youtube_url("https://google.com")
        False
    """
    # Pola regex untuk berbagai format URL YouTube
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
    ]

    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False


def extract_video_id(url: str) -> Optional[str]:
    """
    Ekstrak video ID dari URL YouTube.

    Args:
        url: URL YouTube

    Returns:
        Video ID atau None jika tidak ditemukan
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([\w-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def parse_time(time_str: str) -> float:
    """
    Konversi string waktu ke detik.

    Mendukung format:
    - "MM:SS" (contoh: "01:30" -> 90 detik)
    - "HH:MM:SS" (contoh: "01:30:00" -> 5400 detik)
    - "SS" (contoh: "90" -> 90 detik)

    Args:
        time_str: String waktu dalam format yang didukung

    Returns:
        Jumlah detik sebagai float

    Raises:
        ValueError: Jika format waktu tidak valid
    """
    time_str = time_str.strip()

    # Cek jika hanya angka (detik)
    if time_str.isdigit():
        return float(time_str)

    # Cek format dengan titik dua
    parts = time_str.split(':')

    if len(parts) == 2:
        # Format MM:SS
        minutes, seconds = parts
        try:
            return int(minutes) * 60 + float(seconds)
        except ValueError:
            raise ValueError(f"Format waktu tidak valid: {time_str}")

    elif len(parts) == 3:
        # Format HH:MM:SS
        hours, minutes, seconds = parts
        try:
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except ValueError:
            raise ValueError(f"Format waktu tidak valid: {time_str}")

    raise ValueError(f"Format waktu tidak valid: {time_str}. Gunakan MM:SS atau HH:MM:SS")


def format_time(seconds: float) -> str:
    """
    Konversi detik ke string waktu format MM:SS atau HH:MM:SS.

    Args:
        seconds: Jumlah detik

    Returns:
        String waktu terformat

    Examples:
        >>> format_time(90)
        "01:30"
        >>> format_time(3661)
        "01:01:01"
    """
    if seconds < 0:
        raise ValueError("Detik tidak boleh negatif")

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_output_filename(video_id: str, start_time: float, end_time: float,
                            output_dir: str = "output") -> str:
    """
    Generate nama file output yang unik untuk clip.

    Format: {video_id}_{start}-{end}_{timestamp}.mp4

    Args:
        video_id: ID video YouTube
        start_time: Waktu mulai dalam detik
        end_time: Waktu selesai dalam detik
        output_dir: Direktori output

    Returns:
        Path lengkap file output
    """
    # Buat direktori output jika belum ada
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Format waktu untuk nama file
    start_str = format_time(start_time).replace(':', '-')
    end_str = format_time(end_time).replace(':', '-')

    # Timestamp untuk keunikan
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{video_id}_{start_str}_to_{end_str}_{timestamp}.mp4"
    return os.path.join(output_dir, filename)


def validate_time_range(start: float, end: float, duration: Optional[float] = None) -> Tuple[bool, str]:
    """
    Validasi rentang waktu clip.

    Args:
        start: Waktu mulai dalam detik
        end: Waktu selesai dalam detik
        duration: Durasi total video (opsional)

    Returns:
        Tuple (is_valid, error_message)
    """
    if start < 0:
        return False, "Waktu mulai tidak boleh negatif"

    if end <= start:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"

    if duration is not None:
        if start >= duration:
            return False, f"Waktu mulai ({start}s) melebihi durasi video ({duration}s)"
        if end > duration:
            return False, f"Waktu selesai ({end}s) melebihi durasi video ({duration}s)"

    # Cek durasi clip minimum (3 detik) dan maksimum (180 detik untuk TikTok)
    clip_duration = end - start
    if clip_duration < 3:
        return False, "Durasi clip minimal 3 detik"
    if clip_duration > 180:
        return False, "Durasi clip maksimal 180 detik (3 menit) untuk format TikTok"

    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    Bersihkan nama file dari karakter yang tidak valid.

    Args:
        filename: Nama file yang akan dibersihkan

    Returns:
        Nama file yang sudah dibersihkan
    """
    # Karakter yang tidak diizinkan di Windows
    invalid_chars = '<>:"/\\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Hapus spasi di awal dan akhir
    filename = filename.strip()

    # Batasi panjang nama file
    if len(filename) > 200:
        filename = filename[:200]

    return filename


# Alias untuk backward compatibility
def validate_url(url: str) -> bool:
    """
    Alias untuk validate_youtube_url untuk backward compatibility.
    """
    return validate_youtube_url(url)


def ensure_output_dir(output_dir: str) -> str:
    """
    Pastikan direktori output ada, buat jika belum ada.

    Args:
        output_dir: Path direktori output

    Returns:
        Path direktori output (absolut)
    """
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    return output_dir
