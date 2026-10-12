"""Prior-season MLB career-high innings (regular season) per pitcher, from statsapi yearByYear."""
import json,urllib.request,os
from concurrent.futures import ThreadPoolExecutor
P='data/cache/career_ip.json'
def ip(s):
  a,_,b=str(s).partition('.');return int(a)+int(b or 0)/3
def one(pid):
  try:
    j=json.load(urllib.request.urlopen(f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=yearByYear&group=pitching&sportId=1",timeout=30))
    by={}
    for sp in j['stats'][0]['splits']:
      y=int(sp['season']);by[y]=by.get(y,0)+ip(sp['stat'].get('inningsPitched','0'))
    return str(pid),by
  except Exception as e:return str(pid),None
def ensure(pids):
  d=json.load(open(P)) if os.path.exists(P) else {}
  need=[p for p in set(map(str,map(int,pids))) if p not in d]
  with ThreadPoolExecutor(8) as ex:
    for k,v in ex.map(one,need):
      if v is not None:d[k]={str(y):round(x,1) for y,x in v.items()}
  json.dump(d,open(P,'w'));return d
def prior_high(d,pid,season):
  by=d.get(str(int(pid)),{});v=[x for y,x in by.items() if int(y)<season]
  return max(v) if v else None
if __name__=='__main__':
  import pandas as pd
  ids=set()
  for y in (2025,2026):
    g=pd.read_parquet(f'data/cache/pg_{y}.parquet');ids|=set(g[g.start==1].p)
  print(len(ensure(ids)))
