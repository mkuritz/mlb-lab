"""Pre-game Kalshi 1+ HR prices for settled 2026 games (public API, no key). Mid of yes bid/ask on the last hourly candle closing at/before first pitch."""
import json,urllib.request,datetime as dt,time,sys,os,re
from concurrent.futures import ThreadPoolExecutor
B="https://api.elections.kalshi.com/trade-api/v2"
def J(u):
  for i in range(4):
    try:return json.load(urllib.request.urlopen(u,timeout=30))
    except Exception as e:time.sleep(2+3*i)
  return {}
def start_ts(et):
  m=re.search(r'-(\d\d)([A-Z]{3})(\d\d)(\d{4})',et);yy,mon,dd,hm=m.groups()
  mo=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'].index(mon)+1
  t=dt.datetime(2000+int(yy),mo,int(dd),int(hm[:2]),int(hm[2:]))+dt.timedelta(hours=4) # ET(EDT)->UTC
  return int(t.replace(tzinfo=dt.timezone.utc).timestamp())
def one(et):
  ms=[m for m in J(f"{B}/markets?event_ticker={et}&limit=200").get('markets',[]) if m.get('floor_strike')==0.5];hist=False
  if not ms:
    ms=[m for m in J(f"{B}/historical/markets?event_ticker={et}&limit=200").get('markets',[]) if m.get('floor_strike')==0.5];hist=True
  if not ms:return []
  t=start_ts(et);out=[]
  tk=",".join(m['ticker'] for m in ms)
  if hist:
    cm={m['ticker']:J(f"{B}/historical/markets/{m['ticker']}/candlesticks?start_ts={t-6*3600}&end_ts={t}&period_interval=60").get('candlesticks',[]) for m in ms}
  else:
    r=J(f"{B}/markets/candlesticks?market_tickers={tk}&start_ts={t-6*3600}&end_ts={t}&period_interval=60")
    cm={x.get('market_ticker'):x.get('candlesticks',[]) for x in r.get('markets',[])}
  for m in ms:
    cs=[c for c in cm.get(m['ticker'],[]) if c['end_period_ts']<=t+60]
    p=None
    if cs:
      c=cs[-1];yb,ya=c['yes_bid'],c['yes_ask'];b=float(yb.get('close_dollars',yb.get('close')) or 0);a=float(ya.get('close_dollars',ya.get('close')) or 0)
      if a>0 and b>0 and a-b<=0.06:p=(a+b)/2
    out.append(dict(ev=et,t=t,name=m['yes_sub_title'].replace(': 1+',''),res=m['result'],p=p))
  return out
ev=json.load(open(sys.argv[1]));ets=sorted(e['event_ticker'] for e in ev)[::int(sys.argv[3]) if len(sys.argv)>3 else 1]
res=[]
with ThreadPoolExecutor(12) as ex:
  for i,o in enumerate(ex.map(one,ets)):
    res+=o
    if i%25==0:print(i,len(res),flush=True)
json.dump(res,open(sys.argv[2],'w'));print('done',len(res),sum(1 for r in res if r['p']))
