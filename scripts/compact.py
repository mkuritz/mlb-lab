"""Raw Statcast pitch parquet -> compact PA table + pitcher-game table (committed, small)."""
import pandas as pd,numpy as np,glob,sys,os
OUTS={'strikeout':1,'field_out':1,'force_out':1,'grounded_into_double_play':2,'double_play':2,'sac_fly':1,'sac_bunt':1,
 'fielders_choice_out':1,'strikeout_double_play':2,'triple_play':3,'sac_fly_double_play':2,'fielders_choice':0,'sac_bunt_double_play':2}
FB={'FF','SI','FC'}
def compact(df):
  for c in df.columns:
    if str(df[c].dtype) in ('Int64','Int32','Int16','Int8','Float64','Float32','boolean'): df[c]=df[c].astype('float64')
    elif str(df[c].dtype) in ('string',): df[c]=df[c].astype(object)
  for c in ['launch_speed','launch_angle','launch_speed_angle','estimated_ba_using_speedangle','estimated_slg_using_speedangle','estimated_woba_using_speedangle','woba_value','woba_denom','release_speed','release_spin_rate','pitcher_days_since_prev_game','at_bat_number','pitch_number','inning','umpire']:
    if c in df: df[c]=pd.to_numeric(df[c],errors='coerce')
  df=df[df.game_type.isin(['R','F','D','L','W'])].copy()
  df['game_date']=pd.to_datetime(df.game_date).dt.strftime('%Y-%m-%d')
  df['bat_home']=(df.inning_topbot=='Bot').astype(int)
  ev=df[df.events.notna()&(df.events!='truncated_pa')].copy()
  pa=pd.DataFrame(dict(pk=ev.game_pk,d=ev.game_date,gt=ev.game_type,b=ev.batter,p=ev.pitcher,st=ev.stand,pt=ev.p_throws,
    h=ev.bat_home,ab=ev.at_bat_number,inn=ev.inning,hr=(ev.events=='home_run').astype('int8'),k=ev.events.isin(['strikeout','strikeout_double_play']).astype('int8'),
    bb=ev.events.isin(['walk','intent_walk']).astype('int8'),bbe=ev.launch_speed.notna()&ev.bb_type.notna(),
    ev=ev.launch_speed.astype('float32'),la=ev.launch_angle.astype('float32'),brl=(ev.launch_speed_angle==6).astype('int8'),
    xba=ev.estimated_ba_using_speedangle.astype('float32'),xslg=ev.estimated_slg_using_speedangle.astype('float32'),
    xw=ev.estimated_woba_using_speedangle.fillna(ev.woba_value).astype('float32'),wd=ev.woba_denom.fillna(0).astype('int8'),
    outs=ev.events.map(OUTS).fillna(0).astype('int8'),ump=ev.umpire))
  pa['bbe']=pa.bbe.astype('int8')
  # pitcher-game
  d=df.copy();desc=d.description
  d['csw']=desc.isin(['called_strike','swinging_strike','swinging_strike_blocked','foul_tip']).astype(int)
  d['whf']=desc.isin(['swinging_strike','swinging_strike_blocked','foul_tip']).astype(int)
  d['sw']=desc.isin(['swinging_strike','swinging_strike_blocked','foul_tip','foul','foul_bunt','hit_into_play','missed_bunt','bunt_foul_tip']).astype(int)
  d['fbv']=np.where(d.pitch_type.isin(['FF','SI']),d.release_speed,np.nan)
  d['ffspin']=np.where(d.pitch_type=='FF',d.release_spin_rate,np.nan)
  d['isfb']=d.pitch_type.isin(FB).astype(int);d['isbrk']=d.pitch_type.isin(['SL','ST','SV','CU','KC','CS','SW']).astype(int);d['isoff']=d.pitch_type.isin(['CH','FS','FO','SC']).astype(int)
  first=d.groupby(['game_pk','bat_home']).apply(lambda g:g.sort_values(['at_bat_number','pitch_number']).pitcher.iloc[0]).rename('sp').reset_index()
  g=d.groupby(['game_pk','pitcher']).agg(d=('game_date','first'),gt=('game_type','first'),bh=('bat_home','first'),pt=('p_throws','first'),
     np_=('pitch_number','size'),csw=('csw','sum'),whf=('whf','sum'),sw=('sw','sum'),fbv=('fbv','mean'),spin=('ffspin','mean'),
     fb=('isfb','mean'),brk=('isbrk','mean'),off=('isoff','mean'),rest=('pitcher_days_since_prev_game','first'),ump=('umpire','first')).reset_index()
  pg=pa.groupby(['pk','p']).agg(bf=('hr','size'),K=('k','sum'),HR=('hr','sum'),BB=('bb','sum'),outs=('outs','sum')).reset_index().rename(columns={'pk':'game_pk','p':'pitcher'})
  g=g.merge(pg,on=['game_pk','pitcher'],how='left')
  g=g.merge(first.rename(columns={'bat_home':'bh'}),on=['game_pk','bh'],how='left');g['start']=(g.sp==g.pitcher).astype(int);g=g.drop(columns='sp')
  g=g.rename(columns={'game_pk':'pk','pitcher':'p','np_':'np'})
  return pa,g
if __name__=='__main__':
  src,yr=sys.argv[1],sys.argv[2]
  fs=sorted(glob.glob(src+'/*.parquet'))
  df=pd.concat([pd.read_parquet(f) for f in fs],ignore_index=True).drop_duplicates(['game_pk','at_bat_number','pitch_number'])
  pa,g=compact(df)
  os.makedirs('data/cache',exist_ok=True)
  pa.to_parquet(f'data/cache/pa_{yr}.parquet',index=False);g.to_parquet(f'data/cache/pg_{yr}.parquet',index=False)
  print(yr,len(pa),len(g),g.start.sum())
