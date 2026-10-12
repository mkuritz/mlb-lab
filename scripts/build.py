"""MLB Lab daily build: slate selection, live HR Score + K projections, odds, exports. $0: statsapi, Savant, Open-Meteo, Kalshi public, DK via Bet Lab's budgeted pull."""
import json,os,sys,math,urllib.request,datetime as dt,unicodedata,re,time
import pandas as pd,numpy as np
sys.path.insert(0,os.path.dirname(__file__))
from features import *
import hr_model,k_model,people,career
from fetch_sched import games as sched_games
from scipy.stats import nbinom
from sklearn.linear_model import LogisticRegression,PoissonRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
D='data';LOG=[]
def log(*a):s=' '.join(map(str,a));print(s);LOG.append(s)
def get(u,t=30):return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'mlb-lab'}),timeout=t))
def clean(o):
  if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
  if isinstance(o,(list,tuple)):return [clean(v) for v in o]
  if isinstance(o,(np.integer,)):return int(o)
  if isinstance(o,(float,np.floating)):return None if (math.isnan(o) or math.isinf(o)) else float(o)
  if o is pd.NaT:return None
  return o
def W(n,o):o=clean(o);json.dump(o,open(f'{D}/{n}','w'),separators=(',',':'),allow_nan=False,default=lambda x:None if x!=x else float(x) if isinstance(x,(np.floating,)) else int(x) if isinstance(x,np.integer) else str(x))
def norm(s):s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower();s=re.sub(r'[^a-z ]','',s);return re.sub(r'\b(jr|sr|ii|iii)\b','',s).strip()
def r(x,n=3):
  try:
    return None if x is None or (isinstance(x,float) and math.isnan(x)) else round(float(x),n)
  except Exception:return None
NOW=dt.datetime.now(dt.timezone.utc);TODAY=NOW.astimezone(ET).date();YR=TODAY.year

# ---------- 1. refresh schedule + statcast ----------
def refresh_sched():
  s=json.load(open(f'{C}/sched_{YR}.json'))
  fresh=sched_games(TODAY-dt.timedelta(days=5),TODAY+dt.timedelta(days=7))
  m={g['pk']:g for g in s};m.update({g['pk']:g for g in fresh})
  s=sorted(m.values(),key=lambda g:(g['date'],g['start']));json.dump(s,open(f'{C}/sched_{YR}.json','w'));return pd.DataFrame(s)
def pick_slate(S):
  """today if any game today; else next scheduled date (<=7d); else latest completed date."""
  live=S[S.status!='Postponed']
  t=live[live.date==str(TODAY)]
  if len(t):return str(TODAY),'today'
  nxt=live[(live.date>str(TODAY))&(live.date<=str(TODAY+dt.timedelta(days=7)))]
  if len(nxt):return nxt.date.min(),'next'
  done=live[(live.date<str(TODAY))&(live.status=='Final')]
  return (done.date.max(),'latest_completed') if len(done) else (None,'none')

# ---------- 2. lineups ----------
def lineups(pk):
  try:
    b=get(f'https://statsapi.mlb.com/api/v1/game/{pk}/boxscore')
    out={}
    for side,h in (('home',1),('away',0)):
      bo=b['teams'][side].get('battingOrder') or []
      out[h]=[int(x) for x in bo[:9]]
    return out
  except Exception as e:log('lineup',pk,e);return {}
def projected_lineup(pa,s,team):
  """last game's starting nine for this team (from Statcast PA order)."""
  m=pa.merge(s[['pk','home','away','date']],on='pk');m['bteam']=np.where(m.h==1,m.home,m.away)
  m=m[m.bteam==team]
  if not len(m):return []
  last=m[m.date==m.date.max()];sp=lineup_spots(last);sp=sp[sp.spot>0].sort_values('spot')
  return sp.b.astype(int).tolist()

