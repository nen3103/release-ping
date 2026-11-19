import re, json, subprocess
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
def get(url):
    try:
        r=subprocess.run(['curl','-sS','-m','25','-L','--compressed','-H','Accept-Language: en-US,en','-A',UA,url],capture_output=True,timeout=40)
        return r.stdout.decode('utf-8','replace')
    except Exception: return ''
def idata(h):
    m=re.search(r'ytInitialData\s*=\s*\{',h)
    if not m: return None
    try: return json.JSONDecoder().raw_decode(h[m.end()-1:])[0]
    except Exception: return None
def walk(o,key,out):
    if isinstance(o,dict):
        for k,v in o.items():
            if k==key: out.append(v)
            else: walk(v,key,out)
    elif isinstance(o,list):
        for v in o: walk(v,key,out)
def texts(o,out):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='content' and isinstance(v,str): out.append(v)
            else: texts(v,out)
    elif isinstance(o,list):
        for v in o: texts(v,out)
def lockups(h):
    d=idata(h)
    if d is None: return None
    ls=[]; walk(d,'lockupViewModel',ls); res=[]
    for l in ls:
        vid=l.get('contentId')
        if not vid or l.get('contentType') not in (None,'LOCKUP_CONTENT_TYPE_VIDEO'): continue
        badges=[]; walk(l.get('contentImage',{}),'thumbnailBadgeViewModel',badges)
        bt=[(b.get('text') or '',b.get('badgeStyle') or '') for b in badges]
        meta=l.get('metadata',{}).get('lockupMetadataViewModel',{})
        title=(meta.get('title') or {}).get('content')
        tx=[]; texts(meta.get('metadata',{}),tx)
        joined=' · '.join(tx)
        if any('LIVE' in s for _,s in bt) or any(t.upper()=='LIVE' for t,_ in bt) or 'watching' in joined: st='live'
        elif any(t.upper()=='UPCOMING' for t,_ in bt) or 'Scheduled' in joined or 'waiting' in joined or 'Premieres' in joined: st='upcoming'
        else: st='past'
        res.append({'id':vid,'state':st,'title':title,'meta':joined,'badge':[t for t,_ in bt]})
    return res
if __name__=='__main__':
    import sys
    for hnd in sys.argv[1:]:
        r=lockups(get('https://www.youtube.com/%s/streams'%hnd))
        print(hnd, None if r is None else len(r))
        for x in (r or [])[:6]: print('   ',x['state'],x['id'],x['badge'],'|',(x['title'] or '')[:70],'|',x['meta'][:80])
