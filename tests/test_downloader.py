"""
Unit tests untuk modul downloader.py

Test cases untuk fungsi download video dan helper terkait.
Catatan: Beberapa test memerlukan mock karena bergantung pada external tools.
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Tambahkan parent directory ke path untuk import modul
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from downloader import (
    get_video_info,
    download_video,
    _find_latest_video,
    get_video_duration,
    extract_audio
)


class TestGetVideoInfo(unittest.TestCase):
    """Test cases untuk fungsi get_video_info"""

    @patch('downloader.subprocess.run')
    def test_get_video_info_success(self, mock_run):
        """Test mendapatkan info video berhasil"""
        # Mock response dari yt-dlp
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"id": "test123", "title": "Test Video", "duration": 120}'
        )

        result = get_video_info("https://www.youtube.com/watch?v=test123")

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test123')
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['duration'], 120)

    @patch('downloader.subprocess.run')
    def test_get_video_info_failure(self, mock_run):
        """Test mendapatkan info video gagal"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Error message'
        )

        result = get_video_info("https://www.youtube.com/watch?v=invalid")
        self.assertIsNone(result)

    @patch('downloader.subprocess.run')
    def test_get_video_info_timeout(self, mock_run):
        """Test timeout saat mendapatkan info video"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='yt-dlp', timeout=60)

        result = get_video_info("https://www.youtube.com/watch?v=test")
        self.assertIsNone(result)

    @patch('downloader.subprocess.run')
    def test_get_video_info_json_error(self, mock_run):
        """Test error parsing JSON"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='invalid json {'
        )

        result = get_video_info("https://www.youtube.com/watch?v=test")
        self.assertIsNone(result)


class TestDownloadVideo(unittest.TestCase):
    """Test cases untuk fungsi download_video"""

    def setUp(self):
        """Setup temporary directory untuk test"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('downloader.subprocess.Popen')
    @patch('downloader._find_latest_video')
    def test_download_video_success(self, mock_find, mock_popen):
        """Test download video berhasil"""
        expected_path = os.path.join(self.temp_dir, 'test.mp4')
        
        # Mock Popen process
        mock_process = MagicMock()
        mock_process.stdout = [
            '[download]  10.0% of 100.00MiB',
            '[download] 100.0% of 100.00MiB',
            expected_path
        ]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        mock_find.return_value = expected_path

        # Buat file dummy
        with open(expected_path, 'w') as f:
            f.write('dummy video content')

        result = download_video(
            "https://www.youtube.com/watch?v=test",
            output_dir=self.temp_dir
        )

        self.assertIsNotNone(result)

    @patch('downloader.subprocess.Popen')
    def test_download_video_failure(self, mock_popen):
        """Test download video gagal"""
        mock_process = MagicMock()
        mock_process.stdout = ['Error message']
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = download_video(
            "https://www.youtube.com/watch?v=test",
            output_dir=self.temp_dir
        )

        self.assertIsNone(result)

    @patch('downloader.subprocess.Popen')
    def test_download_video_creates_output_dir(self, mock_popen):
        """Test download membuat direktori output"""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        new_dir = os.path.join(self.temp_dir, 'new_output')
        download_video(
            "https://www.youtube.com/watch?v=test",
            output_dir=new_dir
        )

        self.assertTrue(os.path.exists(new_dir))


class TestFindLatestVideo(unittest.TestCase):
    """Test cases untuk fungsi _find_latest_video"""

    def setUp(self):
        """Setup temporary directory dengan file dummy"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_finds_mp4_file(self):
        """Test menemukan file MP4"""
        video_path = os.path.join(self.temp_dir, 'video.mp4')
        with open(video_path, 'w') as f:
            f.write('dummy')

        result = _find_latest_video(self.temp_dir)
        self.assertEqual(result, video_path)

    def test_finds_mkv_file(self):
        """Test menemukan file MKV"""
        video_path = os.path.join(self.temp_dir, 'video.mkv')
        with open(video_path, 'w') as f:
            f.write('dummy')

        result = _find_latest_video(self.temp_dir)
        self.assertEqual(result, video_path)

    def test_finds_webm_file(self):
        """Test menemukan file WebM"""
        video_path = os.path.join(self.temp_dir, 'video.webm')
        with open(video_path, 'w') as f:
            f.write('dummy')

        result = _find_latest_video(self.temp_dir)
        self.assertEqual(result, video_path)

    def test_returns_none_empty_dir(self):
        """Test mengembalikan None untuk direktori kosong"""
        result = _find_latest_video(self.temp_dir)
        self.assertIsNone(result)

    def test_ignores_non_video_files(self):
        """Test mengabaikan file non-video"""
        # Buat file non-video
        txt_path = os.path.join(self.temp_dir, 'file.txt')
        with open(txt_path, 'w') as f:
            f.write('dummy')

        result = _find_latest_video(self.temp_dir)
        self.assertIsNone(result)

    def test_finds_latest_when_multiple(self):
        """Test menemukan file terbaru jika ada beberapa"""
        import time

        # Buat file pertama
        old_path = os.path.join(self.temp_dir, 'old.mp4')
        with open(old_path, 'w') as f:
            f.write('old')

        time.sleep(0.1)  # Pastikan timestamp berbeda

        # Buat file kedua (lebih baru)
        new_path = os.path.join(self.temp_dir, 'new.mp4')
        with open(new_path, 'w') as f:
            f.write('new')

        result = _find_latest_video(self.temp_dir)
        self.assertEqual(result, new_path)


