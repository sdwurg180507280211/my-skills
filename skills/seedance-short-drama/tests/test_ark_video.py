"""Offline tests: no network and no real API key."""
import base64
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ark_common  # noqa: E402
import ark_video  # noqa: E402


class MediaUrlTests(unittest.TestCase):
    def test_remote_and_asset_urls_pass_through(self):
        for url in ("https://example.com/a.png", "http://example.com/v.wav", "asset://asset-123"):
            self.assertEqual(ark_video.media_url(url), url)

    def test_local_files_are_inlined_without_reencoding(self):
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "sheet.PNG"
            img.write_bytes(b"\x89PNG-original-bytes")
            url = ark_video.media_url(img)
            self.assertTrue(url.startswith("data:image/png;base64,"))
            self.assertEqual(base64.b64decode(url.split(",", 1)[1]), b"\x89PNG-original-bytes")
            wav = Path(d) / "voice.wav"
            wav.write_bytes(b"RIFF")
            self.assertTrue(ark_video.media_url(wav).startswith("data:audio/wav;base64,"))

    def test_unknown_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.gif"
            p.write_bytes(b"x")
            with self.assertRaises(ValueError):
                ark_video.media_url(p)


class BodyTests(unittest.TestCase):
    def test_roles_follow_reference_order(self):
        body = ark_video.build_body(
            "model-id", "提示词", refs=["https://e/1.png", "https://e/2.png"], ref_audios=["https://e/v.wav"],
            first_frame="https://e/f.png", ratio="9:16", duration=8, resolution="720p", audio=True, seed=7)
        self.assertEqual([c.get("role") for c in body["content"]],
                         [None, "first_frame", "reference_image", "reference_image", "reference_audio"])
        self.assertEqual(body["content"][0], {"type": "text", "text": "提示词"})
        self.assertEqual(body["content"][4]["type"], "audio_url")
        self.assertEqual(body["content"][2]["image_url"]["url"], "https://e/1.png")
        self.assertEqual((body["duration"], body["resolution"], body["generate_audio"], body["watermark"], body["seed"]),
                         (8, "720p", True, False, 7))

    def test_seed_omitted_by_default(self):
        self.assertNotIn("seed", ark_video.build_body("m", "p"))


class CommonTests(unittest.TestCase):
    def test_env_key_takes_precedence(self):
        with mock.patch.dict(os.environ, {"ARK_API_KEY": "synthetic-key"}):
            self.assertEqual(ark_common.load_key(), "synthetic-key")

    def test_missing_key_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ARK_API_KEY": ""}), \
                mock.patch.object(ark_common, "KEY_FILE", Path(d) / "absent"):
            with self.assertRaises(ark_common.ArkError):
                ark_common.load_key()

    def test_requests_ignore_environment_proxies(self):
        # 没装自定义 opener 时，urlopen 会按 HTTP(S)_PROXY 走代理；装了 ProxyHandler({}) 后，
        # 默认的代理处理器被替换，空处理器本身也不会登记，所以 opener 里不应有任何带代理的处理器。
        opener = urllib.request._opener
        self.assertIsNotNone(opener)
        proxied = [h for h in opener.handlers if isinstance(h, urllib.request.ProxyHandler) and h.proxies]
        self.assertEqual(proxied, [])

    def test_submit_network_error_is_not_retried(self):
        calls = []

        def boom(*args, **kwargs):
            calls.append(1)
            raise ConnectionError("reset")

        with mock.patch.dict(os.environ, {"ARK_API_KEY": "k"}), mock.patch("urllib.request.urlopen", boom):
            with self.assertRaises(ConnectionError):
                ark_common.request("POST", "/x", {"a": 1})
        self.assertEqual(len(calls), 1)

    def test_query_network_error_is_retried(self):
        calls = []

        def flaky(*args, **kwargs):
            calls.append(1)
            raise ConnectionError("reset")

        with mock.patch.dict(os.environ, {"ARK_API_KEY": "k"}), mock.patch("urllib.request.urlopen", flaky), \
                mock.patch("time.sleep"):
            with self.assertRaises(ConnectionError):
                ark_common.request("GET", "/x", tries=3)
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
