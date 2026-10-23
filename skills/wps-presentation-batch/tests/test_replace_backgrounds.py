"""Offline checks for replace_backgrounds.py on a synthetic deck (needs lxml and python-pptx)."""
import importlib.util
import io
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Emu
except ImportError:  # pragma: no cover
    Presentation = None

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/replace_backgrounds.py"
spec = importlib.util.spec_from_file_location("replace_backgrounds", SCRIPT)
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

W, H = 12192000, 6858000


def png(rgb, size=(16, 9)):
    w, h = size
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def build_old_deck(path: Path) -> None:
    """Master image bg, a layout with a full-slide picture, slide-level bgs on slides 1 and 3."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(W), Emu(H)
    title_layout, body_layout = prs.slide_layouts[0], prs.slide_layouts[5]
    for i, layout in enumerate([title_layout, body_layout, body_layout, body_layout], 1):
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = f"Title {i}"
    prs.save(path)

    pkg = rb.Package(path)
    deck = rb.Deck(pkg)
    old_master = rb.add_media(pkg, "old_master", png((10, 10, 10)), "png")
    old_layout = rb.add_media(pkg, "old_layout", png((20, 20, 20)), "png")
    old_slide = rb.add_media(pkg, "old_slide", png((30, 30, 30)), "png")
    rb.set_bg(pkg, deck.masters[0], old_master)
    rb.set_bg(pkg, deck.slides[0], old_slide)
    rb.set_bg(pkg, deck.slides[2], old_slide)
    layout = deck.parent(deck.slides[1], "slideLayout")
    rid = pkg.add_image_rel(layout, old_layout)
    pic = rb.etree.fromstring(
        f'<p:pic xmlns:p="{rb.P}" xmlns:a="{rb.A}" xmlns:r="{rb.R}"><p:nvPicPr><p:cNvPr id="99" name="old bg"/>'
        f'<p:cNvPicPr/><p:nvPr userDrawn="1"/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/>'
        f'<a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{W}" cy="{H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
    pkg.xml(layout).find("p:cSld/p:spTree", rb.NS).insert(2, pic)
    pkg.save(path)


@unittest.skipIf(Presentation is None, "python-pptx not installed")
class ReplaceBackgroundsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.src = self.dir / "deck.pptx"
        build_old_deck(self.src)
        self.content, self.cover = self.dir / "content.png", self.dir / "cover.png"
        self.content.write_bytes(png((200, 220, 240)))
        self.cover.write_bytes(png((40, 90, 200)))
        self.out = self.dir / "out"

    def run_cli(self, *args):
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = rb.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_inspect_flags_layout_pictures(self):
        info = rb.inspect_deck(self.src)
        self.assertEqual(info["slides_hiding_master_bg"], [2, 3, 4])
        self.assertEqual([s["slide"] for s in info["slide_overrides"]], [1, 3])

    def test_apply_sets_master_and_cover_and_clears_overrides(self):
        code, out, _ = self.run_cli("apply", self.src, "--content", self.content, "--cover", self.cover,
                                    "--out-dir", self.out)
        self.assertEqual(code, 0, out)
        pkg = rb.Package(self.out / "deck.pptx")
        deck = rb.Deck(pkg)
        content_md5, cover_md5 = rb.md5(self.content.read_bytes()), rb.md5(self.cover.read_bytes())
        for i in range(1, 5):
            eff = deck.effective(i)
            self.assertEqual(eff["covered_by"], [])
            self.assertEqual(eff["bg"]["md5"], cover_md5 if i == 1 else content_md5, f"slide {i}")
        self.assertFalse([n for n in pkg.data if "old_" in n], "old background media should be dropped")

    def test_text_is_unchanged(self):
        self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.out)
        before = [s.shapes.title.text for s in Presentation(self.src).slides]
        after = [s.shapes.title.text for s in Presentation(self.out / "deck.pptx").slides]
        self.assertEqual(before, after)

    def test_without_cover_every_slide_uses_content(self):
        self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.out)
        deck = rb.Deck(rb.Package(self.out / "deck.pptx"))
        self.assertEqual(deck.effective(1)["bg"]["md5"], rb.md5(self.content.read_bytes()))

    def test_refuses_existing_output_and_source(self):
        self.assertEqual(self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.out)[0], 0)
        code, _, err = self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.out)
        self.assertEqual(code, 1)
        self.assertIn("exists", err)
        code, _, err = self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.dir)
        self.assertEqual(code, 1)
        self.assertIn("overwrite the source", err)

    def test_report_keeps_one_copy_of_each_removed_image(self):
        report = self.dir / "report"
        self.run_cli("apply", self.src, "--content", self.content, "--out-dir", self.out, "--report-dir", report)
        self.assertTrue((report / "report.json").exists())
        self.assertEqual(len(list((report / "removed-images").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
