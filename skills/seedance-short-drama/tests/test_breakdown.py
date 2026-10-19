"""Offline tests for reference-video breakdown helpers (synthetic cuts and OCR hits)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import breakdown  # noqa: E402


class BreakdownTests(unittest.TestCase):
    def test_shots_cover_whole_video_and_drop_edge_cuts(self):
        self.assertEqual(breakdown.shots_from_cuts([3.0, 0.02, 1.5, 9.98], 10.0),
                         [(1, 0.0, 1.5), (2, 1.5, 3.0), (3, 3.0, 10.0)])

    def test_no_cuts_is_one_shot(self):
        self.assertEqual(breakdown.shots_from_cuts([], 6.5), [(1, 0.0, 6.5)])

    def test_subtitles_merge_consecutive_frames_and_skip_upper_text(self):
        hits = [(4.0, 1.0, "抓紧", "0.43,0.76,0.13,0.03"),
                (4.5, 1.0, "抓紧", "0.43,0.76,0.13,0.04"),
                (5.0, 1.0, "无信号", "0.45,0.47,0.14,0.04"),     # 画面中间的字，不是字幕
                (6.0, 1.0, "抓紧", "0.43,0.76,0.13,0.04"),      # 隔了一帧，算新的一句
                (6.0, 1.0, "抓紧", "0.40,0.78,0.13,0.04"),      # 同一帧重复识别
                (7.0, 0.5, "说普通话", "0.41,0.76,0.18,0.04")]
        self.assertEqual(breakdown.subtitle_lines(hits, 2), [
            {"start": 4.0, "end": 5.0, "text": "抓紧"},
            {"start": 6.0, "end": 6.5, "text": "抓紧"},
            {"start": 7.0, "end": 7.5, "text": "说普通话"}])

    def test_lines_attach_to_shot_by_start_time(self):
        lines = [{"start": 1.0, "end": 2.5, "text": "甲"}, {"start": 2.9, "end": 3.4, "text": "乙"},
                 {"start": 3.0, "end": 4.0, "text": "丙"}]
        self.assertEqual(breakdown.lines_for_shot(lines, 0.0, 3.0), ["甲", "乙"])
        self.assertEqual(breakdown.lines_for_shot(lines, 3.0, 10.0), ["丙"])

    def test_stats_count_hook_shots(self):
        shots = [(1, 0.0, 2.0), (2, 2.0, 11.0), (3, 11.0, 13.0), (4, 13.0, 20.0)]
        s = breakdown.stats(20.0, shots, [])
        self.assertEqual(s["镜头数"], 4)
        self.assertEqual(s["前 12 秒的镜头数"], 3)
        self.assertEqual(s["平均每个镜头"], "5.0 秒")

    def test_sample_plan_covers_opening_and_long_shots(self):
        shots = [(1, 0.0, 20.0), (2, 20.0, 25.0), (3, 25.0, 143.5), (4, 143.5, 150.0)]
        self.assertEqual(breakdown.sample_plan(shots, 150.0), [
            ("开头_每秒.jpg", 0.0, 20.0, 1, 5),                 # 镜头 1 整个在开头里，不再单独抽
            ("镜头03_每4秒.jpg", 25.0, 143.5, 4, 6)])

    def test_sample_plan_short_video_opening_is_whole_video(self):
        self.assertEqual(breakdown.sample_plan([(1, 0.0, 8.0)], 8.0), [("开头_每秒.jpg", 0.0, 8.0, 1, 5)])

    def test_draft_points_long_shot_to_its_sheet(self):
        md = breakdown.draft(Path("a.mp4"), 150.0, "1920×1080", [(1, 0.0, 20.0), (2, 20.0, 150.0)], [],
                             ["镜头总览_1.jpg"], samples=["开头_每秒.jpg", "镜头02_每4秒.jpg"])
        self.assertIn("| 2 | 20.0–150.0 | 130.0 | 可能不止一个镜头，看 镜头02_每4秒.jpg |", md)
        self.assertIn("| 1 | 0.0–20.0 | 20.0 |  |", md)


if __name__ == "__main__":
    unittest.main()
