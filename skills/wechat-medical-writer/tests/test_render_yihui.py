import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'render_yihui.py')
IDS = ['医荟她-栏目', '医荟她-导语', '医荟她-章节', '医荟她-正文', '医荟她-参考文献', '医荟她-资料说明', '医荟她-结尾']
SLOTS = {'医荟她-导语': '{{intro}}', '医荟她-章节': '{{number}}.{{heading}}', '医荟她-正文': '{{paragraphs}}',
         '医荟她-参考文献': '<ol>{{references}}</ol>', '医荟她-资料说明': '{{sourceNote}}', '医荟她-结尾': '{{disclaimer}}'}
QA_IDS = ['医荟她-栏目', '医荟她-导语', '医荟她访谈-提问', '医荟她访谈-回答', '医荟她访谈-图片', '医荟她-参考文献',
          '医荟她-资料说明', '医荟她-结尾', '医荟她访谈-编辑信息']
SLOTS.update({'医荟她访谈-提问': '{{askAvatar}}|{{question}}', '医荟她访谈-回答': '{{answerAvatar}}|{{answer}}',
              '医荟她访谈-图片': '<img src="{{src}}" alt="{{alt}}">', '医荟她访谈-编辑信息': '{{credits}}'})
STYLES = {'styles': [{'id': 'layout-current', 'kind': 'layout', 'componentIds': IDS,
                      'template': {'shell': '<html><body><div id="shell">{{content}}</div></body></html>'}},
                     {'id': 'layout-yihui-interview', 'kind': 'layout', 'componentIds': QA_IDS,
                      'template': {'shell': '<html><body><div id="qa-shell">{{content}}</div></body></html>',
                                   'slots': {'askAvatar': 'ASK', 'answerAvatar': 'ANS'}}}],
          'components': [{'id': i, 'html': '<section data-c="%s">%s</section>' % (i, SLOTS.get(i, ''))}
                         for i in dict.fromkeys(IDS + QA_IDS)]}
ARTICLE = """# 标题

> 第一段导语，带 **重点**。

## 01 第一节

![示意](imgs/01-a.png)

**PDT = Photodynamic Therapy（光动力治疗）**。正文 <b> 引用 [1]，多个 [2][3]。

- 一项
- 二项

| 指标 | 数值 |
|---|---|
| 有效率 | 41.1% |

## 02 第二节

![数据](imgs/02-b.png)

收尾一句。

---

## 参考文献

[1] 机构. [标题一](https://example.com/a). 官方网页，访问日期：2026-10-12.

[2] 作者. [标题二](https://doi.org/10.1/x). 综述，访问日期：2026-10-14.

[3] 作者. 无链接条目. 指南，访问日期：2026-10-13.

*本文为健康科普，不能替代个人诊疗意见。请到妇科就诊。*
"""

QA_ARTICLE = """# 问答标题

> 这是读者常见问题整理。

**读者问：** 第一个问题？

**医荟她答：** 第一段回答 [1]。

第二段回答。

- 要点一
- 要点二

![配图](imgs/01-a.png)

**读者问：** 第二个问题？

**医荟她答：** 只有一段 [2]。

---

## 参考文献

[1] 机构. [标题一](https://example.com/a). 官方网页，访问日期：2026-10-12.

[2] 作者. 无链接条目. 指南，访问日期：2026-10-13.

*本文为健康科普，按读者常见问题整理，不能替代个人诊疗意见。*
"""


