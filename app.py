import json, re, uuid, unicodedata, hmac
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
import pandas as pd
import folium
import streamlit.components.v1 as components
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
import html
import math
import streamlit as st

ROOT = Path(__file__).parent
st.set_page_config(page_title='Travel Planner V6.3', page_icon='🧭', layout='wide')
st.markdown('''<style>
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#102f53,#193e62);color:white}
section[data-testid="stSidebar"] *{color:inherit}
section[data-testid="stSidebar"] div[role="radiogroup"] label{background:#254b6d;border-radius:11px;padding:11px 10px;margin:3px 0;transition:background .15s}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:#087bce!important;color:white!important}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#35648b}
.tp-idea{border-radius:16px!important;box-shadow:0 3px 12px #0c33520c}
.tp-panel,.tp-kpi{box-shadow:0 4px 16px #0c33520b}
</style>''',unsafe_allow_html=True)


# Protection de l'interface avant tout accès aux données Supabase.
def require_login():
    if 'APP_PASSWORD' not in st.secrets or not str(st.secrets['APP_PASSWORD']).strip():
        st.error('Configurez APP_PASSWORD dans les Secrets Streamlit avant de continuer.')
        st.stop()
    if st.session_state.get('authenticated', False):
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


# Les données originales ont souvent country="" : classification locale, sans modifier Supabase.
COUNTRY_FLAGS={'France':'🇫🇷','Belgique':'🇧🇪','Allemagne':'🇩🇪','Pays-Bas':'🇳🇱','Suisse':'🇨🇭','Italie':'🇮🇹','Espagne':'🇪🇸','Royaume-Uni':'🇬🇧','Portugal':'🇵🇹','Autriche':'🇦🇹','Luxembourg':'🇱🇺','Irlande':'🇮🇪','République tchèque':'🇨🇿','Pologne':'🇵🇱','Danemark':'🇩🇰','Monaco':'🇲🇨'}
COUNTRY_OVERRIDES={
 'londres':'Royaume-Uni','dublin':'Irlande','utrecht':'Pays-Bas','rotterdam':'Pays-Bas','amsterdam':'Pays-Bas','la haye':'Pays-Bas',
 'ghent':'Belgique','gand':'Belgique','antwerp':'Belgique','anvers':'Belgique','bruges':'Belgique','ostende':'Belgique','oostende':'Belgique','mechelen':'Belgique','malines':'Belgique','leuven':'Belgique','louvain':'Belgique','bruxelles':'Belgique','liege':'Belgique','namur':'Belgique','mons':'Belgique',
 'lausanne':'Suisse','basel':'Suisse','bale':'Suisse','geneve':'Suisse','zurich':'Suisse','berne':'Suisse','montreux':'Suisse',
 'francfort':'Allemagne','frankfurt':'Allemagne','cologne':'Allemagne','koln':'Allemagne','aachen':'Allemagne','aix la chapelle':'Allemagne','treves':'Allemagne','trier':'Allemagne','dusseldorf':'Allemagne','berlin':'Allemagne','munich':'Allemagne','hambourg':'Allemagne','hamburg':'Allemagne','stuttgart':'Allemagne','heidelberg':'Allemagne',
 'turin':'Italie','milan':'Italie','rome':'Italie','venise':'Italie','florence':'Italie','genes':'Italie',
 'madrid':'Espagne','barcelone':'Espagne','seville':'Espagne','valence':'Espagne','bilbao':'Espagne',
 'lisbonne':'Portugal','porto':'Portugal','vienne':'Autriche','salzbourg':'Autriche','luxembourg':'Luxembourg',
 'prague':'République tchèque','copenhague':'Danemark','varsovie':'Pologne','monaco':'Monaco'
}
@st.cache_data
def city_country_catalog():
    catalog=read_json(ROOT/'data'/'europe-cities.json',{})
    lookup={}
    for country,names in catalog.items():
        for city in names: lookup.setdefault(norm(city),country)
    lookup.update(COUNTRY_OVERRIDES)
    return lookup

