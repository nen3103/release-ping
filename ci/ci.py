#!/usr/bin/env python3
"""GitHub の自動実行用: 配信状況を点検し、今のデータが古い時だけ apec-wall ブランチの wall/status.json を書き換える。
使い方（apec-wall を取得したフォルダで）: python3 ci/ci.py [--force] [--rounds N] [--gap 秒]
- セッション内の点検が動いていてデータが新しい間は、何も書かない（衝突しない）。
- データが STALE 秒より古ければ、こちらが書く（セッション側が止まった時の代役）。"""
import sys, os, json, time, subprocess, argparse
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); sys.path.insert(0,HERE)
import run, picker
STALE=170
def sh(c): return subprocess.run(c,shell=True,cwd=ROOT,capture_output=True,text=True)
def once(force):
    d=run.main(None)
    if d['n_ch']<20: print('YouTube 読み取り失敗: 取得できたチャンネル',d['n_ch'],'失敗',len(d['fail'])); return 'unreadable'
    d=picker.apply(d,os.path.join(HERE,'picks.json')); d['by']='github'
    print(d['checked'],'ok',d['n_ch'],'rows',len(d['streams']),'picks',len(d.get('picks',[])))
    for _ in range(3):
        sh('git fetch -q origin apec-wall && git reset -q --hard FETCH_HEAD')
        try: cur=json.load(open(os.path.join(ROOT,'wall','status.json')))
        except Exception: cur={}
        age=time.time()-cur.get('ts',0)
        if not force and age<STALE: print('今のデータは %d 秒前（%s）。新しいので書かない'%(age,cur.get('by','?'))); return 'fresh'
        if cur.get('ts',0)>=d['ts']: print('こちらより新しいデータがある。書かない'); return 'fresh'
        d=picker.apply(d,os.path.join(HERE,'picks.json'))   # 取り直した最新の選定リストで当てはめ直す
        json.dump(d,open(os.path.join(ROOT,'wall','status.json'),'w'),ensure_ascii=False)
        base=sh('git rev-parse FETCH_HEAD').stdout.strip()
        r=sh('git add wall/status.json && git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" commit -q --amend -m "wall: status update" && git push -q --force-with-lease=apec-wall:%s origin HEAD:apec-wall'%base)
        if r.returncode==0: print('書き込み完了（今のデータは %d 秒前だった）'%age); return 'wrote'
        print('押し込み失敗、取り直して再試行:',r.stderr.strip()[:200]); time.sleep(3)
    return 'push-failed'
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--force',action='store_true'); ap.add_argument('--rounds',type=int,default=1); ap.add_argument('--gap',type=int,default=150)
    a=ap.parse_args(); res=[]
    for n in range(a.rounds):
        if n: time.sleep(a.gap)
        res.append(once(a.force and n==0))
    print('結果:',res)
    sys.exit(1 if res[0]=='unreadable' else 0)
