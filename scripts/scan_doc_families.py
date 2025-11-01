#!/usr/bin/env python3
import os
import json
from pathlib import Path


def detect_family(doc_root: Path):
    guides = doc_root / 'Guides' / 'html'
    if guides.exists():
        subs = [p.name for p in guides.iterdir() if p.is_dir()]
        known = {'expert', 'gettingstarted', 'documentsecurity'}
        present = known.intersection(set(subs))
        ok = all((guides / s / 'Content').exists() for s in present)
        if len(present) >= 2 and ok:
            return 'idolserver-merged'
    help_dir = doc_root / 'Help'
    if help_dir.exists() and (help_dir / 'Content').exists():
        return 'single-bundle'
    # exceptional fallback: shallow scan
    triad = {'Content', 'Data', 'Resources'}
    hits = set()
    for root, dirs, files in os.walk(doc_root):
        for d in dirs:
            if d in triad:
                hits.add(d)
        if len(hits) == 3:
            break
    return 'exceptional' if len(hits) < 2 else 'single-bundle'


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Scan documentation roots and classify families')
    ap.add_argument('roots', nargs='+', help='Document root directories to scan')
    ap.add_argument('--out', default='doc_family_report.json', help='Output JSON report path')
    args = ap.parse_args()

    report = {}
    for r in args.roots:
        p = Path(r)
        if not p.exists():
            continue
        report[str(p)] = detect_family(p)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()


