"""Extract article structure from Tressling PDFs into an intermediate block list (JSON)."""
import json, re, sys, html
import pymupdf as fitz

def esc(s):
    return html.escape(s, quote=False)

def span_html(spans):
    out = []
    for sp in spans:
        t = sp['text']
        if not t:
            continue
        t = esc(t)
        bold = 'Bold' in sp['font'] or (sp['flags'] & 16)
        ital = 'Italic' in sp['font'] or (sp['flags'] & 2)
        if bold and t.strip():
            t = f'<strong>{t}</strong>'
        if ital and t.strip():
            t = f'<em>{t}</em>'
        out.append(t)
    s = ''.join(out)
    s = s.replace('</strong><strong>', '').replace('</em><em>', '')
    return s

def norm(s):
    s = re.sub(r'[  ]+', ' ', s)
    return s.strip()

def join(a, b):
    a = a.rstrip()
    b = b.lstrip()
    if not a:
        return b
    plain = re.sub(r'<[^>]+>', '', a)
    if plain.endswith('-') and not plain.endswith(' -'):
        return a + b
    return a + ' ' + b

def extract(path):
    d = fitz.open(path)
    events = []
    for pno, p in enumerate(d):
        links = [(l['from'], l.get('uri')) for l in p.get_links() if l.get('uri')]
        for b in p.get_text('dict')['blocks']:
            if b['type'] == 1:
                x0, y0, x1, y1 = b['bbox']
                w, h = x1 - x0, y1 - y0
                if w < 45 or (w < 80 and h < 80):   # author avatar / author photo
                    continue
                if pno == 0 and y0 < 150:  # masthead banner
                    continue
                events.append(dict(kind='img', page=pno, y=y0, bbox=[x0, y0, x1, y1]))
                continue
            for l in b['lines']:
                spans = [s for s in l['spans']]
                text = ''.join(s['text'] for s in spans)
                if not text.strip():
                    continue
                sp = spans[0]
                size = round(sp['size'], 1)
                if size <= 7.1:  # running header/footer
                    continue
                if pno == 0 and l['bbox'][1] < 300:  # title block
                    continue
                bold = all(('Bold' in s['font'] or s['flags'] & 16) for s in spans if s['text'].strip())
                ital = all(('Italic' in s['font']) for s in spans if s['text'].strip())
                uri = None
                r = fitz.Rect(l['bbox'])
                for lr, u in links:
                    if lr.intersects(r) and abs(lr.y0 - r.y0) < 8:
                        uri = u
                events.append(dict(kind='text', page=pno, y=l['bbox'][1], x=round(l['bbox'][0]),
                                   size=size, bold=bold, ital=ital, text=norm(text),
                                   html=norm(span_html(spans)), uri=uri))
    events.sort(key=lambda e: (e['page'], e['y'], e.get('x', 0)))
    # lines on the same baseline (within 4.5pt) are ordered left to right
    changed = True
    while changed:
        changed = False
        for k in range(len(events) - 1):
            a, b = events[k], events[k + 1]
            if a['kind'] == b['kind'] == 'text' and a['page'] == b['page'] and abs(a['y'] - b['y']) < 4.5 and a['x'] > b['x']:
                events[k], events[k + 1] = b, a
                changed = True
    return d, events

