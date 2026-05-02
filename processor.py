#!/usr/bin/env python3
"""
Modul untuk memproses video menjadi format TikTok/Reels
Output: Portrait 9:16, video di-crop untuk memenuhi layar (center crop)
"""

import os
import subprocess
import re
from typing import Optional, Callable
from datetime import datetime
from tracker import analyze_faces


# Konfigurasi kualitas video
QUALITY_PRESETS = {
    'low': {
        'resolution': '720x1280',
        'bitrate': '2M',
        'crf': 28,
        'preset': 'fast'
    },
    'medium': {
        'resolution': '1080x1920',
        'bitrate': '5M',
        'crf': 23,
        'preset': 'medium'
    },
    'high': {
        'resolution': '1080x1920',
        'bitrate': '8M',
        'crf': 18,
        'preset': 'slow'
    }
}


def process_clip(
    input_path: str,
    start_time: float,
    end_time: float,
    output_dir: str,
    quality: str = 'high',
    clip_index: Optional[int] = None,
    use_face_tracking: bool = False,
    blur_background: bool = False,
    verbose: bool = False,
    progress_callback: Optional[Callable[[float], None]] = None
) -> Optional[str]:
    """
    Proses clip menjadi format TikTok (9:16 portrait dengan center crop, face tracking, atau blur background)

    Args:
        input_path: Path ke file video input
        start_time: Waktu mulai clip dalam detik
        end_time: Waktu akhir clip dalam detik
        output_dir: Folder untuk menyimpan output
        quality: Preset kualitas (low, medium, high)
        clip_index: Index clip untuk penamaan (opsional)
        use_face_tracking: Gunakan AI face tracking
        blur_background: Gunakan background blur jika aspect ratio tidak pas
        verbose: Tampilkan output detail
        progress_callback: Callback untuk melaporkan progress (0.0 - 1.0)

    Returns:
        Path ke file output atau None jika gagal
    """
    # Validasi input
    if not os.path.exists(input_path):
        print(f"[ERROR] File tidak ditemukan: {input_path}")
        return None

    if start_time >= end_time:
        print("[ERROR] Waktu mulai harus lebih kecil dari waktu akhir")
        return None

    # Dapatkan preset kualitas
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS['high'])
    width, height = map(int, preset['resolution'].split('x'))

    # Generate nama output file
    output_path = _generate_output_path(input_path, output_dir, clip_index)
    
    # Handle face tracking
    tracking_cmd_path = None
    if use_face_tracking:
        if verbose:
            print("[INFO] Menganalisis wajah untuk tracking...")
        
        tracking_cmd_path = output_path + ".tracker.txt"
        
        # Tracker progress is first 50%
        def tracker_progress(p):
            if progress_callback:
                progress_callback(p * 0.5)

        success = analyze_faces(
            video_path=input_path,
            start_time=start_time,
            duration=end_time - start_time,
            target_width=width,
            target_height=height,
            output_cmd_path=tracking_cmd_path,
            progress_callback=tracker_progress if progress_callback else None
        )
        
        if not success:
            print("[WARNING] Face tracking gagal atau tidak ditemukan wajah. Menggunakan center crop.")
            tracking_cmd_path = None

    if verbose:
        print(f"[INFO] Memproses clip: {start_time:.2f}s - {end_time:.2f}s")
        print(f"[INFO] Output: {output_path}")
        print(f"[INFO] Kualitas: {quality} ({preset['resolution']})")
        if tracking_cmd_path:
            print(f"[INFO] Mode: Face Tracking")
        elif blur_background:
            print(f"[INFO] Mode: Blur Background")
        else:
            print(f"[INFO] Mode: Center Crop")

    # Hitung durasi
    duration = end_time - start_time

    # FFmpeg progress is second 50% if tracking is used, otherwise 100%
    def ffmpeg_progress(p):
        if progress_callback:
            if use_face_tracking:
                progress_callback(0.5 + p * 0.5)
            else:
                progress_callback(p)

    # Build FFmpeg command untuk TikTok format
    success = _run_ffmpeg_tiktok(
        input_path=input_path,
        output_path=output_path,
        start_time=start_time,
        duration=duration,
        preset=preset,
        tracking_cmd_path=tracking_cmd_path,
        blur_background=blur_background,
        verbose=verbose,
        progress_callback=ffmpeg_progress if progress_callback else None
    )

    # Cleanup tracking file
    if tracking_cmd_path and os.path.exists(tracking_cmd_path):
        os.remove(tracking_cmd_path)

    if success and os.path.exists(output_path):
        # Ensure 100% progress at the end
        if progress_callback:
            progress_callback(1.0)
        return output_path
    else:
        return None


