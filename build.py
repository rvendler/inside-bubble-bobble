#!/usr/bin/env python3
"""Build inside-bubble-bobble.md and the standalone HTML (inside-bubble-bobble.html, index.html) from chapters/."""
import base64
import glob
import html
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))

CSS = """body{font-family:Georgia,"Times New Roman",serif;line-height:1.55;max-width:860px;margin:0 auto;padding:2em 1.5em;color:#222;background:#fbfaf7}
h1{font-size:2.2em;margin-top:2.5em;border-bottom:3px solid #c33;padding-bottom:.2em}h2{font-size:1.5em;margin-top:2em;border-bottom:1px solid #ccc}h3{font-size:1.2em;margin-top:1.5em}
code{font-family:Menlo,Consolas,monospace;font-size:.92em;background:#f0ede6;padding:0 .25em;border-radius:3px}
pre.code{background:#1e1e1e;color:#e6e6e6;padding:1em;overflow-x:auto;border-radius:6px;font-size:.85em;line-height:1.4}pre.code code{background:none;padding:0;color:inherit}
table{border-collapse:collapse;margin:1em 0;font-size:.9em;width:100%}th,td{border:1px solid #bbb;padding:.35em .6em;text-align:left;vertical-align:top}th{background:#eee8dc}
figure{margin:1.5em 0;text-align:center}figure img{max-width:100%;image-rendering:pixelated;border:1px solid #ddd;background:#111}figcaption{font-size:.9em;color:#555;margin-top:.4em;font-style:italic}
blockquote{border-left:4px solid #c33;margin:1em 0;padding:.3em 1em;background:#f6f1e7}
aside.box{border:1px solid #d8cfbd;border-top:4px solid #4a7a9c;margin:1.5em 0;padding:.2em 1.2em .4em;background:#f1f4f6;border-radius:0 0 6px 6px;font-size:.95em}aside.box p.box-title{font-family:Helvetica,Arial,sans-serif;font-weight:bold;font-size:.8em;letter-spacing:.06em;text-transform:uppercase;color:#4a7a9c;margin:.8em 0 .3em}
nav.toc{background:#f3efe6;padding:1em 1.5em;border-radius:6px;margin:2em 0}nav.toc ul{list-style:none;padding:0;margin:0}nav.toc li.l2{margin-left:1.5em;font-size:.95em}nav.toc a{text-decoration:none;color:#333}
.title{text-align:center;margin:3em 0 4em}.title h1{border:none;font-size:3em;margin:0}.title p{color:#666;font-size:1.2em}
@media print{body{max-width:none;font-size:11pt}pre.code{white-space:pre-wrap}}
"""

TITLE = ('<div class="title"><h1>Inside Bubble Bobble</h1><p>A walkthrough of the arcade game\'s code, data and design</p>'
         '<p>Built from the ROMs, verified against a running machine</p></div>')

# An info box in the chapters is a GitHub note: "> [!NOTE]", then "> **Title**", then the text.
BOX_RE = re.compile(r'^\*\*(.+?)\*\*$')


def slug(text):
    text = re.sub(r'<[^>]+>', '', text).lower()
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def inline(text):
    parts = re.split(r'(`[^`]*`)', text)
    out = []
    for p in parts:
        if p.startswith('`') and p.endswith('`') and len(p) >= 2:
            out.append('<code>' + html.escape(p[1:-1], quote=False) + '</code>')
        else:
            p = html.escape(p, quote=False)
            p = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', p)
            p = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', p)
            out.append(p)
    return ''.join(out)


def image(alt, src):
    path = os.path.join(ROOT, src)
    data = open(path, 'rb').read()
    mime = 'image/svg+xml' if src.endswith('.svg') else 'image/png'
    uri = 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode())
    return '<figure><img alt="%s" src="%s"><figcaption>%s</figcaption></figure>' % (alt, uri, inline(alt))


def unique(ident, seen):
    base, k = ident, 0
    while ident in seen:
        k += 1
        ident = '%s-%d' % (base, k)
    seen.add(ident)
    return ident


def render(lines, toc, seen=None):
    """Render a list of Markdown lines to a list of HTML blocks."""
    if seen is None:
        seen = set()
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            lang = line[3:].strip()
            j = i + 1
            while not lines[j].startswith('```'):
                j += 1
            body = html.escape('\n'.join(lines[i + 1:j]), quote=False)
            cls = 'code lang-' + lang if lang else 'code'
            out.append('<pre class="%s"><code>%s</code></pre>' % (cls, body))
            i = j + 1
            continue
        m = re.match(r'^(#{1,3}) (.*)$', line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            ident = unique(slug(text), seen)
            if toc is not None and level <= 2:
                toc.append('<li class="l%d"><a href="#%s">%s</a></li>' % (level, ident, text))
            out.append('<h%d id="%s">%s</h%d>' % (level, ident, text, level))
            i += 1
            continue
        m = re.match(r'^!\[(.*)\]\((.*)\)$', line)
        if m:
            out.append(image(m.group(1), m.group(2)))
            i += 1
            continue
        if line.startswith('|'):
            rows = []
            while i < n and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head = ''.join('<th>%s</th>' % inline(c) for c in rows[0])
            body = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(c) for c in r) for r in rows[2:])
            out.append('<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (head, body))
            continue
        if line.startswith('>'):
            inner = []
            while i < n and lines[i].startswith('>'):
                inner.append(lines[i][2:] if lines[i].startswith('> ') else lines[i][1:])
                i += 1
            if inner and inner[0].strip() == '[!NOTE]':
                title = BOX_RE.match(inner[1].strip()).group(1)
                out.append('<aside class="box"><p class="box-title">%s</p>%s</aside>' % (
                    inline(title), '\n'.join(render(inner[2:], None, seen))))
            else:
                out.append('<blockquote>%s</blockquote>' % '\n'.join(render(inner, None, seen)))
            continue
        m = re.match(r'^([*-]|\d+\.) ', line)
        if m:
            tag = 'ol' if m.group(1)[0].isdigit() else 'ul'
            items = []
            while i < n and (re.match(r'^([*-]|\d+\.) ', lines[i]) or (lines[i].startswith('  ') and lines[i].strip())):
                if re.match(r'^([*-]|\d+\.) ', lines[i]):
                    items.append(re.sub(r'^([*-]|\d+\.) ', '', lines[i]))
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s\n</li>' % inline(t) for t in items), tag))
            continue
        para = []
        while i < n and lines[i].strip() and not re.match(r'^(```|#{1,3} |!\[|\||>|[*-] |\d+\. )', lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append('<p>%s</p>' % inline(' '.join(para)))
    return out


def main():
    chapters = sorted(glob.glob(os.path.join(ROOT, 'chapters', '*.md')))
    text = ''.join(open(f).read() + '\n' for f in chapters).replace('../img/', 'img/')
    text = text[:-1]
    with open(os.path.join(ROOT, 'inside-bubble-bobble.md'), 'w') as f:
        f.write(text)
    toc = []
    body = render(text.split('\n'), toc)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Inside Bubble Bobble</title><style>\n%s</style></head><body>\n%s\n'
            '<nav class="toc"><h2>Contents</h2><ul>%s</ul></nav>\n%s\n</body></html>') % (
        CSS, TITLE, ''.join(toc), '\n'.join(body))
    for name in ('inside-bubble-bobble.html', 'index.html'):
        with open(os.path.join(ROOT, name), 'w') as f:
            f.write(page)


if __name__ == '__main__':
    main()
