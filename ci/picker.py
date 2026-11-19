"""枠の選定（セッション内の点検と GitHub の自動実行の両方が使う）。"""
import json
# 通信社・国際放送（未登録の枠でも、三者会談と判定され配信中なら自動で上位に入れる対象）
FEEDS={"AP通信","ロイター","CGTN","新華社 New China TV","CCTV Video News Agency","CCTV-4","Sky News","BBC News","BBC中文","DW","France 24","Euronews","アルジャジーラ英語","CNA","ホワイトハウス","C-SPAN","ブルームバーグTV","ABC豪","TRT World","CNBC","CNBC International"}
def choose(streams,order,n=6):
    """枠の並び: ①登録済みの通信社・国際放送の三者会談枠 ②未登録でも通信社・国際放送の三者会談枠 ③その他の登録済み三者会談枠 ④その他の登録済み枠（いずれも配信中のみ）。同じ局は1枠。"""
    by={r['id']:r for r in streams}; live=[r for r in streams if r['st']=='live']; on={r['id'] for r in live}
    tri=lambda i: by[i]['sc']=='米中ロ会談'
    reg=[i for i in order if i in on]
    auto=sorted([r for r in live if r['sc']=='米中ロ会談' and r['ch'] in FEEDS and r['id'] not in order],key=lambda r:-(r['v'] or 0))
    feed=lambda i: by[i]['ch'] in FEEDS
    seq=[i for i in reg if tri(i) and feed(i)]+[r['id'] for r in auto]+[i for i in reg if tri(i) and not feed(i)]+[i for i in reg if not tri(i)]
    seen=set(); out=[]
    for i in seq:
        if by[i]['ch'] not in seen: seen.add(by[i]['ch']); out.append(i)
    return out[:n]

def apply(d,picks_path):
    """status（d）に picks.json の優先順を当てはめ、並べる枠 d['picks'] とメモを入れる。"""
    try:
        pk=json.load(open(picks_path))
    except Exception:
        return d
    live={r['id'] for r in d['streams']}
    d['picks']=choose(d['streams'],pk.get('picks',[]))
    d['notes']={k:x for k,x in pk.get('notes',{}).items() if k in live}
    d['picked']=pk.get('picked'); d['picknote']=pk.get('picknote')
    return d
