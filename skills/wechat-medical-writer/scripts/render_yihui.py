#!/usr/bin/env python3
"""把医荟她健康的 Markdown 成稿套进图库排版案例 layout-current，输出公众号正文 HTML。

组件 HTML 全部来自图库 styles.json（componentIds 对应的 components），本脚本只负责把
Markdown 块映射到组件并填槽，不另存一份样式。输出的 <body> 只含正文，供苍何发布器读取。

成稿约定：H1 标题（不进正文）→ `>` 导语 → `## 01 小节标题` → `---` → `## 参考文献`
（`[n] ...` 每条一段）→ 最后一行斜体免责声明。公众号会去掉外部链接，所以参考文献的网址
写成可见文字。

用法：render_yihui.py <article.md> <styles.json> <out.html> [--source-note TEXT] [--preview]
"""
import html
import json
import re
import sys

LAYOUT_ID = 'layout-current'
GRAY = '#6F6E6E'
P_STYLE = 'margin:0 0 16px;padding:0;'
CITE = '<span style="font-size:11px;vertical-align:baseline;">[%s]</span>'
TD = 'border:1px solid #F3D3D8;padding:8px 10px;text-align:left;vertical-align:top;font-size:14px;'


def load_components(styles_path):
    catalog = json.load(open(styles_path, encoding='utf-8'))
    layout = next(s for s in catalog['styles'] if s['id'] == LAYOUT_ID)
    parts = {c['id']: c['html'] for c in catalog['components'] if c['id'] in layout['componentIds']}
    missing = set(layout['componentIds']) - set(parts)
    if missing:
        raise SystemExit('styles.json is missing components: %s' % sorted(missing))
    return layout, parts


def show_url(url):
    return re.sub(r'^https?://', '', url).rstrip('/')


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![*\w])\*([^*\n]+?)\*(?![*\w])', r'<em>\1</em>', text)
    # 公众号会去掉外部链接：正文链接保留文字，网址以灰色小字附在后面
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)',
                  lambda m: '%s<span style="color:%s;font-size:11px;word-break:break-all;">（%s）</span>'
                  % (m.group(1), GRAY, html.escape(show_url(html.unescape(m.group(2))))), text)
    return re.sub(r'\[(\d+(?:[,，、\-–]\d+)*)\]', lambda m: CITE % m.group(1), text)


def table_html(lines):
    rows = [[c.strip() for c in l.strip().strip('|').split('|')]
            for l in lines if not re.match(r'^\|?\s*:?-{3,}', l.strip())]
    out = ['<tr>' + ''.join('<th style="%sbackground:#FDF1F4;color:#333;font-weight:bold;">%s</th>' % (TD, inline(c))
                            for c in rows[0]) + '</tr>']
    out += ['<tr>' + ''.join('<td style="%s">%s</td>' % (TD, inline(c)) for c in r) + '</tr>' for r in rows[1:]]
    return ('<section style="overflow-x:auto;margin:0 0 16px;"><table style="border-collapse:collapse;width:100%%;'
            'line-height:1.6;letter-spacing:0;">%s</table></section>' % ''.join(out))


def reference_item(line):
    m = re.match(r'^\[(\d+)\]\s*(.+)$', line)
    if not m:
        raise SystemExit('reference line must start with [n]: %r' % line[:60])
    text, urls = m.group(2), []

    def keep(link):
        urls.append(html.unescape(link.group(2)))
        return link.group(1)

    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', keep, text)
    body = inline(text)
    links = ''.join('<br><span style="word-break:break-all;">%s</span>' % html.escape(show_url(u)) for u in urls)
    return int(m.group(1)), '<li style="margin:0 0 10px;"><p style="margin:0;">%s%s</p></li>' % (body, links)


def parse(md):
    lines = md.splitlines()
    intro, sections, refs, disclaimer, state = [], [], [], '', 'intro'
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('# '):
            i += 1
            continue
        if stripped == '---':
            state = 'tail' if state != 'refs' else state
            i += 1
            continue
        if stripped.startswith('## '):
            title = stripped[3:].strip()
            if title == '参考文献':
                state = 'refs'
            else:
                m = re.match(r'^(\d+)\s+(.+)$', title)
                if not m:
                    raise SystemExit('section heading must be "## 01 标题": %r' % title)
                sections.append({'number': m.group(1), 'heading': m.group(2), 'blocks': []})
                state = 'body'
            i += 1
            continue
        if re.fullmatch(r'\*[^*].*[^*]\*', stripped) and (state in ('refs', 'tail') or i == len(lines) - 1):
            disclaimer = stripped[1:-1].strip()
            i += 1
            continue
        if state == 'refs':
            refs.append(reference_item(stripped))
            i += 1
            continue
        if state == 'intro':
            if not stripped.startswith('>'):
                raise SystemExit('text before the first section must be the > intro: %r' % stripped[:60])
            intro.append(stripped.lstrip('>').strip())
            i += 1
            continue
        if not sections:
            raise SystemExit('body text outside a section: %r' % stripped[:60])
        blocks = sections[-1]['blocks']
        if stripped.startswith('|'):
            j = i
            while j < len(lines) and lines[j].strip().startswith('|'):
                j += 1
            blocks.append(('table', [l.strip() for l in lines[i:j]]))
            i = j
            continue
        if re.match(r'^([-*]|\d+\.)\s+', stripped):
            j = i
            while j < len(lines) and re.match(r'^\s*([-*]|\d+\.)\s+', lines[j]):
                j += 1
            blocks.append(('list', [l.strip() for l in lines[i:j]]))
            i = j
            continue
        if stripped.startswith('>'):
            blocks.append(('quote', stripped.lstrip('>').strip()))
            i += 1
            continue
        m = re.fullmatch(r'!\[(.*?)\]\((\S+?)\)', stripped)
        blocks.append(('image', m.group(2), m.group(1)) if m else ('para', stripped))
        i += 1
    return intro, sections, refs, disclaimer


