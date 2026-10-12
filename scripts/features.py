"""Walk-forward feature builders for MLB Lab. Every feature for a game on date D uses only data from dates < D."""
import pandas as pd,numpy as np,json,re,os,math
C='data/cache'
def load_pa(y): return pd.read_parquet(f'{C}/pa_{y}.parquet')
def load_pg(y): return pd.read_parquet(f'{C}/pg_{y}.parquet')
def load_sched(y): return pd.DataFrame(json.load(open(f'{C}/sched_{y}.json')))
WX=None
def wxh():
  global WX
  if WX is None:
    p=f'{C}/wx_games.json'
    WX=json.load(open(p)) if os.path.exists(p) else {}
  return WX
def shr(num,den,prior,k): return (num+k*prior)/(den+k)

def wind_parse(w):
  """statsapi wind '12 mph, Out To CF' -> (mph, out-component -1..1)"""
  if not w:return (np.nan,np.nan)
  m=re.match(r'(\d+)\s*mph,?\s*(.*)',w)
  if not m:return (np.nan,np.nan)
  mph=float(m.group(1));d=m.group(2).lower()
  comp={'out to cf':1,'out to lf':.7,'out to rf':.7,'in from cf':-1,'in from lf':-.7,'in from rf':-.7}.get(d,0.0)
  return (mph,comp)
CLOSED={'Dome','Roof Closed'}
def game_env(s):
  """per game: temp, wind mph, wind_out (mph*component), humidity, roof_closed."""
  rows=[]
  W=wxh()
  for r in s.itertuples():
    wx=r.wx if isinstance(r.wx,dict) else {}
    cond=wx.get('condition');closed=cond in CLOSED or r.roof=='Dome'
    t=pd.to_numeric(wx.get('temp'),errors='coerce');mph,comp=wind_parse(wx.get('wind'))
    h=W.get(str(r.pk))
    hum=h[1] if h else np.nan
    if np.isnan(t) and h:t=h[0]
    if closed:mph,comp,hum=0.0,0.0,50.0
    rows.append(dict(pk=r.pk,temp=t,wmph=mph,wout=(mph*comp) if not np.isnan(mph) else np.nan,hum=hum,closed=int(bool(closed)),venueId=r.venueId))
  return pd.DataFrame(rows)

def daily_cum(df,keys,cols,windows=(),targets=None):
  """df has keys+['d']+cols, aggregated per day. returns per (keys,d) exclusive cumsums and rolling-window sums (closed='left')."""
  g=df.groupby(keys+['d'],as_index=False)[cols].sum()
  if targets is not None:
    t=targets[keys+['d']].drop_duplicates()
    g=pd.concat([g,t.assign(**{c:0 for c in cols})]).groupby(keys+['d'],as_index=False)[cols].sum()
  g['dt']=pd.to_datetime(g.d);g=g.sort_values(keys+['dt']).reset_index(drop=True)
  cs=g.groupby(keys)[cols].cumsum()-g[cols]
  out=g[keys+['d']].copy()
  for c in cols:out['c_'+c]=cs[c].values
  for w in windows:
    rr=g.set_index('dt').groupby(keys)[cols].rolling(f'{w}D',closed='left').sum().reset_index(drop=True).fillna(0)
    for c in cols:out[f'w{w}_'+c]=rr[c].values
  return out

def prior_rates(pa_prev,key,num,den,lg,k2):
  if pa_prev is None or len(pa_prev)==0: return {}
  a=pa_prev.groupby(key)[[num,den]].sum() if num!=den else None
  return ((a[num]+k2*lg)/(a[den]+k2)).to_dict()

def park_factors(pa_hist,sched_hist,col='hr',k=3000):
  m=pa_hist.merge(sched_hist[['pk','venueId']],on='pk')
  lg=m[col].mean();g=m.groupby('venueId')[col].agg(['sum','size'])
  return ((g['sum']+k*lg)/(g['size']+k)/lg).to_dict()

def lineup_spots(pa):
  f=pa.sort_values('ab').groupby(['pk','h','b'],as_index=False).ab.first().sort_values(['pk','h','ab'])
  f['spot']=f.groupby(['pk','h']).cumcount()+1
  f.loc[f.spot>9,'spot']=0
  return f[['pk','h','b','spot']]
