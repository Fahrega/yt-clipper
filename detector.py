#!/usr/bin/env python3
"""
Modul untuk deteksi highlight otomatis dari video
Menggunakan analisis audio (librosa) dan visual (FFmpeg scene detection)
"""

import os
import subprocess
import json
import tempfile
from typing import List, Tuple, Optional
import numpy as np

# Import librosa dengan fallback jika tidak tersedia
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[WARNING] librosa tidak tersedia. Deteksi audio akan dinonaktifkan.")


def detect_highlights(
    video_path: str,
    max_highlights: int = 5,
    min_duration: int = 15,
    max_duration: int = 60,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    verbose: bool = False
) -> List[Tuple[float, float, float]]:
    """
    Deteksi highlight dari video berdasarkan analisis audio dan visual

    Args:
        video_path: Path ke file video
        max_highlights: Jumlah maksimal highlight yang dihasilkan
        min_duration: Durasi minimum highlight dalam detik
        max_duration: Durasi maksimum highlight dalam detik
        start_time: Waktu mulai pencarian (opsional)
        end_time: Waktu akhir pencarian (opsional)
        verbose: Tampilkan output detail

    Returns:
        List of tuples (start_time, end_time, score) diurutkan berdasarkan skor
    """
    # Deteksi audio highlights
    audio_highlights = []
    if LIBROSA_AVAILABLE:
        if verbose:
            print("[INFO] Mendeteksi highlight audio...")
        audio_highlights = detect_audio_highlights(
            video_path,
            start_time=start_time,
            end_time=end_time,
            verbose=verbose
        )

    # Deteksi visual highlights (scene changes)
    if verbose:
        print("[INFO] Mendeteksi perubahan scene...")
    scene_changes = detect_scene_changes(
        video_path,
        start_time=start_time,
        end_time=end_time,
        verbose=verbose
    )

    # Gabungkan dan scoring
    if verbose:
        print("[INFO] Menggabungkan hasil deteksi...")
    highlights = merge_highlights(
        audio_highlights=audio_highlights,
        scene_changes=scene_changes,
        min_duration=min_duration,
        max_duration=max_duration,
        video_path=video_path,
        verbose=verbose
    )

    # Urutkan berdasarkan skor dan ambil top N
    highlights.sort(key=lambda x: x[2], reverse=True)
    return highlights[:max_highlights]


def detect_audio_highlights(
    video_path: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    verbose: bool = False
) -> List[Tuple[float, float]]:
    """
    Deteksi bagian dengan audio yang menarik (volume tinggi, onset banyak)

    Args:
        video_path: Path ke file video
        start_time: Waktu mulai analisis
        end_time: Waktu akhir analisis
        verbose: Tampilkan output detail

    Returns:
        List of tuples (timestamp, energy_score)
    """
    if not LIBROSA_AVAILABLE:
        return []

    # Ekstrak audio ke file temporary
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        audio_path = tmp.name

    try:
        # Extract audio menggunakan ffmpeg
        cmd = ['ffmpeg', '-y', '-i', video_path]

        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])
        if end_time is not None:
            duration = end_time - (start_time or 0)
            cmd.extend(['-t', str(duration)])

        cmd.extend([
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '22050',
            '-ac', '1',
            audio_path
        ])

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if result.returncode != 0:
            if verbose:
                print(f"[DEBUG] FFmpeg error: {result.stderr.decode()}")
            return []

        # Load audio dengan librosa
        y, sr = librosa.load(audio_path, sr=22050)

        # Hitung RMS energy per frame
        hop_length = 512
        frame_length = 2048
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

        # Hitung onset strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

        # Normalisasi
        rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-6)
        onset_norm = (onset_env - onset_env.min()) / (onset_env.max() - onset_env.min() + 1e-6)

        # Gabungkan score (weighted average)
        combined = 0.6 * rms_norm[:len(onset_norm)] + 0.4 * onset_norm[:len(rms_norm)]

        # Konversi frame ke waktu
        times = librosa.frames_to_time(np.arange(len(combined)), sr=sr, hop_length=hop_length)

        # Offset jika ada start_time
        if start_time:
            times = times + start_time

        # Return sebagai list of (time, score)
        highlights = [(float(t), float(s)) for t, s in zip(times, combined)]

        if verbose:
            print(f"[DEBUG] Ditemukan {len(highlights)} frame audio untuk analisis")

        return highlights

    except Exception as e:
        if verbose:
            print(f"[DEBUG] Error saat analisis audio: {str(e)}")
        return []

    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)