class RenderTest(unittest.TestCase):
    def run_render(self, *extra, article=ARTICLE):
        with tempfile.TemporaryDirectory() as d:
            styles, md, out = (os.path.join(d, n) for n in ('styles.json', 'a.md', 'out.html'))
            with open(styles, 'w', encoding='utf-8') as stream:
                json.dump(STYLES, stream, ensure_ascii=False)
            with open(md, 'w', encoding='utf-8') as stream:
                stream.write(article)
            p = subprocess.run([sys.executable, SCRIPT, md, styles, out] + list(extra),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            html = ''
            if p.returncode == 0:
                with open(out, encoding='utf-8') as stream:
                    html = stream.read()
            return p, html

    def test_structure_and_slots(self):
        p, html = self.run_render()
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        info = json.loads(p.stdout.decode())
        self.assertEqual(info['images'], ['imgs/01-a.png', 'imgs/02-b.png'])
        self.assertEqual((info['sections'], info['references']), (2, 3))
        order = [html.index('data-c="%s"' % i) for i in IDS]
        self.assertEqual(order, sorted(order))
        self.assertIn('01.第一节', html)
        self.assertNotIn('{{', html)
        self.assertNotIn('<h1', html)
        self.assertNotIn('# 标题', html)

    def test_inline_escaping_citations_and_lists(self):
        _, html = self.run_render()
        self.assertIn('&lt;b&gt;', html)
        self.assertIn('<strong>重点</strong>', html)
        self.assertIn('vertical-align:baseline;">[2]</span>', html)
        self.assertIn('· 一项', html)
        self.assertIn('<td style=', html)
        self.assertIn('41.1%', html)

    def test_reference_urls_are_visible_text(self):
        _, html = self.run_render()
        refs = html[html.index('data-c="医荟她-参考文献"'):html.index('data-c="医荟她-资料说明"')]
        self.assertNotIn('<a ', refs)
        self.assertIn('example.com/a', refs)
        self.assertIn('doi.org/10.1/x', refs)
        self.assertIn('无链接条目', refs)

    def test_source_note_and_disclaimer(self):
        _, html = self.run_render()
        self.assertIn('资料核对日期：2026年10月14日', html)
        self.assertIn('请到妇科就诊。', html)
        _, html = self.run_render('--source-note', '自定义说明')
        self.assertIn('自定义说明', html)

    def test_preview_uses_shell(self):
        _, html = self.run_render('--preview')
        self.assertIn('<div id="shell">', html)

    def test_rejects_unnumbered_section_and_bad_references(self):
        p, _ = self.run_render(article=ARTICLE.replace('## 01 第一节', '## 第一节'))
        self.assertNotEqual(p.returncode, 0)
        p, _ = self.run_render(article=ARTICLE.replace('[3] 作者', '[4] 作者'))
        self.assertNotEqual(p.returncode, 0)

    def test_regular_article_keeps_default_layout(self):
        p, html = self.run_render('--preview')
        self.assertEqual(json.loads(p.stdout.decode())['layout'], 'layout-current')
        self.assertNotIn('医荟她访谈', html)

    def test_qa_article_uses_interview_layout(self):
        p, html = self.run_render('--preview', article=QA_ARTICLE)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        info = json.loads(p.stdout.decode())
        self.assertEqual(info['layout'], 'layout-yihui-interview')
        self.assertEqual((info['sections'], info['questions'], info['answers'], info['references']), (0, 2, 2, 2))
        self.assertEqual(info['images'], ['imgs/01-a.png'])
        self.assertIn('<div id="qa-shell">', html)
        self.assertNotIn('{{', html)
        self.assertNotIn('data-c="医荟她-章节"', html)
        order = [html.index('data-c="%s"' % i) for i in QA_IDS]
        self.assertEqual(order, sorted(order))
        self.assertIn('ASK|<p style=', html)
        self.assertIn('<strong>读者问：</strong> 第一个问题？', html)
        first = html[html.index('ANS|'):html.index('data-c="医荟她访谈-图片"')]
        self.assertIn('第二段回答。', first)
        self.assertIn('· 要点二', first)
        self.assertEqual(first.count('margin:0 0 12px;'), 2)
        self.assertIn('<img src="imgs/01-a.png" alt="配图">', html)
        self.assertIn('整理：医荟她健康', html)

    def test_rejects_mixed_or_one_sided_qa(self):
        mixed = QA_ARTICLE.replace('**读者问：** 第二个问题？', '## 01 小节')
        p, _ = self.run_render(article=mixed)
        self.assertNotEqual(p.returncode, 0)
        one_sided = QA_ARTICLE.replace('**医荟她答：** 第一段回答', '第一段回答').replace('**医荟她答：** 只有一段', '只有一段')
        p, _ = self.run_render(article=one_sided)
        self.assertNotEqual(p.returncode, 0)
        after_image = QA_ARTICLE.replace('**读者问：** 第二个问题？', '图片后的散段')
        p, _ = self.run_render(article=after_image)
        self.assertNotEqual(p.returncode, 0)


if __name__ == '__main__':
    unittest.main()