# ---------- 3. weather ----------
def forecast(g):
  try:
    u=f"https://api.open-meteo.com/v1/forecast?latitude={g['lat']}&longitude={g['lon']}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation_probability,weather_code&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC&forecast_days=10&past_days=3"
    h=get(u)['hourly'];k=str(g['start'])[:13];i=[t[:13] for t in h['time']].index(k)
    return dict(temp=h['temperature_2m'][i],hum=h['relative_humidity_2m'][i],wmph=h['wind_speed_10m'][i],wdir=h['wind_direction_10m'][i],pop=h['precipitation_probability'][i],code=h['weather_code'][i],src='Open-Meteo forecast')
  except Exception as e:log('forecast',g.get('venue'),e);return None
def env_for(g):
  wx=g.get('wx') if isinstance(g.get('wx'),dict) else {}
  cond=wx.get('condition');fc=forecast(g) or {}
  roof=g.get('roof');closed=None;roof_note=''
  if roof=='Dome':closed=True;roof_note='Fixed dome'
  elif cond in CLOSED:closed=True;roof_note='Roof closed (MLB game-day report)'
  elif cond and roof=='Retractable':closed=False;roof_note='Roof open (MLB game-day report)'
  elif roof=='Retractable':
    t=fc.get('temp');closed=bool((t is not None and t<60) or (fc.get('pop') or 0)>=40);roof_note=('Estimate: roof likely closed' if closed else 'Estimate: roof likely open')+' (no MLB report yet; based on forecast temp/rain)'
  else:closed=False;roof_note='Open-air park'
  az=g.get('az');temp=pd.to_numeric(wx.get('temp'),errors='coerce') if wx.get('temp') else fc.get('temp')
  mph,comp=wind_parse(wx.get('wind')) if wx.get('wind') else (fc.get('wmph'),None)
  wsrc='MLB game-day report' if wx.get('wind') else fc.get('src')
  if comp is None and fc.get('wdir') is not None and az is not None:
    toward=(fc['wdir']+180)%360;comp=math.cos(math.radians(toward-az))
  wout=0.0 if closed else (mph*comp if mph is not None and comp is not None else 0.0)
  return dict(temp=r(temp if not closed else 72,0),temp_out=r(temp,0),hum=r(fc.get('hum') if not closed else 50,0),wmph=r(mph,0),wdir=fc.get('wdir'),wcomp=r(comp,2),wout=r(wout,1),closed=int(bool(closed)),
    roof=roof,roof_note=roof_note,az=az,cond=cond,pop=fc.get('pop'),code=fc.get('code'),wsrc=wsrc)

# ---------- 4. markets ----------
def american_to_p(o):
  o=float(o);return 100/(o+100) if o>0 else -o/(-o+100)
def dk_props():
  try:
    j=get('https://mkuritz.github.io/bet-lab/data/mlb_dk_props.json');return j
  except Exception as e:log('dk props unavailable',e);return {}
def kalshi(series):
  out=[];cur=''
  try:
    for _ in range(20):
      j=get(f"https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker={series}&status=open&limit=1000"+(f"&cursor={cur}" if cur else ''))
      out+=j.get('markets',[]);cur=j.get('cursor')
      if not cur:break
  except Exception as e:log('kalshi',series,e)
  res={}
  for m in out:
    nm=(m.get('yes_sub_title') or '').split(':')[0];k=m.get('floor_strike')
    b=float(m.get('yes_bid_dollars') or 0);a=float(m.get('yes_ask_dollars') or 0)
    if a<=0 or b<=0 or a-b>0.08:continue
    res.setdefault(norm(nm),{})[k]=dict(mid=round((a+b)/2,3),bid=b,ask=a,ticker=m['ticker'],ev=m.get('event_ticker'))
  return res

