#!/usr/bin/env python3
"""全チャンネルを点検し status.json（db の live/status 用）を書く。"""
import yt, re, json, datetime, concurrent.futures as cf, sys
from channels import C
TR=re.compile(r'trump|川普|特朗普|トランプ|трамп|트럼프',re.I)
XI=re.compile(r'\bxi\b|習|习|시진핑|си цзиньпин',re.I)
PU=re.compile(r'putin|普京|普丁|蒲亭|プーチン|путин|푸틴|poutine',re.I)
AP=re.compile(r'apec|shenzhen|深圳|trilateral|three-way|3-way|атэс|шэньчжэн|美中俄|中美俄|米中ロ|米中露|米中首脳|미중|미·중|川習|習川|川习|习特|習特',re.I)
TRI=re.compile(r'trilateral|three-way|3-way|three leaders|美中俄|中美俄|米中ロ|米中露|трёхсторон|трехсторон|미·중·러|미중러|三方',re.I)
DIN=re.compile(r'dinner|gala|banquet|reception|晚宴|晩餐|夕食会',re.I)
PRS=re.compile(r'記者会見|会見|press conference|presser|記者會',re.I)
US_CN=re.compile(r'川習|習川|川习|习特|習特|米中首脳|미중 정상|미·중 정상',re.I)
def scene(t):
    tr,xi,pu=bool(TR.search(t)),bool(XI.search(t)),bool(PU.search(t))
    if PRS.search(t): return '記者会見'
    if TRI.search(t) or (tr and xi and pu): return '米中ロ会談'
    if DIN.search(t): return '歓迎宴'
    if (tr and xi) or US_CN.search(t): return '米中会談'
    if tr and pu: return '米ロ会談'
    if xi and pu: return '中ロ会談'
    return 'APEC全般'
def related(t):
    n=sum(bool(r.search(t)) for r in (TR,XI,PU))
    return bool(AP.search(t)) or n>=2
PT=datetime.timezone(datetime.timedelta(hours=-8)); CN=datetime.timezone(datetime.timedelta(hours=8))
def sched(meta):
    m=re.search(r'(\d+)/(\d+)/(\d+), (\d+):(\d+)\s*([AP]M)',meta or '')
    if not m: return None
    mo,d,y,h,mi,ap=m.groups(); h=int(h)%12+(12 if ap=='PM' else 0)
    return datetime.datetime(2000+int(y),int(mo),int(d),h,int(mi),tzinfo=PT).astimezone(CN)
def viewers(meta):
    m=re.search(r'([\d.,]+)([KM]?) (watching|waiting)',meta or '')
    if not m: return None
    return int(float(m.group(1).replace(',',''))*{'':1,'K':1e3,'M':1e6}[m.group(2)])
def one(h):
    for _ in range(2):
        r=yt.lockups(yt.get('https://www.youtube.com/%s/streams'%h))
        if r is not None: return h,r
    return h,None
def main(out):
    now=datetime.datetime.now(CN)
    with cf.ThreadPoolExecutor(10) as ex: res=list(ex.map(one,C))
    rows=[]; fail=[]
    for h,r in res:
        name,co,grp,always=C[h][:4]; only=C[h][4] if len(C[h])>4 else None
        if r is None: fail.append(name); continue
        gen=0
        for x in r:
            if x['state']=='past': continue
            t=x['title'] or ''; rel=related(t)
            if only is not None:
                if x['id'] not in only: continue
                rel=True
            if not rel:
                if not(always and x['state']=='live' and gen==0): continue
                gen=1
            s=sched(x['meta'])
            if x['state']=='upcoming' and s and (now-s).total_seconds()>3*3600: continue  # 放置された予定枠
            rows.append({'id':x['id'],'ch':name,'co':co,'g':grp,'st':x['state'],'sc':scene(t) if rel else '常時配信','t':t[:160],'v':viewers(x['meta']),'at':s.strftime('%d日 %H:%M') if s else None})
    return {'checked':now.strftime('%m/%d %H:%M'),'ts':int(now.timestamp()),'n_ch':len(C)-len(fail),'fail':fail,'streams':rows}
if __name__=='__main__':
    d=main(sys.argv[1]); json.dump(d,open(sys.argv[1],'w'),ensure_ascii=False)
    live=[r for r in d['streams'] if r['st']=='live' and r['sc']!='常時配信']
    print(d['checked'],'ch ok',d['n_ch'],'fail',d['fail'],'rows',len(d['streams']),'bytes',len(json.dumps(d,ensure_ascii=False).encode()))
    for r in sorted(d['streams'],key=lambda r:(r['g'],r['st'],-(r['v'] or 0))):
        if r['g']=='main': print(' ',r['st'][:4],r['sc'],r['ch'],r['v'],r['at'],'|',r['t'][:60])
    print('  agg rows:',sum(r['g']=='agg' for r in d['streams']))