def _generate_output_path(input_path: str, output_dir: str, clip_index: Optional[int]) -> str:
    """
    Generate nama file output yang unik
    """
    # Pastikan folder output ada
    os.makedirs(output_dir, exist_ok=True)

    # Ambil nama base dari input
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # Sanitize nama file (hapus karakter yang tidak valid)
    base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_'))[:50]

    # Tambahkan timestamp untuk keunikan
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Buat nama file
    if clip_index is not None:
        filename = f"{base_name}_clip{clip_index}_{timestamp}.mp4"
    else:
        filename = f"{base_name}_tiktok_{timestamp}.mp4"

    return os.path.join(output_dir, filename)


def _run_ffmpeg_tiktok(
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    preset: dict,
    tracking_cmd_path: Optional[str] = None,
    blur_background: bool = False,
    verbose: bool = False,
    progress_callback: Optional[Callable[[float], None]] = None
) -> bool:
    """
    Jalankan FFmpeg untuk membuat video TikTok format

    Format output:
    - Aspect ratio 9:16 (portrait)
    - Center crop, Face Tracking, atau Blur Background
    """
    # Parse resolusi
    width, height = map(int, preset['resolution'].split('x'))

    if tracking_cmd_path:
        # Gunakan sendcmd untuk tracking dinamis
        rel_path = os.path.relpath(tracking_cmd_path).replace('\\', '/')
        rel_path = rel_path.replace("'", "'\\\\\\''")
        video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,sendcmd=f='{rel_path}',crop={width}:{height}"
        current_preset = preset['preset']
    elif blur_background:
        # Sederhanakan filter untuk memastikan eksekusi
        # 1. Scale background ke 1080x1920 dan blur
        # 2. Scale foreground (original) ke fit
        # 3. Overlay
        video_filter = (
            f"split[bg][fg];"
            f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=20[bg];"
            f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        current_preset = 'faster'
    else:
        # Center crop statis
        video_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        current_preset = preset['preset']

    # Build command
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output
        '-ss', str(start_time),  # Start time
        '-i', input_path,
        '-t', str(duration),  # Duration
        '-vf', video_filter,
        '-map', '0:v',
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-preset', current_preset,
        '-crf', str(preset['crf']),
        '-maxrate', preset['bitrate'],
        '-bufsize', str(int(preset['bitrate'].replace('M', '')) * 2) + 'M',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '44100',
        '-movflags', '+faststart',
        output_path
    ]

    if verbose:
        print(f"[DEBUG] FFmpeg command: {' '.join(cmd)}")

    try:
        # Jalankan FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        for line in process.stdout:
            if verbose:
                print(line, end='')
            
            # Parse progress
            # time=00:00:07.40
            match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
            if match and progress_callback:
                hours, minutes, seconds = map(float, match.groups())
                current_time = hours * 3600 + minutes * 60 + seconds
                progress = min(1.0, current_time / duration)
                progress_callback(progress)

        process.wait()

        if process.returncode != 0:
            return False

        return True

    except Exception as e:
        print(f"[ERROR] Gagal memproses video: {str(e)}")
        return False


def process_clip_simple(
    input_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    verbose: bool = False
) -> bool:
    """
    Proses clip tanpa konversi format (simple cut)
    Berguna untuk testing atau jika user tidak butuh format TikTok
    """
    duration = end_time - start_time

    cmd = [
        'ffmpeg',
        '-y',
        '-ss', str(start_time),
        '-i', input_path,
        '-t', str(duration),
        '-c', 'copy',  # Stream copy (no re-encoding)
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300
        )

        return result.returncode == 0

    except Exception:
        return False


def get_video_info(video_path: str) -> Optional[dict]:
    """
    Dapatkan informasi video (resolusi, durasi, codec, dll)
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,codec_name,r_frame_rate',
            '-show_entries', 'format=duration,size',
            '-of', 'json',
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

        import json
        data = json.loads(result.stdout)

        stream = data.get('streams', [{}])[0]
        format_info = data.get('format', {})

        # Parse frame rate
        fps_str = stream.get('r_frame_rate', '30/1')
        try:
            num, den = map(int, fps_str.split('/'))
            fps = num / den if den else 30
        except ValueError:
            fps = 30

        return {
            'width': stream.get('width'),
            'height': stream.get('height'),
            'duration': float(format_info.get('duration', 0)),
            'codec': stream.get('codec_name'),
            'fps': fps,
            'size': int(format_info.get('size', 0))
        }

    except Exception:
        return None


def create_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 0,
    size: str = '320x180'
) -> bool:
    """
    Buat thumbnail dari video pada timestamp tertentu
    """
    cmd = [
        'ffmpeg',
        '-y',
        '-ss', str(timestamp),
        '-i', video_path,
        '-vframes', '1',
        '-s', size,
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )

        return result.returncode == 0

    except Exception:
        return False
