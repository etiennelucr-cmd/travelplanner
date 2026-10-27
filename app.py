import json, re, uuid, unicodedata, hmac
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
import pandas as pd
import folium
import streamlit.components.v1 as components
from collections import Counter
from datetime import date, datetime
import streamlit as st

ROOT = Path(__file__).parent
st.set_page_config(page_title='Travel Planner V6.1', page_icon='🧭', layout='wide')

# Protection de l'interface avant tout accès aux données Supabase.
def require_login():
    if 'APP_PASSWORD' not in st.secrets or not str(st.secrets['APP_PASSWORD']).strip():
        st.error('Configurez APP_PASSWORD dans les Secrets Streamlit avant de continuer.')
        st.stop()
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            if st.button('🔒 Se déconnecter'):
                st.session_state.authenticated = False
                st.rerun()
        return
    st.title('🔒 Travel Planner — Connexion')
    with st.form('login_form'):
        password = st.text_input('Mot de passe', type='password')
        submit = st.form_submit_button('Se connecter')
    if submit:
        if hmac.compare_digest(password.encode('utf-8'), str(st.secrets['APP_PASSWORD']).encode('utf-8')):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error('Mot de passe incorrect.')
    st.stop()

require_login()

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s).lower()) if not unicodedata.combining(c)).strip()

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception: return default

@st.cache_data
def coords():
    txt=(ROOT/'city-coordinates.js').read_text(encoding='utf-8')
    return json.loads(re.search(r'window\.TP_CITY_COORDS\s*=\s*(\{.*?\})\s*;',txt,re.S).group(1))

def markers(t):
    d=coords(); out=[]
    for x in t:
        name=str(x.get('name') or '')
        if x.get('lat') is not None and x.get('lon') is not None:
            out.append(dict(lat=float(x['lat']),lon=float(x['lon']),destination=name,statut=x.get('kind','')))
            continue
        parts=re.split(r'\s+[-–—]\s*|\s*/\s*|\s*→\s*',name)
        for part in parts:
            key=norm(part)
            if key in d:
                lat,lon=d[key];out.append(dict(lat=lat,lon=lon,destination=name,statut=x.get('kind','')))
    return out

def supabase_request(method, path, payload=None, prefer=None):
    url = st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = st.secrets["SUPABASE_KEY"]
    headers = {"apikey": key, "Authorization": "Bearer " + key,
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=25) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except HTTPError as e:
        raise RuntimeError(f"Supabase HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}") from e
    except URLError as e:
        raise RuntimeError(f"Connexion Supabase impossible : {e.reason}") from e

def fetch_trips():
    rows = supabase_request("GET", "travelplanner_trips?select=id,data&order=id&limit=1000")
    return [row["data"] for row in rows if row["id"] != "__tp_records__"]

def upsert_trips(items):
    rows = [{"id": str(item["id"]), "data": item} for item in items]
    for i in range(0, len(rows), 100):
        supabase_request("POST", "travelplanner_trips?on_conflict=id", rows[i:i+100], "resolution=merge-duplicates,return=minimal")

def delete_trip(trip_id):
    from urllib.parse import quote
    supabase_request("DELETE", "travelplanner_trips?id=eq." + quote(str(trip_id), safe=""), prefer="return=minimal")

try:
    if 'SUPABASE_URL' not in st.secrets or 'SUPABASE_KEY' not in st.secrets:
        st.error('Configurez SUPABASE_URL et SUPABASE_KEY dans les Secrets de Streamlit Cloud.')
        st.stop()
    if 'trips' not in st.session_state:
        remote = fetch_trips()
        if not remote:
            initial = read_json(ROOT/'data'/'trips.json', [])
            if initial:
                upsert_trips(initial)
                remote = fetch_trips()
        st.session_state.trips = remote
except Exception as e:
    st.error(f"Erreur Supabase : {e}. Aucune modification n'a été effectuée localement.")
    st.stop()

