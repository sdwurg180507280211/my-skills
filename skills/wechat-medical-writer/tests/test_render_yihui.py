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
STYLES = {'styles': [{'id': 'layout-current', 'kind': 'layout', 'componentIds': IDS,
                      'template': {'shell': '<html><body><div id="shell">{{content}}</div></body></html>'}}],
          'components': [{'id': i, 'html': '<section data-c="%s">%s</section>' % (i, SLOTS.get(i, ''))} for i in IDS]}
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


if __name__ == '__main__':
    unittest.main()
