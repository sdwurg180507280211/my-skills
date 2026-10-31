"""Offline tests for the script review; nothing is sent."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_script  # noqa: E402


class ReviewScriptTests(unittest.TestCase):
    def test_default_provider_is_gemini_without_effort(self):
        body = review_script.build_body("S1 台词", "B")
        self.assertEqual(body["model"], "gemini-3.8-flash-high")
        self.assertNotIn("reasoning_effort", body)

    def test_body_carries_model_effort_route_and_script(self):
        body = review_script.build_body("S1 台词", "B", provider="deepseek", context="医生 IP 样片")
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["reasoning_effort"], "max")
        user = body["messages"][1]["content"]
        self.assertIn("台词表演与可拍性", user)
        self.assertIn("S1 台词", user)
        self.assertIn("医生 IP 样片", user)
        self.assertNotIn("上一轮意见", user)

    def test_reviewer_is_told_to_skip_copyright_and_compliance(self):
        body = review_script.build_body("剧本", "A")
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        self.assertIn("不讨论版权、合规", system)
        self.assertIn("不追批文号", user)

    def test_today_is_given_to_the_reviewer(self):
        user = review_script.build_messages("剧本", "A", today="2026-10-20")[1]["content"]
        self.assertIn("今天是 2026-10-20", user)

    def test_recheck_includes_previous_review(self):
        user = review_script.build_messages("剧本", "A", prev="1. S3 护士没入画")[1]["content"]
        self.assertIn("S3 护士没入画", user)
        self.assertIn("上次必须改的落实情况", user)

    def test_key_prefers_env_then_file(self):
        for provider, env, folder in [("deepseek", "DEEPSEEK_API_KEY", "deepseek"), ("gemini", "SUB2API_API_KEY", "sub2api")]:
            with tempfile.TemporaryDirectory() as home:
                f = Path(home) / ".config" / folder / "api-key"
                f.parent.mkdir(parents=True)
                f.write_text("from-file\n", encoding="utf-8")
                with mock.patch.dict(os.environ, {env: "from-env"}), mock.patch.object(Path, "home", return_value=Path(home)):
                    self.assertEqual(review_script.load_key(provider), "from-env")
                with mock.patch.dict(os.environ, {env: ""}), mock.patch.object(Path, "home", return_value=Path(home)):
                    self.assertEqual(review_script.load_key(provider), "from-file")

    def test_missing_key_stops_without_printing_secrets(self):
        for provider, env in [("deepseek", "DEEPSEEK_API_KEY"), ("gemini", "SUB2API_API_KEY")]:
            with tempfile.TemporaryDirectory() as home:
                with mock.patch.dict(os.environ, {env: ""}), mock.patch.object(Path, "home", return_value=Path(home)):
                    with self.assertRaises(SystemExit):
                        review_script.load_key(provider)

    def test_must_fix_section_is_parsed(self):
        clear = review_script.must_fix_clear
        self.assertTrue(clear("## 必须改\n无。\n\n## 可以更好\n- 小事"))
        self.assertTrue(clear("## 必须改\n\n**无**\n## 可以更好"))
        self.assertFalse(clear("## 必须改\n1. S8 第二镜跑到走廊\n## 可以更好\n无"))
        self.assertIsNone(clear("没有按格式输出"))

    def test_render_names_routes_and_usage(self):
        d = {"model": "deepseek-flash", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
             "choices": [{"message": {"content": "## 必须改\n无"}}]}
        text = review_script.render([("A", d)])
        self.assertIn("A 路：专业事实与真实性", text)
        self.assertIn("输入 10 tokens", text)


if __name__ == "__main__":
    unittest.main()
