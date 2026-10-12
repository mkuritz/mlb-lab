import pandas as pd,numpy as np,json,sys
sys.path.insert(0,'scripts');import career
IDS={'650911':'Cristopher Sánchez','694819':'Jacob Misiorowski','693645':'Cam Schlittler'}
pg=pd.read_parquet('data/cache/pg_2026.parquet');pa=pd.read_parquet('data/cache/pa_2026.parquet')
bt=pd.read_parquet('/workspace/mlbraw/k_bt_preds.parquet')
CI=json.load(open(career.P));out={}
for pid,nm in IDS.items():
  g=pg[(pg.p==int(pid))].sort_values('d').copy()
  g['ip']=g.outs/3;g['cum_ip']=g.ip.cumsum();g['cswp']=g.csw/g['np'];g['kp']=g.K/g.bf;g['whp']=g.whf/g.sw
  hi=career.prior_high(CI,pid,2026)
  g=g.merge(bt[bt.p==int(pid)][['pk','mu']],on='pk',how='left')
  st=g[g.start==1];st['m']=st.d.str[:7]
  mon=st.groupby('m').agg(starts=('pk','size'),ip_per=('ip','mean'),np_per=('np','mean'),fbv=('fbv','mean'),csw=('cswp','mean'),k_pct=('kp','mean'),hr=('HR','sum'),bf=('bf','sum'),K=('K','sum'),proj=('mu','sum')).reset_index()
  reg=st[st['gt']=='R'];first=reg[reg.d<'2026-07-01'];last=reg.tail(6)
  def summ(x):return dict(starts=int(len(x)),ip_per=round(x.ip.mean(),2),np_per=round(x['np'].mean(),1),fbv=round(x.fbv.mean(),2),spin=round(x.spin.mean(),0),csw=round((x.csw.sum()/x['np'].sum()),3),k_pct=round(x.K.sum()/x.bf.sum(),3),hr_per_bf=round(x.HR.sum()/x.bf.sum(),3),K_vs_proj=round(float(x.K.sum()-x.mu.sum()),1) if x.mu.notna().all() else None)
  # cross-over point where cum IP passed prior high
  cross=reg[reg.cum_ip>hi].d.min() if hi else None
  out[nm]=dict(id=pid,prior_career_high_ip=hi,reg_season_ip=round(reg.ip.sum(),1),total_ip_incl_post=round(g.ip.sum(),1),passed_prior_high_on=cross,
    first_half=summ(first),last6_reg=summ(last),post=summ(st[st['gt']!='R']) if (st['gt']!='R').any() else None,
    monthly=[{k:(round(v,3) if isinstance(v,float) else v) for k,v in r.items()} for r in mon.to_dict('records')],
    starts=[dict(d=r.d,gt=r.gt,ip=round(r.ip,1),np=int(r.np),K=int(r.K),bf=int(r.bf),fbv=round(r.fbv,1) if r.fbv==r.fbv else None,cum_ip=round(r.cum_ip,1),proj=round(r.mu,2) if r.mu==r.mu else None) for r in st.itertuples()])
import re as _re
open('data/fatigue_case.json','w').write(_re.sub(r'\bNaN\b','null',json.dumps(out,indent=1,default=float)))
for k,v in out.items():print(k,{x:v[x] for x in ('prior_career_high_ip','reg_season_ip','total_ip_incl_post','passed_prior_high_on')});print(' H1',v['first_half']);print(' L6',v['last6_reg']);print(' PS',v['post']);print(' months',[(m['m'],m['starts'],m['fbv'],round(m['k_pct'],3),round(m['ip_per'],1)) for m in v['monthly']])
