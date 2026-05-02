"""
Unit tests untuk modul tracker.py
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Tambahkan parent directory ke path untuk import modul
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import analyze_faces

class TestTracker(unittest.TestCase):
    """Test cases untuk fungsi analyze_faces"""

    @patch('tracker.cv2.VideoCapture')
    @patch('tracker.vision.FaceDetector.create_from_options')
    @patch('tracker.os.path.exists')
    def test_analyze_faces_progress_callback(self, mock_exists, mock_detector_create, mock_video_capture):
        """Test progress_callback dipanggil dalam analyze_faces"""
        # Mock exists untuk MODEL_PATH
        mock_exists.return_value = True
        
        # Mock VideoCapture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            0: 1920, # CAP_PROP_FRAME_WIDTH
            0: 1080, # CAP_PROP_FRAME_HEIGHT (actually prop ids are different but for mock it's fine if we handle it)
        }.get(prop, 30.0) # CAP_PROP_FPS and others
        
        # Correctly mock CAP_PROP
        import cv2
        import numpy as np
        def mock_get(prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH: return 1920
            if prop == cv2.CAP_PROP_FRAME_HEIGHT: return 1080
            if prop == cv2.CAP_PROP_FPS: return 30.0
            return 0
        mock_cap.get.side_effect = mock_get
        mock_cap.read.return_value = (True, np.zeros((1080, 1920, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        # Mock FaceDetector
        mock_detector = MagicMock()
        mock_detector.detect_for_video.return_value = MagicMock(detections=[])
        mock_detector_create.return_value.__enter__.return_value = mock_detector
        
        # Callback to track progress
        progress_values = []
        def progress_cb(p):
            progress_values.append(p)
            
        # Call analyze_faces
        # duration 1s, fps 30, fps_sampling 5.0 -> sample interval 6. Total samples: 1/0.2 = 5 samples
        with patch('builtins.open', unittest.mock.mock_open()):
            analyze_faces(
                video_path='dummy.mp4',
                start_time=0,
                duration=1.0,
                target_width=720,
                target_height=1280,
                output_cmd_path='dummy.txt',
                fps_sampling=5.0,
                progress_callback=progress_cb
            )
            
        self.assertTrue(len(progress_values) > 0)
        self.assertAlmostEqual(progress_values[-1], 1.0)

if __name__ == '__main__':
    unittest.main()