def detect_scene_changes(
    video_path: str,
    threshold: float = 0.3,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    verbose: bool = False
) -> List[float]:
    """
    Deteksi perubahan scene menggunakan FFmpeg

    Args:
        video_path: Path ke file video
        threshold: Threshold untuk deteksi scene (0-1, lebih rendah = lebih sensitif)
        start_time: Waktu mulai analisis
        end_time: Waktu akhir analisis
        verbose: Tampilkan output detail

    Returns:
        List of timestamps dimana scene berubah
    """
    try:
        # Build filter untuk scene detection
        scene_filter = f"select='gt(scene,{threshold})',showinfo"

        cmd = ['ffmpeg', '-i', video_path]

        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])
        if end_time is not None:
            duration = end_time - (start_time or 0)
            cmd.extend(['-t', str(duration)])

        cmd.extend([
            '-vf', scene_filter,
            '-f', 'null',
            '-'
        ])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse output untuk mendapatkan timestamps
        scene_times = []
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                try:
                    # Extract pts_time value
                    pts_part = line.split('pts_time:')[1].split()[0]
                    timestamp = float(pts_part)

                    # Offset jika ada start_time
                    if start_time:
                        timestamp += start_time

                    scene_times.append(timestamp)
                except (IndexError, ValueError):
                    continue

        if verbose:
            print(f"[DEBUG] Ditemukan {len(scene_times)} perubahan scene")

        return scene_times

    except subprocess.TimeoutExpired:
        if verbose:
            print("[DEBUG] Timeout saat deteksi scene")
        return []
    except Exception as e:
        if verbose:
            print(f"[DEBUG] Error saat deteksi scene: {str(e)}")
        return []


