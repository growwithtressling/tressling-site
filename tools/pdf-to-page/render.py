"""Render Tressling article/case-study PDFs as web pages in the tressling.ai site style."""
import json, re, os, html, io
import pymupdf as fitz
from PIL import Image
from extract import build

SITE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'site'))
IMGDIR = os.path.join(SITE, 'assets', 'articles')
os.makedirs(IMGDIR, exist_ok=True)

DAN_BIO = ('Since founding Tressling in 2003, Dan McLaughlin has been an operator, investor, and advisor. '
           'As an owner-operator, he has scaled businesses in construction, real estate, and manufacturing. '
           'As Chief Investment Officer of SASCO Global Investments, he led investment decisions for a US$400 million fund, '
           'and as an advisor, he has structured more than US$1 billion in debt and equity financings. '
           'He also held senior roles in restructuring at PwC and in international finance and restructuring at Bombardier Aerospace.')

def e(s):
    return html.escape(s, quote=True)

# ---------------------------------------------------------------- manual exhibits
def table(head, rows, total_rows=(), first_col_head=True):
    h = '<thead><tr>' + ''.join(f'<th scope="col">{c}</th>' for c in head) + '</tr></thead>'
    body = []
    for r in rows:
        cls = ' class="total"' if r[0] in total_rows else ''
        body.append(f'<tr{cls}><th scope="row">{r[0]}</th>' + ''.join(f'<td>{c}</td>' for c in r[1:]) + '</tr>')
    return f'<div class="table-wrap"><table>{h}<tbody>{"".join(body)}</tbody></table></div>'

BUGGY_EX1 = table(['Revenue segment', 'Full-year 2012', 'Full-year 2018'], [
    ['Domestic DVD', '$1.137 billion', '$365.6 million'],
    ['Domestic streaming', '$2.185 billion', '$7.647 billion'],
    ['International streaming', '$287.5 million', '$7.782 billion'],
    ['Total revenue', '$3.609 billion', '$15.794 billion'],
    ['DVD share of revenue', '31.5%', '2.3%'],
], total_rows=('Total revenue', 'DVD share of revenue'))

KODAK_EX3 = table(['', '2005', '2011', '2018'], [
    ['Position', 'No. 1 in US digital cameras', 'Last full year before the January 2012 filing', 'Five years after emerging in September 2013'],
    ['Revenue', '$14.3 billion', '$6.0 billion', '$1.3 billion'],
    ['Net result', 'Loss of $1.36 billion', 'Loss of $764 million', 'Loss of $16 million'],
    ['Employees', 'About 51,100', 'About 17,100', 'About 5,400'],
])

KODAK_EX4 = table(['', 'Kodak and Fujifilm', 'What this means for your business'], [
    ['What customers value', 'Digital lets customers take and view photographs without buying and processing another roll of film.',
     'What do customers value in what you provide? How could AI help you improve it, and what could customers now do for themselves?'],
    ['How that value changes', 'Phones reduced the need for a separate camera. Kodak also competed with established camera manufacturers.',
     'Consider the alternatives available to your customer, including those from outside your industry. Will your contribution still give them a reason to choose you?'],
    ['Where else it matters', 'Fujifilm applied its film-making knowledge to products such as protective display films.',
     'Where else could your knowledge, assets, or relationships be useful?'],
    ['Why customers choose you', 'Kodak’s camera expertise faced strong alternatives. Fujifilm established a substantial position in display films and other markets.',
     'What advantage would you have in that market? Test it against what customers can obtain from others, and what they will pay.'],
    ['What you must invest', 'Kodak funded its move partly by selling its Health Group. Fujifilm restructured and acquired businesses as it expanded.',
     'What must you build or buy to serve those customers profitably? Estimate the cash required and decide whether you can finance it.'],
])

def stats(items):
    return '<ul class="stat-tiles">' + ''.join(f'<li><strong>{a}</strong><span>{b}</span></li>' for a, b in items) + '</ul>'

TWENTY_SIX_STATS = stats([('1,200+', 'employees, up from 200'), ('3', 'years'), ('26', 'active job sites'),
                          ('100+', 'engineers supervising about 1,000 tradesmen')])
