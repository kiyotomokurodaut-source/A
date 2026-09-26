#!/usr/bin/env python3
"""Generate context-specific headers. Never store preview noindex in production."""
from pathlib import Path
import argparse
import hashlib
import os
import re

ROOT = Path(__file__).resolve().parents[1]

def make_headers(root: Path, context: str) -> str:
    base = (root / 'tools/netlify_headers_base_r17.txt').read_text(encoding='utf-8').rstrip()
    base = re.sub(r'^\s*X-Robots-Tag:.*\n?', '', base, flags=re.M | re.I)
    lines = [base, '\n# One exact asset rule per URL; no conflicting wildcard cache rules.']
    for path in sorted((root / 'public/assets').rglob('*')):
        if not path.is_file():
            continue
        name = path.name
        tag = re.search(r'-([0-9a-f]{12})\.(?:css|js)$', name)
        immutable = bool(tag and hashlib.sha256(path.read_bytes()).hexdigest()[:12] == tag.group(1))
        policy = 'public, max-age=31536000, immutable' if immutable else 'public, max-age=0, must-revalidate'
        url = '/' + path.relative_to(root / 'public').as_posix()
        lines += [url, '  Cache-Control: ' + policy, '']
    # CONTEXT is provided by Netlify. Missing context means a local production build.
    if context in {'deploy-preview', 'branch-deploy', 'dev'}:
        lines += ['# Preview deployments must not compete with the public site.', '/*', '  X-Robots-Tag: noindex, nofollow', '']
    elif context != 'production':
        raise ValueError('Unrecognized deploy context: ' + context)
    return '\n'.join(lines).rstrip() + '\n'

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--context', default=os.getenv('CONTEXT', 'production'))
    args = p.parse_args()
    text = make_headers(ROOT, args.context)
    (ROOT / 'public/_headers').write_text(text, encoding='utf-8')
    print('Prepared headers for', args.context)

if __name__ == '__main__':
    main()