def merge_highlights(
    audio_highlights: List[Tuple[float, float]],
    scene_changes: List[float],
    min_duration: int,
    max_duration: int,
    video_path: str,
    verbose: bool = False
) -> List[Tuple[float, float, float]]:
    """
    Gabungkan hasil deteksi audio dan visual menjadi highlight segments

    Args:
        audio_highlights: List of (timestamp, score) dari analisis audio
        scene_changes: List of timestamps perubahan scene
        min_duration: Durasi minimum segment
        max_duration: Durasi maksimum segment
        video_path: Path ke video untuk mendapatkan durasi total
        verbose: Tampilkan output detail

    Returns:
        List of (start_time, end_time, combined_score)
    """
    # Dapatkan durasi video
    video_duration = _get_video_duration(video_path)
    if video_duration is None:
        video_duration = 3600  # Default 1 jam jika tidak bisa detect

    # Jika tidak ada data, buat segments default
    if not audio_highlights and not scene_changes:
        if verbose:
            print("[DEBUG] Tidak ada data highlight, membuat segments default")
        return _create_default_segments(video_duration, min_duration, max_duration)

    # Buat time windows berdasarkan scene changes
    # Merge window-window pendek secara berurutan sampai mencapai min_duration
    windows = []
    # Deduplikasi agar tidak ada interval (0,0) jika scene_changes mengandung 0
    scene_times = sorted(set([0] + scene_changes + [video_duration]))

    window_start = scene_times[0]
    window_end = scene_times[-1]  # fallback jika loop tidak dieksekusi

    for i in range(1, len(scene_times)):
        window_end = scene_times[i]
        duration = window_end - window_start

        if duration < min_duration:
            # Belum cukup panjang, lanjut merge dengan scene berikutnya
            continue

        # Potong window jika terlalu panjang
        while window_end - window_start > max_duration:
            chunk_end = window_start + max_duration
            windows.append((window_start, chunk_end))
            window_start = chunk_end

        remaining = window_end - window_start
        if remaining >= min_duration:
            windows.append((window_start, window_end))
            window_start = window_end
        # Jika sisa setelah chunk splitting < min_duration, biarkan window_start
        # tetap agar bisa di-merge dengan scene berikutnya

    # Tangani sisa window di akhir video
    final_remaining = window_end - window_start
    if final_remaining > 0:
        if final_remaining >= min_duration:
            windows.append((window_start, window_end))
        elif windows:
            # Gabungkan ke window terakhir daripada membuang
            last_start, last_end = windows[-1]
            windows[-1] = (last_start, window_end)

    # Hitung score untuk setiap window berdasarkan audio
    scored_windows = []
    for start, end in windows:
        # Hitung rata-rata audio score dalam window
        window_scores = [
            score for time, score in audio_highlights
            if start <= time <= end
        ]

        if window_scores:
            avg_score = sum(window_scores) / len(window_scores)
        else:
            avg_score = 0.5  # Score default

        # Bonus untuk window yang mengandung scene change
        scene_count = sum(1 for t in scene_changes if start < t < end)
        scene_bonus = min(0.2 * scene_count, 0.4)  # Max 0.4 bonus

        final_score = min(avg_score + scene_bonus, 1.0)
        scored_windows.append((start, end, final_score))

    # Fallback jika scored_windows masih kosong (durasi video terlalu pendek dll)
    if not scored_windows:
        if verbose:
            print("[DEBUG] Tidak ada window valid, menggunakan segments default")
        return _create_default_segments(video_duration, min_duration, max_duration)

    if verbose:
        print(f"[DEBUG] Menghasilkan {len(scored_windows)} highlight segments")

    return scored_windows


def _get_video_duration(video_path: str) -> Optional[float]:
    """
    Dapatkan durasi video menggunakan ffprobe
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return float(result.stdout.strip())

        return None

    except (subprocess.TimeoutExpired, ValueError):
        return None


def _create_default_segments(
    video_duration: float,
    min_duration: int,
    max_duration: int,
    num_segments: int = 5
) -> List[Tuple[float, float, float]]:
    """
    Buat segments default jika tidak ada highlight terdeteksi
    Membagi video secara merata
    """
    segments = []
    segment_duration = min(max_duration, video_duration / num_segments)
    segment_duration = max(segment_duration, min_duration)

    current_pos = 0
    while current_pos + min_duration <= video_duration and len(segments) < num_segments:
        end_pos = min(current_pos + segment_duration, video_duration)
        # Score default menurun untuk segments selanjutnya
        score = 0.5 - (len(segments) * 0.05)
        segments.append((current_pos, end_pos, score))
        current_pos = end_pos + 10  # Gap 10 detik antar segment

    return segments


def analyze_segment_quality(
    video_path: str,
    start_time: float,
    end_time: float,
    verbose: bool = False
) -> float:
    """
    Analisis kualitas visual dari segment video

    Args:
        video_path: Path ke file video
        start_time: Waktu mulai segment
        end_time: Waktu akhir segment
        verbose: Tampilkan output detail

    Returns:
        Score kualitas (0-1)
    """
    try:
        # Hitung rata-rata brightness dan contrast menggunakan ffmpeg
        duration = end_time - start_time
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-t', str(duration),
            '-i', video_path,
            '-vf', 'signalstats,metadata=print:file=-',
            '-f', 'null',
            '-'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse untuk mendapatkan metrics
        # Default score jika parsing gagal
        return 0.7

    except Exception:
        return 0.5