SO_CLOSE_STATS = stats([('2×', 'Revenue doubled'), ('4×', 'Retained earnings quadrupled'), ('10×', 'Working capital increased tenfold')])

GAUNTLET_ALT = ('Running the gauntlet, Tressling’s five stages: 1 Recognize the need to transform, 2 Build a financeable strategy, '
                '3 Execute, 4 Prove it works, 5 Scale. This {kind} covers stage {n}.')

ARTICLES = {
    'Tressling-Buggy-Whips.pdf': dict(
        slug='buggy-whips', kind='article', eyebrow='Stage 1 · Recognize the need to transform', title='Buggy Whips',
        sub='And what they mean in the world of AI', read='7 min read', size='PDF, 620 KB', stage=1,
        desc='Netflix used its DVD business to fund the move to streaming. Getty Images saw AI coming and still filed for Chapter 11 in 2026. How to keep the existing business performing while you develop and finance what comes next.',
        exhibits={'Exhibit 1': dict(html=BUGGY_EX1)},
        img_alt={(0, 382): 'Fifth Avenue in New York on Easter Sunday 1900, filled with horse-drawn carriages.',
                 (1, 81): 'Fifth Avenue in New York on Easter Sunday 1913, filled with motor cars and no carriages.'},
        links={'Kodak and Fujifilm offer an interesting comparison, and I will explore it in an upcoming article.':
               'Kodak and Fujifilm offer an interesting comparison, and I explore it in <a href="kodak-vs-fujifilm.html">Kodak vs. Fujifilm</a>.'},
    ),
    'Tressling-Kodak-vs-Fujifilm.pdf': dict(
        slug='kodak-vs-fujifilm', kind='article', eyebrow='Stage 2 · Build a financeable strategy', title='Kodak vs. Fujifilm',
        sub='Two pivots, two outcomes, and what that means in the world of AI', read='7 min read', size='PDF, 460 KB', stage=2,
        desc='Kodak led the US digital camera market in 2005 and filed for bankruptcy protection in 2012. Fujifilm faced the same collapse in film and built new businesses. The difference came down to value-added.',
        exhibits={'Exhibit 1': dict(alt='Film: repeated purchases. Buy film, take photos, process, then buy film again; more photographs meant more purchases. Digital: equipment purchase. Buy a camera, then take, view and share many photographs without buying another roll of film; revenue depends on the next sale.'),
                  'Exhibit 2': dict(alt='Statista chart of worldwide shipments of photo cameras by CIPA members, 1951 to 2023. Film camera shipments rose to about 37 million a year by the late 1990s. Digital camera shipments peaked near 120 million around 2010, then fell below 10 million by 2023.'),
                  'Exhibit 3': dict(html=KODAK_EX3),
                  'Exhibit 4': dict(html=KODAK_EX4)},
        drop_imgs=[(0, 361)],  # Kodak logo
        img_alt={(5, 491): 'Strategy and capital allocation develop together. Step 1, define the option: where could we add value, what would we offer, to whom and at what scale. Step 2, assess the trade-offs: costs in cash, people and time; benefits in value and returns; risks. Step 3, adjust the strategy: change the scope, timing or resources committed, and decide what to test next. Reassess the revised option as evidence develops. At every round ask what gives up funding and what must be proven before investing more, and commit in stages.'},
        links={'In my Buggy Whips article on my Substack,': 'In my <a href="buggy-whips.html">Buggy Whips</a> article,',
               'In the next article, The Cube,': 'In the next article, <a href="the-cube.html">The Cube</a>,'},
    ),
    'Tressling-The-Cube.pdf': dict(
        slug='the-cube', kind='article', eyebrow='Stage 2 · Build a financeable strategy', title='The Cube',
        sub='Choosing where to grow in an AI world', read='6 min read', size='PDF, 450 KB', stage=2,
        desc='A business can grow through new customers, new products and services, or new territories. The Cube compares the people, cash and service each direction requires. AI makes it faster to bid. You still need the crews and capital to deliver what you win.',
        exhibits={'Exhibit 1': dict(alt='The Cube: three directions for growth from one pool of resources. Axes for customers, products and services, and geography. Compare the cash, capabilities and management time each direction requires.'),
                  'Exhibit 2': dict(alt='The Cube: entering a new region. An equipment distributor moves along the customers and geography axes while its product range stays the same. It builds on its product range, supplier relationships, technical knowledge and ordering systems. AI can help research prospective accounts, adapt product information for local buyers and extend routine technical support. AI can also increase pressure: buyers find suppliers directly, local competitors improve service, and other entrants reach the same customers. Still to fund and manage: local stock, service coverage, customer credit and management presence.')},
        links={},
    ),
    'Tressling-Case-Study-Twenty-Six-Sites.pdf': dict(
        slug='twenty-six-sites', kind='case study', eyebrow='Case study · Stage 5 · Scale', title='Twenty-Six Sites',
        sub='Scaling a general contractor from 200 to 1,200 people in three years', read='7 min read', size='PDF, 540 KB', stage=5,
        desc='A Canadian-owned general contractor in Riyadh grew from 200 to 1,200 people, including more than 100 engineers across 26 job sites, before its sale in 2015. Dan McLaughlin owned logistics, systems and financing.',
        exhibits={'Exhibit 1': dict(alt='North America: the general contractor manages electrical, mechanical and masonry subcontractors, each with its own crews, so workforce risk sits with the subcontractors. Saudi Arabia: the general contractor employs the trades directly, with more than 100 site engineers, bilingual crew supervisors and about 1,000 tradesmen on payroll, plus recruitment and visas, training, and housing, transport and catering. Workforce risk sits with the general contractor.'),
                  'Exhibit 2': dict(alt='Chart of the share of labour hours used against percent complete as certified by the supervising engineer. On plan, 50 percent of hours are used at 50 percent complete. The warning case shows 80 percent of labour hours used at 50 percent certified complete, a 30-point gap.'),
                  'Exhibit 3': dict(alt='The supervising engineer certifies progress and the government pays against the certificate, so payments arrive on the government’s cycle into the operating account that covers payroll, materials and equipment. Below the floor, the larger general contractor, acting as financial backstop, advances cash. Above the threshold, the advances are repaid.')},
        replace_imgs={(0, 483): TWENTY_SIX_STATS},
        links={'Saudi Arabia.1': 'Saudi Arabia.<sup><a href="#source-1">1</a></sup>',
               'Its five stages guide the work from recognizing the need for change to building a business that can grow at scale.': 'Its six stages guide the work from recognizing the need for change to building a business that can grow at scale and realizing its value.'},
    ),
    'Tressling-Case-Study-So-Close-to-Glory.pdf': dict(
        slug='so-close-to-glory', kind='case study', eyebrow='Case study · Turnaround · Stage 6 · Realize the value', title='So Close to Glory',
        sub='A skilled-trades contractor turnaround and a failed exit', read='8 min read', size='PDF, 150 KB', stage=6,
        gauntlet_caption='So Close to Glory illustrates the sixth stage: realizing the value. Creating value and realizing it are separate steps.',
        desc='A 25-person skilled-trades contractor in crisis, a four-year turnaround with Dan McLaughlin as the owner’s full-time partner, and a buyer with an approved loan package. Prioritizing threats, building the tools to manage performance, and why creating value and realizing it are separate steps.',
        exhibits={}, stats_after='After four years, the results demonstrated the effect of the changes:',
        links={},
    ),
}

