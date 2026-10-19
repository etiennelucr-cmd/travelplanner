/* Travel Planner V6.10 - weather forecast for the chosen city (14 days). */
(()=>{
 'use strict';
 const cityInput=document.getElementById('city');
 const countrySelect=document.getElementById('europeCountry');
 const citySelect=document.getElementById('europeCity');
 const status=document.getElementById('weatherStatus');
 const days=document.getElementById('weatherDays');
 const button=document.getElementById('weatherRefresh');
 if(!cityInput||!status||!days||!button)return;
 let requestNumber=0, debounce;
 const icons=code=>code===0?'☀️':code<=3?'⛅':code<=48?'🌫️':code<=67?'🌧️':code<=77?'❄️':code<=82?'🌦️':code<=86?'🌨️':'⛈️';
 const weatherName=code=>code===0?'Ensoleillé':code<=3?'Nuageux':code<=48?'Brume / brouillard':code<=67?'Pluie':code<=77?'Neige':code<=82?'Averses':code<=86?'Averses de neige':'Orage';
 const valid=(lat,lon)=>Number.isFinite(Number(lat))&&Number.isFinite(Number(lon))&&Math.abs(Number(lat))<=90&&Math.abs(Number(lon))<=180&&(Math.abs(Number(lat))+Math.abs(Number(lon))>0.001);
 const fetchJson=async url=>{const ctrl=new AbortController();const timeout=setTimeout(()=>ctrl.abort(),12000);try{const response=await fetch(url,{signal:ctrl.signal});if(!response.ok)throw Error('Service météo indisponible ('+response.status+')');return await response.json()}finally{clearTimeout(timeout)}};
 const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
 const countryCodes={'France':'FR','Belgique':'BE','Andorre':'AD','Autriche':'AT','Allemagne':'DE','Italie':'IT','Espagne':'ES','Portugal':'PT','Pays-Bas':'NL','Suisse':'CH','Luxembourg':'LU','Royaume-Uni':'GB','Irlande':'IE','Danemark':'DK','Suède':'SE','Norvège':'NO','Finlande':'FI','Pologne':'PL','Tchéquie':'CZ','République tchèque':'CZ','Grèce':'GR','Croatie':'HR','Hongrie':'HU','Roumanie':'RO','Slovaquie':'SK','Slovénie':'SI','Bulgarie':'BG','Serbie':'RS','Malte':'MT','Monaco':'MC'};
 async function locate(city,country){
   // Prefer the exact city/country pair, independent of the Travel Planner geocoder cache.
   const code=countryCodes[country];
   const url='https://geocoding-api.open-meteo.com/v1/search?name='+encodeURIComponent(city)+'&count=20&language=fr&format=json';
   const result=await fetchJson(url);
   let matches=(result.results||[]).filter(r=>valid(r.latitude,r.longitude));
   if(code){const filtered=matches.filter(r=>r.country_code===code);if(filtered.length)matches=filtered;else throw Error('Ville non trouvée dans le pays sélectionné.');}
   const wanted=normalize(city);
   matches.sort((a,b)=>(normalize(b.name)===wanted?1:0)-(normalize(a.name)===wanted?1:0));
   if(!matches.length)throw Error('Ville non localisée par le service météo.');
   return matches[0];
 }
 async function load(){
   const city=cityInput.value.trim();
   const country=countrySelect?.value||'';
   const current=++requestNumber;
   days.replaceChildren();
   if(!city){status.textContent='Choisis une ville pour afficher la météo.';return;}
   status.textContent='Recherche météo pour '+city+'…';
   button.disabled=true;
   try{
     const location=await locate(city,country);
     if(current!==requestNumber)return;
     const url='https://api.open-meteo.com/v1/forecast?latitude='+encodeURIComponent(location.latitude)+'&longitude='+encodeURIComponent(location.longitude)+'&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=14';
     const result=await fetchJson(url);
     if(current!==requestNumber)return;
     const daily=result.daily;
     if(!daily||!Array.isArray(daily.time)||!daily.time.length)throw Error('Prévisions indisponibles pour cette ville.');
     status.textContent='Prévisions pour '+location.name+' ('+(location.country||country)+') · '+daily.time.length+' jours';
     daily.time.forEach((date,i)=>{
       const card=document.createElement('div');card.className='tp-weather-day';
       const day=document.createElement('strong');day.textContent=new Intl.DateTimeFormat('fr-FR',{weekday:'short',day:'numeric',month:'short',timeZone:'UTC'}).format(new Date(date+'T12:00:00Z'));
       const symbol=document.createElement('span');symbol.className='tp-weather-icon';symbol.textContent=icons(daily.weather_code?.[i]??3);
       const label=document.createElement('small');label.textContent=weatherName(daily.weather_code?.[i]??3);
       const temps=document.createElement('span');temps.className='tp-weather-temps';temps.textContent=Math.round(daily.temperature_2m_max[i])+'° / '+Math.round(daily.temperature_2m_min[i])+'°';
       const rain=document.createElement('small');rain.textContent='Pluie : '+(daily.precipitation_probability_max?.[i]??'—')+' %';
       card.append(day,symbol,label,temps,rain);days.append(card);
     });
   }catch(error){if(current===requestNumber)status.textContent='Météo indisponible : '+(error.name==='AbortError'?'délai de réponse dépassé':error.message);}
   finally{if(current===requestNumber)button.disabled=false;}
 }
 const schedule=()=>{clearTimeout(debounce);debounce=setTimeout(load,650)};
 cityInput.addEventListener('input',schedule);
 citySelect?.addEventListener('change',()=>setTimeout(load,0));
 countrySelect?.addEventListener('change',()=>{requestNumber++;days.replaceChildren();status.textContent='Choisis une ville pour afficher la météo.'});
 button.addEventListener('click',load);
 document.getElementById('search')?.addEventListener('click',()=>setTimeout(load,0));
 document.getElementById('plan')?.addEventListener('click',()=>setTimeout(load,0));
 if(cityInput.value.trim())load();
})();
