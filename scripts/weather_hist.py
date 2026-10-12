import json,urllib.request,time,sys
from collections import defaultdict
import os,datetime as dt
out=json.load(open('/workspace/mlbraw/wx_hist.json')) if os.path.exists('/workspace/mlbraw/wx_hist.json') else {}
for yr in sys.argv[1:]:
  g=json.load(open(f'data/cache/sched_{yr}.json'));V={}
  for x in g:
    if x['lat']:V[x['venueId']]=(x['lat'],x['lon'])
  for vid,(la,lo) in V.items():
    u=f"https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}&start_date={yr}-03-15&end_date={min(f'{yr}-11-05',str(dt.date.today()-dt.timedelta(days=2)))}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC"
    for i in range(3):
      try:h=json.load(urllib.request.urlopen(u,timeout=60))['hourly'];break
      except Exception as e:print(e);time.sleep(5);h=None
    if not h:continue
    for t,a,b,c,d in zip(h['time'],h['temperature_2m'],h['relative_humidity_2m'],h['wind_speed_10m'],h['wind_direction_10m']):
      out[f"{vid}|{t[:13]}"]=[a,b,c,d]
    time.sleep(0.5)
json.dump(out,open('/workspace/mlbraw/wx_hist.json','w'));print(len(out))
