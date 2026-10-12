import pandas as pd,numpy as np,json,sys,unicodedata,re
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss,log_loss
sys.path.insert(0,'scripts');from hr_model import FEATS
def mk(kind):
  if kind=='logit':return make_pipeline(StandardScaler(),LogisticRegression(C=0.5,max_iter=2000))
  return HistGradientBoostingClassifier(max_iter=250,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=200,l2_regularization=1.0)
def norm(s):s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower();s=re.sub(r'[^a-z ]','',s);return re.sub(r'\b(jr|sr|ii|iii)\b','',s).strip()
def calib(y,p,n=10):
  q=pd.qcut(p,n,labels=False,duplicates='drop');d=pd.DataFrame(dict(y=y,p=p,q=q)).groupby('q').agg(pred=('p','mean'),obs=('y','mean'),n=('y','size'))
  return [dict(pred=round(r.pred,4),obs=round(r.obs,4),n=int(r.n)) for r in d.itertuples()]
def metrics(y,p):return dict(brier=round(brier_score_loss(y,p),5),logloss=round(log_loss(y,np.clip(p,1e-4,1-1e-4)),5),n=int(len(y)),mean_pred=round(float(np.mean(p)),4),obs=round(float(np.mean(y)),4))
A=pd.read_parquet('/workspace/mlbraw/hrF_2025.parquet');B=pd.read_parquet('/workspace/mlbraw/hrF_2026.parquet')
A=A[(A['gt']=='R')&(A.spot>0)].dropna(subset=FEATS);B=B[(B['gt']=='R')&(B.spot>0)].dropna(subset=FEATS)
# model selection on 2025 only (no 2026 info)
cut='2025-07-01';sel={}
for k in ('logit','gbm'):
  m=mk(k).fit(A[A.d<cut][FEATS],A[A.d<cut].y);p=m.predict_proba(A[A.d>=cut][FEATS])[:,1];sel[k]=metrics(A[A.d>=cut].y,p)
print('selection 2025H2',sel)
# walk-forward 2026, weekly refit
B=B.sort_values('d');B['wk']=pd.to_datetime(B.d).dt.to_period('W-SUN').astype(str)
preds={k:pd.Series(index=B.index,dtype=float) for k in ('logit','gbm')};base=pd.Series(index=B.index,dtype=float)
for wk,g in B.groupby('wk'):
  d0=g.d.min();tr=pd.concat([A,B[B.d<d0]])
  for k in preds:preds[k].loc[g.index]=mk(k).fit(tr[FEATS],tr.y).predict_proba(g[FEATS])[:,1]
  prior26=B[B.d<d0];base.loc[g.index]=prior26.y.mean() if len(prior26)>2000 else A.y.mean()
B['p_logit']=preds['logit'];B['p_gbm']=preds['gbm'];B['p_base']=base
res={'selection_2025H2':sel,'walkforward_2026':{}}
for k in ('logit','gbm','base'):res['walkforward_2026'][k]=metrics(B.y,B['p_'+k])
chosen=min(('logit','gbm'),key=lambda k:sel[k]['logloss']);res['chosen']=chosen
p=B['p_'+chosen]
res['calibration']=calib(B.y,p,10)
dec=pd.qcut(p,10,labels=False);res['top_decile_hit']=round(float(B.y[dec==9].mean()),4);res['bottom_decile_hit']=round(float(B.y[dec==0].mean()),4)
res['lift_top_decile']=round(res['top_decile_hit']/float(B.y.mean()),3)
bb=res['walkforward_2026']['base']['brier'];res['brier_skill_vs_league']=round(1-res['walkforward_2026'][chosen]['brier']/bb,4)
res['logloss_improve_vs_league']=round(res['walkforward_2026']['base']['logloss']-res['walkforward_2026'][chosen]['logloss'],5)
# market comparison (Kalshi pre-game mid, sampled every 3rd game)
try:
  K=pd.DataFrame(json.load(open('/workspace/mlbraw/kalshi_hr_hist.json')));K=K[K.p.notna()].rename(columns={'p':'mkt'})
  K['d']=pd.to_datetime(K.t,unit='s',utc=True).dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d');K['nm']=K.name.map(norm)
  ppl=json.load(open('data/cache/people.json'));B['nm']=B.b.astype(int).astype(str).map(lambda i:norm(ppl.get(i,{}).get('n','')))
  M=B.merge(K[['d','nm','mkt','res']].drop_duplicates(['d','nm']),on=['d','nm'],how='inner')
  M=M[M.res.isin(['yes','no'])]
  res['market']=dict(n=int(len(M)),games_note='Kalshi 1+ HR markets, pre-game bid/ask mid (spread<=6c), every 3rd game sampled',
    ours=metrics(M.y,M['p_'+chosen]),kalshi=metrics(M.y,M.mkt),agree_rate_label=None,
    blend=metrics(M.y,0.5*M.mkt+0.5*M['p_'+chosen]))
  M['edge']=M['p_'+chosen]-M.mkt
  e=M[M.edge>0.03];res['market']['edge_bets']=dict(n=int(len(e)),hit=round(float(e.y.mean()),4) if len(e) else None,avg_price=round(float(e.mkt.mean()),4) if len(e) else None,
     roi_per_1=round(float((e.y/e.mkt-1).mean()),4) if len(e) else None)
  res['market']['calib_kalshi']=calib(M.y,M.mkt,8);res['market']['calib_ours']=calib(M.y,M['p_'+chosen],8)
except Exception as x:print('market',x);res['market']=None
# monthly
B['m']=B.d.str[:7];res['monthly']=[dict(m=m,**metrics(g.y,g['p_'+chosen]),base_brier=round(brier_score_loss(g.y,g.p_base),5)) for m,g in B.groupby('m')]
# coefficient view from final logistic fit on everything
lm=mk('logit').fit(pd.concat([A,B])[FEATS],pd.concat([A,B]).y);res['logit_coefs']=dict(zip(FEATS,[round(float(c),4) for c in lm[-1].coef_[0]]))
B[['pk','d','b','y','spot','p_'+chosen,'p_base']].to_parquet('/workspace/mlbraw/hr_bt_preds.parquet')
json.dump(res,open('data/backtest_hr.json','w'),indent=1);print(json.dumps({k:v for k,v in res.items() if k not in('calibration','monthly')},indent=1))
