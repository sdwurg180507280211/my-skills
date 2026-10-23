"""Offline checks for swap_template_pages.py on a synthetic deck (needs lxml and python-pptx)."""
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Emu, Pt
except ImportError:  # pragma: no cover
    Presentation = None

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("swap_template_pages", SCRIPTS / "swap_template_pages.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
rb = st.rb

from test_replace_backgrounds import png  # noqa: E402

W, H = 12192000, 6858000


def decoration(rid, x, y, cx, cy, sid=90):
    return rb.etree.fromstring(
        f'<p:pic xmlns:p="{rb.P}" xmlns:a="{rb.A}" xmlns:r="{rb.R}"><p:nvPicPr><p:cNvPr id="{sid}" name="old mark"/>'
        f'<p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/>'
        f'<a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/>'
        f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def build_other_family_deck(path: Path) -> None:
    """Title page first (no picture cover), a layout decoration also pasted onto a slide,
    a title in the logo corner, and a white-text Thanks page."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(W), Emu(H)
    for text, layout in (("讲题", prs.slide_layouts[0]), ("内容标题", prs.slide_layouts[5]), ("Thanks", prs.slide_layouts[5])):
        prs.slides.add_slide(layout).shapes.title.text = text
    title = prs.slides[1].shapes.title
    title.left, title.top, title.width, title.height = Pt(39), Pt(20), Pt(800), Pt(40)
    prs.save(path)

    pkg = rb.Package(path)
    deck = rb.Deck(pkg)
    mark = rb.add_media(pkg, "old_mark", png((220, 30, 30)), "png")
    layout = deck.parent(deck.slides[1], "slideLayout")
    for part in (layout, deck.slides[1]):
        rid = pkg.add_image_rel(part, mark)
        pkg.xml(part).find("p:cSld/p:spTree", rb.NS).append(decoration(rid, 0, 0, Pt(194), Pt(39)))
    pkg.save(path)


@unittest.skipIf(Presentation is None, "python-pptx not installed")
class SwapTemplatePagesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.src = self.dir / "14.deck.pptx"
        build_other_family_deck(self.src)
        self.imgs = {}
        for name, rgb in (("cover", (40, 90, 200)), ("title", (200, 60, 60)), ("content", (230, 230, 230))):
            self.imgs[name] = self.dir / f"{name}.png"
            self.imgs[name].write_bytes(png(rgb))

    def run_cli(self, *extra):
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = st.main([str(self.src), "--cover", str(self.imgs["cover"]), "--title", str(self.imgs["title"]),
                            "--content", str(self.imgs["content"]), "--out-dir", str(self.dir / "out"),
                            "--report-dir", str(self.dir / "report"), *extra])
        return code, out.getvalue() + err.getvalue()

    def test_restyle_inserts_cover_strips_copies_moves_title_and_rewrites_end(self):
        code, output = self.run_cli("--restyle", "14", "--logo-box", "15,15,68,68", "--end-text", "感谢聆听|THANKS")
        self.assertEqual(code, 0, output)
        pkg = rb.Package(self.dir / "out" / self.src.name)
        deck = rb.Deck(pkg)
        self.assertEqual(len(deck.slides), 4)
        texts = ["".join(pkg.xml(s).find("p:cSld", rb.NS).itertext()) for s in deck.slides]
        self.assertEqual(texts[0], "")
        self.assertEqual(texts[3], "感谢聆听THANKS")
        for part in deck.layouts + deck.slides:
            self.assertFalse(pkg.xml(part).findall(".//p:pic", rb.NS), part)
        title = next(el for el in pkg.xml(deck.slides[2]).iter(f"{{{rb.P}}}sp") if "内容标题" in "".join(el.itertext()))
        x, _, cx, _ = st.box_of(st.xfrm_of(title))
        self.assertEqual((x, x + cx), (75 * st.PT, (39 + 800) * st.PT))

    def test_existing_output_needs_overwrite_for_a_single_deck_rerun(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli()[0], 1)
        self.assertEqual(self.run_cli("--overwrite")[0], 0)


if __name__ == "__main__":
    unittest.main()
