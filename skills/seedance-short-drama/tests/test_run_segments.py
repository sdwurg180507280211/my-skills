"""Offline tests for segment planning; nothing is submitted."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_segments  # noqa: E402


class PlanTests(unittest.TestCase):
    def test_next_take_skips_existing_and_running(self):
        with tempfile.TemporaryDirectory() as d:
            out, log = Path(d) / "out", Path(d) / "log"
            out.mkdir()
            log.mkdir()
            (out / "S1_t1_2.5_720p.mp4").touch()
            (log / "S1_t2.running").touch()
            self.assertEqual(run_segments.next_take(out, log, "S1"), 3)
            self.assertEqual(run_segments.next_take(out, log, "S2"), 1)

    def test_command_maps_names_to_project_assets_in_order(self):
        cfg = {"时长": 8, "图片": ["甲", "乙"], "音频": ["甲"]}
        cmd = run_segments.build_command(Path("/proj"), "S3", cfg, "model-id", "720p", "/proj/4_生成片段/S3.mp4")
        refs = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--ref"]
        self.assertEqual(refs, [str(Path("/proj/2_素材/角色/甲_三视图.png")), str(Path("/proj/2_素材/角色/乙_三视图.png"))])
        self.assertEqual([cmd[i + 1] for i, a in enumerate(cmd) if a == "--ref-audio"],
                         [str(Path("/proj/2_素材/声音/甲.wav"))])
        for flag, value in (("--duration", "8"), ("--resolution", "720p"), ("--ratio", "9:16"),
                            ("--model", "model-id"), ("--prompt-file", str(Path("/proj/3_提示词/S3.txt")))):
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--audio", cmd)

    def test_missing_inputs_are_reported_before_submit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "3_提示词").mkdir()
            (p / "3_提示词" / "S1.txt").write_text("x", encoding="utf-8")
            cmd = run_segments.build_command(p, "S1", {"时长": 5, "图片": ["甲"]}, "m", "720p", p / "o.mp4")
            self.assertEqual(run_segments.missing_inputs(cmd), [str(p / "2_素材" / "角色" / "甲_三视图.png")])

    def test_cost_matches_official_unit_price(self):
        self.assertAlmostEqual(run_segments.cost(238500, 70), 16.695)


if __name__ == "__main__":
    unittest.main()