# ---------- 5. models ----------
def fit_hr():
  A=pd.read_parquet(f'{C}/hrF_2025.parquet') if os.path.exists(f'{C}/hrF_2025.parquet') else hr_model.build(2025)
  B=hr_model.build(YR)
  tr=pd.concat([A,B]);tr=tr[(tr.spot>0)].dropna(subset=hr_model.FEATS)
  m=make_pipeline(StandardScaler(),LogisticRegression(C=0.5,max_iter=2000)).fit(tr[hr_model.FEATS],tr.y)
  return m,B
def fit_k():
  A=pd.read_parquet(f'{C}/kF_2025.parquet') if os.path.exists(f'{C}/kF_2025.parquet') else k_model.build(2025)
  B=k_model.build(YR);tr=pd.concat([A,B]).dropna(subset=k_model.KFEATS+['K'])
  m=make_pipeline(StandardScaler(),PoissonRegressor(alpha=1e-3,max_iter=1000)).fit(tr[k_model.KFEATS],tr.K)
  mu=m.predict(tr[k_model.KFEATS]);a=max(1e-3,float(np.mean(((tr.K-mu)**2-mu))/np.mean(mu**2)))
  return m,a,B
def pge(mu,a,k):n=1/a;p=n/(n+mu);return float(1-nbinom.cdf(k-1,n,p))

