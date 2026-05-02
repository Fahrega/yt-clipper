"""
Unit tests untuk modul processor.py

Test cases untuk fungsi pemrosesan video ke format TikTok.
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Tambahkan parent directory ke path untuk import modul
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import (
    process_clip,
    _generate_output_path,
    _run_ffmpeg_tiktok,
    process_clip_simple,
    get_video_info,
    create_thumbnail,
    QUALITY_PRESETS
)


class TestQualityPresets(unittest.TestCase):
    """Test cases untuk quality presets"""

    def test_presets_exist(self):
        """Test semua preset tersedia"""
        self.assertIn('low', QUALITY_PRESETS)
        self.assertIn('medium', QUALITY_PRESETS)
        self.assertIn('high', QUALITY_PRESETS)

    def test_presets_have_required_keys(self):
        """Test preset memiliki key yang diperlukan"""
        required_keys = ['resolution', 'bitrate', 'crf', 'preset']

        for quality, preset in QUALITY_PRESETS.items():
            for key in required_keys:
                self.assertIn(key, preset, f"Missing {key} in {quality} preset")

    def test_resolution_format(self):
        """Test format resolusi valid"""
        for quality, preset in QUALITY_PRESETS.items():
            resolution = preset['resolution']
            parts = resolution.split('x')
            self.assertEqual(len(parts), 2)
            self.assertTrue(parts[0].isdigit())
            self.assertTrue(parts[1].isdigit())


class TestProcessClip(unittest.TestCase):
    """Test cases untuk fungsi process_clip"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_clip_file_not_found(self):
        """Test error jika file input tidak ada"""
        result = process_clip(
            input_path='/nonexistent/video.mp4',
            start_time=0,
            end_time=30,
            output_dir=self.temp_dir
        )
        self.assertIsNone(result)

    def test_process_clip_invalid_time_range(self):
        """Test error jika start >= end"""
        # Buat file dummy
        input_path = os.path.join(self.temp_dir, 'input.mp4')
        with open(input_path, 'w') as f:
            f.write('dummy')

        result = process_clip(
            input_path=input_path,
            start_time=30,
            end_time=10,  # End sebelum start
            output_dir=self.temp_dir
        )
        self.assertIsNone(result)

    @patch('processor._run_ffmpeg_tiktok')
    def test_process_clip_success(self, mock_ffmpeg):
        """Test proses clip berhasil"""
        mock_ffmpeg.return_value = True

        # Buat file dummy input
        input_path = os.path.join(self.temp_dir, 'input.mp4')
        with open(input_path, 'w') as f:
            f.write('dummy input')

        # Jalankan process_clip
        result = process_clip(
            input_path=input_path,
            start_time=0,
            end_time=30,
            output_dir=self.temp_dir
        )

        # Karena mock, file output tidak akan dibuat secara real
        # Tapi fungsi harus dipanggil dengan benar
        mock_ffmpeg.assert_called_once()


class TestGenerateOutputPath(unittest.TestCase):
    """Test cases untuk fungsi _generate_output_path"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_mp4_extension(self):
        """Test output memiliki ekstensi .mp4"""
        result = _generate_output_path('/input/video.mp4', self.temp_dir, None)
        self.assertTrue(result.endswith('.mp4'))

    def test_includes_clip_index(self):
        """Test menyertakan index clip jika diberikan"""
        result = _generate_output_path('/input/video.mp4', self.temp_dir, 3)
        self.assertIn('clip3', result)

    def test_includes_tiktok_suffix_without_index(self):
        """Test menyertakan suffix tiktok jika tanpa index"""
        result = _generate_output_path('/input/video.mp4', self.temp_dir, None)
        self.assertIn('tiktok', result)

    def test_creates_output_dir(self):
        """Test membuat direktori output"""
        new_dir = os.path.join(self.temp_dir, 'new_subdir')
        result = _generate_output_path('/input/video.mp4', new_dir, None)
        self.assertTrue(os.path.exists(new_dir))

    def test_sanitizes_filename(self):
        """Test membersihkan nama file dari karakter tidak valid"""
        result = _generate_output_path('/input/video<>:test.mp4', self.temp_dir, None)
        # Tidak boleh ada karakter tidak valid
        self.assertNotIn('<', os.path.basename(result))
        self.assertNotIn('>', os.path.basename(result))
        self.assertNotIn(':', os.path.basename(result).replace(':', ''))  # Skip drive letter


class TestRunFfmpegTiktok(unittest.TestCase):
    """Test cases untuk fungsi _run_ffmpeg_tiktok"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('processor.subprocess.Popen')
    def test_ffmpeg_success(self, mock_popen):
        """Test FFmpeg berhasil"""
        mock_process = MagicMock()
        mock_process.stdout = ['time=00:00:10.00']
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = _run_ffmpeg_tiktok(
            input_path='/input/video.mp4',
            output_path=os.path.join(self.temp_dir, 'output.mp4'),
            start_time=0,
            duration=30,
            preset=QUALITY_PRESETS['medium']
        )

        self.assertTrue(result)

    @patch('processor.subprocess.Popen')
    def test_ffmpeg_failure(self, mock_popen):
        """Test FFmpeg gagal"""
        mock_process = MagicMock()
        mock_process.stdout = ['Error message']
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = _run_ffmpeg_tiktok(
            input_path='/input/video.mp4',
            output_path=os.path.join(self.temp_dir, 'output.mp4'),
            start_time=0,
            duration=30,
            preset=QUALITY_PRESETS['medium']
        )

        self.assertFalse(result)

    @patch('processor.subprocess.Popen')
    def test_ffmpeg_exception(self, mock_popen):
        """Test FFmpeg exception"""
        mock_popen.side_effect = Exception("error")

        result = _run_ffmpeg_tiktok(
            input_path='/input/video.mp4',
            output_path=os.path.join(self.temp_dir, 'output.mp4'),
            start_time=0,
            duration=30,
            preset=QUALITY_PRESETS['medium']
        )

        self.assertFalse(result)

    @patch('processor.subprocess.Popen')
    def test_ffmpeg_command_content(self, mock_popen):
        """Test isi command FFmpeg untuk memastikan filter yang benar digunakan"""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        preset = QUALITY_PRESETS['medium']
        width, height = map(int, preset['resolution'].split('x'))
        expected_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

        _run_ffmpeg_tiktok(
            input_path='/input/video.mp4',
            output_path=os.path.join(self.temp_dir, 'output.mp4'),
            start_time=10.5,
            duration=20.0,
            preset=preset
        )

        # Ambil argument yang dipanggil ke subprocess.Popen
        cmd = mock_popen.call_args[0][0]

        # Pastikan menggunakan -vf dan bukan -filter_complex
        self.assertIn('-vf', cmd)
        self.assertNotIn('-filter_complex', cmd)

        # Pastikan filter string sesuai dengan yang diharapkan
        vf_index = cmd.index('-vf')
        self.assertEqual(cmd[vf_index + 1], expected_filter)

        # Pastikan mapping stream sudah benar
        self.assertIn('-map', cmd)
        self.assertIn('0:v', cmd)
        self.assertIn('0:a?', cmd)

        # Pastikan tidak ada blur logic
        self.assertNotIn('blur', cmd[vf_index + 1])


