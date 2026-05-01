#!/usr/bin/env python3
"""
Modul untuk tracking wajah menggunakan MediaPipe (Tasks API)
Menghasilkan koordinat crop dinamis untuk FFmpeg
"""

import os
import cv2
import mediapipe as mp
import numpy as np
from typing import List, Tuple, Optional
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Path ke model detector
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'blaze_face_short_range.tflite')

def analyze_faces(
    video_path: str,
    start_time: float,
    duration: float,
    target_width: int,
    target_height: int,
    output_cmd_path: str,
    fps_sampling: float = 5.0,
    smoothing_window: int = 5
) -> bool:
    """
    Analisis wajah dalam video dan buat file perintah FFmpeg sendcmd
    """
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model MediaPipe tidak ditemukan di: {MODEL_PATH}")
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False

    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if (orig_width / orig_height) > (target_width / target_height):
        scale = target_height / orig_height
    else:
        scale = target_width / orig_width

    scaled_orig_w = int(orig_width * scale)
    scaled_orig_h = int(orig_height * scale)

    # Inisialisasi Face Detector
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO
    )

    raw_coords = []
    start_frame = int(start_time * fps)
    total_frames = int(duration * fps)
    sample_interval = max(1, int(fps / fps_sampling))

    with vision.FaceDetector.create_from_options(options) as detector:
        for i in range(0, total_frames, sample_interval):
            frame_idx = start_frame + i
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            # Convert frame ke MediaPipe Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Deteksi wajah dengan timestamp (ms)
            timestamp_ms = int((i / fps) * 1000)
            detection_result = detector.detect_for_video(mp_image, timestamp_ms)
            
            current_time = i / fps
            
            if detection_result.detections:
                # Ambil wajah pertama
                bbox = detection_result.detections[0].bounding_box
                # Pusat wajah (pixel coordinate di original video)
                # bounding_box origin_x/origin_y adalah pixel
                center_x = (bbox.origin_x + bbox.width / 2) / orig_width
                center_y = (bbox.origin_y + bbox.height / 2) / orig_height
                raw_coords.append((current_time, center_x, center_y))
            else:
                raw_coords.append((current_time, 0.5, 0.5))

    cap.release()

    if not raw_coords:
        return False

    smoothed_commands = []
    for i in range(len(raw_coords)):
        start_idx = max(0, i - smoothing_window // 2)
        end_idx = min(len(raw_coords), i + smoothing_window // 2 + 1)
        
        avg_x = sum(c[1] for c in raw_coords[start_idx:end_idx]) / (end_idx - start_idx)
        avg_y = sum(c[2] for c in raw_coords[start_idx:end_idx]) / (end_idx - start_idx)
        
        timestamp = raw_coords[i][0]
        
        crop_x = int(avg_x * scaled_orig_w - target_width / 2)
        crop_y = int(avg_y * scaled_orig_h - target_height / 2)

        crop_x = max(0, min(crop_x, scaled_orig_w - target_width))
        crop_y = max(0, min(crop_y, scaled_orig_h - target_height))

        smoothed_commands.append(f"{timestamp:.3f} crop x {crop_x}, crop y {crop_y};")

    with open(output_cmd_path, 'w') as f:
        f.write('\n'.join(smoothed_commands))

    return True
