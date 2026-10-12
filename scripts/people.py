import json,urllib.request,os,pandas as pd
P='data/cache/people.json'
def load():
  return json.load(open(P)) if os.path.exists(P) else {}
def ensure(ids):
  d=load();need=[str(int(i)) for i in set(ids) if i==i and str(int(i)) not in d]
  for i in range(0,len(need),150):
    u="https://statsapi.mlb.com/api/v1/people?personIds="+",".join(need[i:i+150])+"&hydrate=currentTeam"
    for p in json.load(urllib.request.urlopen(u,timeout=60)).get('people',[]):
      d[str(p['id'])]=dict(n=p['fullName'],bats=p.get('batSide',{}).get('code'),thr=p.get('pitchHand',{}).get('code'),pos=p.get('primaryPosition',{}).get('abbreviation'),tm=p.get('currentTeam',{}).get('id'))
  json.dump(d,open(P,'w'));return d
if __name__=='__main__':
  ids=set()
  for y in (2025,2026):
    pa=pd.read_parquet(f'data/cache/pa_{y}.parquet');ids|=set(pa.b)|set(pa.p)
  print(len(ensure(ids)))
