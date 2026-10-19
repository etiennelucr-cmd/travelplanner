const $=id=>document.getElementById(id);
let trips=[],selected=null,month=new Date(),activeTab='overview';
const map=L.map('map').setView([47.8,5.4],5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).addTo(map);
const tripLayer=L.layerGroup().addTo(map),workLayer=L.layerGroup().addTo(map);
let cache={};try{cache=JSON.parse(localStorage.getItem('tpGeoV2')||'{}')}catch{cache={}};
// Offline positions for cities supported by the local tourist catalog.
const offlineCities={"rouen": [49.4402, 1.0947], "strasbourg": [48.5818, 7.7507], "paris": [48.853, 2.3499], "lyon": [45.7578, 4.832], "nantes": [47.2165, -1.549], "bordeaux": [44.8417, -0.5694], "marseille": [43.2951, 5.3741], "bruxelles": [50.8467, 4.3525], "lille": [50.6366, 3.0635], "annecy": [45.8984, 6.126], "dijon": [47.3217, 5.041], "reims": [49.2538, 4.0347], "bruges": [51.2089, 3.2247], "rome": [41.8902, 12.4922], "amsterdam": [52.3731, 4.8932], "aachen": [50.7753, 6.0839], "aix-la-chapelle": [50.7753, 6.0839], "aix la chapelle": [50.7753, 6.0839], "berlin": [52.5200, 13.4050], "ostende": [51.2300, 2.9200], "oostende": [51.2300, 2.9200], "ostend": [51.2300, 2.9200], "cologne": [50.9413, 6.9583], "koln": [50.9413, 6.9583], "koeln": [50.9413, 6.9583]};
// V5.7: city coordinates are approximate city centres (not street addresses).
const extraCityCoords={
 'zurich':[47.3769,8.5417], 'zurich suisse':[47.3769,8.5417],
 'lisieux':[49.1455,0.2271], 'deauville':[49.3570,0.0753],
 'hague':[52.0705,4.3007], 'la haye':[52.0705,4.3007], 'den haag':[52.0705,4.3007], 'the hague':[52.0705,4.3007],
 'mons':[50.4542,3.9523], 'poitiers':[46.5802,0.3404],
 'la rochelle':[46.1603,-1.1511], 'caen':[49.1829,-0.3707],
 'granville':[48.8379,-1.5970], 'rennes':[48.1173,-1.6778],
 'saint malo':[48.6493,-2.0257], 'saint-malo':[48.6493,-2.0257],
 'dax':[43.7102,-1.0537], 'arcachon':[44.6580,-1.1681]
};
Object.assign(offlineCities,extraCityCoords,{gand:[51.0543,3.7174],gent:[51.0543,3.7174],ghent:[51.0543,3.7174]});
// V6.1: complete offline centres for all cities in the supplied trip list.
Object.assign(offlineCities,{"nantes":[47.2184,-1.5536],"evreux":[49.0241,1.1508],"lyon":[45.764,4.8357],"tours":[47.3941,0.6848],"rouen":[49.4432,1.0993],"metz":[49.1193,6.1757],"marseille":[43.2965,5.3698],"londres":[51.5074,-0.1278],"annecy":[45.8992,6.1294],"le mont saint michel":[48.6361,-1.5115],"etretat":[49.7074,0.2056],"reims":[49.2583,4.0317],"nancy":[48.6921,6.1844],"utrecht":[52.0907,5.1214],"lausanne":[46.5197,6.6323],"rotterdam":[51.9244,4.4777],"le havre":[49.4944,0.1079],"basel":[47.5596,7.5886],"ghent":[51.0543,3.7174],"antwerp":[51.2194,4.4025],"turin":[45.0703,7.6869],"milan":[45.4642,9.19],"francfort":[50.1109,8.6821],"madrid":[40.4168,-3.7038],"barcelone":[41.3874,2.1686],"zurich":[47.3769,8.5417],"munich":[48.1351,11.582],"lisieux":[49.1455,0.2271],"deauville":[49.357,0.0753],"hague":[52.0705,4.3007],"amsterdam":[52.3676,4.9041],"orleans":[47.9029,1.9093],"vitre":[48.1242,-1.2118],"vannes":[47.6582,-2.7608],"carnac":[47.5846,-3.077],"quiberon":[47.4833,-3.119],"lorient":[47.7483,-3.3702],"lille":[50.6292,3.0573],"auxerre":[47.7982,3.5738],"dijon":[47.322,5.0415],"geneve":[46.2044,6.1432],"aix les bains":[45.6885,5.915],"grenoble":[45.1885,5.7245],"troyes":[48.2973,4.0744],"strasbourg":[48.5734,7.7521],"bruxelles":[50.8503,4.3517],"mons":[50.4542,3.9523],"poitiers":[46.5802,0.3404],"la rochelle":[46.1603,-1.1511],"cabourg":[49.2897,-0.1168],"caen":[49.1829,-0.3707],"granville":[48.8379,-1.597],"rennes":[48.1173,-1.6778],"saint malo":[48.6493,-2.0257],"aix en provence":[43.5297,5.4474],"nimes":[43.8367,4.3601],"dieppe":[49.9229,1.0775],"clermont ferrand":[45.7772,3.087],"chartres":[48.4469,1.489],"angers":[47.4784,-0.5632],"nice":[43.7102,7.262],"menton":[43.7745,7.4975],"monaco":[43.7384,7.4246],"liege":[50.6326,5.5797],"fecamp":[49.7579,0.374],"bourges":[47.081,2.3988],"biarritz":[43.4832,-1.5586],"hendaye":[43.3587,-1.7745],"saint jean de luz":[43.3891,-1.661],"bayonne":[43.4929,-1.4748],"bordeaux":[44.8378,-0.5792],"montpellier":[43.6108,3.8767],"palavas les flots":[43.5294,3.9316],"sete":[43.4076,3.6966],"beziers":[43.3442,3.2158],"avignon":[43.9493,4.8055],"blois":[47.5861,1.3359],"bruges":[51.2093,3.2247],"ostende":[51.23,2.92],"aachen":[50.7753,6.0839],"cologne":[50.9375,6.9603],"mechelen":[51.0259,4.4775],"leuven":[50.8798,4.7005],"cannes":[43.5528,7.0174],"antibes":[43.5804,7.1251],"toulon":[43.1242,5.928],"brest":[48.3904,-4.4861],"dublin":[53.3498,-6.2603],"seville":[37.3891,-5.9845],"dusseldorf":[51.2277,6.7735],"dax":[43.7102,-1.0537],"arcachon":[44.658,-1.1681],"berlin":[52.52,13.405],"stuttgart":[48.7758,9.1829],"lisbonne":[38.7223,-9.1393],"edinburgh":[55.9533,-3.1883],"colmar":[48.0794,7.3585],"vienne":[48.2082,16.3738],"berne":[46.948,7.4474],"dresden":[51.0504,13.7373],"rome":[41.9028,12.4964],"leiden":[52.1601,4.497],"porto":[41.1579,-8.6291],"leipzig":[51.3397,12.3731],"salzburg":[47.8095,13.055],"neuchatel":[46.9896,6.9293],"hamburg":[53.5511,9.9937],"new york":[40.7128,-74.006],"luxembourg":[49.6116,6.1319],"le touquet":[50.5211,1.585],"verdun":[49.1596,5.3844],"namur":[50.4674,4.8718],"dinant":[50.2609,4.9122],"limoges":[45.8336,1.2611],"chamonix":[45.9237,6.8694],"saint etienne":[45.4397,4.3872],"eindhoven":[51.4416,5.4697],"wurburg":[49.7913,9.9534],"dunkerque":[51.0344,2.3768],"saint raphael":[43.4252,6.7684],"lourdes":[43.095,-0.0457],"lugano":[46.0037,8.9511],"dinard":[48.6326,-2.0614],"le mans":[48.0061,0.1996],"montreux":[46.4312,6.9107],"albufeira":[37.0891,-8.2479],"la haye":[52.0705,4.3007],"den haag":[52.0705,4.3007],"the hague":[52.0705,4.3007],"koln":[50.9375,6.9603],"koeln":[50.9375,6.9603],"oostende":[51.23,2.92],"wurzburg":[49.7913,9.9534],"wurtzbourg":[49.7913,9.9534],"saint-malo":[48.6493,-2.0257],"aix-en-provence":[43.5297,5.4474],"palavas-les-flots":[43.5294,3.9316]});
Object.assign(offlineCities,window.TP_CITY_COORDS||{});
// Centres de secours verifiés pour les noms qui echappent au geocodeur.
Object.assign(offlineCities,{'honfleur':[49.4194,0.2329]});
Object.assign(offlineCities,{'andorre-la-vieille':[42.5063,1.5218],'andorra la vella':[42.5063,1.5218],'anvers':[51.2194,4.4025],'tournai':[50.6056,3.3893]});
for(const [name,pos] of Object.entries(offlineCities)){if(!cache[name])cache[name]={lat:pos[0],lon:pos[1],name:name}}

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const el=(tag,txt,cls)=>{const n=document.createElement(tag);if(txt!==undefined)n.textContent=txt;if(cls)n.className=cls;return n};
function notice(msg){$('toast').textContent=msg;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',5200)}
async function api(path,options){const r=await fetch(path,options);const j=await r.json();if(!r.ok)throw Error(j.error||'Erreur serveur');return j}
function status(t){return t.kind==='past'?'past':(t.start&&!/Projet \/ souhait/i.test(t.notes||''))?'scheduled':'wish'}
const label={past:'Visité',scheduled:'Programmé',wish:'Envie'};
function normName(v){return String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[‘’'"“”]/g,' ').replace(/\s+/g,' ').trim()}
function validCoord(p){return Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=90&&Math.abs(p[1])<=180}
// Les dates et les evenements ne sont jamais des villes.
function cleanTripName(value){
 let name=String(value||'').trim();
 name=name.replace(/^\s*(?:[0-9#️⃣⃣\uFE0F]+\s*)+/u,'').trim();
 name=name.replace(/\s*\(\s*(?:\d{1,2}\s*(?:\/|-|au)\s*)?\d{1,2}\s+[a-zA-ZÀ-ÿ]+(?:\s+\d{4})?\s*\)\s*$/iu,'').trim();
 name=name.replace(/\s*\(\s*[a-zA-ZÀ-ÿ]+\s*(?:\d{4})?\s*\)\s*$/iu,'').trim();
 name=name.replace(/\s*[«"“][^"”»]+["”»]\s*/gu,' ').replace(/\s+/g,' ').trim();
 return name;
}
function mapParts(t){
 const name=cleanTripName(t?.name);
 return name.split(/\s+[-–—]\s+|\s+[-–—]\s*|\s*,\s*/).map(x=>x.trim()).filter(Boolean);
}
function cityLookupKey(name){
 const key=normName(name);
 if(/^dax\b/.test(key)&&/feria|f[eê]te/.test(key))return 'dax';
 if(['hague','the hague','den haag'].includes(key))return 'la haye';
 if(key==='wurburg'||key==='wurzburg')return 'wurtzbourg';
 return key;
}
function cachedPosition(name){const key=cityLookupKey(name);const c=offlineCities[key]||cache[key];if(!c)return null;const p=Array.isArray(c)?c:[Number(c.lat),Number(c.lon)];return validCoord(p)?p:null}
function tripPositions(t){const parts=mapParts(t);const pos=[];for(const name of parts){const c=cachedPosition(name);if(c)pos.push({name,coord:c})}if(!pos.length&&parts.length===1&&t.lat!=null&&t.lon!=null){const p=[Number(t.lat),Number(t.lon)];if(validCoord(p))pos.push({name:t.name,coord:p})}return pos}
function coordinates(t){return tripPositions(t)[0]?.coord||null}
let locatingInBackground=false,geocodeFailed=new Set(),locationProgress='';
async function locateMissingTrips(force=false){
 if(locatingInBackground)return;
 locatingInBackground=true;
 try{
  const names=new Map();
  for(const t of trips){for(const part of mapParts(t)){const key=cityLookupKey(part);if(!cachedPosition(part)&&(force||!geocodeFailed.has(key)))names.set(key,{name:part,country:t.country||''})}}
  const pending=[...names.values()];let done=0;
  for(const item of pending){
   const key=cityLookupKey(item.name);locationProgress=`Localisation ${++done}/${pending.length} : ${item.name}`;renderMap();
   try{
    let result;
    if(item.country){try{result=await geocode(item.name+', '+item.country)}catch{result=await geocode(item.name)}}
    else result=await geocode(item.name);
    if(result&&Number.isFinite(Number(result.lat))&&Number.isFinite(Number(result.lon))){cache[key]={lat:Number(result.lat),lon:Number(result.lon),name:item.name};localStorage.setItem('tpGeoV2',JSON.stringify(cache));geocodeFailed.delete(key)}
    else geocodeFailed.add(key);
   }catch(e){geocodeFailed.add(key);console.warn('Localisation impossible :',item.name,e.message)}
   renderMap();await sleep(1200);
  }
 }finally{locationProgress='';locatingInBackground=false;renderMap()}
}
function point(lat,lon,title,color,layer){return L.circleMarker([lat,lon],{radius:9,color:'#ffffff',weight:2.5,fillColor:color,fillOpacity:1,opacity:1}).bindPopup(el('span',title)).addTo(layer)}
let mapStatusFilter='all';
function renderMap(){
 tripLayer.clearLayers();const colors={past:'#1976d2',scheduled:'#f28c18',wish:'#9346d6'};
 // Filtre propre à la carte, indépendant du filtre des fiches de voyages.
 let visible=0,missing=0;const missingNames=[];const grouped=new Map();
 const allCityNames=new Map(),locatedCityNames=new Set();
 for(const t of trips){
  if(mapStatusFilter!=='all'&&status(t)!==mapStatusFilter)continue;
  const positions=tripPositions(t),parts=mapParts(t);
  for(const part of parts){
    const key=cityLookupKey(part);if(!key)continue;
    if(!allCityNames.has(key))allCityNames.set(key,part);
    if(!cachedPosition(part)&&!(t.lat!=null&&t.lon!=null&&parts.length===1)){missing++;missingNames.push(part)}
   }
  for(const {name,coord} of positions){
   if(!validCoord(coord))continue;
   const key=coord.map(x=>x.toFixed(4)).join(',');
   if(!grouped.has(key))grouped.set(key,{coord,items:[]});
   grouped.get(key).items.push({name,trip:t});visible++;locatedCityNames.add(cityLookupKey(name));
  }
 }
 // Each status gets its own coloured marker. Small offsets keep overlapping
 // statuses individually clickable; the original city centre remains unchanged.
 let markerCount=0;
 for(const {coord,items} of grouped.values()){
  const byStatus=new Map();
  for(const item of items){const st=status(item.trip);if(!byStatus.has(st))byStatus.set(st,[]);byStatus.get(st).push(item)}
  const categories=[...byStatus.keys()];
  categories.forEach((st,index)=>{
   const angle=categories.length===1?0:(index*2*Math.PI/categories.length-Math.PI/2);
   const delta=categories.length===1?0:0.00045;
   const lat=coord[0]+Math.sin(angle)*delta;
   const lon=coord[1]+Math.cos(angle)*delta/Math.max(0.25,Math.cos(coord[0]*Math.PI/180));
   const subset=byStatus.get(st);
   const marker=point(lat,lon,subset.map(x=>x.name).join(', '),colors[st],tripLayer);
   const popup=el('div');
   popup.append(el('strong',label[st]+' · '+subset.length+' voyage(s)'));
   for(const {name,trip} of subset){const line=el('p');line.textContent=`${name} · ${trip.start||'Sans date'}`;line.style.borderLeft=`4px solid ${colors[st]}`;line.style.paddingLeft='7px';popup.append(line)}
   marker.bindPopup(popup);
   // Permanent city labels: no hover and no zoom threshold.
   // Use textContent via a DOM node to avoid interpreting imported names as HTML.
   const cityLabel=el('span',[...new Set(subset.map(x=>x.name))].join(' / '));
   marker.bindTooltip(cityLabel,{permanent:true,direction:'right',offset:[12,0],opacity:1,className:'tp-city-label',interactive:false});
   markerCount++;
  });
 }
 const unique=[...new Set(missingNames)];
 const unresolved=[...allCityNames].filter(([key])=>!locatedCityNames.has(key)).map(([,name])=>name);
 const totalCities=allCityNames.size;
 $('mapStatus').textContent=`${trips.filter(t=>mapStatusFilter==='all'||status(t)===mapStatusFilter).length} voyage(s) affiché(s) · ${totalCities} ville(s) distincte(s) · ${locatedCityNames.size} ville(s) localisée(s) · ${grouped.size} position(s) GPS · ${markerCount} marqueur(s) · ${unresolved.length} ville(s) manquante(s). ${locationProgress}`;
 let details=$('missingDestinations');
 if(details){details.replaceChildren();if(unresolved.length){details.append(el('strong',`Villes non localisées (${unresolved.length}) : `),document.createTextNode(unresolved.join(', ')));} 
   const panel=el('details');panel.style.marginTop='10px';
   const summary=el('summary',`Contrôle des ${totalCities} villes (nom, statut, GPS)`);summary.style.cursor='pointer';panel.append(summary);
   const list=el('div');list.style.maxHeight='320px';list.style.overflowY='auto';list.style.padding='8px 0';
   for(const [key,name] of [...allCityNames].sort((a,b)=>a[1].localeCompare(b[1],'fr'))){
     const p=cachedPosition(name),st=[...new Set(trips.filter(t=>(mapStatusFilter==='all'||status(t)===mapStatusFilter)&&mapParts(t).some(x=>cityLookupKey(x)===key)).map(status))];
     const line=el('div',`${p?'✓':'✗'} ${name} · ${st.map(s=>label[s]).join(' / ')} · ${p?p.map(n=>n.toFixed(4)).join(', '):'GPS absent'}`);
     line.style.padding='3px 0';list.append(line);
   }
   panel.append(list);details.append(panel);}
}

document.querySelectorAll('[data-map-filter]').forEach(button=>{
 button.addEventListener('click',()=>{
  mapStatusFilter=button.dataset.mapFilter;
  document.querySelectorAll('[data-map-filter]').forEach(b=>{
   const active=b.dataset.mapFilter===mapStatusFilter;
   b.classList.toggle('active',active);
   b.setAttribute('aria-pressed',String(active));
  });
  renderMap();
 });
});

function renderTrips(){const host=$('trips');host.replaceChildren();const query=$('filter').value.toLowerCase(),filter=$('statusFilter').value;for(const t of [...trips].filter(t=>String(t?.name||'').toLowerCase().includes(query)&&(filter==='all'||status(t)===filter)).sort((a,b)=>(b.start||'').localeCompare(a.start||''))){const card=el('article',undefined,'trip '+status(t));card.append(el('h3',t.name+(t.country?' · '+t.country:'')),el('span',label[status(t)],'pill'),el('p',(t.start||'Sans date')+(t.end?' → '+t.end:'')));if(t.notes)card.append(el('p',t.notes.length>160?t.notes.slice(0,160)+'…':t.notes));const a=el('div',undefined,'actions'),edit=el('button','Modifier'),explore=el('button','Visiter'),del=el('button','Supprimer','secondary');edit.onclick=()=>openEditor(t);explore.onclick=()=>{$('city').value=t.name;switchTab('explore');searchCity()};del.onclick=async()=>{if(confirm('Supprimer ce voyage ?')){try{await api('/api/trips/'+t.id,{method:'DELETE'});await refresh()}catch(e){notice(e.message)}}};a.append(edit,explore,del);card.append(a);host.append(card)}if(!host.children.length)host.append(el('p','Aucun voyage trouvé.'))}
function render(){if(typeof renderV3==='function')renderV3();const past=trips.filter(t=>status(t)==='past').length,scheduled=trips.filter(t=>status(t)==='scheduled').length;$('stats').textContent=`${past} visités · ${scheduled} programmés · ${trips.length-past-scheduled} envies`;renderTrips();renderMap();renderCalendar();renderIdeas()}
async function refresh(){trips=(await api('/api/trips')).filter(t=>t&&typeof t==='object'&&typeof t.name==='string');render();locateMissingTrips()}
function switchTab(tab){activeTab=tab;document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id==='view-'+tab));document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));if(tab==='dashboard')setTimeout(()=>{map.invalidateSize();if(tripLayer.getLayers().length){const bounds=L.featureGroup(tripLayer.getLayers()).getBounds();if(bounds.isValid())map.fitBounds(bounds.pad(.08),{maxZoom:7})}},100);if(typeof onV3Tab==='function')onV3Tab(tab)}
document.querySelectorAll('.tabs button').forEach(x=>x.onclick=()=>switchTab(x.dataset.tab));$('filter').oninput=renderTrips;$('statusFilter').onchange=()=>{renderTrips();renderMap()};
function openEditor(t){$('tripForm').reset();$('tripId').value=t?.id||'';for(const k of ['name','country','kind','start','end','notes'])if(t&&t[k]!=null)$(k).value=t[k];$('formTitle').textContent=t?'Modifier le voyage':'Ajouter un voyage';$('editor').showModal()}
$('new').onclick=()=>openEditor();$('cancel').onclick=()=>$('editor').close();
$('tripForm').onsubmit=async e=>{e.preventDefault();try{const id=$('tripId').value;const obj={name:cleanTripName($('name').value),country:$('country').value,kind:$('kind').value,start:$('start').value,end:$('end').value,notes:$('notes').value,lat:null,lon:null};if(id){const old=trips.find(t=>t.id===id);if(old&&old.name===obj.name&&old.country===obj.country){obj.lat=old.lat;obj.lon=old.lon}}await api('/api/trips'+(id?'/'+id:''),{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});$('editor').close();await refresh();notice('Voyage enregistré')}catch(err){notice(err.message)}};
// Geocodage universel : la liste locale n'est qu'un raccourci.
// Pays utilise pour lever les homonymies ; le cache est distinct par pays.
const tpCountryCodes={'France':'FR','Belgique':'BE','Andorre':'AD','Autriche':'AT','Allemagne':'DE','Italie':'IT','Espagne':'ES','Portugal':'PT','Pays-Bas':'NL','Suisse':'CH','Luxembourg':'LU','Royaume-Uni':'GB','Irlande':'IE','Danemark':'DK','Suède':'SE','Norvège':'NO','Finlande':'FI','Pologne':'PL','Tchéquie':'CZ','République tchèque':'CZ','Grèce':'GR','Croatie':'HR','Hongrie':'HU','Roumanie':'RO','Slovaquie':'SK','Slovénie':'SI','Bulgarie':'BG','Serbie':'RS','Malte':'MT','Monaco':'MC','Estonie':'EE','Lettonie':'LV','Lituanie':'LT','Islande':'IS','Chypre':'CY','Ukraine':'UA','Albanie':'AL','Bosnie-Herzégovine':'BA','Monténégro':'ME','Macédoine du Nord':'MK','Kosovo':'XK','Moldavie':'MD','Biélorussie':'BY','Turquie':'TR','Saint-Marin':'SM','Liechtenstein':'LI'};
function tpValidLocation(p){return p&&Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))&&Math.abs(Number(p.lat))<=90&&Math.abs(Number(p.lon))<=180&&(Math.abs(Number(p.lat))+Math.abs(Number(p.lon))>0.001)}
function tpCountry(){return $('europeCountry')?.value||''}
function tpCacheLocation(key,result){if(!tpValidLocation(result))return;cache[key]={lat:Number(result.lat),lon:Number(result.lon),name:result.name};try{localStorage.setItem('tpGeoV2',JSON.stringify(cache))}catch(e){console.warn('Cache GPS indisponible',e)}}
async function tpRemoteLocation(city,country){
 const url='https://geocoding-api.open-meteo.com/v1/search?name='+encodeURIComponent(city)+'&count=100&language=fr&format=json';
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(url,{signal:controller.signal});
  if(!response.ok)throw Error('Service GPS en ligne indisponible ('+response.status+')');
  const json=await response.json();
  let candidates=(json.results||[]).filter(x=>tpValidLocation({lat:x.latitude,lon:x.longitude}));
  const code=tpCountryCodes[country];
  if(code){candidates=candidates.filter(x=>x.country_code===code);}
  if(!candidates.length)throw Error('Ville non trouvée'+(country?' en '+country:'')+' : '+city);
  const norm=s=>cityLookupKey(s).replace(/[^a-z0-9]/g,'');
  candidates.sort((a,b)=>Number(norm(b.name)===norm(city))-Number(norm(a.name)===norm(city)));
  const found=candidates[0];
  return {lat:Number(found.latitude),lon:Number(found.longitude),name:found.name+', '+found.country};
 }finally{clearTimeout(timeout)}
}
async function geocode(q,country=''){
 const city=String(q||'').trim();if(!city)throw Error('Indique une ville.');
 const key=cityLookupKey(city), scopedKey=key+'|'+cityLookupKey(country);
 const saved=cache[scopedKey];if(tpValidLocation(saved))return {...saved,lat:Number(saved.lat),lon:Number(saved.lon)};
 // Pour une ville sans pays, on peut utiliser les anciennes coordonnees locales.
 const known=offlineCities[key];
 if(Array.isArray(known)&&validCoord(known)&&Math.abs(known[0])+Math.abs(known[1])>0.001){
  const found={lat:known[0],lon:known[1],name:city};tpCacheLocation(scopedKey,found);return found;
 }
 // Eviter de reutiliser un cache non qualifie pour un homonyme dans un autre pays.
 if(!country&&tpValidLocation(cache[key]))return {...cache[key],lat:Number(cache[key].lat),lon:Number(cache[key].lon)};
 let lastError;
 try{const found=await tpRemoteLocation(city,country);tpCacheLocation(scopedKey,found);return found}catch(e){lastError=e}
 // Deuxieme fournisseur : geocodage du serveur local (Nominatim).
 try{
  const query=country?city+', '+country:city;
  const data=await api('/api/geocode?q='+encodeURIComponent(query));
  if(!Array.isArray(data)||!data.length)throw Error('Aucun résultat');
  const item=data.find(x=>tpValidLocation(x));
  if(!item)throw Error('Coordonnées invalides');
  const found={lat:Number(item.lat),lon:Number(item.lon),name:item.display_name||city};
  tpCacheLocation(scopedKey,found);return found;
 }catch(e){throw Error('Ville non localisée : '+city+(country?' ('+country+')':'')+'. '+(lastError?.message||e.message))}
}
$('locate').onclick=async()=>{const btn=$('locate');btn.disabled=true;btn.textContent='Localisation en cours…';try{await locateMissingTrips(true);notice('Recherche terminée. Consulte la liste des villes encore non localisées sous la carte.')}finally{btn.disabled=false;btn.textContent='📍 Relancer la localisation'}};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(trips,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='mes-voyages-travelplanner.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),500)};
async function searchCity(){try{const q=$('city').value.trim();if(!q){notice('Indique une ville');return null}selected=await geocode(q,tpCountry());$('results').replaceChildren(el('p','Ville localisée : '+(selected.name||$('city').value.trim())));notice('Ville localisée');return selected}catch(e){selected=null;notice(e.message);return null}}
$('search').onclick=searchCity;
const hav=(a,b,c,d)=>{const r=Math.PI/180,x=Math.sin((c-a)*r/2)**2+Math.cos(a*r)*Math.cos(c*r)*Math.sin((d-b)*r/2)**2;return 6371*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))};
// V4.2: robust tourism planner with server fallback and explicit errors.
let visitMap=null,visitMapLayer=null;
function showVisitMap(plan){
 const box=$('visitMap');
 if(!plan.length||typeof L==='undefined'){box.hidden=true;return}
 box.hidden=false;
 if(!visitMap){visitMap=L.map(box,{scrollWheelZoom:false});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).addTo(visitMap);visitMapLayer=L.layerGroup().addTo(visitMap)}
 visitMapLayer.clearLayers();
 const pts=plan.map(p=>[p.lat,p.lon]);
 plan.forEach((p,i)=>L.circleMarker([p.lat,p.lon],{radius:9,color:'#fff',weight:2,fillColor:'#1976d2',fillOpacity:1}).bindPopup(`${i+1}. ${p.name}`).addTo(visitMapLayer));
 if(pts.length>1)L.polyline(pts,{color:'#f28c18',weight:3,dashArray:'6,8'}).addTo(visitMapLayer);
 setTimeout(()=>{visitMap.invalidateSize();if(pts.length===1)visitMap.setView(pts[0],14);else visitMap.fitBounds(L.latLngBounds(pts).pad(.2))},150);
}
function visitScroll(){setTimeout(()=>$('visitOutput').scrollIntoView({behavior:'smooth',block:'start'}),80)}
async function buildVisitPlan(){
 const host=$('results');host.replaceChildren();$('visitMap').hidden=true;visitScroll();
 const btn=$('plan');btn.disabled=true;
 try {
  const city=$('city').value.trim();if(!city)throw Error('Saisis le nom d’une ville.');
  host.append(el('p','Localisation et recherche des lieux en cours…'));
  const selectedCountry=tpCountry();
  // La recherche libre fonctionne pour toute ville, pas uniquement la liste proposee.
  const loc=await geocode(city,selectedCountry);
  if(!tpValidLocation(loc))throw Error('Ville non localisée : '+city+'. Vérifie le pays et réessaie.');
  const duration=Number($('duration').value);
  const raw=await api(`/api/places?lat=${encodeURIComponent(loc.lat)}&lon=${encodeURIComponent(loc.lon)}&city=${encodeURIComponent(city)}&country=${encodeURIComponent(selectedCountry)}`);
  const source=raw.source||'online';
  const places=raw.elements;
  if(!Array.isArray(places))throw Error('Réponse touristique invalide.');
  const goodPoint=p=>p&&Number.isFinite(Number(p.lat))&&Number.isFinite(Number(p.lon))&&Math.abs(Number(p.lat))<=90&&Math.abs(Number(p.lon))<=180&&(Math.abs(Number(p.lat))+Math.abs(Number(p.lon))>0.001);
  const geo=goodPoint(loc)?{lat:Number(loc.lat),lon:Number(loc.lon)}:null;
  const providerCenter=goodPoint(raw.center)?{lat:Number(raw.center.lat),lon:Number(raw.center.lon)}:null;
  const coords=places.map(p=>({lat:Number(p.lat??p.center?.lat),lon:Number(p.lon??p.center?.lon)})).filter(goodPoint);
  // Never use an empty or remote cache to infer a city center.
  const nearGeo=geo?coords.filter(p=>hav(geo.lat,geo.lon,p.lat,p.lon)<=12):coords;
  // A median of several nearby landmarks is a robust fallback if the geocoder failed.
  const median=values=>{const a=[...values].sort((x,y)=>x-y);return a[Math.floor(a.length/2)]};
  const landmarkCenter=nearGeo.length>=3?{lat:median(nearGeo.map(p=>p.lat)),lon:median(nearGeo.map(p=>p.lon))}:null;
  const landmarksNearMedian=landmarkCenter?nearGeo.filter(p=>hav(landmarkCenter.lat,landmarkCenter.lon,p.lat,p.lon)<=12):[];
  const inferred=landmarksNearMedian.length>=3?landmarkCenter:null;
  // For a local catalog, use its own position. Otherwise, trust the geocoder only
  // when it agrees with the cluster of actual monuments.
  let anchor=source==='local'?(inferred||providerCenter||geo):(geo||providerCenter||inferred);
  if(inferred&&(!anchor||(!geo&&hav(anchor.lat,anchor.lon,inferred.lat,inferred.lon)>12)))anchor=inferred;
  if(!anchor)throw Error('Localisation impossible pour '+city+' : aucun centre GPS fiable disponible.');

  const seen=new Set();
  let pool=places.map(p=>({name:p.tags?.['name:fr']||p.tags?.name,kind:p.tags?.tourism||p.tags?.historic||p.tags?.leisure||p.tags?.amenity||'site',lat:Number(p.lat??p.center?.lat),lon:Number(p.lon??p.center?.lon),priority:(p.tags?.wikipedia?6:0)+(p.tags?.wikidata?4:0)+(p.tags?.heritage?3:0)+(p.tags?.historic?2:0)+(p.tags?.tourism==='attraction'?2:0)+(p.tags?.tourism==='museum'?2:0)-(p.tags?.tourism==='information'?4:0)}))
   .filter(p=>p.name&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&(Math.abs(p.lat)+Math.abs(p.lon)>0.000001)&&!/^(null island|bouée soul)$/i.test(p.name.trim()))
   .filter(p=>{const k=String(p?.name||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();if(seen.has(k))return false;seen.add(k);return true});
  // Prefer nearby places; avoid long detours in short visits.
  pool=pool.filter(p=>hav(anchor.lat,anchor.lon,p.lat,p.lon)<=(duration<=60?2.5:duration<=240?5:8));
  // Ranking favors notable heritage; proximity is still used to limit travel.
  const importance=p=>p.priority+(p.kind==='museum'?2:0)+(p.kind==='castle'?3:0)+(p.kind==='monument'?3:0);
  let remain=duration,cur=anchor;const plan=[];
  while(pool.length&&remain>=12&&plan.length<Math.min(40,Math.ceil(duration/20))){
   pool.sort((a,b)=>(hav(cur.lat,cur.lon,a.lat,a.lon)*1.5-importance(a)*.35)-(hav(cur.lat,cur.lon,b.lat,b.lon)*1.5-importance(b)*.35));
   let chosen=-1,walk=0,visit=0;
   for(let i=0;i<pool.length;i++){
    const p=pool[i];const w=Math.max(2,Math.ceil(hav(cur.lat,cur.lon,p.lat,p.lon)/3.8*60));
    const v=p.kind==='museum'?Math.min(60,Math.max(15,remain-w)):Math.min(25,Math.max(10,remain-w));
    if(w+v<=remain){chosen=i;walk=w;visit=v;break}
   }
   if(chosen<0)break;
   const [p]=pool.splice(chosen,1);plan.push({...p,walk,visit});remain-=walk+visit;cur=p;
  }
  host.replaceChildren(el('h3',`Programme pour ${city} · ${duration} min`));
  if(source==='cache')host.append(el('p','Lieux enregistrés lors d’une recherche précédente : disponibles hors ligne.','hint'));
  if(source==='wikipedia')host.append(el('p','Lieux trouvés sur Wikipédia : sélection géographique à vérifier, non classée par importance touristique.','hint'));
  if(source==='online')host.append(el('p','Lieux découverts sur OpenStreetMap et enregistrés pour une prochaine utilisation hors ligne.','hint'));
  if(source==='local')host.append(el('p','Mode hors ligne : sélection de monuments enregistrés localement. Vérifie les lieux, les horaires et les accès avant ton départ.','hint'));
  if(source==='unavailable')host.append(el('p','La recherche en ligne est momentanément indisponible et cette ville n’a pas encore de lieux enregistrés. Réessaie avec une connexion Internet.','hint'));
  if(!plan.length){host.append(el('p','Aucun lieu touristique exploitable trouvé à proximité. Essaie une ville du catalogue local ou relance la recherche en ligne.'));return}
  const ol=el('ol');ol.className='visit-steps';let used=0;
  for(const p of plan){
   if(duration>480&&used>0&&Math.floor(used/480)!==Math.floor((used+p.walk+p.visit)/480))ol.append(el('li',`Pause / nouvelle journée (repère indicatif)`));
   const li=el('li');li.append(el('strong',p.name),el('p',`Déplacement estimé : ${p.walk} min · Visite : ${p.visit} min · ${p.kind}`));ol.append(li);used+=p.walk+p.visit;
  }
  host.append(ol,el('p',`Temps estimé utilisé : ${used} min · Reste : ${remain} min. Les marches sont estimées à vol d’oiseau, pas sur le réseau piéton. Horaires et accès à vérifier.`, 'hint'));
  showVisitMap(plan);visitScroll();notice(`${plan.length} étape(s) proposées sous le formulaire.`);
 }catch(e){$('visitMap').hidden=true;host.replaceChildren(el('p','Impossible de créer le programme : '+e.message));visitScroll();notice('Programme indisponible : '+e.message)}
 finally{btn.disabled=false}
}
// European country -> city picker. Manual entry remains available for any other city.
let europeCities={};
async function loadEuropeanCities(){
 try{
  const r=await fetch('/europe-cities.json');if(!r.ok)throw Error('Liste indisponible');
  europeCities=await r.json();
  const country=$('europeCountry');
  Object.keys(europeCities).sort((a,b)=>a.localeCompare(b,'fr')).forEach(name=>{const o=document.createElement('option');o.value=name;o.textContent=name;country.append(o)});
 }catch(e){console.warn('Liste de villes européennes :',e.message)}
}
$('europeCountry').addEventListener('change',()=>{
 const name=$('europeCountry').value,select=$('europeCity');
 select.replaceChildren();const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent=name?'Choisir une ville…':'Choisir un pays d’abord';select.append(placeholder);
 select.disabled=!name;
 for(const city of (europeCities[name]||[])){const option=document.createElement('option');option.value=city;option.textContent=city;select.append(option)}
 // La ville saisie librement reste conservee quand le pays change.
});
$('europeCity').addEventListener('change',()=>{$('city').value=$('europeCity').value;selected=null});
$('city').addEventListener('input',()=>{if($('city').value!==$('europeCity').value)$('europeCity').value=''});
loadEuropeanCities();
$('plan').onclick=buildVisitPlan;
$('makeRoute').onclick=async()=>{const host=$('routeResults');host.replaceChildren();try{const names=$('stops').value.split(/[,\n;]+/).map(x=>x.trim()).filter(Boolean);if(names.length<2||names.length>10)throw Error('Indique entre 2 et 10 villes.');const places=[];for(const name of names){places.push(await geocode(name));await sleep(1200)}const coords=places.map(p=>p.lon+','+p.lat).join(';');const mode=$('routeMode').value;const result=mode==='driving'?await api('/api/route?profile=driving&coords='+encodeURIComponent(coords)):null;const route=result?.routes?.[0];if(mode==='train'){const km=places.slice(1).reduce((sum,p,i)=>sum+hav(places[i].lat,places[i].lon,p.lat,p.lon),0);const stops=Math.max(0,places.length-1)*Number($('routeStopMinutes').value||0);host.append(el('h3',`Train : ${Math.round(km)} km à vol d’oiseau · ${Math.round(km/85*10)/10} h théoriques hors correspondances · ${stops} min de visites`));host.append(el('p','Ce calcul n’est PAS un itinéraire ferroviaire. Vérifie les lignes, les horaires et les billets auprès d’un opérateur ferroviaire.','hint'));const ol=el('ol');places.forEach(p=>ol.append(el('li',p.name)));host.append(ol);return}if(!route?.geometry?.coordinates)throw Error('Aucun trajet routier trouvé.');workLayer.clearLayers();const line=route.geometry.coordinates.map(([lon,lat])=>[lat,lon]);L.polyline(line,{color:'#db682d',weight:5}).addTo(workLayer);for(const p of places)point(p.lat,p.lon,p.name,'#d5662a',workLayer);host.append(el('h3',`${Math.round(route.distance/1000)} km · ${Math.round(route.duration/3600*10)/10} h de conduite · ${Math.max(0,places.length-1)*Number($('routeStopMinutes').value||0)} min de visites aux arrêts`));const ol=el('ol');places.forEach(p=>ol.append(el('li',p.name)));host.append(ol,el('p','Tracé affiché dans l’onglet Carte & voyages. Les temps ne comprennent pas les visites, pauses ou embouteillages.','hint'));notice('Trajet calculé : ouvre la carte');switchTab('dashboard');setTimeout(()=>map.fitBounds(L.latLngBounds(line).pad(.12)),120)}catch(e){notice('Trajet impossible : '+e.message);host.append(el('p',e.message))}};
$('routeClear').onclick=()=>{workLayer.clearLayers();$('routeResults').replaceChildren()};
// V4.2: NEW destinations only, including neighbors of past trips.
const normCity=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
const recommendations=[
 // Name, theme, description, neighboring city (if any)
 ['Amiens','city','Cathédrale gothique et quartier Saint-Leu','Rouen'],
 ['Honfleur','city','Vieux Bassin, galeries et port normand','Deauville'],
 ['Giverny','city','Village impressionniste et jardins de Monet','Evreux'],
 ['Provins','city','Cité médiévale et remparts','Troyes'],
 ['Beaune','city','Hospices et patrimoine bourguignon','Dijon'],
 ['Besançon','city','Citadelle et vieille ville sur le Doubs','Dijon'],
 ['Arras','city','Places baroques et beffroi','Lille'],
 ['Saint-Omer','nature','Marais audomarois et patrimoine','Lille'],
 ['Le Crotoy','nature','Baie de Somme et oiseaux','Dieppe'],
 ['Yport','nature','Falaises et village côtier','Fecamp'],
 ['Le Tréport','nature','Falaises et funiculaire','Dieppe'],
 ['Albi','city','Cité épiscopale et musée Toulouse-Lautrec','Montpellier'],
 ['Uzès','city','Ruelles, marché et patrimoine','Nîmes'],
 ['Arles','city','Arènes romaines et photographie','Avignon'],
 ['Sisteron','nature','Citadelle et paysages provençaux','Aix en Provence'],
 ['Cassis','nature','Port et calanques (accès réglementé)','Marseille'],
 ['Moustiers-Sainte-Marie','nature','Village provençal et gorges du Verdon','Aix en Provence'],
 ['Gruyères','city','Village médiéval et paysages suisses','Lausanne'],
 ['Thun','nature','Lac, château et Alpes bernoises','Berne'],
 ['Lucerne','city','Pont de la Chapelle et lac','Zurich'],
 ['Lugano','nature','Lac et promenades tessinoises','Milan'],
 ['Maastricht','city','Centre historique sur la Meuse','Liege'],
 ['Haarlem','city','Canaux et musées','Amsterdam'],
 ['Delft','city','Faïence et canaux','Rotterdam'],
 ['Gouda','city','Centre ancien et traditions fromagères','Rotterdam'],
 ['Amersfoort','city','Canaux et portes médiévales','Utrecht'],
 ['Breda','city','Patrimoine et places animées','Antwerp'],
 ['Tournai','city','Cathédrale et beffroi','Mons'],
 ['Ypres','city','Patrimoine et mémoire de la Grande Guerre','Ghent'],
 ['Trèves','city','Vestiges romains et Porta Nigra','Metz'],
 ['Heidelberg','city','Château et vieux pont','Francfort'],
 ['Bonn','city','Musées et patrimoine rhénan','Cologne'],
 ['Coblence','nature','Confluence Rhin-Moselle et forteresse','Cologne'],
 ['Fribourg-en-Brisgau','nature','Vieille ville et Forêt-Noire','Basel'],
 ['Baden-Baden','nature','Thermes et promenade en Forêt-Noire','Strasbourg'],
 ['Ratisbonne','city','Centre médiéval classé UNESCO','Munich'],
 ['Pise','city','Place des Miracles et tour penchée','Turin'],
 ['Bergame','city','Città Alta et remparts','Milan'],
 ['Vérone','city','Arènes et ruelles historiques','Milan'],
 ['Bilbao','city','Musées et architecture contemporaine','Bayonne'],
 ['Saint-Sébastien','nature','Baie de la Concha et gastronomie','Hendaye'],
 ['Gérone','city','Vieille ville et quartier juif','Barcelone'],
 ['Tolède','city','Cité historique multiculturelle','Madrid'],
 ['Braga','city','Sanctuaire du Bom Jesus et patrimoine','Porto'],
 ['Coimbra','city','Université historique et ruelles','Lisbonne'],
 ['Avila','city','Remparts médiévaux','Madrid'],
 ['Sarlat-la-Canéda','city','Centre médiéval du Périgord','Bordeaux'],
 ['Rocamadour','nature','Village perché et vallée de l’Alzou','Brive'],
 ['Fête des Lumières à Lyon','events','Événement lumineux, dates et programme à vérifier','Lyon'],
 ['Festival d’Avignon','events','Théâtre et spectacles, dates à vérifier','Avignon'],
 ['Marchés de Noël de Nuremberg','events','Marchés de Noël, calendrier à vérifier','Munich'],
 ['Festival des cerfs-volants de Berck','events','Événement côtier, dates à vérifier','Le Touquet']
];
// Split composite trip names only on the explicitly used separator " - ".
function knownCityKeys(){
 const set=new Set();
 for(const t of trips){
  const name=String(t.name||'').replace(/[“”"']/g,' ');
  for(const part of name.split(/\s+-\s+/)){
   const key=normCity(part);if(key)set.add(key);
  }
 }
 return set;
}
function renderIdeas(){
 const host=$('ideasList');host.replaceChildren();
 const known=knownCityKeys(),theme=$('ideaTheme').value;
 const mode=$('ideaMode')?.value||'all';
 const prior=trips.filter(t=>status(t)==='past').flatMap(t=>String(t.name||'').split(/\s+-\s+/).map(normCity));
 const visited=new Set(prior);
 const options=recommendations.filter(([name,cat,desc,near])=>
  (theme==='all'||theme===cat)&&!known.has(normCity(name))&&
  // Events may have a visited city, but the event itself is a different experience.
  !(cat!=='events'&&visited.has(normCity(name)))&&
  (mode!=='near'||(near&&visited.has(normCity(near)))));
 $('ideasCount').textContent=`${options.length} idée(s) inédites hors de ta liste`;
 for(const [name,cat,desc,near] of options){
  const card=el('article',undefined,'idea');
  card.append(el('h3',name),el('p',desc),el('span',cat==='city'?'Culture & villes':cat==='nature'?'Nature & paysages':'Événements','pill'));
  if(near)card.append(el('p',`À associer à : ${near}${visited.has(normCity(near))?' (déjà visitée)':''}`,'hint'));
  const actions=el('div',undefined,'actions'),visit=el('button','Créer un programme'),add=el('button','Ajouter à mes envies','secondary');
  visit.onclick=()=>{$('city').value=name.startsWith('Fête des Lumières')?'Lyon':name.startsWith('Festival d’Avignon')?'Avignon':name.startsWith('Marchés de Noël')?'Nuremberg':name.startsWith('Festival des cerfs-volants')?'Berck':name;switchTab('explore');buildVisitPlan()};
  add.onclick=async()=>{try{await api('/api/trips',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,kind:'future',start:'',end:'',country:'',notes:'Suggestion Travel Planner V4.2 : '+desc+(near?' · À proximité de '+near:'')})});await refresh();notice('Ajouté aux envies : '+name)}catch(e){notice(e.message)}};
  actions.append(visit,add);card.append(actions);host.append(card)
 }
 if(!options.length)host.append(el('p','Aucune suggestion pour ces filtres. Choisis un autre thème ou « Toutes les suggestions ».'));
}
$('ideaTheme').onchange=renderIdeas;$('ideaMode').onchange=renderIdeas;$('refreshIdeas').onclick=renderIdeas;
function renderCalendar(){const y=month.getFullYear(),m=month.getMonth(),first=new Date(y,m,1),days=new Date(y,m+1,0).getDate(),offset=(first.getDay()+6)%7;$('monthTitle').textContent=new Intl.DateTimeFormat('fr-FR',{month:'long',year:'numeric'}).format(first);const grid=$('calendarGrid');grid.replaceChildren();for(const d of ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'])grid.append(el('div',d,'calhead'));for(let i=0;i<offset;i++)grid.append(el('div','','calday muted'));for(let d=1;d<=days;d++){const cell=el('div',undefined,'calday');const dayKey=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;const todayKey=`${new Date().getFullYear()}-${String(new Date().getMonth()+1).padStart(2,'0')}-${String(new Date().getDate()).padStart(2,'0')}`;if(dayKey<todayKey)cell.classList.add('cal-past');if(dayKey===todayKey)cell.classList.add('cal-today');cell.append(el('strong',String(d)));const day=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;for(const t of trips.filter(t=>t.start&&t.start<=day&&(t.end||t.start)>=day)){const badge=el('span',t.name,'event '+status(t));badge.title=`${t.start} — ${t.end||t.start}`;cell.append(badge)}grid.append(cell)}}
$('prevMonth').onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()-1,1);renderCalendar()};$('nextMonth').onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()+1,1);renderCalendar()};
// Import de la liste Keep : nom, dates et statut sont des champs distincts.
const frenchMonths={janvier:1,fevrier:2,mars:3,avril:4,mai:5,juin:6,juillet:7,aout:8,septembre:9,octobre:10,novembre:11,decembre:12};
function isoFrenchDate(day,month,year){const m=frenchMonths[normName(month)],d=Number(day),y=Number(year);if(!m||!Number.isInteger(d)||d<1||d>31||y<2000||y>2100)return '';const date=new Date(Date.UTC(y,m-1,d));return date.getUTCFullYear()===y&&date.getUTCMonth()===m-1&&date.getUTCDate()===d?`${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`:''}
function parseVoyageLine(line){
 let raw=String(line||'').replace(/^\uFEFF/,'').trim();
 if(!raw||/^voyages\s*$/i.test(raw)||/^[-#=\s]+$/.test(raw))return null;
 // Format normalise : Ville | JJ/MM/AAAA (ou periode) | Realisee / Non realisee.
 if(raw.includes('|')){
  const fields=raw.split('|').map(x=>x.trim());
  if(fields.length<3)return null;
  const name=cleanTripName(fields[0]);if(name.length<2)return null;
  const dateText=fields[1],state=normName(fields[2]);
  let start='',end='',dateNote='';
  const single=dateText.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const range=dateText.match(/^(\d{1,2})\s*[-–]\s*(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  const monthYear=dateText.match(/^(\d{1,2})\/(\d{4})$/);
  if(single)start=isoNumericDate(single[1],single[2],single[3]);
  else if(range){start=isoNumericDate(range[1],range[3],range[4]);end=isoNumericDate(range[2],range[3],range[4])}
  else if(monthYear)dateNote=dateText;
  else if(!/^(?:date non precisee|)$/i.test(normName(dateText)))dateNote=dateText;
  const kind=state==='realisee'||state==='realise'||state==='visite'?'past':'future';
  const notes=['Import liste Voyages',...(dateNote?['Date indicative : '+dateNote]:[])].join(' — ');
  return {name,kind,start,end,country:'',notes,lat:null,lon:null};
 }
 // Ancien format Google Keep : numero + ville (date) + coche.
 raw=raw.replace(/^(?:[0-9#️⃣⃣\uFE0F]+\s*)+/u,'').trim();
 const visited=/✅/.test(raw),scheduled=/☑/.test(raw);
 raw=raw.replace(/[✅☑❌\uFE0F]/gu,'').trim();
 let start='',end='',dateNote='';
 const parens=[...raw.matchAll(/\(([^()]*)\)/g)];
 for(const match of parens){
  const inner=match[1].trim(),normalized=normName(inner);
  const full=normalized.match(/^(\d{1,2})(?:\s*\/\s*(\d{1,2}))?\s+([a-z]+)\s+(\d{4})$/);
  if(full){start=isoFrenchDate(full[1],full[3],full[4]);if(full[2])end=isoFrenchDate(full[2],full[3],full[4]);dateNote=inner;raw=raw.replace(match[0],'').trim();break}
  const monthOnly=normalized.match(/^([a-z]+)(?:\s+(\d{4}))?$/);
  if(monthOnly&&frenchMonths[monthOnly[1]]){dateNote=inner;raw=raw.replace(match[0],'').trim();break}
 }
 const events=[...raw.matchAll(/["“«]\s*([^"”»]+?)\s*["”»]/g)].map(x=>x[1].trim());
 const name=cleanTripName(raw);if(name.length<2)return null;
 const notes=['Import liste Voyages',...events.map(x=>'Événement : '+x),...(dateNote&&!start?['Date indicative : '+dateNote]:[])].join(' — ');
 return {name,kind:visited?'past':'future',start,end,country:'',notes,lat:null,lon:null};
}
function isoNumericDate(day,month,year){
 const d=Number(day),m=Number(month),y=Number(year);
 if(!Number.isInteger(d)||!Number.isInteger(m)||!Number.isInteger(y)||y<2000||y>2100||m<1||m>12||d<1||d>31)return '';
 const v=new Date(Date.UTC(y,m-1,d));
 return v.getUTCFullYear()===y&&v.getUTCMonth()===m-1&&v.getUTCDate()===d?`${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`:'';
}
$('importVoyages').onchange=async e=>{
 const file=e.target.files?.[0];e.target.value='';if(!file)return;
 try{
  const lines=(await file.text()).split(/\r?\n/),parsed=lines.map(parseVoyageLine).filter(Boolean);
  if(!parsed.length)throw Error('Aucune ligne de voyage reconnue.');
  const existing=new Set(trips.filter(t=>t&&typeof t.name==='string').map(t=>`${normName(cleanTripName(t.name))}|${t.start||''}`));
  const additions=parsed.filter(t=>{const key=`${normName(t.name)}|${t.start||''}`;if(existing.has(key))return false;existing.add(key);return true});
  if(!confirm(`${parsed.length} voyages reconnus, ${additions.length} nouveaux.\nLes ${trips.length} voyages existants seront conservés.\nImporter les nouveaux voyages ?`))return;
  let added=0;for(const t of additions){await api('/api/trips',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(t)});added++}
  await refresh();notice(`${added} voyage(s) ajouté(s), ${parsed.length-added} doublon(s) ignoré(s).`);
 }catch(err){notice('Import liste : '+err.message)}
};
$('import').onchange=async e=>{let imported=0;for(const file of e.target.files){try{const content=await file.text();let title=file.name.replace(/\.(txt|json)$/i,''),notes=content,date='';if(file.name.toLowerCase().endsWith('.json')){const j=JSON.parse(content);title=j.title||title;notes=j.textContent||j.text||'';if(j.createdTimestampUsec){const n=Number(j.createdTimestampUsec)/1000;if(Number.isFinite(n))date=new Date(n).toISOString().slice(0,10)}}await api('/api/trips',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:title,kind:'future',start:date,end:'',country:'',notes})});imported++}catch(err){notice(`Import ${file.name} : ${err.message}`)}}e.target.value='';await refresh();notice(`${imported} note(s) importée(s). Vérifie les dates et les doublons.`)};
refresh().catch(e=>notice(e.message));
