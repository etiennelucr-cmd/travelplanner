/* Travel Planner V3 additions — no external paid service required */
let records={budgets:{},journals:{}};
const euro=n=>new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(n);
const safeNum=(id,defaultValue=0)=>{const v=Number($(id).value);return Number.isFinite(v)&&v>=0?v:defaultValue};
const sortedTrips=()=>[...trips].sort((a,b)=>a.name.localeCompare(b.name,'fr'));
function fillSelect(id){const node=$(id),current=node.value;node.replaceChildren();for(const t of sortedTrips()){const opt=document.createElement('option');opt.value=t.id;opt.textContent=t.name+(t.start?' — '+t.start:'');node.append(opt)}if([...node.options].some(o=>o.value===current))node.value=current}
function renderV3(){fillSelect('budgetTrip');fillSelect('journalTrip');renderOverview()}
function onV3Tab(tab){if(tab==='budget')loadBudget();if(tab==='journal')loadJournal()}
function localDateKey(d=new Date()){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function daysUntil(date){const today=new Date();today.setHours(0,0,0,0);const target=new Date(date+'T12:00:00');return Math.round((target-today)/86400000)}
function renderOverview(){
 const counts={past:0,scheduled:0,wish:0},years={};
 for(const t of trips){counts[status(t)]++;if(t.start&&/^\d{4}-/.test(t.start)){const y=t.start.slice(0,4);years[y]=(years[y]||0)+1}}
 const k=$('kpis');k.replaceChildren();for(const [title,value] of [['Voyages réalisés',counts.past],['Programmés',counts.scheduled],['Destinations envisagées',counts.wish],['Entrées au total',trips.length]]){const item=el('div',undefined,'kpi');item.append(el('strong',String(value)),el('span',title));k.append(item)}
 const bars=$('yearBars');bars.replaceChildren();const values=Object.values(years),max=Math.max(1,...values),min=Math.min(...values),total=values.reduce((a,b)=>a+b,0);
 for(const [year,num] of Object.entries(years).sort()){const isMax=num===max,isMin=num===min;const row=el('div',undefined,'barrow'+(isMax?' year-max':'')+(isMin?' year-min':''));const track=el('div',undefined,'bartrack'),fill=el('div',undefined,'barfill');fill.style.width=`${num/max*100}%`;track.append(fill);row.append(el('span',year),track,el('strong',`${num} · ${(100*num/total).toFixed(1)} %`));if(isMax||isMin)row.title=[isMax?'Année la plus voyagée':'',isMin?'Année la moins voyagée':''].filter(Boolean).join(' / ');bars.append(row)}
 if(!values.length)bars.append(el('p','Aucune année renseignée.','hint'));
 if(values.length){const hint=el('p','Pourcentages calculés sur les voyages avec date de départ. Les égalités sont toutes surlignées.','hint');bars.append(hint)}
 const now=localDateKey(),up=$('upcoming');up.replaceChildren();const next=trips.filter(t=>t.start&&t.start>=now&&status(t)==='scheduled').sort((a,b)=>a.start.localeCompare(b.start)).slice(0,8);
 if(!next.length)up.append(el('p','Aucun départ daté à venir.'));
 for(const t of next){const days=daysUntil(t.start);const row=el('div',undefined,'upcoming-row');row.append(el('span',`${t.start} — ${t.name}`),el('strong',days===0?"Aujourd’hui":`J-${days} · ${days} jour${days>1?'s':''} restant${days>1?'s':''}`));up.append(row)}
 $('breakdown').textContent=`${counts.past} réalisés · ${counts.scheduled} programmés · ${counts.wish} envies`;
}

async function loadRecords(){try{const r=await api('/api/records');records={budgets:r.budgets||{},journals:r.journals||{}}}catch(e){notice('Carnet : '+e.message)}}
async function saveRecords(){await api('/api/records',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(records)})}
const budgetKeys=['Days','Transport','Hotel','Food','Visits','Other','People'];
function budgetValues(){const x={};for(const k of budgetKeys)x[k]=safeNum('budget'+k,k==='People'||k==='Days'?1:0);x.Days=Math.max(1,Math.round(x.Days));x.People=Math.max(1,Math.round(x.People));return x}
function calculateBudget(){const x=budgetValues();const hotel=Math.max(0,x.Days-1)*x.Hotel,food=x.Days*x.Food*x.People,total=x.Transport+hotel+food+x.Visits+x.Other;const host=$('budgetOutput');host.replaceChildren(el('h3','Budget estimé : '+euro(total)),el('p',`Transport : ${euro(x.Transport)} · Hébergement : ${euro(hotel)} · Repas : ${euro(food)} · Visites : ${euro(x.Visits)} · Autres : ${euro(x.Other)}`),el('p',`Pour ${x.People} personne(s) sur ${x.Days} jour(s) : ${euro(total/x.People)} par personne.`, 'hint'));return x}
function loadBudget(){const x=records.budgets[$('budgetTrip').value];if(x)for(const k of budgetKeys)if(x[k]!=null)$('budget'+k).value=x[k];calculateBudget()}
function estimateBudget(){
 const t=trips.find(t=>t.id===$('budgetTrip').value);
 const days=Math.max(1,Math.round(safeNum('budgetDays',2))),people=Math.max(1,Math.round(safeNum('budgetPeople',1)));
 // Indicative planning ranges only, never represented as supplier prices.
 const name=(t?.name||'').toLowerCase(),country=(t?.country||'').toLowerCase();
 const expensive=/suisse|norvège|norvege|islande|danemark|londres|zurich|genève|geneve|oslo|copenhague|reykjavik/.test(name+' '+country);
 const moderate=/paris|amsterdam|rome|milan|berlin|bruxelles|vienne|stockholm|munich|venise/.test(name+' '+country);
 const hotel=expensive?155:moderate?115:85,food=expensive?55:moderate?43:32;
 $('budgetHotel').value=hotel;$('budgetFood').value=food;
 $('budgetTransport').value=Math.round((expensive?180:moderate?130:95)*people);
 $('budgetVisits').value=Math.round((expensive?30:moderate?25:20)*days*people);
 $('budgetOther').value=Math.round(12*days*people);
 calculateBudget();
 const note=$('budgetEstimateNote');note.textContent=`Estimation indicative pour ${t?.name||'ce voyage'} : hypothèses de planification, PAS des tarifs Booking.com, SNCF ou Tripadvisor. Transport : aller-retour global approximatif, sans ville de départ ni dates vérifiées. Hôtel : par chambre/nuit, repas : par personne/jour. Vérifie les prix réels avant réservation.`;
}
$('budgetEstimate').onclick=estimateBudget;
$('budgetTrip').onchange=loadBudget;$('budgetCalculate').onclick=calculateBudget;
$('budgetSave').onclick=async()=>{try{records.budgets[$('budgetTrip').value]=calculateBudget();await saveRecords();notice('Budget enregistré')}catch(e){notice(e.message)}};
let currentPhotos=[];
function gallery(){const g=$('journalGallery');g.replaceChildren();currentPhotos.forEach((src,i)=>{const wrap=el('div',undefined,'photo');const img=document.createElement('img');img.src=src;img.alt='Souvenir '+(i+1);const remove=el('button','Retirer','secondary');remove.onclick=()=>{currentPhotos.splice(i,1);gallery()};wrap.append(img,remove);g.append(wrap)})}
function loadJournal(){const j=records.journals[$('journalTrip').value]||{};$('journalTitle').value=j.title||'';$('journalText').value=j.text||'';currentPhotos=[...(j.photos||[])];gallery()}
$('journalTrip').onchange=loadJournal;
function compressImage(file){return new Promise((resolve,reject)=>{if(!['image/jpeg','image/png','image/webp'].includes(file.type))return reject(Error('Format photo non pris en charge'));if(file.size>12000000)return reject(Error('Photo de plus de 12 Mo'));const url=URL.createObjectURL(file),img=new Image();img.onload=()=>{try{const scale=Math.min(1,1100/Math.max(img.width,img.height));const canvas=document.createElement('canvas');canvas.width=Math.round(img.width*scale);canvas.height=Math.round(img.height*scale);canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',.67))}catch(e){reject(e)}finally{URL.revokeObjectURL(url)}};img.onerror=()=>{URL.revokeObjectURL(url);reject(Error('Image illisible'))};img.src=url})}
$('journalPhotos').onchange=async e=>{try{for(const file of e.target.files){if(currentPhotos.length>=8)throw Error('Maximum 8 photos par carnet');currentPhotos.push(await compressImage(file))}gallery();notice('Photos ajoutées : pense à enregistrer le carnet')}catch(err){notice(err.message)}finally{e.target.value=''}};
$('journalSave').onclick=async()=>{try{records.journals[$('journalTrip').value]={title:$('journalTitle').value.slice(0,120),text:$('journalText').value.slice(0,15000),photos:currentPhotos};await saveRecords();notice('Carnet enregistré')}catch(e){notice('Enregistrement impossible : '+e.message)}};
$('journalPdf').onclick=()=>{const t=trips.find(t=>t.id===$('journalTrip').value);if(!t)return;const win=window.open('','_blank');if(!win){notice('Autorise les fenêtres pop-up pour imprimer');return}const d=win.document;d.title='Carnet - '+t.name;const style=d.createElement('style');style.textContent='body{font:16px/1.6 Arial,sans-serif;color:#172b42;max-width:800px;margin:40px auto}h1{color:#155f91}img{max-width:46%;max-height:320px;object-fit:contain;margin:1%}pre{white-space:pre-wrap;font:inherit}@page{margin:18mm}';d.head.append(style);const h=d.createElement('h1');h.textContent=$('journalTitle').value||t.name;d.body.append(h);const p=d.createElement('p');p.textContent=t.name+' — '+(t.start||'Sans date');d.body.append(p);const pre=d.createElement('pre');pre.textContent=$('journalText').value;d.body.append(pre);for(const src of currentPhotos){const img=d.createElement('img');img.src=src;d.body.append(img)}const note=d.createElement('p');note.textContent='Dans la fenêtre d’impression : Destination → Enregistrer au format PDF.';d.body.append(note);win.focus();setTimeout(()=>win.print(),800)};
loadRecords().then(()=>{if(trips.length){loadBudget();loadJournal()}});
