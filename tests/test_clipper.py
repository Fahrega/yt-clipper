"""
Unit tests untuk modul clipper.py (CLI entry point)

Test cases untuk parsing argumen, validasi, dan alur utama CLI.
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Tambahkan parent directory ke path untuk import modul
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clipper import (
    parse_arguments,
    validate_arguments,
    run_manual_mode,
    run_auto_mode,
    main
)


class TestParseArguments(unittest.TestCase):
    """Test cases untuk fungsi parse_arguments"""

    def test_parse_minimal_manual_args(self):
        """Test parsing argumen minimal untuk mode manual"""
        test_args = [
            '--url', 'https://www.youtube.com/watch?v=test123',
            '--start', '01:00',
            '--end', '02:00'
        ]

        with patch('sys.argv', ['clipper.py'] + test_args):
            args = parse_arguments()

            self.assertEqual(args.url, 'https://www.youtube.com/watch?v=test123')
            self.assertEqual(args.start, '01:00')
            self.assertEqual(args.end, '02:00')
            self.assertFalse(args.auto)

    def test_parse_auto_mode_args(self):
        """Test parsing argumen untuk mode otomatis"""
        test_args = [
            '--url', 'https://www.youtube.com/watch?v=test123',
            '--auto',
            '--max-clips', '3'
        ]

        with patch('sys.argv', ['clipper.py'] + test_args):
            args = parse_arguments()

            self.assertTrue(args.auto)
            self.assertEqual(args.max_clips, 3)

    def test_parse_with_quality(self):
        """Test parsing dengan opsi kualitas"""
        test_args = [
            '--url', 'https://www.youtube.com/watch?v=test123',
            '--start', '00:00',
            '--end', '00:30',
            '--quality', 'low'
        ]

        with patch('sys.argv', ['clipper.py'] + test_args):
            args = parse_arguments()

            self.assertEqual(args.quality, 'low')

    def test_parse_short_flags(self):
        """Test parsing dengan flag pendek"""
        test_args = [
            '-u', 'https://www.youtube.com/watch?v=test123',
            '-a',
            '-m', '5',
            '-v'
        ]

        with patch('sys.argv', ['clipper.py'] + test_args):
            args = parse_arguments()

            self.assertEqual(args.url, 'https://www.youtube.com/watch?v=test123')
            self.assertTrue(args.auto)
            self.assertEqual(args.max_clips, 5)
            self.assertTrue(args.verbose)

    def test_default_values(self):
        """Test nilai default argumen"""
        test_args = [
            '--url', 'https://www.youtube.com/watch?v=test123',
            '--auto'
        ]

        with patch('sys.argv', ['clipper.py'] + test_args):
            args = parse_arguments()

            self.assertEqual(args.max_clips, 5)  # Default
            self.assertEqual(args.min_duration, 15)  # Default
            self.assertEqual(args.max_duration, 60)  # Default
            self.assertEqual(args.output, 'output')  # Default
            self.assertEqual(args.quality, 'high')  # Default


class TestValidateArguments(unittest.TestCase):
    """Test cases untuk fungsi validate_arguments"""

    def test_valid_manual_mode(self):
        """Test validasi mode manual yang valid"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=False,
            start='00:30',
            end='01:30',
            min_duration=15,
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_invalid_url(self):
        """Test validasi URL tidak valid"""
        args = MagicMock(
            url='https://google.com',
            auto=False,
            start='00:30',
            end='01:30',
            min_duration=15,
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)
        self.assertIn("tidak valid", error.lower())

    def test_manual_mode_missing_start(self):
        """Test mode manual tanpa start time"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=False,
            start=None,
            end='01:30',
            min_duration=15,
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)
        self.assertIn("start", error.lower())

    def test_manual_mode_missing_end(self):
        """Test mode manual tanpa end time"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=False,
            start='00:30',
            end=None,
            min_duration=15,
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)
        self.assertIn("end", error.lower())

    def test_invalid_time_range(self):
        """Test rentang waktu tidak valid (start >= end)"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=False,
            start='02:00',
            end='01:00',  # End sebelum start
            min_duration=15,
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)

    def test_invalid_min_duration_too_low(self):
        """Test durasi minimum terlalu kecil"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=True,
            start=None,
            end=None,
            min_duration=2,  # Kurang dari 5
            max_duration=60,
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)
        self.assertIn("5 detik", error)

    def test_invalid_max_duration_too_high(self):
        """Test durasi maksimum terlalu besar"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=True,
            start=None,
            end=None,
            min_duration=15,
            max_duration=200,  # Lebih dari 180
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)
        self.assertIn("180 detik", error)

    def test_invalid_duration_order(self):
        """Test min_duration > max_duration"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=True,
            start=None,
            end=None,
            min_duration=60,
            max_duration=30,  # Kurang dari min
            max_clips=5
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)

    def test_invalid_max_clips_too_low(self):
        """Test max_clips kurang dari 1"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=True,
            start=None,
            end=None,
            min_duration=15,
            max_duration=60,
            max_clips=0
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)

    def test_invalid_max_clips_too_high(self):
        """Test max_clips lebih dari 20"""
        args = MagicMock(
            url='https://www.youtube.com/watch?v=test123',
            auto=True,
            start=None,
            end=None,
            min_duration=15,
            max_duration=60,
            max_clips=25
        )

        is_valid, error = validate_arguments(args)
        self.assertFalse(is_valid)


class TestRunManualMode(unittest.TestCase):
    """Test cases untuk fungsi run_manual_mode"""

    @patch('clipper.process_clip')
    def test_run_manual_calls_process_clip(self, mock_process):
        """Test mode manual memanggil process_clip dengan benar"""
        mock_process.return_value = '/output/clip.mp4'

        result = run_manual_mode(
            video_path='/input/video.mp4',
            start_time='01:00',
            end_time='02:00',
            output_dir='output',
            quality='high',
            verbose=False
        )

        self.assertEqual(result, '/output/clip.mp4')
        mock_process.assert_called_once()

    @patch('clipper.process_clip')
    def test_run_manual_converts_time(self, mock_process):
        """Test mode manual mengkonversi waktu dengan benar"""
        mock_process.return_value = '/output/clip.mp4'

        run_manual_mode(
            video_path='/input/video.mp4',
            start_time='01:30',  # 90 detik
            end_time='02:00',    # 120 detik
            output_dir='output',
            quality='high',
            verbose=False
        )

        call_args = mock_process.call_args
        self.assertEqual(call_args.kwargs['start_time'], 90)
        self.assertEqual(call_args.kwargs['end_time'], 120)


class TestRunAutoMode(unittest.TestCase):
    """Test cases untuk fungsi run_auto_mode"""

    @patch('clipper.detect_highlights')
    @patch('clipper.process_clip')
    def test_run_auto_returns_empty_when_no_highlights(self, mock_process, mock_detect):
        """Test mode auto mengembalikan list kosong jika tidak ada highlight"""
        mock_detect.return_value = []

        result = run_auto_mode(
            video_path='/input/video.mp4',
            output_dir='output',
            max_clips=5,
            min_duration=15,
            max_duration=60,
            quality='high'
        )

        self.assertEqual(result, [])
        mock_process.assert_not_called()

    @patch('clipper.detect_highlights')
    @patch('clipper.process_clip')
    def test_run_auto_processes_each_highlight(self, mock_process, mock_detect):
        """Test mode auto memproses setiap highlight"""
        mock_detect.return_value = [
            (10, 40, 0.9),
            (60, 90, 0.8),
            (120, 150, 0.7)
        ]
        mock_process.return_value = '/output/clip.mp4'

        result = run_auto_mode(
            video_path='/input/video.mp4',
            output_dir='output',
            max_clips=5,
            min_duration=15,
            max_duration=60,
            quality='high'
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(mock_process.call_count, 3)


class TestMainFunction(unittest.TestCase):
    """Test cases untuk fungsi main"""

    @patch('clipper.validate_arguments')
    @patch('clipper.parse_arguments')
    def test_main_returns_1_on_invalid_args(self, mock_parse, mock_validate):
        """Test main mengembalikan 1 jika argumen tidak valid"""
        mock_parse.return_value = MagicMock()
        mock_validate.return_value = (False, "Invalid URL")

        result = main()
        self.assertEqual(result, 1)

    @patch('clipper.download_video')
    @patch('clipper.ensure_output_dir')
    @patch('clipper.validate_arguments')
    @patch('clipper.parse_arguments')
    def test_main_returns_1_on_download_failure(self, mock_parse, mock_validate,
                                                  mock_output, mock_download):
        """Test main mengembalikan 1 jika download gagal"""
        mock_parse.return_value = MagicMock(
            url='https://youtube.com/watch?v=test',
            auto=False,
            start='00:00',
            end='00:30',
            output='output',
            verbose=False,
            keep_original=False
        )
        mock_validate.return_value = (True, "")
        mock_output.return_value = 'output'
        mock_download.return_value = None  # Download gagal

        result = main()
        self.assertEqual(result, 1)

    @patch('clipper.os.remove')
    @patch('clipper.os.path.exists')
    @patch('clipper.run_manual_mode')
    @patch('clipper.download_video')
    @patch('clipper.ensure_output_dir')
    @patch('clipper.validate_arguments')
    @patch('clipper.parse_arguments')
    def test_main_success_manual_mode(self, mock_parse, mock_validate,
                                       mock_output, mock_download,
                                       mock_manual, mock_exists, mock_remove):
        """Test main berhasil untuk mode manual"""
        mock_parse.return_value = MagicMock(
            url='https://youtube.com/watch?v=test',
            auto=False,
            start='00:00',
            end='00:30',
            output='output',
            verbose=False,
            keep_original=False,
            quality='high'
        )
        mock_validate.return_value = (True, "")
        mock_output.return_value = 'output'
        mock_download.return_value = '/tmp/video.mp4'
        mock_manual.return_value = '/output/clip.mp4'
        mock_exists.return_value = True

        result = main()
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
