"""
Unit tests untuk modul utils.py

Test cases untuk validasi URL YouTube, parsing waktu, dan fungsi helper lainnya.
"""

import unittest
import os
import sys
import tempfile
import shutil

# Tambahkan parent directory ke path untuk import modul
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    validate_youtube_url,
    validate_url,
    extract_video_id,
    parse_time,
    format_time,
    generate_output_filename,
    validate_time_range,
    sanitize_filename,
    ensure_output_dir
)


class TestValidateYoutubeUrl(unittest.TestCase):
    """Test cases untuk fungsi validate_youtube_url"""

    def test_valid_watch_url(self):
        """Test URL format youtube.com/watch"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(url))

    def test_valid_watch_url_without_www(self):
        """Test URL tanpa www"""
        url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(url))

    def test_valid_short_url(self):
        """Test URL format youtu.be"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(url))

    def test_valid_shorts_url(self):
        """Test URL format youtube.com/shorts"""
        url = "https://www.youtube.com/shorts/abcdefghijk"
        self.assertTrue(validate_youtube_url(url))

    def test_valid_embed_url(self):
        """Test URL format youtube.com/embed"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(url))

    def test_valid_http_url(self):
        """Test URL dengan http (bukan https)"""
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertTrue(validate_youtube_url(url))

    def test_invalid_google_url(self):
        """Test URL bukan YouTube"""
        url = "https://google.com"
        self.assertFalse(validate_youtube_url(url))

    def test_invalid_vimeo_url(self):
        """Test URL Vimeo"""
        url = "https://vimeo.com/123456789"
        self.assertFalse(validate_youtube_url(url))

    def test_invalid_empty_string(self):
        """Test string kosong"""
        url = ""
        self.assertFalse(validate_youtube_url(url))

    def test_invalid_random_text(self):
        """Test teks random"""
        url = "this is not a url"
        self.assertFalse(validate_youtube_url(url))

    def test_validate_url_alias(self):
        """Test alias validate_url sama dengan validate_youtube_url"""
        url = "https://www.youtube.com/watch?v=test123"
        self.assertEqual(validate_url(url), validate_youtube_url(url))


class TestExtractVideoId(unittest.TestCase):
    """Test cases untuk fungsi extract_video_id"""

    def test_extract_from_watch_url(self):
        """Test ekstrak ID dari URL watch"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_short_url(self):
        """Test ekstrak ID dari URL youtu.be"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_embed_url(self):
        """Test ekstrak ID dari URL embed"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_extract_from_shorts_url(self):
        """Test ekstrak ID dari URL shorts"""
        url = "https://www.youtube.com/shorts/abcdefghijk"
        self.assertEqual(extract_video_id(url), "abcdefghijk")

    def test_extract_with_extra_params(self):
        """Test ekstrak ID dari URL dengan parameter tambahan"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        # Regex mungkin hanya menangkap sampai karakter valid
        video_id = extract_video_id(url)
        self.assertTrue(video_id is not None)
        self.assertTrue(video_id.startswith("dQw4w9WgXcQ"))

    def test_extract_from_invalid_url(self):
        """Test ekstrak ID dari URL tidak valid"""
        url = "https://google.com"
        self.assertIsNone(extract_video_id(url))


class TestParseTime(unittest.TestCase):
    """Test cases untuk fungsi parse_time"""

    def test_parse_seconds_only(self):
        """Test parsing detik saja"""
        self.assertEqual(parse_time("90"), 90.0)

    def test_parse_mm_ss(self):
        """Test parsing format MM:SS"""
        self.assertEqual(parse_time("01:30"), 90.0)

    def test_parse_mm_ss_with_zero(self):
        """Test parsing format MM:SS dengan nilai nol"""
        self.assertEqual(parse_time("00:30"), 30.0)

    def test_parse_hh_mm_ss(self):
        """Test parsing format HH:MM:SS"""
        self.assertEqual(parse_time("01:30:00"), 5400.0)

    def test_parse_hh_mm_ss_complex(self):
        """Test parsing format HH:MM:SS kompleks"""
        self.assertEqual(parse_time("01:01:01"), 3661.0)

    def test_parse_with_spaces(self):
        """Test parsing dengan spasi"""
        self.assertEqual(parse_time("  01:30  "), 90.0)

    def test_parse_invalid_format(self):
        """Test parsing format tidak valid"""
        with self.assertRaises(ValueError):
            parse_time("invalid")

    def test_parse_too_many_colons(self):
        """Test parsing dengan terlalu banyak titik dua"""
        with self.assertRaises(ValueError):
            parse_time("01:02:03:04")


class TestFormatTime(unittest.TestCase):
    """Test cases untuk fungsi format_time"""

    def test_format_under_minute(self):
        """Test format di bawah 1 menit"""
        self.assertEqual(format_time(30), "00:30")

    def test_format_one_minute(self):
        """Test format tepat 1 menit"""
        self.assertEqual(format_time(60), "01:00")

    def test_format_minutes_seconds(self):
        """Test format menit dan detik"""
        self.assertEqual(format_time(90), "01:30")

    def test_format_hours(self):
        """Test format dengan jam"""
        self.assertEqual(format_time(3661), "01:01:01")

    def test_format_zero(self):
        """Test format nol"""
        self.assertEqual(format_time(0), "00:00")

    def test_format_negative_raises_error(self):
        """Test format negatif menimbulkan error"""
        with self.assertRaises(ValueError):
            format_time(-1)


class TestValidateTimeRange(unittest.TestCase):
    """Test cases untuk fungsi validate_time_range"""

    def test_valid_range(self):
        """Test rentang waktu valid"""
        is_valid, msg = validate_time_range(10, 40)
        self.assertTrue(is_valid)

    def test_invalid_negative_start(self):
        """Test start time negatif"""
        is_valid, msg = validate_time_range(-1, 30)
        self.assertFalse(is_valid)
        self.assertIn("negatif", msg)

    def test_invalid_end_before_start(self):
        """Test end sebelum start"""
        is_valid, msg = validate_time_range(30, 10)
        self.assertFalse(is_valid)
        self.assertIn("lebih besar", msg)

    def test_invalid_too_short(self):
        """Test durasi terlalu pendek"""
        is_valid, msg = validate_time_range(10, 11)
        self.assertFalse(is_valid)
        self.assertIn("minimal 3 detik", msg)

    def test_invalid_too_long(self):
        """Test durasi terlalu panjang"""
        is_valid, msg = validate_time_range(0, 200)
        self.assertFalse(is_valid)
        self.assertIn("maksimal 180 detik", msg)

    def test_valid_with_duration_check(self):
        """Test dengan cek durasi video"""
        is_valid, msg = validate_time_range(10, 40, duration=60)
        self.assertTrue(is_valid)

    def test_invalid_start_exceeds_duration(self):
        """Test start melebihi durasi video"""
        is_valid, msg = validate_time_range(70, 80, duration=60)
        self.assertFalse(is_valid)
        self.assertIn("melebihi durasi", msg)


class TestSanitizeFilename(unittest.TestCase):
    """Test cases untuk fungsi sanitize_filename"""

    def test_valid_filename_unchanged(self):
        """Test nama file valid tidak berubah"""
        filename = "my_video_clip.mp4"
        self.assertEqual(sanitize_filename(filename), filename)

    def test_removes_invalid_chars(self):
        """Test menghapus karakter tidak valid"""
        filename = 'video<>:"/\\|?*.mp4'
        sanitized = sanitize_filename(filename)
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
        self.assertNotIn(':', sanitized)

    def test_strips_whitespace(self):
        """Test menghapus spasi di awal dan akhir"""
        filename = "  video.mp4  "
        self.assertEqual(sanitize_filename(filename), "video.mp4")

    def test_truncates_long_filename(self):
        """Test memotong nama file panjang"""
        filename = "a" * 300 + ".mp4"
        sanitized = sanitize_filename(filename)
        self.assertLessEqual(len(sanitized), 200)


class TestGenerateOutputFilename(unittest.TestCase):
    """Test cases untuk fungsi generate_output_filename"""

    def setUp(self):
        """Setup temporary directory untuk test"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_valid_path(self):
        """Test generate path yang valid"""
        path = generate_output_filename("abc123", 10, 40, self.temp_dir)
        self.assertTrue(path.endswith(".mp4"))
        self.assertIn("abc123", path)
        self.assertIn(self.temp_dir, path)

    def test_creates_output_dir(self):
        """Test membuat direktori output jika belum ada"""
        new_dir = os.path.join(self.temp_dir, "subdir")
        path = generate_output_filename("test", 0, 30, new_dir)
        self.assertTrue(os.path.exists(new_dir))


class TestEnsureOutputDir(unittest.TestCase):
    """Test cases untuk fungsi ensure_output_dir"""

    def setUp(self):
        """Setup temporary directory untuk test"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_directory(self):
        """Test membuat direktori baru"""
        new_dir = os.path.join(self.temp_dir, "new_folder")
        result = ensure_output_dir(new_dir)
        self.assertTrue(os.path.exists(result))

    def test_existing_directory_unchanged(self):
        """Test direktori yang sudah ada tidak berubah"""
        result = ensure_output_dir(self.temp_dir)
        self.assertEqual(result, self.temp_dir)

    def test_returns_absolute_path(self):
        """Test mengembalikan path absolut"""
        result = ensure_output_dir("relative_path")
        self.assertTrue(os.path.isabs(result))
        # Cleanup created directory
        if os.path.exists(result):
            os.rmdir(result)


if __name__ == '__main__':
    unittest.main()
