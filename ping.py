"""Checks three public government release lists for new items and, if any appear,
starts a workflow in another repository via the GitHub API.

Sources (public pages, light requests only):
  - Japan Joint Staff press PDFs  https://www.mod.go.jp/js/pdf/YYYY/pYYYYMMDD_NN.pdf (today/yesterday, JST; size watched for replacements)
  - Taiwan MND "regional activities" list  https://www.mnd.gov.tw/news/plaactlist/1
  - Taiwan Coast Guard Administration news list (category 10)

State: seen.json (IDs already seen). Updated only when something new is found and the dispatch succeeded.
Secrets: DISPATCH_TOKEN (fine-grained token, Actions: write on the target repo), TARGET_REPO (owner/name).
"""
import os, re, sys, json, html, subprocess, datetime as dt, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(HERE, 'seen.json')
JST = dt.timezone(dt.timedelta(hours=9))
UA = 'Mozilla/5.0 (research archive; personal use)'


def get(url):
    p = subprocess.run(['curl', '-sfL', '--max-time', '25', '-A', UA, url], capture_output=True, timeout=40)
    return p.stdout.decode('utf-8', 'replace') if p.returncode == 0 else None


def status(url):
    p = subprocess.run(['curl', '-s', '-L', '--max-time', '20', '-A', UA, '-r', '0-3', '-o', '/dev/null',
                        '-w', '%{http_code}', url], capture_output=True, timeout=30)
    return p.stdout.decode().strip()


def size(url):
    p = subprocess.run(['curl', '-sIL', '--max-time', '20', '-A', UA, url], capture_output=True, timeout=30)
    m = re.findall(r'(?im)^content-length:\s*(\d+)', p.stdout.decode('utf-8', 'replace'))
    return m[-1] if m else None


def js(seen):
    # PDFs are sometimes replaced later with a fuller version (maps/photos added), so the size is watched too
    now = dt.datetime.now(JST)
    days = [now.date(), now.date() - dt.timedelta(days=1)]
    out = []
    for d in days:
        miss = 0
        for n in range(1, 40):
            k = f'js:p{d:%Y%m%d}_{n:02d}'
            url = f'https://www.mod.go.jp/js/pdf/{d:%Y}/{k[3:]}.pdf'
            if k in seen:
                miss = 0
                z = size(url)
                if z:
                    out.append(f'jsz:{k[3:]}:{z}')
                continue
            if status(url) in ('200', '206'):
                out.append(k)
                z = size(url)
                if z:
                    out.append(f'jsz:{k[3:]}:{z}')
                miss = 0
            else:
                miss += 1
                if miss >= 2:
                    break
    return out


def mnd():
    s = get('https://www.mnd.gov.tw/news/plaactlist/1')
    return ['mnd:' + i for i in dict.fromkeys(re.findall(r'href="/?news/plaact/(\d+)"', html.unescape(s or '')))]


def cga():
    s = get('https://www.cga.gov.tw/GipOpen/wSite/lp?ctNode=650&xq_xCat=10&mp=999&nowPage=1&pagesize=15')
    return ['cga:' + i for i in dict.fromkeys(re.findall(r'ct\?xItem=(\d+)&(?:amp;)?ctNode=650', s or ''))]


def dispatch(items):
    tok, repo = os.environ.get('DISPATCH_TOKEN'), os.environ.get('TARGET_REPO')
    if not (tok and repo):
        print('DISPATCH_TOKEN / TARGET_REPO not set')
        return False
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/workflows/watch.yml/dispatches',
        data=json.dumps({'ref': 'main', 'inputs': {'send': 'true'}}).encode(), method='POST',
        headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ping'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 204
    except Exception as e:
        print('dispatch failed:', e)
        return False


def main():
    seen = set(json.load(open(SEEN))) if os.path.exists(SEEN) else set()
    found = []
    for f in (lambda: js(seen), mnd, cga):
        try:
            found += f()
        except Exception as e:
            print('check error', e)
    # a size key for a PDF seen for the first time in this run is not a replacement
    first = {x[3:] for x in found if x.startswith('js:') and x not in seen}
    known_size = {x.split(':')[1] for x in seen if x.startswith('jsz:')}
    for x in found:
        if x.startswith('jsz:') and x not in seen and x.split(':')[1] not in known_size and x.split(':')[1] not in first:
            seen.add(x)   # PDFs already seen before this check existed: record the current size quietly
    if '--seed' in sys.argv:
        json.dump(sorted(seen | set(found)), open(SEEN, 'w'), indent=0)
        print('seeded', len(seen | set(found)))
        return
    new = [x for x in found if x not in seen]
    print('new:', ','.join(new) or 'none')
    if not new:
        if found and set(found) - set(json.load(open(SEEN)) if os.path.exists(SEEN) else []):
            json.dump(sorted(seen), open(SEEN, 'w'), indent=0)   # quietly recorded sizes
        return
    if dispatch(new):
        keep = sorted(seen | set(new))
        # keep the file small: JS keys older than 10 days are dropped
        cut = (dt.datetime.now(JST) - dt.timedelta(days=10)).strftime('%Y%m%d')
        keep = [k for k in keep if not (k.startswith('js:p') and k[4:12] < cut)
                and not (k.startswith('jsz:p') and k[5:13] < cut)][-3000:]
        json.dump(keep, open(SEEN, 'w'), indent=0)
        print('dispatched')


if __name__ == '__main__':
    main()
