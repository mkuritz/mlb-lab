/* HR King · interactive Home Run Score view (MLB Lab). Stylized park drawn from published wall distances; no photos. */
(function(){
const HK={data:undefined,sel:null,spray:false,card:null};window.HK=HK;
const X=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const css=`.hk-h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:4px 0 12px}.hk-h h2{margin:0;font-weight:400}.hk-h h2 b{font-weight:800}
.hk-pick{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;margin-bottom:12px;scrollbar-width:thin}
.hk-pick a{flex:0 0 auto;display:flex;align-items:center;gap:7px;padding:5px 10px 5px 5px;border-radius:99px;background:var(--p);border:1px solid var(--b);color:var(--t);font-weight:600;font-size:13px}
.hk-pick a.on{border-color:var(--o);background:#2a1d0c}.hk-pick a .hs{width:28px;height:28px}.hk-pick a i{font-style:normal;font-weight:900;font-size:12px;padding:1px 6px;border-radius:6px;color:#000}
.hk{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(280px,1fr);gap:14px}@media(max-width:900px){.hk{grid-template-columns:1fr}}
.hk-park{position:relative;background:radial-gradient(120% 90% at 50% 100%,#13284a 0,#0d1630 55%,#0a1124 100%);border:1px solid var(--b);border-radius:16px;overflow:hidden}
.hk-park .bar{position:absolute;left:0;right:0;top:0;height:auto;margin:0;padding:10px 14px;background:linear-gradient(180deg,#0b1020ee,#0b102000);font-weight:700;font-size:15px;border-radius:0;z-index:2;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.hk-park svg{display:block;width:100%;height:auto;margin-top:34px;max-height:78vh}
.hk-wb{position:absolute;display:flex;gap:8px;align-items:center;background:#0b1020d9;border:1px solid #2c6b7a;border-radius:12px;padding:6px 10px;font-size:12px;color:#bfefff;right:12px;bottom:12px;z-index:2}.hk-wb b{display:block;font-size:15px;color:#fff}
.hk-tg{position:absolute;left:12px;bottom:12px;z-index:2;display:flex;gap:6px;flex-wrap:wrap}.hk-tg button{background:#0b1020d9;border:1px solid var(--b);color:var(--t);border-radius:99px;padding:6px 11px;font:600 12px system-ui;cursor:pointer}.hk-tg button.on{background:var(--o);color:#000;border-color:var(--o)}
.hk-side{background:linear-gradient(180deg,#18213d,#121a30);border:1px solid var(--b);border-radius:16px;padding:16px}
.hk-pl{display:flex;gap:14px;align-items:center}.hk-pl img{width:96px;height:96px;border-radius:14px;background:#2a3356;object-fit:cover}
.hk-sc{font-size:56px;font-weight:900;line-height:1}.hk-g{position:relative;height:10px;border-radius:99px;background:linear-gradient(90deg,#22c55e,#facc15 55%,#f97316 75%,#ef4444);margin:18px 0 22px}
.hk-g i{position:absolute;top:-6px;width:3px;height:22px;background:#fff;border-radius:2px;box-shadow:0 0 6px #fff8}.hk-g span{position:absolute;top:16px;font-size:11px;color:var(--m);transform:translateX(-50%)}
.hk-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px}.hk-c{background:#0e1529;border:1px solid var(--b);border-radius:12px;padding:12px;text-align:center;cursor:pointer;color:var(--t);font:inherit}
.hk-c:hover,.hk-c.on{border-color:var(--a)}.hk-c small{display:block;color:var(--m);font-size:12px}.hk-c b{font-size:22px}
.hk-ex{margin-top:10px;background:#10203a;border:1px solid #1f3f6a;border-radius:10px;padding:10px;font-size:12.5px;color:#cfe0ff}
.hk-mu{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.hk-mu div{background:var(--p2);border-radius:10px;padding:10px}.hk-mu b{display:block;font-size:18px}
@keyframes hkdraw{to{stroke-dashoffset:0}}@keyframes hkpop{0%{r:0;opacity:0}70%{r:6}100%{r:4;opacity:1}}@keyframes hkwind{to{stroke-dashoffset:-60}}
.hk-arc{fill:none;stroke-linecap:round;stroke-dasharray:1000;stroke-dashoffset:1000;animation:hkdraw 1.6s cubic-bezier(.3,.7,.3,1) forwards}
.hk-land{opacity:0;animation:hkpop .4s ease-out forwards}.hk-wl{fill:none;stroke:#67e8f9;stroke-width:2.6;stroke-linecap:round;stroke-dasharray:18 42;animation:hkwind 1.8s linear infinite;opacity:.75;filter:drop-shadow(0 0 3px #22d3ee)}
@media (prefers-reduced-motion:reduce){.hk-arc{animation-duration:.01s}.hk-wl{animation:none}}
@media(max-width:640px){.hk-sc{font-size:46px}.hk-pl img{width:76px;height:76px}.hk-wb{position:static;margin:6px 10px 0}.hk-tg{position:static;margin:8px 10px 10px}.hk-park .bar{font-size:13px}}`;
function sty(){if(!document.getElementById('hkcss')){const s=document.createElement('style');s.id='hkcss';s.textContent=css;document.head.appendChild(s)}}
function load(){HK.data=null;fetch('data/hr_king.json?'+Date.now()).then(r=>{if(!r.ok)throw 0;return r.json()}).then(d=>{HK.data=d}).catch(()=>{HK.data={games:[],batters:[]}}).finally(()=>{if(/^#hrking/.test(location.hash))draw()})}
function draw(){const el=document.getElementById('app');el.innerHTML=window.hrking(HK.selArg)}
const SC=0.69,HX=200,HY=344;
const pt=(a,d)=>[HX+Math.sin(a*Math.PI/180)*d*SC,HY-Math.cos(a*Math.PI/180)*d*SC];
function wallPath(dims){const A=[-45,-22.5,0,22.5,45];const P=A.map((a,i)=>pt(a,dims[i]));
 // smooth curve through the five published distances (Catmull-Rom -> cubic)
 let d=`M${P[0][0].toFixed(1)},${P[0][1].toFixed(1)}`;for(let i=0;i<P.length-1;i++){const p0=P[i-1]||P[i],p1=P[i],p2=P[i+1],p3=P[i+2]||p2;
  const c1=[p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6],c2=[p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6];d+=` C${c1.map(v=>v.toFixed(1))} ${c2.map(v=>v.toFixed(1))} ${p2.map(v=>v.toFixed(1))}`}return{d,P}}
function windInfo(g){if(!g)return null;if(g.closed)return{closed:1};const w=g.wind||{};const mph=w.mph??g.model_env.wmph,dir=w.dir??g.model_env.wdir;if(mph==null||dir==null||g.az==null)return null;
 let rel=((dir+180)%360)-g.az;rel=((rel+540)%360)-180;const ar=Math.abs(rel);
 let lab;if(mph<3)lab='Calm';else if(ar<=22.5)lab='Out to CF';else if(ar<=67.5)lab='Out to '+(rel>0?'RF':'LF');else if(ar<=112.5)lab='Across, toward '+(rel>0?'RF':'LF');else if(ar<=157.5)lab='In from '+(rel>0?'LF':'RF');else lab='In from CF';
 return{mph:Math.round(mph),rel,lab,temp:w.temp}}
function fieldSVG(g,b,showSpray){const dims=g&&g.dims;if(!dims)return'<div style="padding:70px 20px;text-align:center" class="m">Park dimensions are not available for this venue yet.</div>';
 const {d:wall,P}=wallPath(dims);const lf=P[0],rf=P[4];
 const field=`${wall} L${HX},${HY} Z`;const inf=[pt(0,0),pt(45,90),pt(0,127.3),pt(-45,90)];const dirt=`M${pt(-45,0)} L${pt(-45,95)} Q${pt(0,190)} ${pt(45,95)} L${HX},${HY} Z`;
 let stripes='';for(let i=1;i<9;i++)stripes+=`<path d="M${HX},${HY} L${pt(-45+i*10-5,430)} L${pt(-45+i*10,430)} Z" fill="#ffffff" opacity=".035"/>`;
 const labels=[[-45,'LF'],[-22.5,''],[0,'CF'],[22.5,''],[45,'RF']].map(([a,t],i)=>{const q=pt(a,dims[i]+22);return `<text x="${q[0].toFixed(0)}" y="${q[1].toFixed(0)}" fill="#c9d4f5" font-size="12" font-weight="700" text-anchor="middle">${dims[i]}</text>${t?`<text x="${q[0].toFixed(0)}" y="${(q[1]+13).toFixed(0)}" fill="#7f8bb3" font-size="9" text-anchor="middle">${t}</text>`:''}`}).join('');
 // wind overlay
 const W=windInfo(g);let wind='';if(W&&!W.closed&&W.mph>=3){const n=Math.min(9,3+Math.round(W.mph/3));let ls='';for(let i=0;i<n;i++){const off=(i-(n-1)/2)*26;ls+=`<path class="hk-wl" style="animation-delay:${(-i*.37).toFixed(2)}s;animation-duration:${Math.max(.8,2.6-W.mph/10).toFixed(2)}s" d="M${off},120 C${off+10},40 ${off-10},-40 ${off},-120"/>`}
  wind=`<g clip-path="url(#hkclip)"><g transform="translate(200,215) rotate(${W.rel.toFixed(0)})">${ls}</g></g>`}
 // batted balls
 let balls='';if(b&&b.air){if(showSpray){balls+=(b.fly||[]).map(([a,d])=>{const q=pt(a,d);return `<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="2.6" fill="#94a3b8" opacity=".45"/>`}).join('');
   balls+=(b.hrs||[]).filter(h=>h.dist).map((h,i)=>{const q=pt(h.a,h.dist);return `<circle class="hk-land" style="animation-delay:${(i*.03).toFixed(2)}s" cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="4" fill="#ffb020" stroke="#fff" stroke-width="1"><title>${X(h.d)} · ${h.dist} ft · ${h.ev??'–'} mph · ${h.la??'–'}°</title></circle>`}).join('')}
  else{const top=[...(b.hrs||[])].filter(h=>h.dist).sort((x,y)=>y.d.localeCompare(x.d)).slice(0,10);
   balls+=top.map((h,i)=>{const q=pt(h.a,h.dist);const lift=30+Math.max(0,(h.la||28)-15)*1.8+h.dist*0.06;const mx=(HX+q[0])/2,my=(HY+q[1])/2-lift;const del=(i*.18).toFixed(2);
    return `<path class="hk-arc" style="animation-delay:${del}s" d="M${HX},${HY} Q${mx.toFixed(1)},${my.toFixed(1)} ${q[0].toFixed(1)},${q[1].toFixed(1)}" stroke="url(#hkarc)" stroke-width="3" filter="url(#hkglow)"/><circle class="hk-land" style="animation-delay:${(+del+1.3).toFixed(2)}s" cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="4" fill="#fff4d6"><title>${X(h.d)} · ${h.dist} ft · ${h.ev??'–'} mph · ${h.la??'–'}°</title></circle>`}).join('')}}
 return `<svg viewBox="0 0 400 370" role="img" aria-label="Stylized ballpark with home run paths and wind"><defs>
 <linearGradient id="hkgrass" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#1f6b3a"/><stop offset="1" stop-color="#174f2d"/></linearGradient>
 <linearGradient id="hkarc" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#ff8a00"/><stop offset="1" stop-color="#ffe08a"/></linearGradient>
 <filter id="hkglow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <clipPath id="hkclip"><path d="${field}"/></clipPath></defs>
 <path d="${wall} L${(rf[0]+30).toFixed(0)},${(rf[1]+10).toFixed(0)} L${HX},${HY+24} L${(lf[0]-30).toFixed(0)},${(lf[1]+10).toFixed(0)} Z" fill="#141c36" stroke="#26304f"/>
 <path d="${field}" fill="url(#hkgrass)"/><g clip-path="url(#hkclip)">${stripes}</g>
 <path d="${dirt}" fill="#8a5a33" opacity=".85"/><path d="M${inf.map(p=>p.map(v=>v.toFixed(1))).join(' L')} Z" fill="#2a7a45" stroke="#e8eefc" stroke-width="1.2" opacity=".95"/>
 <circle cx="${pt(0,60.5)[0]}" cy="${pt(0,60.5)[1].toFixed(1)}" r="5" fill="#9c6a3e"/>
 <path d="${wall}" fill="none" stroke="#e6ebff" stroke-width="3.5" opacity=".9"/><path d="M${lf[0].toFixed(1)},${lf[1].toFixed(1)} L${HX},${HY} L${rf[0].toFixed(1)},${rf[1].toFixed(1)}" stroke="#fff" stroke-width="1.2" fill="none" opacity=".8"/>
 ${inf.map(p=>`<rect x="${(p[0]-3).toFixed(1)}" y="${(p[1]-3).toFixed(1)}" width="6" height="6" fill="#fff" transform="rotate(45 ${p[0].toFixed(1)} ${p[1].toFixed(1)})"/>`).join('')}
 ${wind}${labels}${balls}${g.closed?'<text x="200" y="205" fill="#e6ebff" font-size="15" font-weight="800" text-anchor="middle" opacity=".85">ROOF CLOSED</text>':''}</svg>`}
const CARDS={pf:'Park factor',wind:'Wind boost',brl:'Barrel rate',temp:'Temp'};
function explain(k,p,g,W){const e=p.feats;switch(k){
 case 'pf':return `How this park plays for home runs compared with an average park (0% = average), as used in the HR Score. ${X(g.venue)} walls: ${g.dims?g.dims.join(' / ')+' ft (LF / LCF / CF / RCF / RF)':'not available'}.`;
 case 'wind':return W&&W.closed?'The roof is expected to be closed, so wind has no effect.':`The part of the wind blowing straight out toward center field, in mph, at first pitch. Positive helps fly balls carry, negative knocks them down. The forecast is ${W?W.mph+' mph, '+W.lab:'not available yet'}. Forecasts change, and the score updates with each refresh.`;
 case 'brl':return `How often his batted balls this season were barreled: hit with the exit velocity and launch angle that most often produce extra-base hits and home runs. MLB average is about 8%.`;
 case 'temp':return `Forecast temperature at first pitch. Warmer air is thinner, so balls carry a little farther. Cold October nights slightly suppress home runs.${g.closed?' With the roof closed, indoor temperature is used.':''}`}}
window.hrking=function(arg){sty();HK.selArg=arg;if(HK.data===undefined){load();return'<div class="card">Loading HR King…</div>'}if(HK.data===null)return'<div class="card">Loading HR King…</div>';
 const H=[...(D.hr&&D.hr.players||[])].sort((a,b)=>b.score-a.score);if(!H.length)return'<div class="card"><h3>HR King</h3><p class="m">No batters on the slate yet. HR King fills in once the next game\'s lineups are projected.</p></div>';
 const p=H.find(x=>String(x.id)===String(arg))||H[0];const g=(HK.data.games||[]).find(x=>x.pk===p.pk)||null;const sg=D.slate.games.find(x=>x.pk===p.pk)||{};const b=(HK.data.batters||[]).find(x=>x.id===p.id)||null;const W=windInfo(g);
 const enough=b&&b.air>=20;const e=p.feats;const pfv=e.pf!=null?Math.round((e.pf-1)*100):null;
 const val={pf:pfv==null?'–':(pfv>0?'+':'')+pfv+'%',wind:W&&W.closed?'Roof':e.wout==null?'–':(e.wout>0?'+':'')+(+e.wout).toFixed(1)+' mph',brl:e.barrel==null?'–':(e.barrel*100).toFixed(0)+'%',temp:g&&g.closed?'Indoors':((W&&W.temp)??e.temp)!=null?Math.round((W&&W.temp)??e.temp)+'°F':'–'};
 const opp=p.home?'away':'home';const sp=g&&g.sp&&g.sp[opp];const spn=(sg.sp||{})[opp];const hrv=b&&b.hr_vs;
 let h=`<div class="hk-h"><h2>MLB Lab — <b>HR King</b></h2><span class="m small">Home Run Score · ${X(sg.desc||sg.series||'')} · ${X(sg.away)} @ ${X(sg.home)}</span></div>
 <div class="hk-pick" role="tablist">${H.map(x=>`<a href="#hrking/${x.id}" class="${x.id===p.id?'on':''}" role="tab">${hs(x.id)}${X(x.name)}<i style="background:${scol(x.score)}">${x.score}</i></a>`).join('')}</div>
 <div class="hk"><div class="hk-park"><div class="bar">${X(sg.venue||'Park TBD')} · ${sg.start?tET(sg.start):''}${g&&g.roof&&g.roof!=='Open'?` <span class="pill">${X(g.roof)} roof${g.closed?' · closed':' · open (est.)'}</span>`:''}</div>
 ${g?fieldSVG(g,b,HK.spray):'<div style="padding:70px 20px;text-align:center" class="m">Park data not available yet.</div>'}
 ${W?`<div class="hk-wb"><span style="font-size:20px">${W.closed?'🏟️':'💨'}</span><div>${W.closed?'<b>Roof closed</b>no wind effect':`<b>${W.lab}${W.lab==='Calm'?'':' '+W.mph+' mph'}</b>forecast at first pitch`}</div></div>`:g?'<div class="hk-wb"><div><b>Wind</b>forecast not available yet</div></div>':''}
 <div class="hk-tg"><button class="${HK.spray?'':'on'}" onclick="HK.spray=false;HK.r()">HR paths</button><button class="${HK.spray?'on':''}" onclick="HK.spray=true;HK.r()">Full HR spray chart</button></div></div>
 <div class="hk-side"><div class="hk-pl"><img alt="" src="https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/${p.id}/headshot/67/current"><div><div class="m small">HR Score</div><div class="hk-sc" style="color:${scol(p.score)}">${p.score}</div><div style="font-weight:800;margin-top:4px">${X(p.name)}</div><div class="small m">${X(p.team)} ${p.home?'vs':'@'} ${X(p.opp)} · bats ${X(p.bats)} · #${p.spot??'–'} ${p.lineup==='projected'?'<span class="pill est">proj</span>':'<span class="pill ok">conf</span>'}</div></div></div>
 <div class="hk-g" aria-label="HR Score ${p.score} of 100"><i style="left:calc(${p.score}% - 1px)"></i><span style="left:${p.score}%">${p.score}</span></div>
 <div class="small m" style="margin:-6px 0 12px">Our chance of 1+ HR: <b style="color:var(--t)">${pct(p.p_hr)}</b> · estimate, not a guarantee${p.score>=75?' · <span class="pill ok">Highlighted</span>':''}</div>
 <div class="hk-cards">${Object.entries(CARDS).map(([k,l])=>`<button class="hk-c ${HK.card===k?'on':''}" onclick="HK.card=HK.card==='${k}'?null:'${k}';HK.r()"><small>${l}</small><b>${val[k]}</b></button>`).join('')}</div>
 ${HK.card?`<div class="hk-ex"><b>${CARDS[HK.card]}.</b> ${explain(HK.card,p,g||{venue:sg.venue},W)}</div>`:'<div class="small m" style="margin-top:8px">Tap a card for what it means.</div>'}
 </div></div>
 <div class="card" style="margin-top:14px"><h3>${HK.spray?'Full 2026 HR spray chart':'Home run paths'} <span class="m small">${enough?(HK.spray?`${b.hr_n} HR (orange) and ${b.fly.length} recent long fly balls/liners (gray), drawn on this park`:`his ${Math.min(10,b.hr_n)} most recent 2026 HRs, drawn on this park`):''}</span></h3>
 ${!b||!enough?'<p class="m">Not enough data yet for this batter\'s batted-ball map.</p>':b.hr_n===0?'<p class="m">No 2026 home runs yet. Not enough data yet for a home run map.</p>':`<div class="hk-mu"><div><span class="small m">2026 HR (incl. postseason)</span><b>${b.hr_n}</b></div><div><span class="small m">Pull / Center / Oppo</span><b>${b.hr_zones.pull} / ${b.hr_zones.center} / ${b.hr_zones.oppo}</b></div><div><span class="small m">Avg / longest HR</span><b>${b.avg_hr_dist??'–'} / ${b.max_hr_dist??'–'} ft</b></div><div><span class="small m">HR vs RHP / LHP</span><b>${hrv.R.hr} / ${hrv.L.hr}</b></div></div>`}
 <div class="small m" style="margin-top:8px">Paths and spray points use each ball's real direction and distance from 2026 tracking data, placed on a to-scale drawing of tonight's park. The arc height is stylized.</div></div>
 <div class="card"><h3>Matchup</h3><div class="hk-mu">
 <div><span class="small m">Opposing starter</span><b>${spn&&spn.name?X(spn.name):'Not announced yet'}</b></div>
 <div><span class="small m">Starter HR/9 (2026)</span><b>${sp&&sp.hr9!=null?f(sp.hr9,2):spn&&spn.name?'Not enough data yet':'—'}</b>${sp&&sp.hr9!=null?`<span class="small m">${sp.hr} HR in ${sp.ip} IP</span>`:''}</div>
 <div><span class="small m">His split vs ${spn&&spn.name&&p.pitcher.throws?p.pitcher.throws+'HP':'starter\'s hand'}</span><b>${spn&&spn.name&&e.split!=null?(e.split>0?'+':'')+(e.split*100).toFixed(1)+'%':'—'}</b></div>
 <div><span class="small m">Career vs this starter</span><b>${p.bvp&&p.bvp.pa?p.bvp.hr+' HR / '+p.bvp.pa+' PA':spn&&spn.name?'No meetings':'—'}</b></div>
 <div><span class="small m">Form 7 / 14 / 30 days</span><b>${f(e.t7,2)} / ${f(e.t14,2)} / ${f(e.t30,2)}</b><span class="small m">1.00 = his season norm</span></div>
 <div><span class="small m">Exit velo · xISO</span><b>${f(e.ev,1)} · ${f(e.xiso,3)}</b></div></div>
 ${spn&&spn.name?'':'<div class="small" style="color:#facc15;margin-top:8px">Starters aren\'t announced yet. Starter HR/9 and the hand split fill in once each club names its starter.</div>'}
 <div class="small m" style="margin-top:8px">Top drivers: ${(p.drivers||[]).map(d=>`<span class="${d.v>0?'g':'r'}">${X(d.f)} ${d.v>0?'▲':'▼'}</span>`).join(' · ')||'—'}</div></div>`;
 return h};
HK.r=()=>{const el=document.getElementById('app');el.innerHTML=window.hrking(HK.selArg)};
})();
