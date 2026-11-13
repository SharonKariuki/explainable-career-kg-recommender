"""Text-only search of the AjiraGuide node catalogue, for annotators.

This is a plain word-overlap lookup over node labels and names. It uses no embeddings,
similarity model or recommender output. Use it to find candidate nodes, then judge them
yourself.

Usage:
    python search.py "network routing" "TCP/IP"        # one or more queries
    python search.py -f queries.txt                    # one query per line
    python search.py --node "tool:Git"                 # full record for a node id
Options: -n 20 (results per query)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
NODES = json.loads((HERE / 'skill_nodes.json').read_text(encoding='utf-8'))
BY_ID = {n['id']: n for n in NODES}
STOP = {'and', 'or', 'of', 'the', 'a', 'an', 'to', 'in', 'for', 'with', 'on', 'use', 'using', 'software'}


def stem(t):
    for suffix in ('ing', 'ed', 'es', 's', 'e'):
        if len(t) > len(suffix) + 2 and t.endswith(suffix):
            return t[:-len(suffix)]
    return t


def tokens(text):
    return {stem(t) for t in re.findall(r'[a-z0-9+#]+', text.casefold()) if t not in STOP}


INDEX = [(n, name, name.casefold(), tokens(name)) for n in NODES for name in n['names']]


def search(query, k=12):
    q, qt = query.casefold().strip(), tokens(query)
    best = {}
    for node, name, low, nt in INDEX:
        if low == q:
            score = 100.0
        elif q and (f' {q} ' in f' {low} ' or f' {low} ' in f' {q} '):
            score = 50.0 + 10 * len(qt & nt) / max(len(qt | nt), 1)
        elif qt and nt and qt & nt:
            score = 40.0 * len(qt & nt) / len(qt | nt)
            # partial word matches (e.g. "rout" in "routing") count a little
        elif q and len(q) >= 4 and q in low:
            score = 5.0
        else:
            continue
        if score > best.get(node['id'], (0, ''))[0]:
            best[node['id']] = (score, name)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], BY_ID[kv[0]]['label']))[:k]
    return [(BY_ID[i], s, name) for i, (s, name) in ranked]


def show(query, k):
    print(f'## {query}')
    for node, score, name in search(query, k):
        via = '' if name == node['label'] else f'  (name: "{name}")'
        print(f"  {node['id']} | {node['label']} | {node['type']} | {len(node['careers'])} careers{via}")


def main(argv):
    k = 20
    if '-n' in argv:
        i = argv.index('-n'); k = int(argv[i + 1]); argv = argv[:i] + argv[i + 2:]
    if argv[:1] == ['--node']:
        for nid in argv[1:]:
            print(json.dumps(BY_ID.get(nid, {'error': 'no such node'}), ensure_ascii=False, indent=1))
        return
    if argv[:1] == ['-f']:
        argv = [l.strip() for l in Path(argv[1]).read_text(encoding='utf-8').splitlines() if l.strip()]
    for q in argv:
        show(q, k)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
