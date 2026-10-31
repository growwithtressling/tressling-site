"""Insert the shared Organization and founder structured data into the main site pages.
Run from the repository root after editing site-graph.json: python3 tools/schema/inject.py"""
import json, re, pathlib
root = pathlib.Path(__file__).resolve().parents[2] / 'site'
graph = json.loads((pathlib.Path(__file__).parent / 'site-graph.json').read_text())
tag = '<script type="application/ld+json" id="site-graph">' + json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + '</script>'
for name in ['index', 'about', 'what-we-do', 'our-approach', 'work', 'resources', 'discovery-call']:
    p = root / f'{name}.html'
    t = p.read_text()
    t = re.sub(r'<script type="application/ld\+json" id="site-graph">.*?</script>', '', t, flags=re.S)
    t = t.replace('</head>', tag + '</head>', 1)
    p.write_text(t)
    print('updated', p.name)