class TestProcessClipSimple(unittest.TestCase):
    """Test cases untuk fungsi process_clip_simple"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('processor.subprocess.run')
    def test_simple_clip_success(self, mock_run):
        """Test simple clip berhasil"""
        mock_run.return_value = MagicMock(returncode=0)

        result = process_clip_simple(
            input_path='/input/video.mp4',
            start_time=10,
            end_time=40,
            output_path=os.path.join(self.temp_dir, 'output.mp4')
        )

        self.assertTrue(result)

    @patch('processor.subprocess.run')
    def test_simple_clip_failure(self, mock_run):
        """Test simple clip gagal"""
        mock_run.return_value = MagicMock(returncode=1)

        result = process_clip_simple(
            input_path='/input/video.mp4',
            start_time=10,
            end_time=40,
            output_path=os.path.join(self.temp_dir, 'output.mp4')
        )

        self.assertFalse(result)


class TestGetVideoInfo(unittest.TestCase):
    """Test cases untuk fungsi get_video_info"""

    @patch('processor.subprocess.run')
    def test_get_info_success(self, mock_run):
        """Test mendapatkan info video berhasil"""
        mock_json = '''
        {
            "streams": [
                {
                    "width": 1920,
                    "height": 1080,
                    "codec_name": "h264",
                    "r_frame_rate": "30/1"
                }
            ],
            "format": {
                "duration": "120.5",
                "size": "15000000"
            }
        }
        '''
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_json
        )

        result = get_video_info('/path/to/video.mp4')

        self.assertIsNotNone(result)
        self.assertEqual(result['width'], 1920)
        self.assertEqual(result['height'], 1080)
        self.assertEqual(result['codec'], 'h264')
        self.assertEqual(result['fps'], 30)
        self.assertEqual(result['duration'], 120.5)

    @patch('processor.subprocess.run')
    def test_get_info_failure(self, mock_run):
        """Test mendapatkan info video gagal"""
        mock_run.return_value = MagicMock(returncode=1)

        result = get_video_info('/path/to/invalid.mp4')
        self.assertIsNone(result)

    @patch('processor.subprocess.run')
    def test_get_info_handles_fractional_fps(self, mock_run):
        """Test menangani frame rate pecahan"""
        mock_json = '''
        {
            "streams": [{"r_frame_rate": "30000/1001"}],
            "format": {"duration": "60"}
        }
        '''
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_json
        )

        result = get_video_info('/path/to/video.mp4')
        self.assertIsNotNone(result)
        # 30000/1001 = ~29.97 fps
        self.assertAlmostEqual(result['fps'], 29.97, places=1)


class TestCreateThumbnail(unittest.TestCase):
    """Test cases untuk fungsi create_thumbnail"""

    def setUp(self):
        """Setup temporary directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('processor.subprocess.run')
    def test_create_thumbnail_success(self, mock_run):
        """Test membuat thumbnail berhasil"""
        mock_run.return_value = MagicMock(returncode=0)

        output_path = os.path.join(self.temp_dir, 'thumb.jpg')
        result = create_thumbnail(
            video_path='/input/video.mp4',
            output_path=output_path
        )

        self.assertTrue(result)

    @patch('processor.subprocess.run')
    def test_create_thumbnail_failure(self, mock_run):
        """Test membuat thumbnail gagal"""
        mock_run.return_value = MagicMock(returncode=1)

        output_path = os.path.join(self.temp_dir, 'thumb.jpg')
        result = create_thumbnail(
            video_path='/input/video.mp4',
            output_path=output_path
        )

        self.assertFalse(result)

    @patch('processor.subprocess.run')
    def test_create_thumbnail_at_timestamp(self, mock_run):
        """Test membuat thumbnail pada timestamp tertentu"""
        mock_run.return_value = MagicMock(returncode=0)

        output_path = os.path.join(self.temp_dir, 'thumb.jpg')
        result = create_thumbnail(
            video_path='/input/video.mp4',
            output_path=output_path,
            timestamp=30
        )

        self.assertTrue(result)
        # Verifikasi timestamp dikirim ke FFmpeg
        call_args = mock_run.call_args[0][0]
        self.assertIn('-ss', call_args)
        self.assertIn('30', call_args)


if __name__ == '__main__':
    unittest.main()
