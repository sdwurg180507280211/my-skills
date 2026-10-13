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
    def run_render(self, *extra):
        with tempfile.TemporaryDirectory() as d:
            styles, md, out = (os.path.join(d, n) for n in ('styles.json', 'a.md', 'out.html'))
            json.dump(STYLES, open(styles, 'w', encoding='utf-8'), ensure_ascii=False)
            open(md, 'w', encoding='utf-8').write(ARTICLE)
            res = subprocess.run([sys.executable, SCRIPT, md, styles, out] + list(extra),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return open(out, encoding='utf-8').read(), json.loads(res.stdout.decode())

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
        self.assertTrue(doc.startswith('<!DOCTYPE html>'))
        self.assertLess(doc.index('小团子-栏目'), doc.index('小团子-导语'))
        self.assertLess(doc.index('小团子-参考资料'), doc.index('小团子-结尾'))

    def test_preview_uses_template_shell(self):
        doc, _ = self.run_render('--preview')
        self.assertIn('<div id="shell">', doc)


if __name__ == '__main__':
    unittest.main()
