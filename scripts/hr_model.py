import pandas as pd,numpy as np,json,sys
from features import *
FEATS=['b_hr','b_brl','b_ev','b_xiso','t_hr30','t_hr14','t_hr7','t_brl14','t_brl30','split_hr','p_hr','p_brl','p_fb','p_split','team_hr','bvp','pf','home','temp','wout','hum','closed','lexp_pa','spot_top']
def prev_tables(y):
  pr=[load_pa(x) for x in (y-1,y-2) if os.path.exists(f'{C}/pa_{x}.parquet')]
  return pr
def team_cols(pa,s):
  m=pa.merge(s[['pk','home','away','venueId']],on='pk',how='left')
  m['bteam']=np.where(m.h==1,m.home,m.away);m['pteam']=np.where(m.h==1,m.away,m.home);return m
def hist_targets(pa,pg):
  g=pa.groupby(['pk','b'],as_index=False).agg(d=('d','first'),gt=('gt','first'),h=('h','first'),y=('hr','max'),npa=('hr','size'),nhr=('hr','sum'))
  sp=lineup_spots(pa);g=g.merge(sp,on=['pk','h','b'],how='left')
  st=pg[pg.start==1][['pk','p','bh','pt']].rename(columns={'bh':'h'})
  g=g.merge(st,on=['pk','h'],how='left')
  hand=pa.groupby(['pk','b','p'],as_index=False).st.first()
  g=g.merge(hand,on=['pk','b','p'],how='left')
  g['st']=g.st.fillna(g.merge(pa.groupby(['pk','b'],as_index=False).st.first(),on=['pk','b'],how='left',suffixes=('','_x')).st_x)
  return g