st.markdown("""<style>
.stApp {background:#f2f6fd;color:#0b2346}
[data-testid="stSidebar"] {background:#193a5b}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] label {color:#fff!important}
[data-testid="stSidebar"] [data-testid="stMetric"] {background:#254b6b!important;border:1px solid #41617f!important}
[data-testid="stSidebar"] [data-testid="stMetric"] * {color:#fff!important}
[data-testid="stSidebar"] button {background:#254b6b!important;color:#fff!important;border:1px solid #476a8b!important}
[data-testid="stSidebar"] button * {color:#fff!important}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {background:#254b6b;border-radius:10px;padding:10px}
h1,h2,h3 {color:#0b2346}
[data-testid="stMetric"] {background:white;border:1px solid #d0e1f7;border-radius:12px;padding:16px}
.stTabs [data-baseweb="tab-list"] {background:#e8f1fa;border-radius:12px;flex-wrap:wrap}
.stTabs [data-baseweb="tab"] {font-weight:650}
.tp-header{background:#173858;color:white;padding:16px 22px;border-radius:13px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.tp-header h1{color:white;font-size:30px;margin:0}.tp-header small{color:#d4e6f9}
.tp-clock{background:#edf5ff;color:#102e50;padding:12px 20px;border-radius:12px;font-weight:700}
.tp-kpi{background:white;border:1px solid #cbdff7;border-radius:13px;padding:18px;min-height:120px;display:flex;gap:15px;align-items:center}
.tp-kpi .tp-icon{font-size:28px;background:#e6f1ff;border-radius:50%;padding:10px}
.tp-kpi strong{font-size:30px;color:#0b2346;display:block;line-height:1.1}.tp-kpi small{color:#496889}
.tp-panel{background:white;border:1px solid #d0e1f7;border-radius:13px;padding:20px;margin-top:12px}
.tp-bars{display:flex;align-items:end;gap:15px;height:205px;border-bottom:1px solid #cbdff7;padding:10px 10px 0}
.tp-bar-wrap{flex:1;display:flex;flex-direction:column;justify-content:end;align-items:center;height:100%;font-size:12px}
.tp-bar{width:68%;max-width:65px;background:linear-gradient(#59adff,#2a83e8);border-radius:5px 5px 0 0}
.tp-depart{padding:10px 0;border-bottom:1px solid #e0e9f5}
</style>""",unsafe_allow_html=True)

def original_status(t):
    if t.get('kind') == 'past':
        return 'past'
    if t.get('start') and not re.search(r'Projet / souhait',str(t.get('notes') or ''),re.I):
        return 'scheduled'
    return 'wish'

def htmlsafe(value):
    import html
    return html.escape(str(value))

with st.sidebar:
    st.header('Sauvegarde et restauration')
    st.download_button('⬇️ Télécharger mes voyages (JSON)',json.dumps(st.session_state.trips,ensure_ascii=False,indent=2).encode('utf-8'),'trips-sauvegarde.json','application/json',use_container_width=True)
    up=st.file_uploader('Restaurer un fichier trips.json',type=['json'])
    if up and st.button('Restaurer cette sauvegarde'):
        try:
            data=json.load(up)
            if not isinstance(data,list): raise ValueError('Le JSON doit contenir une liste')
            
            for item in data:
                item['id'] = str(item.get('id') or uuid.uuid4())
            upsert_trips(data)
            st.session_state.trips=fetch_trips();st.success(f'{len(data)} voyages importés dans Supabase (sans supprimer les autres).');st.rerun()
        except Exception as e: st.error(str(e))
    st.divider()
    st.metric('Voyages enregistrés',len(st.session_state.trips))
    st.metric('Déjà effectués',sum(x.get('kind')=='past' for x in st.session_state.trips))
    st.metric('À venir',sum(original_status(x)=='scheduled' for x in st.session_state.trips))


from datetime import date
from collections import Counter
from urllib.parse import quote

def get_records():
    rows=supabase_request('GET','travelplanner_trips?id=eq.__tp_records__&select=data')
    return rows[0]['data'] if rows else {'budgets':{},'journals':{}}

def save_records(data):
    upsert_trips([{'id':'__tp_records__',**data}])

if 'records' not in st.session_state:
    try: st.session_state.records=get_records()
    except Exception as exc: st.warning('Carnets et budgets non chargés : '+str(exc));st.session_state.records={'budgets':{},'journals':{}}