def split_destinations(name):
    # Le libellé d'événement après des guillemets n'est pas une ville.
    cleaned=re.split(r'["“”]',str(name),maxsplit=1)[0].strip()
    return [p.strip(' ,') for p in re.split(r'\s+[-–—]\s*|\s*/\s*|\s*→\s*|\s*,\s*',cleaned) if p.strip(' ,')]

def country_for(name,explicit=''):
    if explicit and str(explicit).strip(): return str(explicit).strip()
    lookup=city_country_catalog()
    for part in split_destinations(name):
        key=norm(part)
        if key in lookup: return lookup[key]
    return ''

COUNTRY_CODES={'France':'fr','Belgique':'be','Allemagne':'de','Pays-Bas':'nl','Suisse':'ch','Italie':'it','Espagne':'es','Royaume-Uni':'gb','Portugal':'pt','Autriche':'at','Luxembourg':'lu','Irlande':'ie','République tchèque':'cz','Pologne':'pl','Danemark':'dk','Monaco':'mc','Albanie':'al'}
def flag_html(country):
    code=COUNTRY_CODES.get(country)
    return f'<img src="https://flagcdn.com/w40/{code}.png" alt="{safe(country)}" width="30" height="20" style="object-fit:cover;border-radius:3px;box-shadow:0 1px 4px #0002;vertical-align:middle">' if code else '🌍'
def flag_for(t): return flag_html(country_for(t.get('name',''),t.get('country','')))
@st.cache_data(ttl=86400,show_spinner=False)
def city_photo(city):
    # Wikipedia thumbnail; missing/offline -> elegant text-only card, never a false city photo.
    from urllib.parse import quote
    for lang in ('fr','en'):
        try:
            req=Request(f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(city.replace(" ","_"))}',headers={'User-Agent':'TravelPlanner/6.3 (personal travel app)'})
            with urlopen(req,timeout=3) as resp: item=json.load(resp)
            thumb=item.get('thumbnail',{}).get('source')
            if thumb and item.get('type')!='disambiguation': return thumb
        except Exception: pass
    return ''


def safe(x): return html.escape(str(x),quote=True)

def local_markers(trips):
    d=coords(); out=[]; missing=[]
    for t in trips:
        name=str(t.get('name') or '')
        if t.get('lat') is not None and t.get('lon') is not None:
            try: out.append(dict(lat=float(t['lat']),lon=float(t['lon']),destination=name,statut=original_status(t)));continue
            except (TypeError,ValueError):pass
        found=0
        for part in split_destinations(name):
            key=norm(part)
            if key in d:
                lat,lon=d[key];out.append(dict(lat=lat,lon=lon,destination=name,statut=original_status(t)));found+=1
        if not found:missing.append(name)
    return out,missing

def weather_symbol(code):
    if code is None:return '🌤️'
    if code==0:return '☀️'
    if code in (1,2,3):return '⛅'
    if code in (45,48):return '🌫️'
    if code in (51,53,55,56,57,61,63,65,66,67,80,81,82):return '🌧️'
    if code in (71,73,75,77,85,86):return '❄️'
    if code in (95,96,99):return '⛈️'
    return '🌤️'

@st.cache_data(ttl=1800,show_spinner=False)
def forecast_city(city):
    from urllib.parse import urlencode
    geo_url='https://geocoding-api.open-meteo.com/v1/search?'+urlencode({'name':city,'count':1,'language':'fr'})
    with urlopen(geo_url,timeout=12) as r: geo=json.load(r).get('results',[])
    if not geo: raise ValueError('Ville introuvable')
    place=geo[0]
    url='https://api.open-meteo.com/v1/forecast?'+urlencode({'latitude':place['latitude'],'longitude':place['longitude'],'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max','current':'temperature_2m,weather_code','timezone':'auto','forecast_days':14})
    with urlopen(url,timeout=15) as r: data=json.load(r)
    return place,data

