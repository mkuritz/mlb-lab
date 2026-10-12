import sys,os,datetime as dt,pandas as pd
from pybaseball import statcast,cache
cache.enable()
s=dt.date.fromisoformat(sys.argv[1]);e=dt.date.fromisoformat(sys.argv[2])
out=sys.argv[3] if len(sys.argv)>3 else 'data/cache/raw';os.makedirs(out,exist_ok=True)
d=s
while d<=e:
  d2=min(d+dt.timedelta(days=6),e);f=f'{out}/{d}.parquet'
  if not os.path.exists(f):
    try:
      df=statcast(str(d),str(d2),verbose=False)
      df.to_parquet(f);print(d,len(df),flush=True)
    except Exception as x:print('ERR',d,x,flush=True)
  d=d2+dt.timedelta(days=1)
