import json,sys,urllib.request,datetime as dt,os
def get(u):
  return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'mlb-lab'}),timeout=60))
def games(s,e):
  u=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={s}&endDate={e}&gameType=R,F,D,L,W&hydrate=weather,officials,venue(location,fieldInfo),probablePitcher,team"
  out=[]
  for d in get(u)['dates']:
    for g in d['games']:
      v=g['venue'];loc=v.get('location',{});fi=v.get('fieldInfo',{})
      hp=[o['official']['id'] for o in g.get('officials',[]) if o['officialType']=='Home Plate']
      out.append(dict(pk=g['gamePk'],date=d['date'],type=g['gameType'],start=g['gameDate'],status=g['status']['detailedState'],
        home=g['teams']['home']['team'].get('abbreviation'),away=g['teams']['away']['team'].get('abbreviation'),
        homeName=g['teams']['home']['team']['name'],awayName=g['teams']['away']['team']['name'],
        homeId=g['teams']['home']['team']['id'],awayId=g['teams']['away']['team']['id'],
        hs=g['teams']['home'].get('score'),as_=g['teams']['away'].get('score'),
        hpp=g['teams']['home'].get('probablePitcher',{}).get('id'),app=g['teams']['away'].get('probablePitcher',{}).get('id'),
        venue=v['name'],venueId=v['id'],lat=loc.get('defaultCoordinates',{}).get('latitude'),lon=loc.get('defaultCoordinates',{}).get('longitude'),
        az=loc.get('azimuthAngle'),elev=loc.get('elevation'),roof=fi.get('roofType'),
        wx=g.get('weather'),ump=hp[0] if hp else None,series=g.get('seriesDescription'),seriesGame=g.get('seriesGameNumber'),desc=g.get('description')))
  return out
if __name__=='__main__':
  yr=sys.argv[1];allg=[]
  for m in range(3,12):
    s=dt.date(int(yr),m,1);e=(s+dt.timedelta(days=32)).replace(day=1)-dt.timedelta(days=1)
    allg+=games(s,e)
  json.dump(allg,open(f'data/cache/sched_{yr}.json','w'))
  print(yr,len(allg))