def block_html(block, images):
    kind = block[0]
    if kind == 'image':
        if block[1] == 'imgs/cover.png':
            return ''
        images.append(block[1])
        return ('<section style="margin:30px 0 36px;padding:0;width:100%%;"><img src="%s" alt="%s" '
                'style="display:block;width:100%%;max-width:100%%;height:auto;margin:0;padding:0;"></section>'
                % (html.escape(block[1]), html.escape(block[2])))
    if kind == 'table':
        return table_html(block[1])
    if kind == 'list':
        out = []
        for n, item in enumerate(block[1], 1):
            m = re.match(r'^([-*]|\d+\.)\s+(.*)$', item)
            mark = '%d. ' % n if m.group(1)[0].isdigit() else '· '
            out.append('<p style="margin:0 0 8px;padding:0 0 0 1em;text-indent:-1em;">%s%s</p>' % (mark, inline(m.group(2))))
        return ''.join(out[:-1]) + out[-1].replace('margin:0 0 8px;', P_STYLE, 1)
    if kind == 'quote':
        return ('<p style="%sborder-left:3px solid #F24D60;padding-left:10px;color:#555;">%s</p>'
                % (P_STYLE.replace('padding:0;', ''), inline(block[1])))
    return '<p style="%s">%s</p>' % (P_STYLE, inline(block[1]))


def default_note(md):
    dates = re.findall(r'访问日期[：:]\s*(\d{4})-(\d{2})-(\d{2})', md)
    if not dates:
        return '具体检查和治疗请咨询专业医生。'
    y, m, d = max(dates)
    return '资料核对日期：%s年%d月%d日。具体检查和治疗请咨询专业医生。' % (y, int(m), int(d))


def render(md, layout, parts, source_note=None):
    def fill(cid, **slots):
        out = parts[cid]
        for key, value in slots.items():
            out = out.replace('{{%s}}' % key, value)
        return out

    intro, sections, refs, disclaimer = parse(md)
    if not intro or not sections or not refs or not disclaimer:
        raise SystemExit('article needs > intro, ## sections, ## 参考文献 and an italic disclaimer')
    numbers = [n for n, _ in refs]
    if numbers != list(range(1, len(refs) + 1)):
        raise SystemExit('references must be numbered 1..n in order, got %s' % numbers)
    images, content = [], [parts['医荟她-栏目'],
                           fill('医荟她-导语', intro=''.join('<p style="margin:0;">%s</p>' % inline(p) for p in intro))]
    for sec in sections:
        content.append(fill('医荟她-章节', number=html.escape(sec['number']), heading=inline(sec['heading'])))
        content.append(fill('医荟她-正文', paragraphs=''.join(block_html(b, images) for b in sec['blocks'])))
    content.append(fill('医荟她-参考文献', references=''.join(item for _, item in refs)))
    content.append(fill('医荟她-资料说明', sourceNote=html.escape(source_note or default_note(md))))
    content.append(fill('医荟她-结尾', disclaimer=inline(disclaimer)))
    out = ''.join(content)
    leftover = re.findall(r'\{\{\w+\}\}', out)
    if leftover:
        raise SystemExit('unfilled slots: %s' % sorted(set(leftover)))
    return out, images, len(sections), len(refs)


def main():
    argv, note = sys.argv[1:], None
    if '--source-note' in argv:
        k = argv.index('--source-note')
        note = argv[k + 1]
        del argv[k:k + 2]
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 3:
        raise SystemExit(__doc__)
    md_path, styles_path, out_path = args
    layout, parts = load_components(styles_path)
    content, images, n_sections, n_refs = render(open(md_path, encoding='utf-8').read(), layout, parts, note)
    if '--preview' in argv:
        doc = layout['template']['shell'].replace('{{content}}', content)
    else:
        doc = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"></head><body>%s</body></html>' % content
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(json.dumps({'images': images, 'sections': n_sections, 'references': n_refs,
                      'characters': len(content)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
