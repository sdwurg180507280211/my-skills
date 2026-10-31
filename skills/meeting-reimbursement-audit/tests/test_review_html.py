from __future__ import annotations

import contextlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_review_html as review
import read_review_notes as notes


def touch(path: Path, data: bytes = b"img") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def varint(n: int) -> bytes:
    out = b""
    while n >= 0x80:
        out += bytes([n & 0x7F | 0x80])
        n >>= 7
    return out + bytes([n])


def ls_key(key: str) -> bytes:
    return b"_file://\x00\x00" + key.encode("utf-16-le")


def ls_value(value: str) -> bytes:
    return b"\x00" + value.encode("utf-16-le")


def batch_record(ops: list[tuple[str, str | None]]) -> bytes:
    body = struct.pack("<QI", 1, len(ops))
    for key, value in ops:
        k = ls_key(key)
        if value is None:
            body += b"\x00" + varint(len(k)) + k
        else:
            v = ls_value(value)
            body += b"\x01" + varint(len(k)) + k + varint(len(v)) + v
    return struct.pack("<IHB", 0, len(body), 1) + body


class BuildReviewHtmlTests(unittest.TestCase):
    def test_slots_missing_and_other_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch, out = Path(tmp) / "批次", Path(tmp) / "复核"
            touch(batch / "会议A" / "付费服务提供者照片" / "截屏-课前.jpg")
            touch(batch / "会议A" / "会场照片" / "截屏-课中.PNG")
            touch(batch / "会议A" / "最终会议议程-海报.jpg")
            touch(batch / "会议B" / "截屏-课前.jpg")
            touch(batch / "会议B" / "合影.jpg")
            touch(batch / "会议B" / "~$锁.jpg")
            touch(batch / "会议B" / "参会明细.xlsx")
            result = review.build(batch, out, "合成批次")

            self.assertEqual(result["meetings"], 2)
            self.assertEqual(result["storage_key"], "合成批次:")
            self.assertEqual(result["missing"], ["会议B：缺课中截图", "会议B：缺海报"])
            self.assertTrue((out / "images" / "会议A" / "课中截图.png").is_file())
            self.assertTrue((out / "images" / "会议B" / "其他图片.jpg").is_file())
            self.assertEqual(result["images"], 5)
            page = (out / "截图复核.html").read_text(encoding="utf-8")
            self.assertIn('const K="合成批次:"', page)
            self.assertIn("data-k='会议A|有问题'", page)
            self.assertIn("未找到海报", page)

    def test_output_inside_batch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "批次"
            touch(batch / "会议A" / "截屏-课前.jpg")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                review.main([str(batch), "--out", str(batch / "复核")])
            self.assertFalse((batch / "复核").exists())


class ReadReviewNotesTests(unittest.TestCase):
    def test_chrome_log_later_writes_win_and_other_keys_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "Default" / "Local Storage" / "leveldb" / "000003.log"
            data = batch_record([("批次:会议A|有问题", "1"), ("批次:会议A|备注", "海报透明")])
            data += batch_record([("批次:会议B|有问题", "1"), ("别的:会议C|有问题", "1")])
            data += batch_record([("批次:会议B|有问题", "0"), ("批次:会议A|备注", None)])
            touch(log, data)
            kv, sources = notes.from_chrome("批次:", Path(tmp))

            self.assertEqual(sources, [str(log)])
            self.assertEqual(notes.flagged(kv), [{"会议": "会议A", "有问题": True, "备注": ""}])

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = touch(Path(tmp) / "截图复核结果.csv",
                         "﻿会议,有问题,备注\n\"会议A\",\"是\",\"课中无头像\"\n\"会议B\",\"\",\"再看\"\n".encode())
            self.assertEqual(notes.flagged(notes.from_csv(path)), [
                {"会议": "会议A", "有问题": True, "备注": "课中无头像"},
                {"会议": "会议B", "有问题": False, "备注": "再看"},
            ])

    def test_no_entries_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
            code = notes.main(["--key", "不存在", "--chrome-dir", tmp])
        self.assertEqual(code, 2)
        self.assertIn("--csv", out.getvalue())


if __name__ == "__main__":
    unittest.main()
