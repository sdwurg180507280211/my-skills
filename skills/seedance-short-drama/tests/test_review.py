"""Offline tests for review parsing helpers (synthetic ffmpeg and OCR output)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review  # noqa: E402

SILENCE = """[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 0.578 | silence_duration: 0.578
[silencedetect @ 0x1] silence_start: 1.357
[silencedetect @ 0x1] silence_end: 2.323 | silence_duration: 0.966
"""


class ReviewParsingTests(unittest.TestCase):
    def test_speech_runs_to_end_when_not_silent(self):
        self.assertEqual(review.speech_intervals(SILENCE, 5.04), [(0.58, 1.36), (2.32, 5.04)])

    def test_trailing_silence_closes_last_interval(self):
        text = SILENCE + "[silencedetect @ 0x1] silence_start: 4.78\n"
        self.assertEqual(review.speech_intervals(text, 5.04), [(0.58, 1.36), (2.32, 4.78)])

    def test_ocr_lines_become_timestamped_hits(self):
        out = "f_0001.png\t0.30\t乱码字幕\t0.38,0.76,0.25,0.04\nf_0021.png\t1.00\t190\t0.29,0.02,0.11,0.05\nbad line\n"
        self.assertEqual(review.parse_ocr(out, 4), [(0.0, 0.3, "乱码字幕", "0.38,0.76,0.25,0.04"),
                                                     (5.0, 1.0, "190", "0.29,0.02,0.11,0.05")])

    def test_scene_cuts_from_showinfo(self):
        text = "[Parsed_showinfo_1] n:0 pts:48 pts_time:2.0 ...\n[Parsed_showinfo_1] n:1 pts:81 pts_time:3.3751 ...\n"
        self.assertEqual(review.scene_cuts(text), [2.0, 3.38])


if __name__ == "__main__":
    unittest.main()