all_trips=st.session_state.trips
count_past=sum(original_status(t)=='past' for t in all_trips)
count_future=sum(original_status(t)=='scheduled' for t in all_trips)
count_wish=sum(original_status(t)=='wish' for t in all_trips)
now=datetime.now()
st.markdown(f"""<div class='tp-header'><div><h1>✈ Travel Planner <small>V6.1</small></h1><small>Mes voyages · Ma carte · Mes découvertes</small></div><div class='tp-clock'>📅 {now.strftime('%d/%m/%Y')} &nbsp; 🕒 {now.strftime('%H:%M')}</div><div><b>{count_past} visités · {count_future} programmés · {count_wish} envies</b></div></div>""",unsafe_allow_html=True)
st.header('Vue d’ensemble de mes voyages')
mc=st.columns(4)
for c,(icon,label,num,sub) in zip(mc,[('🌐','Voyages',len(all_trips),'enregistrés'),('📍','Villes',len({norm(p['destination']) for p in markers(all_trips)}),'destinations localisées'),('📷','Visités',count_past,'voyages réalisés'),('🎈','À venir',count_future,'voyages programmés')]):
    with c:
        st.markdown(f'<div class="tp-kpi"><span class="tp-icon">{icon}</span><div><strong>{num}</strong><b>{label}</b><br><small>{sub}</small></div></div>',unsafe_allow_html=True)
years=Counter(str(t.get('start',''))[:4] for t in all_trips if re.match(r'^\d{4}-',str(t.get('start',''))))
left,right=st.columns(2)
with left:
    st.subheader('Voyages par année')
    if years:
        highest=max(years.values())
        bars=''.join(f'<div class="tp-bar-wrap"><b>{years[y]}</b><div class="tp-bar" style="height:{max(3,round(years[y]/highest*155))}px"></div><span>{htmlsafe(y)}</span></div>' for y in sorted(years))
        st.markdown('<div class="tp-panel"><div class="tp-bars">'+bars+'</div></div>',unsafe_allow_html=True)
with right:
    st.subheader('Prochains départs')
    upcoming=sorted([t for t in all_trips if str(t.get('start',''))>=date.today().isoformat() and original_status(t)=='scheduled'],key=lambda t:t['start'])[:8]
    if not upcoming: st.info('Aucun départ daté à venir.')
    else:
        rows=''.join(f'<div class="tp-depart">📍 <b>{htmlsafe(t.get("name",""))}</b> <small>— {htmlsafe(t.get("start",""))}</small></div>' for t in upcoming)
        st.markdown('<div class="tp-panel">'+rows+'</div>',unsafe_allow_html=True)
st.subheader('Répartition des destinations')
country_counts=Counter(t.get('country','').strip() or 'Pays non renseigné' for t in all_trips)
if country_counts:
    st.bar_chart(pd.DataFrame([{'Pays':k,'Voyages':v} for k,v in country_counts.most_common(12)]).set_index('Pays'))
st.caption('Les pays non renseignés dans les données ne sont pas devinés. Les statuts suivent la logique de la version locale.')

tab_map,tab_list,tab_add,tab_import,tab_places=st.tabs(['🗺️ Carte','📋 Mes destinations','➕ Ajouter / modifier','📥 Import TXT','🏛️ Lieux à découvrir'])
with tab_map:
    filt=st.selectbox('Afficher',['Tous','Effectués','À venir'])
    subset=[x for x in st.session_state.trips if filt=='Tous' or original_status(x)==('past' if filt=='Effectués' else 'scheduled')]
    pts=markers(subset)
    st.write(f'{len(pts)} marqueurs pour {len(subset)} voyages (les étapes multi-villes peuvent produire plusieurs marqueurs).')
    if pts:
        m=folium.Map(location=[47.8,5.4],zoom_start=5,tiles='OpenStreetMap',control_scale=True)
        colors={'past':'blue','scheduled':'orange','wish':'purple'}
        for p in pts:
            match=next((t for t in subset if t.get('name')==p['destination']),{})
            folium.Marker([p['lat'],p['lon']],popup=folium.Popup(htmlsafe(p['destination']),max_width=260),tooltip=p['destination'],icon=folium.Icon(color=colors.get(original_status(match),'blue'),icon='info-sign')).add_to(m)
        components.html(m.get_root().render(),height=560,scrolling=False)
    else: st.info('Aucune coordonnée disponible pour les destinations filtrées.')
    missing=[x.get('name','') for x in subset if not any(p['destination']==x.get('name','') for p in pts)]
    if missing:
        with st.expander(f'{len(missing)} destinations non localisées'):
            st.write(', '.join(missing))
