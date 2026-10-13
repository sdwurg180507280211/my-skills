import base64
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('deliver_draft', os.path.join(HERE, '..', 'scripts', 'deliver_draft.py'))
deliver_draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deliver_draft)


class PayloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        subprocess.run(['git', 'init', '-q', self.repo], check=True)
        self.article = 'data/技术公众号/示例_一篇文章'
        folder = os.path.join(self.repo, self.article)
        os.makedirs(os.path.join(folder, 'imgs'))
        open(os.path.join(folder, '示例.md'), 'w', encoding='utf-8').write(
            '# 示例\n\n![b](imgs/02-b.png)\n\n文字\n\n![a](imgs/01-a.png)\n')
        open(os.path.join(folder, '配图需求.md'), 'w', encoding='utf-8').write('# 配图需求\n')
        for name in ('01-a.png', '02-b.png', 'cover.png'):
            open(os.path.join(folder, 'imgs', name), 'wb').write(name.encode())
        subprocess.run(['git', '-C', self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '.'], check=True)
        subprocess.run(['git', '-C', self.repo, '-c', 'user.name=t', '-c', 'user.email=t@t',
                        'commit', '-qm', 'init'], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_payload_follows_markdown_order(self):
        p = deliver_draft.check_payload(self.repo, self.article)
        self.assertEqual(p['body']['path'], '示例.md')
        self.assertEqual([i['path'] for i in p['images']], ['imgs/02-b.png', 'imgs/01-a.png'])
        self.assertEqual(len(p['cover']['sha256']), 64)
        self.assertNotIn('content_b64', json.dumps(p))

    def test_deliver_payload_embeds_files_and_commit(self):
        html = os.path.join(self.repo, 'a.html')
        meta = os.path.join(self.repo, 'm.json')
        open(html, 'w', encoding='utf-8').write('<html><body></body></html>')
        json.dump({'title': '示例', 'author': '小团子Java', 'summary': '摘要'}, open(meta, 'w', encoding='utf-8'))
        p = deliver_draft.deliver_payload(self.repo, self.article, html, meta, dry_run=True)
        self.assertTrue(p['dry_run'])
        self.assertRegex(p['git_commit'], r'^[0-9a-f]{40}$')
        self.assertEqual(base64.b64decode(p['cover']['content_b64']), b'cover.png')
        self.assertEqual([i['path'] for i in p['images']], ['imgs/02-b.png', 'imgs/01-a.png'])


if __name__ == '__main__':
    unittest.main()
