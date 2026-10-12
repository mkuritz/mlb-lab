"""Incremental: pull the last N days of Statcast (Baseball Savant via pybaseball), compact, merge into pa_/pg_ tables."""
import sys,os,datetime as dt,pandas as pd
sys.path.insert(0,os.path.dirname(__file__))
from compact import compact
from pybaseball import statcast
def run(days=4,yr=None):
  today=dt.date.today();yr=yr or today.year
  s=today-dt.timedelta(days=days);e=today
  try:df=statcast(str(s),str(e),verbose=False)
  except Exception as x:print('statcast pull failed',x);return 0
  if df is None or len(df)==0:print('no new statcast rows');return 0
  df=df[pd.to_datetime(df.game_date).dt.year==yr]
  pa,pg=compact(df)
  if len(pa)==0:return 0
  P,G=f'data/cache/pa_{yr}.parquet',f'data/cache/pg_{yr}.parquet'
  opa=pd.read_parquet(P);opg=pd.read_parquet(G)
  pks=set(pa.pk)
  opa=pd.concat([opa[~opa.pk.isin(pks)],pa],ignore_index=True);opg=pd.concat([opg[~opg.pk.isin(pks)],pg],ignore_index=True)
  opa.to_parquet(P,index=False);opg.to_parquet(G,index=False);print('statcast merged games',len(pks),'PA',len(pa));return len(pks)
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 4)