class TestGetVideoDuration(unittest.TestCase):
    """Test cases untuk fungsi get_video_duration"""

    @patch('downloader.subprocess.run')
    def test_get_duration_success(self, mock_run):
        """Test mendapatkan durasi berhasil"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='120.5\n'
        )

        result = get_video_duration('/path/to/video.mp4')
        self.assertEqual(result, 120.5)

    @patch('downloader.subprocess.run')
    def test_get_duration_failure(self, mock_run):
        """Test mendapatkan durasi gagal"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=''
        )

        result = get_video_duration('/path/to/invalid.mp4')
        self.assertIsNone(result)

    @patch('downloader.subprocess.run')
    def test_get_duration_timeout(self, mock_run):
        """Test timeout saat mendapatkan durasi"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='ffprobe', timeout=30)

        result = get_video_duration('/path/to/video.mp4')
        self.assertIsNone(result)


class TestExtractAudio(unittest.TestCase):
    """Test cases untuk fungsi extract_audio"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('downloader.subprocess.run')
    def test_extract_audio_success(self, mock_run):
        """Test ekstrak audio berhasil"""
        mock_run.return_value = MagicMock(returncode=0)

        video_path = os.path.join(self.temp_dir, 'video.mp4')
        audio_path = os.path.join(self.temp_dir, 'video_audio.wav')

        # Buat file output yang diharapkan
        with open(audio_path, 'w') as f:
            f.write('dummy audio')

        result = extract_audio(video_path, audio_path)
        self.assertEqual(result, audio_path)

    @patch('downloader.subprocess.run')
    def test_extract_audio_failure(self, mock_run):
        """Test ekstrak audio gagal"""
        mock_run.return_value = MagicMock(returncode=1)

        video_path = os.path.join(self.temp_dir, 'video.mp4')
        result = extract_audio(video_path)

        self.assertIsNone(result)

    @patch('downloader.subprocess.run')
    def test_extract_audio_default_output(self, mock_run):
        """Test ekstrak audio dengan output path default"""
        mock_run.return_value = MagicMock(returncode=0)

        video_path = os.path.join(self.temp_dir, 'myvideo.mp4')
        expected_audio = os.path.join(self.temp_dir, 'myvideo_audio.wav')

        # Buat file output yang diharapkan
        with open(expected_audio, 'w') as f:
            f.write('dummy')

        result = extract_audio(video_path)
        self.assertEqual(result, expected_audio)


if __name__ == '__main__':
    unittest.main()