with tab_list:
    query=st.text_input('Rechercher une destination')
    subset=[x for x in st.session_state.trips if norm(query) in norm(x.get('name',''))]
    df=pd.DataFrame([{'Destination':x.get('name',''),'Pays':x.get('country',''),'Statut':{'past':'Effectué','scheduled':'Programmé','wish':'Envie'}[original_status(x)],'Début':x.get('start',''),'Fin':x.get('end',''),'Notes':x.get('notes','')} for x in subset])
    st.dataframe(df,use_container_width=True,hide_index=True)
with tab_add:
    trips=st.session_state.trips
    options=['➕ Nouveau voyage']+[f"{i+1}. {x.get('name','Sans nom')}" for i,x in enumerate(trips)]
    selected=st.selectbox('Choisir une fiche',range(len(options)),format_func=lambda i:options[i])
    old={} if selected==0 else trips[selected-1]
    with st.form('edit_trip'):
        name=st.text_input('Destination',value=old.get('name',''))
        country=st.text_input('Pays',value=old.get('country',''))
        kind=st.selectbox('Statut',['past','future','wish'],index={'past':0,'scheduled':1,'wish':2}[original_status(old)],format_func=lambda x:{'past':'Effectué','future':'À venir','wish':'Envie'}[x])
        start=st.text_input('Date de début (AAAA-MM-JJ ou texte)',value=old.get('start',''))
        end=st.text_input('Date de fin',value=old.get('end',''))
        notes=st.text_area('Notes',value=old.get('notes',''))
        a,b=st.columns(2)
        lat=a.text_input('Latitude (facultatif)',value='' if old.get('lat') is None else str(old['lat']))
        lon=b.text_input('Longitude (facultatif)',value='' if old.get('lon') is None else str(old['lon']))
        save=st.form_submit_button('💾 Enregistrer')
    if save:
        if not name.strip(): st.error('Indiquez une destination.')
        else:
            try:
                item=dict(old,id=old.get('id') or str(uuid.uuid4()),name=name.strip(),country=country,kind=kind,start=start,end=end,notes=notes,lat=float(lat.replace(',','.')) if lat.strip() else None,lon=float(lon.replace(',','.')) if lon.strip() else None)
                upsert_trips([item])
                if selected==0: trips.append(item)
                else: trips[selected-1]=item
                st.success('Fiche enregistrée dans Supabase.');st.rerun()
            except ValueError: st.error('Latitude ou longitude invalide.')
    if selected and st.button('🗑️ Supprimer cette fiche'):
        delete_trip(trips[selected-1]['id'])
        trips.pop(selected-1);st.rerun()
with tab_import:
    st.write('Importer une liste simple : `Ville | Date | Statut` (une destination par ligne). Les formats Google Keep complexes peuvent nécessiter une vérification manuelle.')
    txt=st.file_uploader('Fichier TXT',type=['txt'],key='txt')
    if txt:
        raw=txt.getvalue().decode('utf-8-sig',errors='replace')
        incoming=[];existing={(norm(x.get('name','')),x.get('start','')) for x in st.session_state.trips}
        for line in raw.splitlines():
            line=line.strip(' \t-•')
            if not line:continue
            parts=[p.strip() for p in line.split('|')]
            name=parts[0];date=parts[1] if len(parts)>1 else ''
            if not name:continue
            if (norm(name),date) in existing:continue
            status=parts[2].lower() if len(parts)>2 else ''
            kind='past' if any(w in status for w in ['fait','effectu','pass','✅','visité']) else 'future'
            incoming.append(dict(id=str(uuid.uuid4()),name=name,country='',kind=kind,start=date,end='',notes='',lat=None,lon=None))
            existing.add((norm(name),date))
        st.write(f'{len(incoming)} nouvelles lignes détectées')
        st.dataframe(pd.DataFrame(incoming)[['name','start','kind']] if incoming else pd.DataFrame(),hide_index=True)
        if incoming and st.button('Confirmer l’import'):
            upsert_trips(incoming)
            st.session_state.trips.extend(incoming);st.rerun()
