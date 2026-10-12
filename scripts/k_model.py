import pandas as pd,numpy as np,json,sys,os
from features import *
import career
KFEATS=['k_rate','csw','whiff','form_k','opp_k','ump_k','park_k','lexp_bf','rest','last_np','last_ip','workload','velo_d','velo_d3','spin_d','home']
def starts_hist(pg):
  return pg[pg.start==1][['pk','d','gt','p','bh','pt','K','bf','np','outs','fbv','spin','csw','whf','sw']].rename(columns={'bh':'oh'})
def build(y,targets=None,live_pa=None,live_pg=None):
  pa=load_pa(y) if live_pa is None else live_pa;pg=load_pg(y) if live_pg is None else live_pg
  s=load_sched(y);prev=[load_pa(x) for x in (y-1,y-2) if os.path.exists(f'{C}/pa_{x}.parquet')];pgp=[load_pg(x) for x in (y-1,) if os.path.exists(f'{C}/pg_{x}.parquet')]
  pp=prev[0] if prev else pa.iloc[:0]
  hist=targets is None
  T=starts_hist(pg) if hist else targets.copy()   # oh = 1 if opponent batters are home team (pitcher is away)
  T=T.merge(s[['pk','home','away','venueId','ump']],on='pk',how='left')
  T['oteam']=np.where(T.oh==1,T.home,T.away);T['home']=1-T.oh
  ref=pp if len(pp) else pa;LGK=ref.k.mean()
  pgr=pgp[0] if pgp else pg;LGcsw=pgr.csw.sum()/pgr.np.sum();LGwh=pgr.whf.sum()/pgr.sw.sum()
  pa=pa.assign(one=1)
  a=pp.assign(one=1).groupby('p')[['k','one']].sum() if len(pp) else None
  PK=((a.k+300*LGK)/(a.one+300)) if a is not None else pd.Series(dtype=float)
  kc=daily_cum(pa,['p'],['one','k'],targets=T);T=T.merge(kc,on=['p','d'],how='left')
  T['k_rate']=shr(T.c_k.fillna(0),T.c_one.fillna(0),T.p.map(PK).fillna(LGK),150);T=T.drop(columns=['c_k','c_one'])
  if len(pgp):
    q=pgp[0].groupby('p')[['csw','np','whf','sw']].sum();PC=(q.csw+600*LGcsw)/(q.np+600);PW=(q.whf+300*LGwh)/(q.sw+300)
  else:PC=PW=pd.Series(dtype=float)
  cc=daily_cum(pg.rename(columns={'np':'npi'}),['p'],['csw','npi','whf','sw','outs'],targets=T)
  T=T.merge(cc,on=['p','d'],how='left')
  T['csw']=shr(T.c_csw.fillna(0),T.c_npi.fillna(0),T.p.map(PC).fillna(LGcsw),600);T['whiff']=shr(T.c_whf.fillna(0),T.c_sw.fillna(0),T.p.map(PW).fillna(LGwh),300)
  T['cum_ip']=T.c_outs.fillna(0)/3;T=T.drop(columns=[c for c in T if c.startswith('c_')])
  # start sequence features (previous starts only)
  S=starts_hist(pg).sort_values(['p','d']);
  if not hist:S=pd.concat([S,T[['pk','d','p']].assign(K=np.nan,bf=np.nan,np=np.nan,outs=np.nan,fbv=np.nan,spin=np.nan)]).drop_duplicates(['p','d'],keep='first').sort_values(['p','d'])
  g=S.groupby('p')
  S['f3k']=g.K.transform(lambda x:x.shift().rolling(3,min_periods=1).sum());S['f3bf']=g.bf.transform(lambda x:x.shift().rolling(3,min_periods=1).sum())
  S['bf5']=g.bf.transform(lambda x:x.shift().rolling(5,min_periods=1).mean());S['n5']=g.bf.transform(lambda x:x.shift().rolling(5,min_periods=1).count())
  S['last_np']=g['np'].shift();S['last_ip']=g.outs.shift()/3
  S['v_szn']=g.fbv.transform(lambda x:x.shift().expanding().mean());S['v_last']=g.fbv.shift();S['v3']=g.fbv.transform(lambda x:x.shift().rolling(3,min_periods=1).mean())
  S['s_szn']=g.spin.transform(lambda x:x.shift().expanding().mean());S['s3']=g.spin.transform(lambda x:x.shift().rolling(3,min_periods=1).mean())
  T=T.merge(S[['p','d','f3k','f3bf','bf5','n5','last_np','last_ip','v_szn','v_last','v3','s_szn','s3']],on=['p','d'],how='left')
  T['form_k']=shr(T.f3k.fillna(0),T.f3bf.fillna(0),T.k_rate,40)-T.k_rate
  T['exp_bf']=shr(T.bf5.fillna(0)*T.n5.fillna(0),T.n5.fillna(0),22.0,2);T['lexp_bf']=np.log(T.exp_bf)
  T['velo_d']=(T.v_last-T.v_szn).fillna(0);T['velo_d3']=(T.v3-T.v_szn).fillna(0);T['spin_d']=((T.s3-T.s_szn)/100).fillna(0)
  T['last_np']=T.last_np.fillna(85);T['last_ip']=T.last_ip.fillna(5)
  # days rest (any appearance)
  ap=pg[['p','d']].drop_duplicates()
  if not hist:ap=pd.concat([ap,T[['p','d']]]).drop_duplicates()
  ap=ap.sort_values(['p','d']);ap['rest']=pd.to_datetime(ap.d).groupby(ap.p).diff().dt.days
  T=T.merge(ap,on=['p','d'],how='left');T['rest']=T.rest.fillna(10).clip(3,12)
  # workload vs prior-season career high
  CI=career.ensure(T.p.unique()) if not os.environ.get('NO_NET') else json.load(open(career.P))
  T['career_hi']=[career.prior_high(CI,p,y) for p in T.p];T['workload']=T.cum_ip/T.career_hi.fillna(60).clip(lower=60)
  # opponent K% vs hand
  pa2=pa.merge(s[['pk','home','away']],on='pk',how='left');pa2['bteam']=np.where(pa2.h==1,pa2.home,pa2.away)
  oc=daily_cum(pa2,['bteam','pt'],['one','k'],targets=T.rename(columns={'oteam':'bteam'}))
  T=T.merge(oc.rename(columns={'bteam':'oteam'}),on=['oteam','pt','d'],how='left');T['opp_k']=shr(T.c_k.fillna(0),T.c_one.fillna(0),LGK,500)/LGK;T=T.drop(columns=['c_k','c_one'])
  # umpire
  allpa=pd.concat([x[['pk','d','k']] for x in prev]+[pa[['pk','d','k']]]).assign(one=1)
  us=pd.concat([load_sched(x)[['pk','ump']] for x in (y,y-1,y-2) if os.path.exists(f'{C}/sched_{x}.json')]).drop_duplicates('pk')
  allpa=allpa.merge(us,on='pk',how='inner').dropna(subset=['ump'])
  uc=daily_cum(allpa,['ump'],['one','k'],targets=T.dropna(subset=['ump']))
  T=T.merge(uc,on=['ump','d'],how='left');T['ump_k']=shr(T.c_k.fillna(0),T.c_one.fillna(0),LGK,2000)/LGK;T=T.drop(columns=['c_k','c_one'])
  sh=pd.concat([load_sched(x) for x in (y-1,y-2) if os.path.exists(f'{C}/sched_{x}.json')])
  PF=park_factors(pd.concat(prev),sh,col='k',k=4000) if prev else {}
  T['park_k']=T.venueId.map(PF).fillna(1.0)
  return T
if __name__=='__main__':
  for y in (2025,2026):
    F=build(y);F.to_parquet(f'/workspace/mlbraw/kF_{y}.parquet');print(y,len(F),F.K.mean());print(F[KFEATS].describe().T[['mean','std','min','max']])