def build(y,targets=None,live_pa=None,live_pg=None):
  """y: season. targets: optional live rows (pk,d,b,h,spot,p,pt,st,venueId + env cols). Returns frame with FEATS."""
  pa=load_pa(y) if live_pa is None else live_pa; pg=load_pg(y) if live_pg is None else live_pg
  s=load_sched(y);pa=team_cols(pa,s)
  prev=prev_tables(y);pp=prev[0] if prev else pa.iloc[:0]
  hist=targets is None
  T=hist_targets(pa,pg) if hist else targets.copy()
  T=T.merge(s[['pk','home','away','venueId']].rename(columns={'venueId':'vid'}),on='pk',how='left')
  if 'venueId' not in T:T['venueId']=T.vid
  T['bteam']=np.where(T.h==1,T.home,T.away);T['pteam']=np.where(T.h==1,T.away,T.home)
  # league constants (prior season)
  ref=pp if len(pp) else pa
  LG=dict(hr=ref.hr.mean(),brl=ref.brl.sum()/max(ref.bbe.sum(),1),ev=ref.ev[ref.bbe==1].mean(),
          xiso=((ref.xslg-ref.xba).where(ref.bbe==1,0)).sum()/max((1-ref.bb).sum(),1))
  pa=pa.assign(one=1,evs=pa.ev.where(pa.bbe==1,0).fillna(0),xi=(pa.xslg-pa.xba).where(pa.bbe==1,0).fillna(0),ab=1-pa.bb)
  # priors
  def prior(df,key,num,den,lg,k2):
    a=df.groupby(key)[[num,den]].sum();return ((a[num]+k2*lg)/(a[den]+k2))
  ppx=pp.assign(one=1,evs=pp.ev.where(pp.bbe==1,0).fillna(0),xi=(pp.xslg-pp.xba).where(pp.bbe==1,0).fillna(0),ab=1-pp.bb) if len(pp) else pa.iloc[:0]
  P_hr=prior(ppx,'b','hr','one',LG['hr'],200);P_brl=prior(ppx,'b','brl','bbe',LG['brl'],60)
  P_ev=prior(ppx,'b','evs','bbe',LG['ev'],40) if len(ppx) else pd.Series(dtype=float);P_xi=prior(ppx,'b','xi','ab',LG['xiso'],200)
  Q_hr=prior(ppx,'p','hr','one',LG['hr'],300);Q_brl=prior(ppx,'p','brl','bbe',LG['brl'],100)
  # batter cumulative
  bc=daily_cum(pa,['b'],['one','hr','bbe','brl','evs','xi','ab'],windows=(7,14,30),targets=T)
  T=T.merge(bc,on=['b','d'],how='left')
  T['prior_hr']=T.b.map(P_hr).fillna(LG['hr']);T['prior_brl']=T.b.map(P_brl).fillna(LG['brl'])
  T['b_hr']=shr(T.c_hr,T.c_one,T.prior_hr,200);T['b_brl']=shr(T.c_brl,T.c_bbe,T.prior_brl,60)
  T['b_ev']=shr(T.c_evs,T.c_bbe,T.b.map(P_ev).fillna(LG['ev']),40);T['b_xiso']=shr(T.c_xi,T.c_ab,T.b.map(P_xi).fillna(LG['xiso']),200)
  for w in (7,14,30):T[f't_hr{w}']=shr(T[f'w{w}_hr'],T[f'w{w}_one'],T.b_hr,60)/T.b_hr
  for w in (14,30):T[f't_brl{w}']=shr(T[f'w{w}_brl'],T[f'w{w}_bbe'],T.b_brl,30)-T.b_brl
  T=T.drop(columns=[c for c in T if c.startswith(('c_','w7_','w14_','w30_'))])
  # split vs pitcher hand
  sc=daily_cum(pa,['b','pt'],['one','hr'],targets=T.dropna(subset=['pt']))
  T=T.merge(sc,on=['b','pt','d'],how='left');T['split_hr']=np.log(shr(T.c_hr.fillna(0),T.c_one.fillna(0),T.b_hr,150)/T.b_hr);T=T.drop(columns=['c_hr','c_one'])
  # pitcher
  pc=daily_cum(pa,['p'],['one','hr','bbe','brl'],targets=T.dropna(subset=['p']))
  T=T.merge(pc,on=['p','d'],how='left')
  T['p_hr']=shr(T.c_hr.fillna(0),T.c_one.fillna(0),T.p.map(Q_hr).fillna(LG['hr']),300);T['p_brl']=shr(T.c_brl.fillna(0),T.c_bbe.fillna(0),T.p.map(Q_brl).fillna(LG['brl']),100)
  T=T.drop(columns=[c for c in T if c.startswith('c_')])
  pgx=pg.assign(fbn=pg.fb*pg.np)
  fc=daily_cum(pgx.rename(columns={'np':'npi'}),['p'],['npi','fbn'],targets=T.dropna(subset=['p']))
  T=T.merge(fc,on=['p','d'],how='left');T['p_fb']=shr(T.c_fbn.fillna(0),T.c_npi.fillna(0),0.55,300);T=T.drop(columns=['c_fbn','c_npi'])
  ps=daily_cum(pa,['p','st'],['one','hr'],targets=T.dropna(subset=['p','st']))
  T=T.merge(ps,on=['p','st','d'],how='left');T['p_split']=np.log(shr(T.c_hr.fillna(0),T.c_one.fillna(0),T.p_hr,250)/T.p_hr);T=T.drop(columns=['c_hr','c_one'])
  tc=daily_cum(pa,['pteam'],['one','hr'],targets=T)
  T=T.merge(tc,on=['pteam','d'],how='left');T['team_hr']=shr(T.c_hr.fillna(0),T.c_one.fillna(0),LG['hr'],1500)/LG['hr'];T=T.drop(columns=['c_hr','c_one'])
  # BvP (prior seasons + this season before date)
  allpa=pd.concat([x[['b','p','d','hr','xw','wd']] for x in prev]+[pa[['b','p','d','hr','xw','wd']]]).assign(one=1)
  allpa['xwn']=allpa.xw.where(allpa.wd>0,0).fillna(0)
  bv=daily_cum(allpa,['b','p'],['one','hr','xwn','wd'],targets=T.dropna(subset=['p']))
  T=T.merge(bv,on=['b','p','d'],how='left')
  T['bvp_pa']=T.c_one.fillna(0);T['bvp_hr']=T.c_hr.fillna(0);T['bvp_xwoba']=(T.c_xwn/T.c_wd).where(T.c_wd>0)
  T['bvp']=np.log(shr(T.bvp_hr,T.bvp_pa,T.b_hr,60)/T.b_hr);T=T.drop(columns=[c for c in T if c.startswith('c_')])
  # park
  sh=pd.concat([load_sched(x) for x in (y-1,y-2) if os.path.exists(f'{C}/sched_{x}.json')])
  PF=park_factors(pd.concat(prev),sh) if prev else {}
  T['pf']=T.venueId.map(PF).fillna(1.0)
  T['home']=T.h
  if hist:
    E=game_env(s);T=T.merge(E.drop(columns='venueId'),on='pk',how='left')
  for c,v in (('temp',72),('wout',0),('hum',55),('closed',0)):T[c]=T[c].fillna(v)
  # expected PA by spot (prior season)
  ref2=pp if len(pp) else pa
  sp=lineup_spots(ref2);n=ref2.groupby(['pk','b'],as_index=False).size().merge(sp.drop(columns='h'),on=['pk','b'])
  EXP=n[n.spot>0].groupby('spot')['size'].mean().to_dict()
  T['exp_pa']=T.spot.map(EXP).fillna(3.0);T['lexp_pa']=np.log(T.exp_pa);T['spot_top']=(T.spot.between(1,5)).astype(int)
  T.attrs['LG']={k:float(v) for k,v in LG.items()}
  return T
if __name__=='__main__':
  for y in (2025,2026):
    F=build(y);F.to_parquet(f'/workspace/mlbraw/hrF_{y}.parquet');print(y,len(F),F.y.mean());print(F[FEATS].describe().T[['mean','std','min','max']])
