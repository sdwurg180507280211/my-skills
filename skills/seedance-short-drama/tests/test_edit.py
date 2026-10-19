"""Offline tests for the edit list renderer; the render test uses tiny synthetic clips."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import edit  # noqa: E402


class GraphTests(unittest.TestCase):
    def test_plain_segment_normalizes_loudness_and_fades_edges(self):
        graph, total = edit.segment_graph({"文件": "x"}, 5.0)
        self.assertEqual(total, 5.0)
        self.assertIn("loudnorm=I=-16", graph)
        self.assertIn("afade=t=in:st=0:d=0.08", graph)
        self.assertIn("afade=t=out:st=4.920:d=0.08", graph)
        self.assertNotIn("tpad", graph)

    def test_zoom_window_splits_and_resets_pixel_aspect(self):
        graph, _ = edit.segment_graph({"推近": [{"起": 1, "止": 2, "裁切": [20, 60, 420, 747]}]}, 5.0)
        self.assertIn("split=3", graph)
        self.assertIn("crop=420:747:20:60,scale=720:1280,setsar=1", graph)
        self.assertIn("concat=n=3:v=1:a=0", graph)

    def test_blur_only_inside_time_window(self):
        graph, _ = edit.segment_graph({"打码": [{"起": 3.4, "止": 7.0, "区域": [0, 590, 175, 250]}]}, 10.0)
        self.assertIn("crop=175:250:0:590,boxblur", graph)
        self.assertIn("overlay=0:590:enable='between(t,3.4,7.0)'", graph)

    def test_hold_and_fade_extend_duration(self):
        graph, total = edit.segment_graph({"定格": 1.0, "淡出": 0.8}, 5.0)
        self.assertEqual(total, 6.0)
        self.assertIn("tpad=stop_mode=clone:stop_duration=1.0", graph)
        self.assertIn("fade=t=out:st=5.200:d=0.8", graph)
        self.assertIn("apad=pad_dur=1.0", graph)

    def test_picture_replacement_keeps_original_audio(self):
        graph, _ = edit.segment_graph({"画面替换": {"文件": "b.mp4", "起": 2.6, "止": 5.3, "源入点": 1.25}}, 11.0)
        self.assertIn("[1:v]trim=1.25:3.95", graph)
        self.assertIn("[0:a]atrim=", graph)
        self.assertNotIn("[1:a]", graph)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "需要 ffmpeg")
class RenderTests(unittest.TestCase):
    def test_end_to_end_with_zoom_replacement_hold_and_card(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name, pattern in (("a.mp4", "testsrc2"), ("b.mp4", "smptebars")):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"{pattern}=size=360x640:rate=24:d=2",
                                "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-shortest",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(p / name)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=360x640",
                            "-frames:v", "1", str(p / "card.png")], check=True)
            edl = {"输出": "out/final.mp4", "画布": [360, 640], "帧率": 24,
                   "段落": [{"段": "S1", "文件": "a.mp4", "推近": [{"起": 0.5, "止": 1.5, "裁切": [10, 30, 210, 373]}],
                            "画面替换": {"文件": "b.mp4", "起": 0.2, "止": 0.6, "源入点": 0.5}},
                           {"段": "S2", "文件": "b.mp4", "响度": -20, "定格": 0.5, "淡出": 0.4}],
                   "片尾卡": {"图片": "card.png", "时长": 1.0, "淡入": 0.2, "淡出": 0.2}}
            (p / "edl.json").write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(edit.main(["--project", str(p), str(p / "edl.json")]), 0)
            self.assertAlmostEqual(edit.duration(p / "out" / "final.mp4"), 5.5, delta=0.2)


if __name__ == "__main__":
    unittest.main()
