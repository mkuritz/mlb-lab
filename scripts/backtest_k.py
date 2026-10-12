import pandas as pd,numpy as np,json,sys
from scipy.stats import nbinom,poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingRegressor
sys.path.insert(0,'scripts');from k_model import KFEATS
def mk(k):
  if k=='glm':return make_pipeline(StandardScaler(),PoissonRegressor(alpha=1e-3,max_iter=1000))
  return HistGradientBoostingRegressor(loss='poisson',max_iter=200,learning_rate=0.04,max_leaf_nodes=15,min_samples_leaf=80)
def alpha_mm(y,mu):  # NB2 dispersion by moments
  return max(1e-3,float(np.mean(((y-mu)**2-mu))/np.mean(mu**2)))
def pge(mu,a,k):  # P(K>=k)
  n=1/a;p=n/(n+mu);return 1-nbinom.cdf(k-1,n,p)
def mets(y,mu,a):
  p10=pge(mu,a,10);ll=-np.mean(np.log(np.clip(nbinom.pmf(y,1/a,(1/a)/((1/a)+mu)),1e-9,1)))
  return dict(mae=round(float(np.mean(np.abs(y-mu))),3),rmse=round(float(np.sqrt(np.mean((y-mu)**2))),3),nll=round(float(ll),4),n=int(len(y)),mean_pred=round(float(mu.mean()),3),obs=round(float(y.mean()),3),
    brier10=round(float(np.mean((p10-(y>=10))**2)),5))
A=pd.read_parquet('/workspace/mlbraw/kF_2025.parquet');B=pd.read_parquet('/workspace/mlbraw/kF_2026.parquet')
A=A[A['gt']=='R'].dropna(subset=KFEATS+['K']);B=B[B['gt']=='R'].dropna(subset=KFEATS+['K']).sort_values('d')
cut='2025-07-01';sel={}
for k in ('glm','gbm'):
  m=mk(k).fit(A[A.d<cut][KFEATS],A[A.d<cut].K);mu_tr=m.predict(A[A.d<cut][KFEATS]);a=alpha_mm(A[A.d<cut].K.values,mu_tr)
  sel[k]=mets(A[A.d>=cut].K.values,m.predict(A[A.d>=cut][KFEATS]),a)
print(sel)
chosen=min(sel,key=lambda k:sel[k]['nll'])
B['wk']=pd.to_datetime(B.d).dt.to_period('W-SUN').astype(str)
B['mu']=np.nan;B['a']=np.nan;B['mu_base']=np.nan
for wk,g in B.groupby('wk'):
  d0=g.d.min();tr=pd.concat([A,B[B.d<d0]]);m=mk(chosen).fit(tr[KFEATS],tr.K)
  B.loc[g.index,'mu']=m.predict(g[KFEATS]);B.loc[g.index,'a']=alpha_mm(tr.K.values,m.predict(tr[KFEATS]))
  # baseline: pitcher's shrunk prior K/start average (this season before d0, else league)
  past=tr[tr.d>=('2026' if (B.d<d0).sum()>300 else '2025')]
  lg=past.K.mean();st=past.groupby('p').K.agg(['sum','size'])
  B.loc[g.index,'mu_base']=[(st['sum'].get(p,0)+3*lg)/(st['size'].get(p,0)+3) for p in g.p]
abase=alpha_mm(B.K.values,B.mu_base.values)
res=dict(selection_2025H2=sel,chosen=chosen,walkforward_2026=dict(model=mets(B.K.values,B.mu.values,float(B.a.mean())),baseline=mets(B.K.values,B.mu_base.values,abase)))
cal={}
for k in (5,6,7,8,10):
  p=pge(B.mu.values,B.a.values,k);q=pd.qcut(p,8,labels=False,duplicates='drop')
  d=pd.DataFrame(dict(p=p,y=(B.K>=k).astype(int),q=q)).groupby('q').agg(pred=('p','mean'),obs=('y','mean'),n=('y','size'))
  cal[str(k)]=[dict(pred=round(r.pred,4),obs=round(r.obs,4),n=int(r.n)) for r in d.itertuples()]
res['calibration_ge']=cal
p10=pge(B.mu.values,B.a.values,10);res['p10']=dict(mean_pred=round(float(p10.mean()),4),obs=round(float((B.K>=10).mean()),4),top50_hit=round(float((B.K.values>=10)[np.argsort(-p10)[:50]].mean()),3),n10=int((B.K>=10).sum()))
B['p10']=p10
# full-data coefficients (glm) for explanation
gm=mk('glm').fit(pd.concat([A,B])[KFEATS],pd.concat([A,B]).K);res['glm_coefs']=dict(zip(KFEATS,[round(float(c),4) for c in gm[-1].coef_]))
# fatigue: residual by workload bucket
B['res']=B.K-B.mu;B['wb']=pd.cut(B.workload,[0,.5,.8,1.0,1.2,5]);res['resid_by_workload']=[dict(b=str(k),n=int(len(g)),mean_resid=round(float(g.res.mean()),3),velo_d3=round(float(g.velo_d3.mean()),2)) for k,g in B.groupby('wb',observed=True)]
B[['pk','d','p','K','bf','mu','a','mu_base','p10','workload','velo_d','velo_d3','cum_ip','career_hi','exp_bf']].to_parquet('/workspace/mlbraw/k_bt_preds.parquet')
json.dump(res,open('data/backtest_k.json','w'),indent=1);print(json.dumps({k:v for k,v in res.items() if k!='calibration_ge'},indent=1))
