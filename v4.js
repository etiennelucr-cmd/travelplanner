/* Travel Planner V4 : sauvegardes, listes de départ, exports texte */
let prepItems=[];
const defaultPrep=['Vérifier les documents et billets','Vérifier les horaires et réservations','Préparer les bagages','Vérifier la météo','Prévoir le budget et les moyens de paiement','Télécharger les cartes hors ligne'];
function downloadText(filename,text,mime='text/plain;charset=utf-8'){
 const blob=new Blob([text],{type:mime});const url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function txtFromNode(node){return node?.innerText?.trim()||'Aucun résultat généré.'}
$('exportVisit').onclick=()=>downloadText('programme-visites.txt',`TRAVEL PLANNER - PROGRAMME DE VISITES\nVille : ${$('city').value}\nDurée : ${$('duration').value} minutes\n\n${txtFromNode($('results'))}\n\nEstimations indicatives. Vérifier les horaires et déplacements.`.replaceAll('\\n','\n'));
$('exportRoute').onclick=()=>downloadText('circuit-voyage.txt',`TRAVEL PLANNER - CIRCUIT\nVilles : ${$('stops').value}\nMode : ${$('routeMode').value}\n\n${txtFromNode($('routeResults'))}\n\nDurées indicatives, trafic et correspondances non vérifiés.`.replaceAll('\\n','\n'));
$('backupAll').onclick=async()=>{try{
 const [t,r]=await Promise.all([api('/api/trips'),api('/api/records')]);
 const backup={format:'TravelPlannerBackup',version:4,exportedAt:new Date().toISOString(),trips:t,records:r};
 downloadText('travel-planner-sauvegarde-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify(backup,null,2),'application/json;charset=utf-8');
 notice('Sauvegarde complète téléchargée : garde ce fichier en lieu sûr.');
}catch(e){notice('Sauvegarde impossible : '+e.message)}};
function prepSelect(){const sel=$('prepTrip'),old=sel.value;sel.replaceChildren();for(const t of sortedTrips()){const opt=document.createElement('option');opt.value=t.id;opt.textContent=t.name+(t.start?' — '+t.start:'');sel.append(opt)}if([...sel.options].some(x=>x.value===old))sel.value=old;loadPrep()}
function loadPrep(){const id=$('prepTrip').value;if(!id){prepItems=[];drawPrep();return}
 const saved=records.checklists?.[id];prepItems=Array.isArray(saved)?saved.map(x=>({text:String(x.text||'').slice(0,150),done:!!x.done})).filter(x=>x.text):defaultPrep.map(text=>({text,done:false}));drawPrep()}
function drawPrep(){const root=$('prepChecklist');root.replaceChildren();prepItems.forEach((item,i)=>{
 const line=el('div',undefined,'prepitem');const input=document.createElement('input');input.type='checkbox';input.checked=item.done;input.onchange=()=>{item.done=input.checked;drawPrep()};
 const label=el('span',item.text);if(item.done)label.style.textDecoration='line-through';const del=el('button','Retirer','secondary');del.type='button';del.onclick=()=>{prepItems.splice(i,1);drawPrep()};line.append(input,label,del);root.append(line)
 });$('prepProgress').textContent=`${prepItems.filter(x=>x.done).length} / ${prepItems.length} tâches terminées`}
$('prepTrip').onchange=loadPrep;
$('prepAdd').onclick=()=>{const text=$('prepNew').value.trim();if(!text)return;if(prepItems.length>=80){notice('Maximum 80 tâches');return}prepItems.push({text:text.slice(0,150),done:false});$('prepNew').value='';drawPrep()};
$('prepSave').onclick=async()=>{try{if(!$('prepTrip').value)throw Error('Aucun voyage sélectionné');records.checklists=records.checklists||{};records.checklists[$('prepTrip').value]=prepItems;await saveRecords();notice('Liste de préparation enregistrée')}catch(e){notice(e.message)}};
const originalRenderV3=renderV3;renderV3=function(){originalRenderV3();prepSelect()};
const originalOnV3Tab=onV3Tab;onV3Tab=function(tab){originalOnV3Tab(tab);if(tab==='prepare')prepSelect()};