# ---------------------------------------------------------------- image helper
def save_clip(doc, page, bbox, name, dpi=200):
    p = doc[page]
    pix = p.get_pixmap(clip=fitz.Rect(bbox), dpi=dpi)
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    path = os.path.join(IMGDIR, name + '.webp')
    im.save(path, 'WEBP', quality=86, method=6)
    return f'assets/articles/{name}.webp', im.size

def figure(src, size, alt, caption=''):
    w, h = size
    cap = f'<figcaption>{caption}</figcaption>' if caption else ''
    return (f'<figure><img src="{src}" alt="{e(alt)}" width="{w}" height="{h}" loading="lazy" decoding="async">{cap}</figure>')

STAGES = ['Recognize the need to transform', 'Build a financeable strategy', 'Execute', 'Prove it works', 'Scale', 'Realize the value']

def gauntlet_strip(cfg, caption):
    here = 'This case study' if cfg['kind'] == 'case study' else 'This article'
    lis = []
    for k, name in enumerate(STAGES, 1):
        cur = k == cfg['stage']
        lis.append(f'<li{" class=\"current\" aria-current=\"step\"" if cur else ""}><a href="our-approach.html#step-{k}"><span class="n">{k}</span>{name}'
                   + (f'<span class="here">{here}</span>' if cur else '') + '</a></li>')
    return (f'<figure class="gauntlet-strip" aria-label="Running the gauntlet"><p class="exhibit-label">Running the gauntlet</p>'
            f'<ol>{"".join(lis)}</ol><figcaption>{caption}</figcaption></figure>')

