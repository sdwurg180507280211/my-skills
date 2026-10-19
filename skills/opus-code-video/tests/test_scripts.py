"""Offline tests for opus-code-video scripts (synthetic timestamps and ffmpeg output; no network)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import doubao_tts  # noqa: E402
import mix_voice  # noqa: E402
import qc  # noqa: E402
import retime  # noqa: E402


def words(text, start=0.5, step=0.2):
    """把"按下回车，不到一秒。"拆成豆包那样的逐字时间戳：标点粘在前一个字上。"""
    out, t = [], start
    for ch in text:
        if ch in retime.PUNCT and out:
            out[-1]["word"] += ch
            continue
        out.append({"word": ch, "startTime": round(t, 3), "endTime": round(t + step, 3)})
        t += step
    return out


class RetimeTests(unittest.TestCase):
    def base(self, place, bounds=(0, "a", "b.0", "duration")):
        return {"duration": 10, "ev": {"a": 3.0, "b": [6.0, 7.0], "hit": 6.0},
                "narration": {"bounds": list(bounds), "place": place, "tail": .5, "end_hold": 1.0}}

    def test_resolve_refs(self):
        ev = {"a": 3.0, "b": [6.0, 7.0]}
        self.assertEqual([retime.resolve(ev, 10, r) for r in (0, "a", "b.1", "duration")], [0.0, 3.0, 7.0, 10.0])

    def test_short_lines_leave_timing_alone(self):
        lines = ["一二。", "三四。", "五六。"]
        out, _, _ = retime.retime(self.base([{"seg": 0, "lead": .2}, {"seg": 1, "lead": .2}, {"seg": 2, "lead": .2}]),
                                  lines, [words(s) for s in lines])
        self.assertEqual(out["duration"], 10)
        self.assertEqual(out["ev"]["b"], [6.0, 7.0])
        self.assertEqual(out["voice"][1]["speech"][0], 3.2)        # 第 1 段开头 3.0 + lead 0.2

    def test_long_line_stretches_only_its_segment(self):
        lines = ["短。", "这是一句很长很长很长很长的话。", "短。"]
        out, bounds, nb = retime.retime(self.base([{"seg": 0, "lead": .2}, {"seg": 1, "lead": .2}, {"seg": 2, "lead": .2}]),
                                        lines, [words(s) for s in lines])
        self.assertAlmostEqual(nb[1] - nb[0], 3.0)                   # 第 0 段够长，不动
        self.assertGreater(nb[2] - nb[1], 3.0)                       # 第 1 段被拉长
        self.assertAlmostEqual(out["duration"], 10 + (nb[2] - nb[1] - 3.0), places=3)
        self.assertGreater(out["ev"]["b"][0], 6.0)                   # 后面的事件整体后移

    def test_anchor_word_lands_on_segment_end(self):
        lines = ["一共四百毫秒。"]
        w = words(lines[0])
        out, _, nb = retime.retime(self.base([{"seg": 1, "anchor_word": "四", "pre": .2}], bounds=(0, "a", "hit", "duration")),
                                   lines, [w])
        four = next(x["startTime"] for x in w if x["word"] == "四")
        self.assertAlmostEqual(out["voice"][0]["at"] + four, out["ev"]["hit"], places=3)

    def test_subtitles_split_on_punct_and_apply_show(self):
        subs = retime.subtitles("加起来多久？问到点 com，好。", words("加起来多久？问到点com，好。"), 10.0, {"点 com": ".com"})
        self.assertEqual([s["text"] for s in subs], ["加起来多久？", "问到.com", "好"])
        self.assertEqual(subs[0]["t"][0], 10.5)

    def test_place_count_must_match_lines(self):
        with self.assertRaises(ValueError):
            retime.retime(self.base([{"seg": 0}]), ["一。", "二。"], [words("一。"), words("二。")])

    def test_merge_small_gaps(self):
        subs = retime.merge_gaps([{"t": [0, 1.0]}, {"t": [1.2, 2]}, {"t": [3, 4]}])
        self.assertEqual(subs[0]["t"][1], 1.2)
        self.assertEqual(subs[1]["t"][1], 2)


class MixAndTtsTests(unittest.TestCase):
    def test_negative_offset_trims_leading_silence(self):
        self.assertEqual(mix_voice.placement(-0.01, 1000, 5000, 1000), (0, 10, 990))
        self.assertEqual(mix_voice.placement(4.5, 1000, 5000, 1000), (4500, 0, 500))   # 超出片尾的部分丢掉

    def test_submit_body_requests_timestamps(self):
        b = doubao_tts.submit_body("你好", "zh_female_mengyatou_uranus_bigtts", rate=10)
        self.assertEqual(b["req_params"]["speaker"], "zh_female_mengyatou_uranus_bigtts")
        self.assertTrue(b["req_params"]["audio_params"]["enable_timestamp"])
        self.assertEqual(b["req_params"]["audio_params"]["speech_rate"], 10)

    def test_headers_use_api_key_only(self):
        h = doubao_tts.headers("k")
        self.assertEqual(h["X-Api-Resource-Id"], "seed-tts-2.0")
        self.assertNotIn("X-Api-App-Id", h)

    def test_explain_known_error(self):
        msg = doubao_tts.explain({"code": 45000000, "message": "load grant: requested grant not found"})
        self.assertIn("X-Api-Key", msg)


class QcTests(unittest.TestCase):
    def test_parse_probe(self):
        info = qc.parse_probe("stream|codec_type=video|width=1920|height=1080|r_frame_rate=30/1|nb_frames=2026\n"
                              "stream|codec_type=audio|width=N/A|height=N/A|r_frame_rate=0/0|nb_frames=3166\n"
                              "format|duration=67.533333\n")
        self.assertEqual((info["width"], info["fps"], info["frames"], info["duration"], info["audio"]), (1920, 30.0, 2026, 67.533, True))

    def test_parse_loudness_and_black(self):
        err = ("[Parsed_ebur128_0] Summary:\n  Integrated loudness:\n    I:         -14.0 LUFS\n"
               "  True peak:\n    Peak:       -1.6 dBFS\n[blackdetect] black_start:0 black_end:0.4 black_duration:0.4\n")
        self.assertEqual(qc.parse_loudness(err), (-14.0, -1.6))
        self.assertEqual(qc.parse_black(err), [(0.0, 0.4)])


if __name__ == "__main__":
    unittest.main()