def render_calendar(trips,yr,mo):
    today=date.today(); cal=calendar.Calendar(firstweekday=0)
    names=['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
    cells=''.join(f'<div class="tp-cal-dayname">{d}</div>' for d in names)
    for week in cal.monthdatescalendar(yr,mo):
        for day in week:
            active=[t for t in trips if str(t.get('start',''))[:10]==day.isoformat()]
            cl=' tp-cal-out' if day.month!=mo else ''
            if day==today:cl+=' tp-cal-today'
            if active:cl+=' tp-cal-trip'
            chips=''.join(f'<div class="tp-cal-chip" title="{safe(t.get("name",""))}">{safe(t.get("name",""))[:14]}</div>' for t in active[:2])
            cells+=f'<div class="tp-cal-cell{cl}"><b>{day.day}</b>{chips}</div>'
    return '<div class="tp-calendar">'+cells+'</div>'
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

.tp-header{background:linear-gradient(110deg,#102d51,#1b4773);box-shadow:0 12px 30px #17385820;border:1px solid #335d83}
.tp-panel,.tp-kpi{box-shadow:0 6px 24px #1436570b;transition:box-shadow .2s ease}
.tp-kpi:hover,.tp-panel:hover{box-shadow:0 9px 30px #14365718}
.tp-kpi .tp-icon{background:#eaf3ff}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#112e50,#193e60)}
[data-testid="stSidebar"] [data-testid="stMetric"]{border-radius:13px}
.stButton>button[kind="primary"]{background:#0877d5;border:0;border-radius:10px}
.stButton>button{border-radius:10px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}
.tp-donut{width:230px;height:230px;border-radius:50%;display:grid;place-items:center;flex-shrink:0}
.tp-donut-center{background:white;border-radius:50%;height:135px;width:135px;display:flex;align-items:center;justify-content:center;flex-direction:column;box-shadow:inset 0 0 0 1px #e5ecf8}
.tp-donut-center b{font-size:34px;color:#0e2c51}.tp-donut-center small{color:#526a85}
.tp-legend{display:grid;grid-template-columns:1fr 1fr;gap:10px 22px;align-content:center;flex:1}
.tp-legend-item{font-size:13px;color:#213d5f;white-space:nowrap}.tp-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px}
.tp-country-layout{display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap;min-height:255px}
.tp-depart{display:flex;align-items:center;gap:12px}.tp-depart .tp-flag{font-size:24px}.tp-depart .tp-when{margin-left:auto;background:#fff2df;border-radius:9px;padding:6px 10px;color:#bc6109;font-size:12px;font-weight:700}
.tp-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px}.tp-cal-dayname{background:#e7f0fb;text-align:center;border-radius:7px;padding:9px 2px;font-weight:700;color:#173858}
.tp-cal-cell{min-height:69px;border:1px solid #d9e5f4;background:white;border-radius:9px;padding:6px;font-size:13px}.tp-cal-out{opacity:.32}.tp-cal-today{border:2px solid #0078df;background:#e8f5ff}.tp-cal-trip{background:#fff0f0;border-color:#ffd1d1}.tp-cal-chip{background:#d8edff;border-radius:5px;padding:2px 4px;font-size:11px;margin-top:3px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.tp-weather-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}.tp-weather-day{background:white;border:1px solid #d9e5f4;border-radius:12px;padding:12px 5px;text-align:center;font-size:12px}.tp-weather-day .tp-wicon{font-size:28px;margin:7px 0}.tp-weather-day b{font-size:14px;color:#12385d}.tp-weather-day small{color:#607b99}
.tp-idea{background:white;border:1px solid #d5e5f8;border-radius:13px;padding:15px;min-height:128px}.tp-idea b{color:#0d3159}.tp-idea p{font-size:13px;color:#59718c}
@media(max-width:1000px){.tp-weather-grid{grid-template-columns:repeat(4,1fr)}.tp-legend{grid-template-columns:1fr}.tp-cal-cell{min-height:53px}}
</style>""",unsafe_allow_html=True)

def original_status(t):
    if t.get('kind') == 'past':
        return 'past'
    if t.get('kind') == 'wish':
        return 'wish'
    if t.get('start') and not re.search(r'Projet / souhait',str(t.get('notes') or ''),re.I):
        return 'scheduled'
    return 'wish'

def htmlsafe(value):
    import html
    return html.escape(str(value))

with st.sidebar:
    st.markdown('## ✈️ Travel Planner')
    section=st.radio('Navigation', ['📊 Tableau de bord','🗺️ Carte & voyages','🏛️ Visites','🌦️ Météo','💡 Idées'],label_visibility='collapsed',key='tp_navigation')
    st.divider()
    st.caption('OUTILS & SAUVEGARDE')
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
    if st.button('🔒 Se déconnecter',use_container_width=True):
        st.session_state.authenticated=False
        st.rerun()


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
# Horloge en direct dans le navigateur : Europe/Paris, avec secondes et heure d'été/hiver.
# La météo de Paris est affichée à côté ; une indisponibilité API ne bloque jamais l'app.
try:
    paris_weather=forecast_city('Paris')[1].get('current',{})
    temp=f"{round(paris_weather.get('temperature_2m',0))}°C"
    symbol=weather_symbol(paris_weather.get('weather_code'))
except Exception:
    temp='—';symbol='🌤️'
# Calendrier miniature intégré au bandeau : navigation locale sans rechargement Streamlit.
calendar_events = {}
for trip in all_trips:
    start = str(trip.get('start') or '')[:10]
    if re.match(r'^\\d{4}-\\d{2}-\\d{2}$', start):
        calendar_events.setdefault(start, []).append(str(trip.get('name') or 'Voyage'))
calendar_events_json = json.dumps(calendar_events, ensure_ascii=False).replace('<', '\\u003c')
header_html=f"""<!doctype html><html lang='fr'><meta charset='utf-8'><style>
*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;color:white}}
.header{{background:linear-gradient(110deg,#102d51,#1b4773);border-radius:15px;padding:12px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;min-height:112px}}
.brand{{font-size:23px;font-weight:800}}.brand small{{font-size:14px;color:#d5e8ff}}.sub{{font-size:12px;color:#d5e8ff;margin-top:5px}}
.clockweather{{background:#f0f6ff;color:#102d51;padding:7px 14px;border-radius:12px;display:flex;gap:24px;align-items:center}}
.clock{{font-size:24px;font-weight:800;letter-spacing:1px;font-variant-numeric:tabular-nums}}.small{{font-size:12px;color:#526a85}}.weather{{border-left:1px solid #c8d9eb;padding-left:20px;font-size:18px;font-weight:800}}
.kpis{{display:flex;gap:7px;align-items:center;flex-wrap:wrap}}.kpi{{display:flex;align-items:center;gap:8px;background:#f4f8ff;color:#102d51;border-radius:10px;padding:9px 12px;min-width:100px}}.kpi-icon{{font-size:23px}}.kpi-num{{font-size:22px;font-weight:800;line-height:1}}.kpi-label{{font-size:11px;font-weight:700;margin-top:4px}}.mini-cal{{background:#f4f8ff;color:#15385e;border-radius:12px;padding:8px 10px;width:224px;flex-shrink:0}}.mini-cal-head{{display:flex;justify-content:space-between;align-items:center;font-weight:700;font-size:12px;margin-bottom:5px}}.mini-cal-head button{{border:0;background:#dbeafe;border-radius:6px;cursor:pointer;padding:2px 8px;color:#17416b;font-size:15px}}.mini-cal-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center}}.mini-cal-grid span{{font-size:10px;line-height:20px;min-height:20px;border-radius:5px}}.mini-cal-grid .dow{{color:#6884a4;font-weight:700}}.mini-cal-grid .has-trip{{background:#f9bdc3;color:#7d2230;font-weight:800}}.mini-cal-grid .today{{outline:2px solid #2683e8}}@media(max-width:850px){{.header{{padding:14px}}.brand{{font-size:21px}}.status{{display:none}}}}
</style><div class='header'><div><div class='brand'>Vue d’ensemble de mes voyages</div><div class='sub'>✈️ Travel Planner · Tableau de bord</div></div>
<div class='clockweather'><div><div class='small' id='today'>Heure de France</div><div class='clock' id='clock'>--:--:--</div><div class='small'>🇫🇷 Europe/Paris</div></div><div class='weather'><div class='small'>Paris</div>{symbol} {temp}<div class='small'>Météo actuelle</div></div></div>
<div class='kpis'>
<div class='kpi'><span class='kpi-icon'>🌐</span><div><div class='kpi-num'>{len(all_trips)}</div><div class='kpi-label'>Voyages</div></div></div>
<div class='kpi'><span class='kpi-icon'>📍</span><div><div class='kpi-num'>{len({norm(part) for t in all_trips for part in split_destinations(t.get('name','')) if norm(part) in coords()})}</div><div class='kpi-label'>Villes</div></div></div>
<div class='kpi'><span class='kpi-icon'>📷</span><div><div class='kpi-num'>{count_past}</div><div class='kpi-label'>Visités</div></div></div>
<div class='kpi'><span class='kpi-icon'>🎈</span><div><div class='kpi-num'>{count_future}</div><div class='kpi-label'>À venir</div></div></div>
</div>
<div class='mini-cal'><div class='mini-cal-head'><button onclick='moveMonth(-1)' aria-label='Mois précédent'>‹</button><span id='cal-month'>Calendrier</span><button onclick='moveMonth(1)' aria-label='Mois suivant'>›</button></div><div class='mini-cal-grid' id='cal-grid'></div></div>
</div>
<script>
const trips={calendar_events_json};const nowParis=new Date(new Date().toLocaleString('en-US',{{timeZone:'Europe/Paris'}}));let cy=nowParis.getFullYear(),cm=nowParis.getMonth();
function moveMonth(delta){{let d=new Date(cy,cm+delta,1);cy=d.getFullYear();cm=d.getMonth();drawCalendar()}}
function drawCalendar(){{document.getElementById('cal-month').textContent=new Intl.DateTimeFormat('fr-FR',{{month:'long',year:'numeric'}}).format(new Date(cy,cm,1));let g=document.getElementById('cal-grid');g.innerHTML='';for(let n of ['L','M','M','J','V','S','D']){{let e=document.createElement('span');e.className='dow';e.textContent=n;g.appendChild(e)}}let first=(new Date(cy,cm,1).getDay()+6)%7;let days=new Date(cy,cm+1,0).getDate();for(let k=0;k<first;k++)g.appendChild(document.createElement('span'));for(let day=1;day<=days;day++){{let e=document.createElement('span');let key=cy+'-'+String(cm+1).padStart(2,'0')+'-'+String(day).padStart(2,'0');e.textContent=day;if(trips[key]){{e.classList.add('has-trip');e.title=trips[key].join(', ')}}if(cy===nowParis.getFullYear()&&cm===nowParis.getMonth()&&day===nowParis.getDate())e.classList.add('today');g.appendChild(e)}}}}drawCalendar();
function tick(){{let d=new Date();document.getElementById('clock').textContent=new Intl.DateTimeFormat('fr-FR',{{timeZone:'Europe/Paris',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}}).format(d);document.getElementById('today').textContent=new Intl.DateTimeFormat('fr-FR',{{timeZone:'Europe/Paris',weekday:'long',day:'numeric',month:'long',year:'numeric'}}).format(d)}}tick();setInterval(tick,1000);</script></html>"""
if section == '📊 Tableau de bord':
    components.html(header_html,height=205,scrolling=False)
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
            rows=''
            for t in upcoming:
                dt=date.fromisoformat(t['start'][:10]);days=(dt-date.today()).days
                badge='Aujourd’hui' if days==0 else f'Dans {days} jours'
                weather_note=''
                if 0<=days<=13:
                    try:
                        place,wx=forecast_city(split_destinations(t.get('name',''))[0])
                        daily=wx.get('daily',{}); idx=daily.get('time',[]).index(dt.isoformat())
                        weather_note=f' · {weather_symbol(daily["weather_code"][idx])} {round(daily["temperature_2m_max"][idx])}°C (prévision)'
                    except Exception: weather_note=' · météo indisponible'
                else: weather_note=' · météo à venir (prévisions non disponibles)'
                rows+=f'<div class="tp-depart"><span class="tp-flag">{flag_for(t)}</span><div><b>{safe(t.get("name",""))}</b><br><small>{dt.strftime("%d/%m/%Y")}{safe(weather_note)}</small></div><span class="tp-when">{badge}</span></div>'
            st.markdown('<div class="tp-panel">'+rows+'</div>',unsafe_allow_html=True)
    st.subheader('Répartition des destinations')
    # Une étape multi-villes compte pour chaque ville ; les inconnues restent hors graphique.
    country_counts=Counter()
    unknown_countries=[]
    for trip in all_trips:
        parts=split_destinations(trip.get('name',''))
        for part in parts:
            country=country_for(part,trip.get('country',''))
            if country:country_counts[country]+=1
            else:unknown_countries.append(part)
    if unknown_countries:
        country_counts['Pays à préciser'] += len(unknown_countries)
    if country_counts:
        colors=['#1976d2','#ff8229','#f2b900','#21ad85','#7157eb','#ff5c7a','#a5b7d0','#5d8ad5','#e8a5b8','#94a3b8']
        identified=[(k,v) for k,v in country_counts.most_common() if k!='Pays à préciser']
        pairs=identified[:7]
        if len(identified)>7:pairs.append(('Autres',sum(v for _,v in identified[7:])))
        if country_counts.get('Pays à préciser'):pairs.append(('Pays à préciser',country_counts['Pays à préciser']))
        total=sum(country_counts.values());cur=0;stops=[];legend=[]
        for i,(country,n) in enumerate(pairs):
            pct=100*n/total
            stops.append(f'{colors[i%len(colors)]} {cur:.3f}% {cur+pct:.3f}%');cur+=pct
            legend.append(f'<div class="tp-legend-item"><span class="tp-dot" style="background:{colors[i%len(colors)]}"></span>{safe(country)} <b>{n}</b> ({pct:.0f}%)</div>')
        donut=f'<div class="tp-donut" style="background:conic-gradient({",".join(stops)})"><div class="tp-donut-center"><b>{total}</b><small>villes identifiées</small></div></div>'
        st.markdown('<div class="tp-panel"><div class="tp-country-layout">'+donut+'<div class="tp-legend">'+''.join(legend)+'</div></div></div>',unsafe_allow_html=True)
    if unknown_countries:
        st.caption(f'{len(unknown_countries)} destination(s) sans pays identifié, affichées dans « Pays à préciser ». Total préservé, aucun pays inventé et aucune donnée Supabase modifiée.')

if section == '🗺️ Carte & voyages':
    tab_map,tab_list,tab_add,tab_import,tab_places=st.tabs(['🗺️ Carte','📋 Mes destinations','➕ Ajouter / modifier','📥 Import TXT','🏛️ Lieux à découvrir'])
    with tab_map:
        filt=st.selectbox('Afficher',['Tous','Effectués','À venir'])
        subset=[x for x in st.session_state.trips if filt=='Tous' or original_status(x)==('past' if filt=='Effectués' else 'scheduled')]
        pts,missing=local_markers(subset)
        st.write(f'{len(pts)} marqueurs pour {len(subset)} voyages (les étapes multi-villes peuvent produire plusieurs marqueurs).')
        if pts:
            m=folium.Map(location=[47.8,5.4],zoom_start=5,tiles='OpenStreetMap',control_scale=True)
            colors={'past':'blue','scheduled':'orange','wish':'purple'}
            for p in pts:
                match=next((t for t in subset if t.get('name')==p['destination']),{})
                folium.Marker([p['lat'],p['lon']],popup=folium.Popup(htmlsafe(p['destination']),max_width=260),tooltip=p['destination'],icon=folium.Icon(color=colors.get(original_status(match),'blue'),icon='info-sign')).add_to(m)
            components.html(m.get_root().render(),height=560,scrolling=False)
        else: st.info('Aucune coordonnée disponible pour les destinations filtrées.')
        if missing:
            with st.expander(f'{len(missing)} intitulés sans ville reconnue'):
                st.write(', '.join(missing))
                st.caption('Les intitulés d’événements ne sont pas interprétés comme des villes. Tu peux préciser une ville ou des coordonnées dans Ajouter / modifier.')
    with tab_list:
        query=st.text_input('Rechercher une destination')
        subset=[x for x in st.session_state.trips if norm(query) in norm(x.get('name',''))]
        df=pd.DataFrame([{'Destination':x.get('name',''),'Pays':country_for(x.get('name',''),x.get('country','')),'Statut':{'past':'Effectué','scheduled':'Programmé','wish':'Envie'}[original_status(x)],'Début':x.get('start',''),'Fin':x.get('end',''),'Notes':x.get('notes','')} for x in subset])
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
                    item=dict(old,id=old.get('id') or str(uuid.uuid4()),name=name.strip(),country=country.strip() or country_for(name),kind=kind,start=start,end=end,notes=notes,lat=float(lat.replace(',','.')) if lat.strip() else None,lon=float(lon.replace(',','.')) if lon.strip() else None)
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
                kind='past' if any(w in status for w in ['fait','effectu','pass','✅','visité']) else ('wish' if not date else 'future')
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


if section == '🌦️ Météo':
    st.subheader('🌦️ Météo des destinations · 14 jours')
    wc1,wc2=st.columns([4,1])
    city=wc1.text_input('Ville',value='Paris',key='weathercity')
    wc2.write(' ')
    refresh=wc2.button('Actualiser',key='refresh_weather')
    if refresh:forecast_city.clear()
    try:
        place,meteo=forecast_city(city)
        daily=meteo['daily'];cards=''
        for i,ds in enumerate(daily['time']):
            d=date.fromisoformat(ds)
            icon=weather_symbol(daily['weather_code'][i]);hi=round(daily['temperature_2m_max'][i]);lo=round(daily['temperature_2m_min'][i]);rain=daily['precipitation_probability_max'][i]
            cards+=f'<div class="tp-weather-day"><b>{d.strftime("%d/%m")}</b><div class="tp-wicon">{icon}</div><b>{hi}° / {lo}°</b><br><small>💧 {rain if rain is not None else "—"}%</small></div>'
        st.caption(f'Prévisions pour {place["name"]} ({place.get("country","")}) · Source : Open-Meteo')
        st.markdown('<div class="tp-weather-grid">'+cards+'</div>',unsafe_allow_html=True)
    except Exception as exc:st.warning('Météo temporairement indisponible : '+str(exc))

if section == '💡 Idées':
    st.subheader('💡 Idées de prochaines destinations')
    st.caption('Des villes nouvelles inspirées des pays où tu as déjà voyagé, sans doublons avec tes destinations enregistrées.')
    catalog=read_json(ROOT/'data'/'europe-cities.json',{})
    visited_countries=Counter(country_for(part,t.get('country','')) for t in all_trips for part in split_destinations(t.get('name','')) if original_status(t)=='past')
    suggested_countries=[c for c,_ in visited_countries.most_common() if c in catalog]
    choices=['🌟 Suggestions selon mes voyages']+sorted(catalog)
    selection=st.selectbox('Découvrir',choices,key='ideacountry')
    country=(suggested_countries[0] if suggested_countries else 'France') if selection==choices[0] else selection
    if selection==choices[0]: st.caption('Suggestions inspirées de tes pays déjà visités. Choisis un pays pour affiner.')
    existing={norm(part) for t in all_trips for part in split_destinations(t.get('name',''))}
    suggestions=[city for city in catalog.get(country,[]) if norm(city) not in existing]
    st.write(f'**{len(suggestions)} idées** à découvrir en {country} {COUNTRY_FLAGS.get(country,"🌍")}')
    for offset in range(0,min(len(suggestions),40),3):
        cols=st.columns(3)
        for col,cityname in zip(cols,suggestions[offset:offset+3]):
            with col:
                photo=city_photo(cityname)
                picture=f'<img src="{safe(photo)}" alt="Vue de {safe(cityname)}" class="tp-city-photo">' if photo else '<div class="tp-city-placeholder">✈️ Découvrir</div>'
                st.markdown(f'<div class="tp-idea tp-idea-photo">{picture}<div class="tp-idea-content"><b>{flag_html(country)} &nbsp; {safe(cityname)}</b><p>Nouvelle destination à explorer · {safe(country)}</p></div></div>',unsafe_allow_html=True)
                if st.button('♡ Ajouter à mes envies',key='idea_'+country+'_'+cityname):
                    item={'id':str(uuid.uuid4()),'name':cityname,'country':country,'kind':'wish','start':'','end':'','notes':'Idée de destination','lat':None,'lon':None}
                    upsert_trips([item]);st.session_state.trips.append(item);st.rerun()

if section == '🏛️ Visites':
    st.subheader('🏛️ Mon programme de visites')
    st.caption('Prépare une journée culturelle avec les lieux disponibles dans le catalogue local. Horaires et billets à vérifier avant le départ.')
    catalog=read_json(ROOT/'data'/'europe-cities.json',{})
    country=st.selectbox('Pays européen',sorted(catalog),key='visitcountry')
    city=st.selectbox('Ville',catalog.get(country,[]),key='visitcity')
    duration=st.select_slider('Temps disponible',options=['30 min','1 h','2 h','4 h','1 jour','2 jours','3 jours'],value='2 h')
    places=read_json(ROOT/'data'/'places-local.json',{})
    results=places.get(norm(city),[])
    if results:
        n={'30 min':2,'1 h':3,'2 h':5,'4 h':8,'1 jour':12,'2 jours':20,'3 jours':30}[duration]
        names=[e.get('tags',{}).get('name','Lieu sans nom') for e in results[:n]]
        for i,name in enumerate(names,1):
            if i>1:
                a,b=results[i-2],results[i-1]
                try:
                    lat1,lon1,lat2,lon2=map(float,(a['lat'],a['lon'],b['lat'],b['lon']))
                    dlat=math.radians(lat2-lat1);dlon=math.radians(lon2-lon1)
                    h=math.sin(dlat/2)**2+math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
                    km=6371*2*math.asin(min(1,math.sqrt(h)))
                    minutes=max(2,round(km*1.3/4.5*60))
                    st.caption(f'🚶 Étape {i-1} → {i} : environ {minutes} min à pied (estimation à vol d’oiseau × 1,3 ; trajet réel non vérifié)')
                except (KeyError,ValueError,TypeError): st.caption(f'🚶 Étape {i-1} → {i} : trajet à vérifier sur une carte')
            st.markdown(f'<div class="tp-idea" style="min-height:0;margin:7px 0"><b>{i:02d} · {safe(name)}</b><p>📍 {safe(city)} · {safe(country)} · étape proposée</p></div>',unsafe_allow_html=True)
        st.download_button('⬇️ Exporter mon programme (TXT)',f'Programme de visites — {city} ({duration})\n\n'+'\n'.join(f'{i}. {name}' for i,name in enumerate(names,1)),file_name='programme-visites.txt')
    else:
        st.info(f'Aucun lieu détaillé en cache pour {city}. Tu peux consulter « Lieux à découvrir » pour les villes déjà enregistrées dans le catalogue local.')

st.markdown('''<style>
/* Réduire la barre blanche de Streamlit, sans masquer le bouton d'ouverture du menu. */
header[data-testid="stHeader"]{height:2.5rem;background:#f2f6fd}
.block-container{padding-top:1rem!important}
[data-testid="stSidebar"] .stRadio label{width:100%!important}
[data-testid="stSidebar"] div[role="radiogroup"] label{width:100%!important;display:flex}
.tp-city-photo{display:block;width:100%;height:150px;object-fit:cover;border-radius:14px 14px 0 0}
.tp-city-placeholder{height:150px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#dbeafe,#a7d7e9);color:#235480;font-weight:700;border-radius:14px 14px 0 0}
.tp-idea-photo{overflow:hidden;padding:0!important}
.tp-idea-content{padding:14px}
.tp-idea-photo .tp-idea-content p{margin-bottom:0}
</style>''',unsafe_allow_html=True)

# Menu latéral uniforme : six boutons de même largeur, hauteur et espacement.
st.markdown('''<style>
section[data-testid="stSidebar"] div[role="radiogroup"]{
 display:flex!important;flex-direction:column!important;gap:8px!important;width:100%!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label{
 box-sizing:border-box!important;display:flex!important;align-items:center!important;
 width:100%!important;min-width:100%!important;max-width:100%!important;
 min-height:48px!important;height:48px!important;margin:0!important;
 padding:0 14px!important;border-radius:11px!important;
 font-size:14px!important;font-weight:600!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{
 display:none!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label p{
 margin:0!important;white-space:nowrap!important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"]{width:100%!important}
</style>''',unsafe_allow_html=True)