with tab_places:
    places=read_json(ROOT/'data'/'places-local.json',{})
    keys=sorted(places)
    if keys:
        city=st.selectbox('Ville avec des lieux pré-enregistrés',keys)
        entries=places[city]
        st.dataframe(pd.DataFrame([{'Lieu':e.get('tags',{}).get('name','Sans nom'),'Type':e.get('tags',{}).get('tourism',''),'Latitude':e.get('lat'),'Longitude':e.get('lon')} for e in entries]),hide_index=True,use_container_width=True)
    else:st.info('Aucun catalogue local disponible.')


st.divider()
st.header('🧳 Autres outils du Travel Planner original')
t_budget,t_journal,t_calendar,t_weather,t_route,t_ideas,t_visit=st.tabs(['💶 Budget','📓 Carnet','📅 Calendrier','🌦️ Météo 14 jours','🚗 Circuit','💡 Idées','🏛️ Programme de visites'])
trip_ids={f"{t.get('name','Sans nom')} — {t.get('start','')} [{t.get('id','')[:8]}]":t.get('id') for t in all_trips}
with t_budget:
    st.subheader('Budget de voyage')
    if trip_ids:
        bname=st.selectbox('Voyage',list(trip_ids),key='budgettrip');bid=trip_ids[bname]
        previous=st.session_state.records.get('budgets',{}).get(bid,{})
        with st.form('budget_form'):
            cols=st.columns(2)
            days=cols[0].number_input('Nombre de jours',min_value=1,value=int(previous.get('Days',2)))
            people=cols[1].number_input('Personnes',min_value=1,value=int(previous.get('People',1)))
            transport=cols[0].number_input('Transport total (€)',min_value=0.,value=float(previous.get('Transport',80)))
            hotel=cols[1].number_input('Hébergement par nuit (€)',min_value=0.,value=float(previous.get('Hotel',90)))
            food=cols[0].number_input('Repas par jour et personne (€)',min_value=0.,value=float(previous.get('Food',35)))
            visits=cols[1].number_input('Visites total (€)',min_value=0.,value=float(previous.get('Visits',35)))
            other=cols[0].number_input('Autres frais (€)',min_value=0.,value=float(previous.get('Other',15)))
            save_b=st.form_submit_button('💾 Calculer et enregistrer le budget')
        total=transport+max(0,days-1)*hotel+days*food*people+visits+other
        st.metric('Budget estimé',f'{total:,.2f} €');st.caption(f'{total/people:,.2f} € par personne — estimation indicative, pas un prix réel')
        if save_b:
            try:
                st.session_state.records.setdefault('budgets',{})[bid]=dict(Days=days,People=people,Transport=transport,Hotel=hotel,Food=food,Visits=visits,Other=other)
                save_records(st.session_state.records);st.success('Budget sauvegardé dans Supabase.')
            except Exception as exc:st.error(str(exc))
with t_journal:
    st.subheader('Carnet de voyage & souvenirs')
    if trip_ids:
        jname=st.selectbox('Voyage',list(trip_ids),key='journaltrip');jid=trip_ids[jname]
        old=st.session_state.records.get('journals',{}).get(jid,{})
        with st.form('journal_form'):
            title=st.text_input('Titre du souvenir',value=old.get('title',''))
            story=st.text_area('Récit de voyage',value=old.get('text',''),height=180)
            sj=st.form_submit_button('💾 Enregistrer le carnet')
        if sj:
            try:
                st.session_state.records.setdefault('journals',{})[jid]={**old,'title':title,'text':story}
                save_records(st.session_state.records);st.success('Carnet enregistré dans Supabase.')
            except Exception as exc:st.error(str(exc))
        st.download_button('⬇️ Exporter ce carnet (TXT)',f'{title}\n\n{story}',file_name='carnet.txt')
        st.caption('Les photos intégrées au carnet original ne sont pas encore prises en charge.')
