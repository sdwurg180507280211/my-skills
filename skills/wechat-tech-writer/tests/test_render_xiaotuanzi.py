import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'scripts', 'render_xiaotuanzi.py')
IDS = ['小团子-栏目', '小团子-导语', '小团子-说文解字', '小团子-章节', '小团子-小节', '小团子-正文', '小团子-代码块',
       '小团子-提示', '小团子-表格', '小团子-图片', '小团子-参考资料', '小团子-资料说明', '小团子-结尾']
SLOTS = {'小团子-导语': '{{intro}}', '小团子-说文解字': '{{term}}|{{english}}|{{chinese}}',
         '小团子-章节': '{{number}}.{{heading}}', '小团子-小节': '{{subheading}}', '小团子-正文': '{{text}}',
         '小团子-代码块': '{{lang}}:{{code}}', '小团子-提示': '{{tip}}', '小团子-表格': '<table>{{rows}}</table>',
         '小团子-图片': '<img src="{{src}}" alt="{{alt}}">', '小团子-参考资料': '{{references}}',
         '小团子-资料说明': '{{sourceNote}}'}
STYLES = {'styles': [{'id': 'layout-xiaotuanzi', 'kind': 'layout', 'componentIds': IDS,
                      'template': {'shell': '<html><body><div id="shell">{{content}}</div></body></html>'}}],
          'components': [{'id': i, 'html': '<section data-c="%s">%s</section>' % (i, SLOTS.get(i, ''))} for i in IDS]}
ARTICLE = """# 标题

第一段导语，有 `ssh` 和 **重点**。

**API = Application Programming Interface（应用程序编程接口）**

## 第一章

![示意](imgs/01-a.png)

### 小节

> **顺序不能反。** 先放行再启用。

```bash
echo "<hi>"
```

| 方案 | 结果 |
|---|---|
| A | 能 |

- 一
- 二

## 参考资料

<div class="sources">
<p>来源：<a href="https://example.com">示例</a>。</p>
<p>资料核对于 2026 年 10 月 13 日。</p>
</div>
"""


class RenderTest(unittest.TestCase):
    def run_render(self, *extra, article=ARTICLE):
        with tempfile.TemporaryDirectory() as d:
            styles, md, out = (os.path.join(d, n) for n in ('styles.json', 'a.md', 'out.html'))
            with open(styles, 'w', encoding='utf-8') as stream:
                json.dump(STYLES, stream, ensure_ascii=False)
            with open(md, 'w', encoding='utf-8') as stream:
                stream.write(article)
            res = subprocess.run([sys.executable, SCRIPT, md, styles, out] + list(extra),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            with open(out, encoding='utf-8') as stream:
                return stream.read(), json.loads(res.stdout.decode())

    def test_maps_blocks_to_components(self):
        doc, info = self.run_render()
        self.assertEqual(info['images'], ['imgs/01-a.png'])
        self.assertNotIn('{{', doc)
        self.assertNotIn('<h1', doc)
        self.assertNotIn('# 标题', doc)
        self.assertIn('<section data-c="小团子-导语">', doc)
        self.assertIn('API|Application Programming Interface|应用程序编程接口', doc)
        self.assertIn('1.第一章', doc)
        self.assertNotIn('参考资料</section>', doc.split('小团子-章节')[-1].split('</section>')[0])
        self.assertIn('bash:echo &quot;&lt;hi&gt;&quot;', doc)
        self.assertIn('顺序不能反', doc.split('小团子-提示')[1])
        self.assertIn('<th', doc)
        self.assertIn('· 一', doc)
        self.assertIn('资料核对于 2026 年 10 月 13 日。', doc.split('小团子-资料说明')[1])
        refs = doc.split('小团子-参考资料')[1].split('小团子-资料说明')[0]
        self.assertIn('示例<span', refs)
        self.assertIn('（example.com）', refs)
        self.assertNotIn('<a ', refs)
        self.assertTrue(doc.startswith('<!DOCTYPE html>'))
        self.assertLess(doc.index('小团子-栏目'), doc.index('小团子-导语'))
        self.assertLess(doc.index('小团子-导语'), doc.index('小团子-说文解字'))
        self.assertLess(doc.index('小团子-说文解字'), doc.index('小团子-章节'))
        self.assertLess(doc.index('小团子-参考资料'), doc.index('小团子-结尾'))

    def test_preview_uses_template_shell(self):
        doc, _ = self.run_render('--preview')
        self.assertIn('<div id="shell">', doc)

    def test_definition_in_chapter_moves_before_body(self):
        article = ('# 示例\n\n导语。\n\n开头补充说明。\n\n## 认识工具\n\n'
                   '![示意](imgs/01-a.png)\n\n原有说明。\n\n'
                   '**ABC = Example Tool（示例工具）**\n\n后续说明。')
        doc, info = self.run_render(article=article)
        self.assertEqual(doc.count('data-c="小团子-说文解字"'), 1)
        self.assertLess(doc.index('小团子-导语'), doc.index('小团子-说文解字'))
        self.assertLess(doc.index('小团子-说文解字'), doc.index('开头补充说明'))
        self.assertLess(doc.index('小团子-说文解字'), doc.index('小团子-章节'))
        self.assertLess(doc.index('原有说明'), doc.index('后续说明'))
        self.assertEqual(info['images'], ['imgs/01-a.png'])

    def test_embedded_definition_preserves_remaining_paragraph(self):
        for punctuation in ('。', '.', '．', ''):
            with self.subTest(punctuation=punctuation):
                article = ('# 示例\n\n导语。\n\n## 第一章\n\n'
                           '**ABC = Example Tool（示例工具）**' + punctuation +
                           '这是它的全名，后面有 **重点** 和 `example --help`。')
                doc, _ = self.run_render(article=article)
                self.assertEqual(doc.count('ABC|Example Tool|示例工具'), 1)
                self.assertLess(doc.index('小团子-说文解字'), doc.index('小团子-章节'))
                self.assertIn('这是它的全名，后面有', doc)
                self.assertIn('example --help</code>', doc)
                self.assertNotIn('。这是', doc)
                self.assertNotIn('.这是', doc)
                self.assertNotIn('．这是', doc)

    def test_does_not_invent_terms_or_extract_examples(self):
        article = ('# 示例\n\n导语。\n\n## 正文\n\n产品名不是缩写，不编全称。\n\n'
                   '正文顺带举例 **XYZ = Example（示例）**，不提升为主角卡片。\n\n'
                   '```text\n**ABC = Example Tool（示例工具）**\n```')
        doc, _ = self.run_render(article=article)
        self.assertNotIn('data-c="小团子-说文解字"', doc)
        self.assertIn('XYZ = Example（示例）', doc)
        self.assertIn('**ABC = Example Tool（示例工具）**', doc)


if __name__ == '__main__':
    unittest.main()