def ref_links(s, has_sources):
    if not has_sources:
        return s
    s = re.sub(r'\[(\d+)\]', r'<a class="ref" href="#source-\1">[\1]</a>', s)
    # keep runs like [1][3] together on one line
    return re.sub(r'((?:<a class="ref"[^>]*>\[\d+\]</a>){2,})', r'<span class="refs">\1</span>', s)

# ---------------------------------------------------------------- render body
def render(pdf):
    cfg = ARTICLES[pdf]
    path = os.path.join(SITE, 'downloads', pdf)
    doc = fitz.open(path)
    blocks = build(path)
    slug = cfg['slug']
    sources = [b for b in blocks if b['t'] == 'src']
    blocks = [b for b in blocks if b['t'] != 'src']
    has_src = bool(sources)
    out = []
    imgn = 0
    seen_ex = set()
    i = 0
    takeaways_html = closing_html = gauntlet_html = ''
    disclaimer = ''

    def fix(s):
        for a, b in cfg.get('links', {}).items():
            s = s.replace(a, b)
        return ref_links(s, has_src)

    while i < len(blocks):
        b = blocks[i]; t = b['t']
        if t == 'p':
            txt = b['html']
            out.append(f'<p>{fix(txt)}</p>')
            if cfg.get('stats_after') and re.sub('<[^>]+>', '', txt).strip() == cfg['stats_after']:
                out.append(SO_CLOSE_STATS)
        elif t == 'h2':
            if b['text'].startswith('Sources'):
                i += 1; continue
            out.append(f'<h2>{e(b["text"])}</h2>')
        elif t == 'callout':
            out.append(f'<p class="callout">{b["html"]}</p>')
        elif t == 'li':
            # gather consecutive list items into nested lists
            items = []
            while i < len(blocks) and blocks[i]['t'] == 'li':
                items.append(blocks[i]); i += 1
            out.append(render_list(items, fix))
            continue
        elif t == 'img':
            key = (b['page'], round(b['bbox'][1]))
            if any(k[0] == key[0] and abs(k[1] - key[1]) < 3 for k in cfg.get('drop_imgs', [])):
                i += 1; continue
            rep = [v for k, v in cfg.get('replace_imgs', {}).items() if k[0] == key[0] and abs(k[1] - key[1]) < 3]
            if rep:
                out.append(rep[0]); i += 1; continue
            cap = b.get('caption', '')
            is_gauntlet = 'stage' in re.sub('<[^>]+>', '', cap).lower() and ('covers' in cap or 'illustrates' in cap)
            imgn += 1
            if is_gauntlet:
                imgn -= 1
                gauntlet_html = gauntlet_strip(cfg, re.sub(r'</?em>', '', cap))
            else:
                src, size = save_clip(doc, b['page'], b['bbox'], f'{slug}-{imgn}')
                alt = [v for k, v in cfg.get('img_alt', {}).items() if k[0] == key[0] and abs(k[1] - key[1]) < 3]
                alt = alt[0] if alt else ''
                c = cap
                if b.get('uri') and 'Archive source' in c:
                    c = c.replace('Archive source', f'<a href="{e(b["uri"])}" rel="noopener">Archive source</a>')
                c = re.sub(r'</?em>', '', c)
                out.append(figure(src, size, alt, c))
        elif t == 'exhibit':
            label = b['label']
            if label in seen_ex:  # PDF repeats "Exhibit 3"; the second is Exhibit 4
                label = f'Exhibit {int(label.split()[1]) + 1}'
            seen_ex.add(label)
            ex = cfg['exhibits'].get(label, {})
            head = f'<p class="exhibit-label">{label}</p><p class="exhibit-title">{e(b["title"])}</p>'
            src_html = ref_links(b['source'], has_src)
            if 'html' in ex:
                body = ex['html']
            else:
                imgs = b['imgs']
                parts = []
                for k, im in enumerate(imgs):
                    imgn += 1
                    s, size = save_clip(doc, im['page'], im['bbox'], f'{slug}-{imgn}')
                    w, h = size
                    parts.append(f'<a class="zoom" href="{s}" title="Open full-size image"><img src="{s}" alt="{e(ex.get("alt", b["title"]))}" width="{w}" height="{h}" loading="lazy" decoding="async"></a>')
                body = ''.join(parts)
            out.append(f'<figure class="exhibit" id="{label.lower().replace(" ", "-")}">{head}{body}<figcaption>{src_html}</figcaption></figure>')
        elif t == 'takeaways':
            lis = ''.join(f'<li>{x}</li>' for x in b['items'])
            takeaways_html = f'<aside class="takeaways" aria-labelledby="takeaways-title"><p class="eyebrow" id="takeaways-title">{b["title"]}</p><ol>{lis}</ol></aside>'
            out.append(takeaways_html)
        elif t == 'closing':
            out.append(f'<p class="closing">{e(b["html"])}</p>')
        elif t == 'disclaimer':
            disclaimer = b['html']
        elif t == 'raw':
            pass
        i += 1

    if not gauntlet_html and cfg.get('gauntlet_caption'):
        gauntlet_html = gauntlet_strip(cfg, cfg['gauntlet_caption'])
    if gauntlet_html:
        out.append(gauntlet_html)

    # sources
    src_html = ''
    if sources:
        lis = []
        for s in sources:
            body = s['html'].strip()
            body = re.sub(r'\s*Source report$', '', body)
            if s.get('uri'):
                body = f'<a href="{e(s["uri"])}" rel="noopener">{body}</a>'
            lis.append(f'<li id="source-{s["num"]}" value="{s["num"]}">{body}</li>')
        heading = 'Sources' if cfg['slug'] in ('the-cube', 'twenty-six-sites') else 'Sources for the company examples'
        src_html = f'<section class="sources" aria-labelledby="sources-title"><h2 id="sources-title">{heading}</h2><ol>{"".join(lis)}</ol></section>'

    author = (f'<section class="author-box" aria-label="About the author"><img src="assets/dan.jpg" alt="Dan McLaughlin" width="96" height="96" loading="lazy">'
              f'<div><p class="eyebrow">About the author</p><p class="author-name"><a href="about.html#dan">Dan McLaughlin</a>, Founder and CEO, Tressling.ai</p>'
              f'<p>{DAN_BIO}</p></div></section>')
    disc = f'<p class="disclaimer">{e(disclaimer)}</p>' if disclaimer else ''
    return '\n'.join(out), author, src_html, disc