def build(path):
    d, ev = extract(path)
    blocks = []
    i = 0
    n = len(ev)
    cur = None  # current paragraph block

    def flush():
        nonlocal cur
        if cur:
            blocks.append(cur)
        cur = None

    last = None
    while i < n:
        e = ev[i]
        if e['kind'] == 'img':
            flush()
            blocks.append(dict(t='img', page=e['page'], bbox=e['bbox'], caption=''))
            i += 1
            continue
        s, x, txt = e['size'], e['x'], e['text']
        # Exhibit label
        if s == 8.0 and e['bold'] and txt.upper().startswith('EXHIBIT'):
            flush()
            ex = dict(t='exhibit', label=txt.title(), page=e['page'], y=e['y'], title='', source='', imgs=[], raw=[])
            if blocks and blocks[-1]['t'] == 'img' and blocks[-1]['page'] == e['page'] and abs(blocks[-1]['bbox'][1] - e['y']) < 20:
                im = blocks.pop(); ex['imgs'].append(dict(page=im['page'], bbox=im['bbox']))
            i += 1
            while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] == 11.0 and ev[i]['bold']:
                ex['title'] = join(ex['title'], ev[i]['text']); i += 1
            # consume until source lines
            while i < n:
                f = ev[i]
                if f['kind'] == 'img':
                    ex['imgs'].append(dict(page=f['page'], bbox=f['bbox'])); i += 1; continue
                if f['size'] == 8.0 and not f['bold'] and f['page'] == ex['page']:
                    ex['source'] = join(ex['source'], f['html']); i += 1
                    while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] == 8.0 and not ev[i]['bold'] and ev[i]['page'] == ex['page']:
                        ex['source'] = join(ex['source'], ev[i]['html']); i += 1
                    break
                ex['raw'].append(f['text']); i += 1
            # trailing image on same page that belongs to exhibit region (e.g. drawn after source)
            blocks.append(ex)
            last = None
            continue
        # Section heading
        if s == 15.0 and e['bold']:
            flush()
            blocks.append(dict(t='h2', text=txt.rstrip(':').strip())); i += 1; last = None; continue
        if s == 11.0 and e['bold'] and txt.startswith('Sources'):
            flush(); blocks.append(dict(t='h2', text=txt)); i += 1; continue
        if s == 12.0 and e['bold'] and x >= 85:
            flush(); blocks.append(dict(t='callout', html=e['html'])); i += 1; continue
        if s == 13.0 and e['bold']:
            flush(); cl = dict(t='closing', html='')
            while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] == 13.0:
                cl['html'] = join(cl['html'], ev[i]['text']); i += 1
            blocks.append(cl); continue
        if s == 8.5 and e['bold']:  # takeaways / what I learned box
            flush()
            title = 'What I learned' if 'L E A R N' in txt else 'Three takeaways'
            box = dict(t='takeaways', title=title, items=[])
            i += 1
            while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] in (10.5, 10.6, 11.0) and ev[i]['x'] >= 90:
                f = ev[i]
                if f['size'] == 11.0 and re.fullmatch(r'0\d', f['text']):
                    box['items'].append('')
                else:
                    box['items'][-1] = join(box['items'][-1], f['html'])
                i += 1
            blocks.append(box); continue
        if s == 8.0 and e['bold'] and 'A B O U T' in txt:
            flush(); i += 1
            # skip name line + bio
            while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] in (12.0, 9.5):
                i += 1
            continue
        if s == 8.5 and not e['bold']:
            flush()
            cap = e['html']; uri = e['uri']; i += 1
            while i < n and ev[i]['kind'] == 'text' and ev[i]['size'] == 8.5 and not ev[i]['bold']:
                cap = join(cap, ev[i]['html']); i += 1
            # attach to last img
            for b in reversed(blocks):
                if b['t'] == 'img':
                    b['caption'] = cap; b['uri'] = uri; break
            continue
        if s in (7.5, 7.6) and e['ital']:
            flush(); blocks.append(dict(t='disclaimer', html=e['text'])); i += 1; continue
        if s == 8.0:  # sources / footnotes
            flush()
            m = re.match(r'^\[?(\d+)\]?\s*(.*)$', txt)
            if e['bold'] and re.fullmatch(r'\[\d+\]', txt):
                blocks.append(dict(t='src', num=txt.strip('[]'), html='', uri=None)); i += 1; continue
            if m and (txt.startswith('[') or re.match(r'^\d+ [A-Z]', txt)):
                body = re.sub(r'^\[?\d+\]?\s*', '', e['html'])
                body = re.sub(r'^<strong>\[?\d+\]?\s*</strong>\s*', '', body)
                blocks.append(dict(t='src', num=m.group(1), html=body, uri=e['uri'])); i += 1; continue
            # continuation of previous source
            for b in reversed(blocks):
                if b['t'] == 'src':
                    if txt == 'Source report':
                        b['uri'] = b.get('uri') or e['uri']
                    else:
                        b['html'] = join(b['html'], e['html'])
                        b['uri'] = b.get('uri') or e['uri']
                    break
            i += 1; continue
        if s in (10.5, 10.6, 11.0) and not e['bold'] or (s in (10.5, 10.6, 11.0) and e['bold'] and False):
            # list items
            if x in (90,) and (txt.startswith('✓') or re.match(r'^\d+\.', txt)):
                flush()
                kind = 'check' if txt.startswith('✓') else 'ol'
                h = re.sub(r'^(✓|\d+\.)\s*', '', e['html'])
                cur = dict(t='li', kind=kind, level=0, html=h, page=e['page'], y=e['y'])
                i += 1; last = e; continue
            if x == 126 and re.match(r'^[a-z]\.', txt):
                flush()
                h = re.sub(r'^[a-z]\.\s*', '', e['html'])
                cur = dict(t='li', kind='ola', level=1, html=h, page=e['page'], y=e['y'])
                i += 1; last = e; continue
            if cur and cur['t'] == 'li' and x in (108, 144) and (e['page'] == cur['page']):
                cur['html'] = join(cur['html'], e['html']); cur['y'] = e['y']; i += 1; last = e; continue
            # paragraph text
            if cur and cur['t'] == 'p':
                newp = False
                if e['page'] == cur['page']:
                    if e['y'] - cur['y'] > 20:
                        newp = True
                else:
                    plain = re.sub(r'<[^>]+>', '', cur['html']).rstrip()
                    if re.search(r'[.?!:\]”")]$', plain):
                        newp = True
                if not newp:
                    cur['html'] = join(cur['html'], e['html']); cur['y'] = e['y']; cur['page'] = e['page']; i += 1; continue
            flush()
            cur = dict(t='p', html=e['html'], page=e['page'], y=e['y'])
            i += 1; continue
        # unknown -> keep as raw
        flush(); blocks.append(dict(t='raw', size=s, bold=e['bold'], text=txt, page=e['page'])); i += 1
    flush()
    return blocks

if __name__ == '__main__':
    out = {}
    for f in sys.argv[1:]:
        out[f] = build(f)
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
