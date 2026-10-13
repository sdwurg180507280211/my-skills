#!/usr/bin/env python3
"""把小团子Java 的 Markdown 成稿套进图库排版案例 layout-xiaotuanzi，输出公众号正文 HTML。

组件 HTML 全部来自图库 styles.json（componentIds 对应的 components），本脚本只负责把
Markdown 块映射到组件并填槽，不另存一份样式。输出的 <body> 只含正文，供苍何发布器读取。

用法：render_xiaotuanzi.py <article.md> <styles.json> <out.html> [--preview]
"""
import html
import json
import re
import sys

LAYOUT_ID = 'layout-xiaotuanzi'
NAVY, GRAY, MONO = '#1E3A5F', '#6B7280', 'Menlo,Consolas,&quot;SF Mono&quot;,monospace'
TD = 'border:1px solid #E3E8EF;padding:8px 10px;text-align:left;vertical-align:top;'
TERM_RE = re.compile(r'\*\*(\S+) = (.+?)（(.+?)）\*\*')


def load_components(styles_path):
    catalog = json.load(open(styles_path, encoding='utf-8'))
    layout = next(s for s in catalog['styles'] if s['id'] == LAYOUT_ID)
    parts = {c['id']: c['html'] for c in catalog['components'] if c['id'] in layout['componentIds']}
    missing = set(layout['componentIds']) - set(parts)
    if missing:
        raise SystemExit('styles.json is missing components: %s' % sorted(missing))
    return layout, parts


def inline(text):
    codes = []

    def keep(m):
        codes.append('<code style="font-size:13px;font-family:%s;color:#1D4ED8;background:#EFF4FF;'
                     'border-radius:4px;padding:1px 5px;letter-spacing:0;">%s</code>' % (MONO, html.escape(m.group(1))))
        return '\0%d\0' % (len(codes) - 1)

    text = re.sub(r'`([^`]+)`', keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:%s;">\1</strong>' % NAVY, text)
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)',
                  lambda m: '<a href="%s" style="color:#2563EB;text-decoration:none;">%s</a>'
                  % (html.escape(m.group(2)), m.group(1)), text)
    return re.sub(r'\0(\d+)\0', lambda m: codes[int(m.group(1))], text)


def table_rows(lines):
    rows = [[c.strip() for c in l.strip().strip('|').split('|')]
            for l in lines if not re.match(r'^\|?\s*:?-{3,}', l.strip())]
    out = ['<tr>' + ''.join('<th style="%sbackground:#EAF1FE;color:%s;font-weight:bold;white-space:nowrap;">%s</th>'
                            % (TD, NAVY, inline(c)) for c in rows[0]) + '</tr>']
    for i, r in enumerate(rows[1:]):
        bg = 'background:#F8FAFD;' if i % 2 else ''
        out.append('<tr>' + ''.join('<td style="%s%s">%s</td>' % (TD, bg, inline(c)) for c in r) + '</tr>')
    return ''.join(out)


def blocks_of(md):
    lines = md.splitlines()
    i, out = 0, []
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append(('code', line[3:].strip(), '\n'.join(lines[i + 1:j])))
            i = j + 1
        elif line.strip().startswith('<div class="sources">'):
            j = i
            while j < len(lines) and '</div>' not in lines[j]:
                j += 1
            out.append(('sources', '\n'.join(lines[i:j + 1])))
            i = j + 1
        elif line.startswith('|'):
            j = i
            while j < len(lines) and lines[j].startswith('|'):
                j += 1
            out.append(('table', lines[i:j]))
            i = j
        elif line.startswith('>'):
            j = i
            while j < len(lines) and lines[j].startswith('>'):
                j += 1
            out.append(('tip', ' '.join(l.lstrip('>').strip() for l in lines[i:j])))
            i = j
        elif re.match(r'^\s*([-*]|\d+\.)\s+', line):
            j = i
            while j < len(lines) and re.match(r'^\s*([-*]|\d+\.)\s+', lines[j]):
                j += 1
            out.append(('list', lines[i:j]))
            i = j
        else:
            if line.strip():
                out.append(('line', line.strip()))
            i += 1
    return out


def render(md, layout, parts):
    def fill(cid, **slots):
        out = parts[cid]
        for key, value in slots.items():
            out = out.replace('{{%s}}' % key, value)
        return out

    body, intro, section, images = [], None, 0, []
    for block in blocks_of(md):
        kind = block[0]
        if kind == 'line':
            line = block[1]
            if line.startswith('# '):
                continue  # 文章标题由发布器单独传，正文不重复 H1
            if line.startswith('## '):
                if line[3:].strip() == '参考资料':
                    continue
                section += 1
                body.append(fill('小团子-章节', number=str(section), heading=inline(line[3:].strip())))
                continue
            if line.startswith('### '):
                body.append(fill('小团子-小节', subheading=inline(line[4:].strip())))
                continue
            m = re.fullmatch(r'!\[(.*?)\]\((\S+?)\)', line)
            if m:
                if m.group(2) != 'imgs/cover.png':
                    images.append(m.group(2))
                    body.append(fill('小团子-图片', src=html.escape(m.group(2)), alt=html.escape(m.group(1))))
                continue
            m = TERM_RE.fullmatch(line)
            if m:
                body.append(fill('小团子-说文解字', term=html.escape(m.group(1)),
                                 english=html.escape(m.group(2)), chinese=html.escape(m.group(3))))
                continue
            if intro is None and section == 0 and not body:
                intro = '<p style="margin:0;">%s</p>' % inline(line)
                continue
            body.append(fill('小团子-正文', text=inline(line)))
        elif kind == 'code':
            body.append(fill('小团子-代码块', lang=html.escape(block[1] or 'text'), code=html.escape(block[2])))
        elif kind == 'tip':
            body.append(fill('小团子-提示', tip=inline(block[1])))
        elif kind == 'table':
            body.append(fill('小团子-表格', rows=table_rows(block[1])))
        elif kind == 'list':
            for n, item in enumerate(block[1], 1):
                m = re.match(r'^\s*([-*]|\d+\.)\s+(.*)$', item)
                mark = '%d. ' % n if m.group(1)[0].isdigit() else '· '
                body.append(fill('小团子-正文', text=mark + inline(m.group(2))))
        elif kind == 'sources':
            paras = re.findall(r'(?s)<p>(.*?)</p>', block[1])
            note = paras.pop() if paras and paras[-1].lstrip().startswith('资料核对') else ''
            link = '<a style="color:%s;text-decoration:underline;" ' % GRAY
            refs = ''.join('<p style="margin:0 0 10px;">%s</p>' % p.replace('<a ', link) for p in paras)
            body.append(fill('小团子-参考资料', references=refs))
            if note:
                body.append(fill('小团子-资料说明', sourceNote=note))
    head = parts['小团子-栏目'] + (fill('小团子-导语', intro=intro) if intro else '')
    content = head + ''.join(body) + parts['小团子-结尾']
    leftover = re.findall(r'\{\{\w+\}\}', content)
    if leftover:
        raise SystemExit('unfilled slots: %s' % sorted(set(leftover)))
    return content, images


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 3:
        raise SystemExit(__doc__)
    md_path, styles_path, out_path = args
    layout, parts = load_components(styles_path)
    content, images = render(open(md_path, encoding='utf-8').read(), layout, parts)
    if '--preview' in sys.argv:
        doc = layout['template']['shell'].replace('{{content}}', content)
    else:
        doc = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"></head><body>%s</body></html>' % content
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(json.dumps({'images': images, 'characters': len(content)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