def render_list(items, fix):
    html_out = []
    kind0 = items[0]['kind']
    tag = 'ul class="checks"' if kind0 == 'check' else 'ol'
    close = 'ul' if kind0 == 'check' else 'ol'
    html_out.append(f'<{tag}>')
    k = 0
    while k < len(items):
        it = items[k]
        li = f'<li>{fix(it["html"])}'
        k += 1
        subs = []
        while k < len(items) and items[k]['level'] == 1:
            subs.append(items[k]); k += 1
        if subs:
            li += '<ol class="alpha">' + ''.join(f'<li>{fix(s["html"])}</li>' for s in subs) + '</ol>'
        li += '</li>'
        html_out.append(li)
    html_out.append(f'</{close}>')
    return ''.join(html_out)

# ---------------------------------------------------------------- page shell
NAV = [('index.html', 'Home'), ('what-we-do.html', 'What We Do'), ('our-approach.html', 'Our Approach'),
       ('work.html', 'Selected Work'), ('about.html', 'About'), ('resources.html', 'Resources')]

def page(pdf):
    cfg = ARTICLES[pdf]
    body, author, sources, disc = render(pdf)
    slug = cfg['slug']
    url = f'https://tressling.ai/{slug}.html'
    current = 'work.html' if cfg['kind'] == 'case study' else 'resources.html'
    nav = ''.join(f'<a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{t}</a>' for h, t in NAV)
    fnav = ''.join(f'<a href="{h}">{t}</a>' for h, t in NAV)
    title = f'{cfg["title"]}: {cfg["sub"]} | Tressling.ai'
    cover = f'https://tressling.ai/assets/covers/{pdf[:-4]}.jpg'
    ld = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': cfg['title'], 'alternativeHeadline': cfg['sub'], 'description': cfg['desc'],
        'url': url, 'mainEntityOfPage': url, 'image': cover, 'inLanguage': 'en',
        'genre': 'Case study' if cfg['kind'] == 'case study' else 'Article',
        'author': {'@type': 'Person', 'name': 'Dan McLaughlin', 'jobTitle': 'Founder and CEO',
                   'url': 'https://tressling.ai/about.html#dan', 'worksFor': {'@type': 'Organization', 'name': 'Tressling.ai'}},
        'publisher': {'@type': 'Organization', 'name': 'Tressling.ai', 'url': 'https://tressling.ai/',
                      'logo': {'@type': 'ImageObject', 'url': 'https://tressling.ai/assets/tressling-logo.png'}},
        'associatedMedia': {'@type': 'MediaObject', 'contentUrl': f'https://tressling.ai/downloads/{pdf}', 'encodingFormat': 'application/pdf'},
    }
    back = ('work.html', 'Selected Work') if cfg['kind'] == 'case study' else ('resources.html', 'Resources')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{e(cfg["desc"])}"><meta name="author" content="Dan McLaughlin"><meta name="theme-color" content="#0a1e3d"><title>{e(title)}</title><link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:site_name" content="Tressling.ai"><meta property="og:title" content="{e(cfg["title"])}: {e(cfg["sub"])}"><meta property="og:description" content="{e(cfg["desc"])}"><meta property="og:url" content="{url}"><meta property="og:image" content="https://tressling.ai/assets/tressling-share.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Tressling.ai logo"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/site.css"><script defer src="assets/site.js"></script><script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script></head><body><a class="skip" href="#main">Skip to content</a><header class="header"><div class="nav-wrap"><a href="index.html" class="brand" aria-label="Tressling.ai home"><img class="brand-logo" src="assets/tressling-logo.png" alt="Tressling.ai"></a><button class="menu-toggle" aria-controls="navigation" aria-expanded="false">Menu <span aria-hidden="true">☰</span></button><nav id="navigation" aria-label="Main navigation">{nav}<a class="nav-cta" href="discovery-call.html">Book a Discovery Call</a></nav></div></header><main id="main"><article class="article"><header class="page-hero article-hero"><div class="wrap"><p class="eyebrow"><a href="{back[0]}">{back[1]}</a> · {e(cfg["eyebrow"])}</p><h1>{e(cfg["title"])}</h1><p class="article-sub">{e(cfg["sub"])}</p><div class="article-meta"><p>By <a href="about.html#dan">Dan McLaughlin</a>, Founder and CEO, Tressling.ai<br><span>{cfg["read"]}</span></p><a class="button secondary on-dark" href="downloads/{pdf}" download>Download PDF<span aria-hidden="true">↓</span></a></div></div></header><div class="article-body">
{body}
{sources}
{author}
{disc}
</div></article><section class="cta"><div class="wrap cta-inner"><div><p class="eyebrow">Start a conversation</p><h2>What comes next<br>for your business?</h2><p>Let’s discuss the changes affecting your market, the opportunity you want to pursue, and the decisions ahead.</p></div><a class="button" href="discovery-call.html">Book a Discovery Call<span aria-hidden="true">↗</span></a></div></section></main><footer><div class="wrap footer-grid"><div><a class="brand" href="index.html"><img class="brand-logo" src="assets/tressling-logo.png" alt="Tressling.ai"></a><p>Transform. Capitalize. Scale.</p></div><nav aria-label="Footer navigation">{fnav}</nav><div><a href="mailto:grow@tressling.ai">grow@tressling.ai</a><p>© 2026 Tressling.ai</p></div></div></footer></body></html>'''

if __name__ == '__main__':
    for pdf, cfg in ARTICLES.items():
        out = page(pdf)
        open(os.path.join(SITE, cfg['slug'] + '.html'), 'w').write(out)
        print('wrote', cfg['slug'], len(out))
