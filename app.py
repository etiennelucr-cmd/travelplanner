import json, re, uuid, unicodedata, hmac
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
import pandas as pd
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
    return [row["data"] for row in rows]

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

st.title('🧭 Travel Planner V6.1')
st.caption('Version Streamlit • données initiales importées depuis votre installation Windows')
st.success('☁️ Sauvegarde automatique Supabase activée. Gardez aussi une copie JSON de secours.')

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
    st.metric('À venir',sum(x.get('kind')=='future' for x in st.session_state.trips))

tab_map,tab_list,tab_add,tab_import,tab_places=st.tabs(['🗺️ Carte','📋 Mes destinations','➕ Ajouter / modifier','📥 Import TXT','🏛️ Lieux à découvrir'])
with tab_map:
    filt=st.selectbox('Afficher',['Tous','Effectués','À venir'])
    subset=[x for x in st.session_state.trips if filt=='Tous' or x.get('kind')==('past' if filt=='Effectués' else 'future')]
    pts=markers(subset)
    st.write(f'{len(pts)} marqueurs pour {len(subset)} voyages (les étapes multi-villes peuvent produire plusieurs marqueurs).')
    if pts:
        st.map(pd.DataFrame(pts),latitude='lat',longitude='lon',size=65)
    else: st.info('Aucune coordonnée disponible pour les destinations filtrées.')
    missing=[x.get('name','') for x in subset if not any(p['destination']==x.get('name','') for p in pts)]
    if missing:
        with st.expander(f'{len(missing)} destinations non localisées'):
            st.write(', '.join(missing))
with tab_list:
    query=st.text_input('Rechercher une destination')
    subset=[x for x in st.session_state.trips if norm(query) in norm(x.get('name',''))]
    df=pd.DataFrame([{'Destination':x.get('name',''),'Pays':x.get('country',''),'Statut':'Effectué' if x.get('kind')=='past' else 'À venir','Début':x.get('start',''),'Fin':x.get('end',''),'Notes':x.get('notes','')} for x in subset])
    st.dataframe(df,use_container_width=True,hide_index=True)
with tab_add:
    trips=st.session_state.trips
    options=['➕ Nouveau voyage']+[f"{i+1}. {x.get('name','Sans nom')}" for i,x in enumerate(trips)]
    selected=st.selectbox('Choisir une fiche',range(len(options)),format_func=lambda i:options[i])
    old={} if selected==0 else trips[selected-1]
    with st.form('edit_trip'):
        name=st.text_input('Destination',value=old.get('name',''))
        country=st.text_input('Pays',value=old.get('country',''))
        kind=st.selectbox('Statut',['past','future'],index=0 if old.get('kind','future')=='past' else 1,format_func=lambda x:'Effectué' if x=='past' else 'À venir')
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