with t_calendar:
    st.subheader('Calendrier des voyages')
    dated=[{'Destination':t.get('name'),'Début':t.get('start'),'Fin':t.get('end'),'Statut':t.get('kind')} for t in all_trips if t.get('start')]
    st.dataframe(pd.DataFrame(sorted(dated,key=lambda x:x['Début'])),hide_index=True,use_container_width=True)
with t_weather:
    st.subheader('Prévisions météo — 14 jours (Open-Meteo)')
    city=st.text_input('Ville',value='Paris',key='weathercity')
    if st.button('🌦️ Voir les prévisions'):
        try:
            from urllib.request import urlopen
            geo=json.load(urlopen('https://geocoding-api.open-meteo.com/v1/search?name='+quote(city)+'&count=1&language=fr',timeout=15))['results'][0]
            url=f"https://api.open-meteo.com/v1/forecast?latitude={geo['latitude']}&longitude={geo['longitude']}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=14"
            forecast=json.load(urlopen(url,timeout=15))['daily']
            st.write('Prévisions pour',geo['name'])
            st.dataframe(pd.DataFrame({'Date':forecast['time'],'Max °C':forecast['temperature_2m_max'],'Min °C':forecast['temperature_2m_min'],'Pluie %':forecast['precipitation_probability_max']}),hide_index=True,use_container_width=True)
        except Exception as exc:st.error('Météo indisponible : '+str(exc))
with t_route:
    st.subheader('Construire un trajet entre plusieurs villes')
    rawstops=st.text_area('2 à 10 étapes (virgule ou nouvelle ligne)',value='Paris, Reims, Metz, Strasbourg')
    mode=st.radio('Transport',['Voiture','Train (estimation géographique)'],horizontal=True)
    pause=st.number_input('Arrêt par ville (minutes)',min_value=0,max_value=1440,value=60)
    if st.button('🗺️ Construire le circuit'):
        stops=[s.strip() for s in re.split(r'[,\n]+',rawstops) if s.strip()]
        if not 2<=len(stops)<=10:st.error('Indique 2 à 10 villes.')
        else:
            cs=coords();located=[(name,cs.get(norm(name))) for name in stops]
            missing=[n for n,c in located if not c]
            if missing:st.warning('Villes non localisées : '+', '.join(missing))
            else:
                st.write('Étapes localisées : '+', '.join(n for n,_ in located))
                st.write(' → '.join(stops));st.caption('Carte des étapes, sans calcul routier ni horaires de train vérifiés.')
                st.download_button('⬇️ Exporter le circuit', '\n'.join(stops),file_name='circuit.txt')
with t_ideas:
    st.subheader('Idées de prochaines destinations')
    catalog=read_json(ROOT/'data'/'europe-cities.json',{})
    country=st.selectbox('Pays',sorted(catalog),key='ideacountry')
    existing={norm(t.get('name','')) for t in all_trips}
    suggestions=[c for c in catalog.get(country,[]) if norm(c) not in existing]
    st.write(f'{len(suggestions)} idées non présentes dans tes voyages')
    st.write(' · '.join(suggestions[:60]) or 'Toutes ces villes figurent déjà dans tes voyages.')
with t_visit:
    st.subheader('Que visiter selon le temps disponible ?')
    catalog=read_json(ROOT/'data'/'europe-cities.json',{})
    country=st.selectbox('Pays européen',sorted(catalog),key='visitcountry')
    city=st.selectbox('Ville',catalog.get(country,[]),key='visitcity')
    duration=st.selectbox('Durée',['30 min','1 h','2 h','4 h','1 jour','2 jours','3 jours'])
    places=read_json(ROOT/'data'/'places-local.json',{})
    results=places.get(norm(city),[])
    if results:
        n={'30 min':2,'1 h':3,'2 h':5,'4 h':8,'1 jour':12,'2 jours':20,'3 jours':30}[duration]
        names=[e.get('tags',{}).get('name','Lieu sans nom') for e in results[:n]]
        st.write('Programme indicatif (horaires à vérifier)')
        for i,name in enumerate(names,1):st.write(f'{i}. {name}')
        st.download_button('⬇️ Programme TXT','\n'.join(names),file_name='programme-visites.txt')
    else:st.info('Pas de lieux en cache pour cette ville. La recherche en ligne de monuments reste à intégrer.')
