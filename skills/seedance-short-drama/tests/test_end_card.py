"""Offline test for the end card renderer (needs Pillow and a Chinese font)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from PIL import Image
    import end_card  # noqa: E402
    FONT = next((f for f in end_card.FONTS if Path(f).exists()), None)
except ImportError:
    FONT = None


@unittest.skipUnless(FONT, "需要 Pillow 和中文字体")
class EndCardTests(unittest.TestCase):
    def test_renders_requested_size_with_text(self):
        with tempfile.TemporaryDirectory() as d:
            for size in ((720, 1280), (360, 640)):
                out = Path(d) / f"card_{size[0]}.png"
                end_card.render(out, "第一行|第二行", tag="下集", note="前半句，|后半句", sub="小字",
                                footer="剧情纯属虚构", size=size)
                img = Image.open(out).convert("RGB")
                self.assertEqual(img.size, size)
                self.assertIsNotNone(img.getbbox())  # 黑底上确实画了文字
                reds = [px for px in img.getdata() if px[0] > 150 and px[1] < 120 and px[2] < 120]
                self.assertTrue(reds)  # 标签底色和标红文字


if __name__ == "__main__":
    unittest.main()