def main():
  os.makedirs(D,exist_ok=True)
  S=refresh_sched()
  try:
    import update_statcast;update_statcast.run(5,YR)
  except Exception as e:log('statcast update skipped',e)
  day,mode=pick_slate(S)
  meta=dict(updated=NOW.isoformat(timespec='seconds'),updatedET=NOW.astimezone(ET).strftime('%b %-d, %Y %-I:%M %p ET'),today=str(TODAY),slate_date=day,slate_mode=mode,season=YR,log=LOG)
  if not day:W('meta.json',meta);return
  G=S[(S.date==day)&(S.status!='Postponed')].copy()
  pa=load_pa(YR);pg=load_pg(YR);P=people.ensure(set(pa.b)|set(pa.p)|set(G.hpp.dropna())|set(G.app.dropna()))
  hrm,HB=fit_hr();km,ka,KB=fit_k()
  bt=json.load(open(f'{D}/backtest_hr.json')) if os.path.exists(f'{D}/backtest_hr.json') else {}
  qs=json.load(open(f'{C}/hr_quantiles.json'))
  dk=dk_props();khr=kalshi('KXMLBHR');kks=kalshi('KXMLBKS')
  games=[];hr_rows=[];k_rows=[]
  for g in G.to_dict('records'):
    env=env_for(g);lu=lineups(g['pk']) if mode!='latest_completed' or True else {}
    final=g['status']=='Final'
    starters={1:g.get('hpp'),0:g.get('app')}
    gi=dict(pk=g['pk'],date=g['date'],start=g['start'],status=g['status'],home=g['home'],away=g['away'],homeName=g['homeName'],awayName=g['awayName'],homeId=g['homeId'],awayId=g['awayId'],
      venue=g['venue'],series=g.get('series'),seriesGame=g.get('seriesGame'),desc=g.get('desc'),score=[g.get('as_'),g.get('hs')],env=env,
      sp={'home':starters[1],'away':starters[0]},lineup_status={})
    for h in (1,0):
      team=g['home'] if h else g['away'];opp=g['away'] if h else g['home']
      ids=lu.get(h) or [];status='confirmed' if ids else 'projected'
      if not ids:ids=projected_lineup(pa,S,team)
      gi['lineup_status']['home' if h else 'away']=status
      p=starters[0 if h else 1];p=int(p) if p==p and p is not None else None
      pt=(P.get(str(p),{}).get('thr') if p else None) or 'R'
      for spot,b in enumerate(ids,1):
        bats=P.get(str(b),{}).get('bats') or 'R';st=('L' if pt=='R' else 'R') if bats=='S' else bats
        hr_rows.append(dict(pk=g['pk'],d=day,b=b,h=h,spot=spot,p=p if p else np.nan,pt=pt,st=st,venueId=g['venueId'],team=team,opp=opp,lu=status,
          temp=env['temp'],wout=env['wout'],hum=env['hum'],closed=env['closed']))
      if p:k_rows.append(dict(pk=g['pk'],d=day,p=p,oh=h,pt=pt,team=opp,opp=team))
    games.append(gi)
  T=pd.DataFrame(hr_rows)
  if len(T):
    F=hr_model.build(YR,targets=T.drop(columns=['team','opp','lu']))
    LG=F.attrs.get('LG',{})
    for c,v in (('p_hr',0.031),('p_brl',0.083),('p_fb',0.55),('p_split',0),('bvp',0),('split_hr',0),('team_hr',1)):F[c]=F[c].fillna(v)
    F=F.merge(T[['pk','b','team','opp','lu']],on=['pk','b'],how='left')
    F['p_hr_model']=hrm.predict_proba(F[hr_model.FEATS])[:,1]
  # actual results for completed games
  done=pa[pa.d==day].groupby('b').agg(hr=('hr','sum'),npa=('hr','size')) if len(pa) else pd.DataFrame()
  # coefficient-based drivers (standardized contributions)
  sc=hrm[0];co=hrm[-1].coef_[0]
  LAB={'b_hr':'HR rate','b_brl':'Barrel%','b_ev':'Exit velo','b_xiso':'xISO','t_hr30':'30-day HR trend','t_hr14':'14-day HR trend','t_hr7':'7-day HR trend','t_brl14':'14-day barrel trend','t_brl30':'30-day barrel trend','split_hr':'Handedness split','p_hr':'Pitcher HR allowed','p_brl':'Pitcher barrels allowed','p_fb':'Pitcher fastball mix','p_split':'Pitcher split vs this hand','team_hr':'Opp. staff HR allowed','bvp':'BvP history','pf':'Park HR factor','home':'Home/away','temp':'Temperature','wout':'Wind (out = +)','hum':'Humidity','closed':'Roof closed','lexp_pa':'Expected PAs','spot_top':'Top-5 lineup spot'}
  out=[]
  for x in (F.to_dict('records') if len(T) else []):
    z=(np.array([x[f] for f in hr_model.FEATS])-sc.mean_)/sc.scale_*co
    drv=sorted([(LAB[f],float(v)) for f,v in zip(hr_model.FEATS,z)],key=lambda t:-abs(t[1]))[:5]
    p=float(x['p_hr_model']);score=int(np.clip(np.searchsorted(qs,p)+1,1,99))
    nm=P.get(str(int(x['b'])),{}).get('n','');kn=khr.get(norm(nm),{}).get(0.5)
    dko=(dk.get('hr') or {}).get(norm(nm))
    mk=None
    if dko:mk=dict(src='DraftKings',odds=dko['odds'],implied=r(american_to_p(dko['odds']),3),line=dko.get('line',0.5),pulled=dk.get('pulled'))
    elif kn:mk=dict(src='Kalshi',implied=kn['mid'],bid=kn['bid'],ask=kn['ask'],ticker=kn['ticker'])
    res=None
    if int(x['b']) in done.index:res=dict(hr=int(done.loc[int(x['b'])].hr),pa=int(done.loc[int(x['b'])].npa))
    pn=P.get(str(int(x['p'])),{}).get('n') if x['p']==x['p'] else None
    out.append(dict(id=int(x['b']),name=nm,team=x['team'],opp=x['opp'],pk=int(x['pk']),spot=int(x['spot']),lineup=x['lu'],bats=x['st'],home=int(x['h']),
      p_hr=r(p,4),score=score,market=mk,edge=r(p-mk['implied'],4) if mk else None,
      pitcher=dict(id=int(x['p']) if x['p']==x['p'] else None,name=pn,throws=x['pt'],hr_rate=r(x['p_hr'],4),brl=r(x['p_brl'],3),fb=r(x['p_fb'],3)),
      feats=dict(hr_rate=r(x['b_hr'],4),barrel=r(x['b_brl'],3),ev=r(x['b_ev'],1),xiso=r(x['b_xiso'],3),t7=r(x['t_hr7'],2),t14=r(x['t_hr14'],2),t30=r(x['t_hr30'],2),split=r(x['split_hr'],3),pf=r(x['pf'],3),temp=x['temp'],wout=x['wout'],hum=x['hum'],closed=x['closed'],exp_pa=r(x['exp_pa'],2)),
      bvp=dict(pa=int(x['bvp_pa']),hr=int(x['bvp_hr']),xwoba=r(x['bvp_xwoba'],3),adj=r(x['bvp'],3),note='2024-26 Statcast, vs today\'s listed starter; shrunk toward his own rate (60-PA prior)'),
      drivers=[dict(f=a,v=r(b,3)) for a,b in drv],result=res))
  out.sort(key=lambda o:-o['p_hr'])
  # K projections
  K=pd.DataFrame(k_rows);kout=[]
  if len(K):
    KF=k_model.build(YR,targets=K.drop(columns=['team','opp']))
    KF=KF.merge(K[['pk','p','team','opp']],on=['pk','p'],how='left');KF['mu']=km.predict(KF[k_model.KFEATS])
    for x in KF.to_dict('records'):
      nm=P.get(str(int(x['p'])),{}).get('n','');mu=float(x['mu'])
      ladder={k:r(pge(mu,ka,k),3) for k in range(3,13)}
      kl=kks.get(norm(nm),{});kal={int(math.ceil(k)):v['mid'] for k,v in kl.items()} if kl else {}
      dko=(dk.get('k') or {}).get(norm(nm))
      line=None;mk=None
      if dko:line=dko['line'];mk=dict(src='DraftKings',line=line,over=dko.get('over'),under=dko.get('under'),implied_over=r(american_to_p(dko['over']),3) if dko.get('over') else None,pulled=dk.get('pulled'))
      elif kal:
        kk=min(kal,key=lambda k:abs(kal[k]-0.5));line=kk-0.5;mk=dict(src='Kalshi',line=line,implied_over=kal[kk],ladder=kal)
      pov=r(pge(mu,ka,int(math.floor(line))+1),3) if line is not None else None
      row=pg[(pg.p==int(x['p']))&(pg.d==day)];act=int(row.K.iloc[0]) if len(row) else None
      hist=pg[(pg.p==int(x['p']))&(pg.start==1)&(pg.d<day)].sort_values('d').tail(6)
      kout.append(dict(id=int(x['p']),name=nm,team=x['team'],opp=x['opp'],pk=int(x['pk']),throws=x['pt'],proj_k=r(mu,2),exp_bf=r(x['exp_bf'],1),exp_ip=r(x['exp_bf']/4.25,1),
        p10=ladder[10],ladder=ladder,line=line,p_over=pov,market=mk,edge=r(pov-mk['implied_over'],3) if (mk and pov is not None and mk.get('implied_over')) else None,
        feats=dict(k_rate=r(x['k_rate'],3),csw=r(x['csw'],3),whiff=r(x['whiff'],3),form=r(x['form_k'],3),opp_k=r(x['opp_k'],3),ump_k=r(x['ump_k'],3),park_k=r(x['park_k'],3)),
        fatigue=dict(rest=r(x['rest'],0),last_np=r(x['last_np'],0),last_ip=r(x['last_ip'],1),cum_ip=r(x['cum_ip'],1),career_hi=r(x['career_hi'],1),workload=r(x['workload'],2),velo_d=r(x['velo_d'],2),velo_d3=r(x['velo_d3'],2),spin_d=r(x['spin_d']*100,0)),
        last_starts=[dict(d=h.d,ip=r(h.outs/3,1),np=int(h.np),K=int(h.K),fbv=r(h.fbv,1)) for h in hist.itertuples()],result_k=act))
    kout.sort(key=lambda o:-o['proj_k'])
  king=max(kout,key=lambda o:(o['proj_k'],o['p10'])) if kout else None
  meta.update(n_games=len(games),n_batters=len(out),king=king['id'] if king else None,
    dk_status=dk.get('status','unavailable') if dk else 'unavailable',kalshi=dict(hr=len(khr),k=len(kks)),
    note={'today':f'Live slate for {day}','next':f'No MLB games today ({TODAY}). Showing the next slate: {day}','latest_completed':f'No upcoming games within 7 days. Showing the latest completed slate: {day}'}[mode])
  W('slate.json',dict(date=day,mode=mode,games=games))
  W('hr_scores.json',dict(date=day,mode=mode,generated=meta['updated'],model='logistic regression, walk-forward backtested',units='p_hr = estimated probability of 1+ HR in the game; score = percentile (1-99) of p_hr among 2026 batter-games',players=out))
  W('k_projections.json',dict(date=day,mode=mode,generated=meta['updated'],model='Poisson GLM + negative-binomial spread (alpha=%.3f)'%ka,king=king,pitchers=kout))
  # postseason workload table
  post=pg[(pg.start==1)&(pg.d>=f'{YR}-09-01')].p.unique()
  teams_alive=set(G.home)|set(G.away)
  wk=[]
  for pid in post:
    a=pg[pg.p==pid].sort_values('d');st=a[a.start==1]
    if len(st)<3:continue
    hi=career.prior_high(json.load(open(career.P)),pid,YR)
    reg=a[a['gt']=='R'];h1=st[(st['gt']=='R')&(st.d<f'{YR}-07-01')];l6=st[st['gt']=='R'].tail(6)
    wk.append(dict(id=int(pid),name=P.get(str(int(pid)),{}).get('n'),ip=r(a.outs.sum()/3,1),reg_ip=r(reg.outs.sum()/3,1),career_hi=hi,ratio=r((a.outs.sum()/3)/hi,2) if hi else None,
      last=st.d.max(),rest=(TODAY-dt.date.fromisoformat(st.d.max())).days,last_np=int(st['np'].iloc[-1]),fbv_h1=r(h1.fbv.mean(),2),fbv_l6=r(l6.fbv.mean(),2),
      k_h1=r(h1.K.sum()/max(h1.bf.sum(),1),3),k_l6=r(l6.K.sum()/max(l6.bf.sum(),1),3),csw_h1=r(h1.csw.sum()/max(h1['np'].sum(),1),3),csw_l6=r(l6.csw.sum()/max(l6['np'].sum(),1),3),
      starts=[dict(d=x.d,gt=x.gt,ip=r(x.outs/3,1),np=int(x.np),K=int(x.K),fbv=r(x.fbv,1)) for x in st.tail(12).itertuples()]))
  wk=[w for w in wk if w['last']>=f'{YR}-09-20']
  wk.sort(key=lambda w:-(w['ratio'] or 0))
  W('pitchers.json',dict(generated=meta['updated'],note='Starters with 3+ starts and a start since Sep 20. Ratio = innings this year (incl. postseason) / prior-season MLB career high.',pitchers=wk))
  meta['log']=LOG[-40:];W('meta.json',meta)
  # history snapshot (for grading later)
  os.makedirs(f'{D}/history',exist_ok=True)
  if mode in('today','next'):W(f'history/{day}.json',dict(hr=[dict(id=o['id'],name=o['name'],p=o['p_hr'],score=o['score'],mk=o['market']) for o in out[:60]],k=[dict(id=o['id'],name=o['name'],mu=o['proj_k'],p10=o['p10'],line=o['line']) for o in kout],saved=meta['updated']))
  log('built',day,mode,len(out),'batters',len(kout),'starters')
if __name__=='__main__':main()
