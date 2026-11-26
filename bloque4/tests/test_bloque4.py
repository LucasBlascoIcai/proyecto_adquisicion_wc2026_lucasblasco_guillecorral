"""Pruebas del Bloque 4 con APIs simuladas (mismo formato JSON que las reales)."""
import importlib.util, random, shutil, sys, unicodedata
from pathlib import Path
from urllib.parse import urlparse
import numpy as np, pandas as pd, requests

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "bloque4_WC26.py"
spec = importlib.util.spec_from_file_location("b4", SRC); b4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b4)

# Trabajar en un directorio temporal para no ensuciar el proyecto
TMP = RAIZ / "tests" / "_tmp"; shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)
b4.DIR_CACHE = TMP / "cache"
random.seed(1)

def sin_tildes(s): return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

ALIAS_API = {"Türkiye": "Turkey", "Czechia": "Czech Republic", "Côte d'Ivoire": "Ivory Coast",
             "Cabo Verde": "Cape Verde Islands", "IR Iran": "Iran", "Bosnia and Herzegovina": "Bosnia & Herzegovina",
             "Curaçao": "Curacao"}

jug = pd.read_excel(RAIZ / "datos" / "jugadoresWC26.xlsx")
verdad, api_players = {}, []
FAKE_SUR = ["Smith", "Garcia", "Kowalski", "Nakamura", "Diallo", "Hassan", "Silva", "Novak"]
for idx, r in jug.iterrows():
    toks = r.nombre_jugador.split()
    if len(r.nombre_jugador) < 3 or random.random() < 0.04:   # 4 % no aparecen en la API
        continue
    pid = 10000 + idx
    nombre = r.nombre_jugador if random.random() < 0.5 else sin_tildes(r.nombre_jugador)
    t = nombre.split()
    first, last = " ".join(t[:-1]), t[-1]
    if random.random() < 0.3: last += " " + random.choice(FAKE_SUR)          # segundo apellido extra
    display = (f"{t[0][0]}. {t[-1]}" if len(t) > 1 else t[0])
    birth = f"{random.randint(1985,2007)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    h = None if random.random() < 0.05 else f"{random.randint(165,200)} cm"
    w = None if random.random() < 0.08 else f"{random.randint(60,95)} kg"
    team = ALIAS_API.get(r.seleccion_nacional, r.seleccion_nacional)
    api_players.append({"player": {"id": pid, "name": display, "firstname": first, "lastname": last,
                                    "birth": {"date": birth}, "nationality": team, "height": h, "weight": w},
                        "statistics": [{"team": {"id": 1, "name": team}}]})
    verdad[idx] = (pid, birth, h, w)
# Distractores: jugadores de la API que no están en nuestro Excel
for k in range(300):
    team = ALIAS_API.get(s := random.choice(jug.seleccion_nacional.unique()), s)
    fn, ln = random.choice(["Alex", "Mohamed", "Luis", "Kenji", "Pierre"]), random.choice(FAKE_SUR) + str(k)
    api_players.append({"player": {"id": 90000 + k, "name": f"{fn[0]}. {ln}", "firstname": fn, "lastname": ln,
                                    "birth": {"date": "1999-01-01"}, "nationality": team, "height": "180 cm", "weight": "75 kg"},
                        "statistics": [{"team": {"id": 2, "name": team}}]})
random.shuffle(api_players)

class Resp:
    def __init__(self, data, headers=None, status=200): self._d, self.headers, self.status_code = data, headers or {}, status
    def json(self): return self._d
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError(self.status_code)

# Simulación del plan gratuito real: temporadas 2022-2024, búsqueda >= 4 letras, 100 llamadas/día
NOMBRES_API = sorted({p["statistics"][0]["team"]["name"] for p in api_players})
TEAM_ID = {n: 500 + i for i, n in enumerate(NOMBRES_API)}
FALTA_EN_AMISTOSOS = "Curacao"                       # obliga a usar /teams?name=...
random.seed(7)
TEMPORADA_JUG = {}                                    # 2024 (85 %), 2023 (10 %), ninguna (5 %)
for x in api_players:
    r = random.random(); TEMPORADA_JUG[x["player"]["id"]] = 2024 if r < .85 else (2023 if r < .95 else None)
ESTADO = {"restantes": 100, "llamadas": 0, "busquedas_cortas": 0}
GRANDE = "Algeria"
relleno = [{"player": {"id": 70000 + k, "name": f"Z. Relleno{k}", "firstname": "Zz", "lastname": f"Relleno{k}",
            "birth": {"date": "2000-01-01"}, "nationality": GRANDE, "height": None, "weight": None},
            "statistics": [{"team": {"id": 3, "name": GRANDE}}]} for k in range(50)]
for x in relleno: TEMPORADA_JUG[x["player"]["id"]] = 2024
api_players[:0] = relleno

def fake_api_football(url, params):
    ESTADO["llamadas"] += 1; ESTADO["restantes"] -= 1
    hdr = {"x-ratelimit-requests-remaining": str(max(ESTADO["restantes"], 0))}
    if ESTADO["restantes"] < 0:
        return Resp({"errors": {"requests": "You have reached the request limit for the day"}, "response": []}, hdr)
    path = urlparse(url).path; season = params.get("season")
    if season is not None and not 2022 <= int(season) <= 2024:
        return Resp({"errors": {"plan": "Free plans do not have access to this season, try from 2022 to 2024."}, "response": []}, hdr)
    if path.endswith("/teams"):
        if "league" in params:
            resp = [{"team": {"id": TEAM_ID[n], "name": n, "national": True}} for n in NOMBRES_API if n != FALTA_EN_AMISTOSOS]
            resp += [{"team": {"id": 9999, "name": "Gibraltar", "national": True}}]
        else:
            n = params["name"]; resp = [{"team": {"id": TEAM_ID[n], "name": n, "national": True}}] if n in TEAM_ID else []
        return Resp({"errors": [], "response": resp}, hdr)
    if int(params.get("page", 1)) > 3:
        return Resp({"errors": {"plan": "Free plans are limited to a maximum value of 3 for the Page parameter"}, "response": []}, hdr)
    if path.endswith("/players") and "team" in params:
        nom = next(n for n, i in TEAM_ID.items() if i == params["team"])
        lista = [x for x in api_players if x["statistics"][0]["team"]["name"] == nom and TEMPORADA_JUG[x["player"]["id"]] == int(season)]
        p = params["page"]; tot = max(1, int(np.ceil(len(lista) / 20)))
        return Resp({"errors": [], "paging": {"current": p, "total": tot}, "response": lista[(p-1)*20: p*20]}, hdr)
    if path.endswith("/players/profiles"):
        if len(params["search"]) < 4:
            ESTADO["busquedas_cortas"] += 1
            return Resp({"errors": {"search": "The Search field must be at least 4 characters in length."}, "response": []}, hdr)
        q = b4.normalizar(params["search"])
        res = [{"player": x["player"]} for x in api_players if q in b4.normalizar(x["player"]["lastname"])][:250]
        return Resp({"errors": [], "paging": {"current": 1, "total": 1}, "response": res}, hdr)
    raise AssertionError((url, params))

def patch(fn):
    def get(self, url, params=None, timeout=None): return fn(url, params or {})
    requests.Session.get = get

def comprobar(df, nombre_test):
    ok = mal = 0
    for idx, (pid, birth, h, w) in verdad.items():
        f = df.at[idx, "fecha_nacimiento"]
        if pd.isna(f): continue
        if f.strftime("%Y-%m-%d") == birth: ok += 1
        else: mal += 1
    extra = sum(1 for i in df.index if i not in verdad and pd.notna(df.at[i, "fecha_nacimiento"]))
    print(f"[{nombre_test}] correctos={ok}/{len(verdad)}  incorrectos={mal}  asignados a ausentes de la API={extra}")
    assert mal == 0 and extra == 0, "Hay emparejamientos erróneos"
    return ok

b4.time.sleep = lambda s: None
patch(fake_api_football)
ENTRADA = RAIZ / "datos" / "jugadoresWC26.xlsx"
out = TMP / "jug_api.xlsx"

# --- Test 1: varios días hasta completar (día 1 con solo 48 llamadas, como en la ejecución real) ---
encontrados, dia = [], 0
ESTADO["restantes"] = 48
while True:
    dia += 1
    antes = ESTADO["llamadas"]
    df = b4.extraer_datos_jugadores(ENTRADA, out, "FAKE", pausa=0, max_llamadas=95)
    n = comprobar(df, f"día {dia}")
    print(f"   llamadas reales ese día: {ESTADO['llamadas'] - antes}")
    assert ESTADO["llamadas"] - antes <= 96
    encontrados.append(n)
    if dia > 1 and encontrados[-1] == encontrados[-2]: break
    ESTADO["restantes"] = 100
    assert dia < 25
assert ESTADO["busquedas_cortas"] == 0, "Se enviaron búsquedas de menos de 4 letras"
print("Días necesarios:", dia - 1, "· encontrados por día:", encontrados)
assert encontrados[-1] >= 0.97 * len(verdad)

x = pd.read_excel(out)
assert list(x.columns[-3:]) == ["fecha_nacimiento", "altura_jugador", "peso_jugador"]
assert (x["fecha_nacimiento"] == "No disponible").sum() > 0
rt = b4.leer_jugadores_api(out)
assert rt["fecha_nacimiento"].dtype.kind == "M" and rt["altura_jugador"].dtype.kind == "f"
mal_h = sum(1 for i,(pid,b,h,w) in verdad.items() if h and pd.notna(rt.at[i,"altura_jugador"]) and rt.at[i,"altura_jugador"] != int(h.split()[0]))
assert mal_h == 0; print("Formato de salida y alturas OK")

# --- Test 2: ejecución extra -> todo desde caché, 0 llamadas ---
antes = ESTADO["llamadas"]; ESTADO["restantes"] = 100
b4.extraer_datos_jugadores(ENTRADA, out, "FAKE", pausa=0)
assert ESTADO["llamadas"] == antes; print("Caché OK: 0 llamadas en la ejecución extra")

# --- Test 4: OSM ---
COORD = {"Estadio Azteca": (19.3029, -99.1505), "Estadio Akron": (20.6817, -103.4626), "Estadio BBVA": (25.6692, -100.2446),
         "BMO Field": (43.6332, -79.4186), "BC Place": (49.2768, -123.1120), "MetLife Stadium": (40.8135, -74.0745),
         "SoFi Stadium": (33.9535, -118.3392), "AT&T Stadium": (32.7473, -97.0945), "Arrowhead Stadium": (39.0489, -94.4839),
         "NRG Stadium": (29.6847, -95.4107), "Mercedes-Benz Stadium": (33.7554, -84.4008), "Hard Rock Stadium": (25.9580, -80.2389),
         "Gillette Stadium": (42.0909, -71.2643), "Lincoln Financial Field": (39.9008, -75.1675), "Levi's Stadium": (37.4030, -121.9700),
         "Lumen Field": (47.5952, -122.3316)}
IDS = {n: 5000 + i for i, n in enumerate(COORD)}
OSM_LLAMADAS = {"nominatim": 0, "v06": 0}
def fake_osm(url, params):
    if "nominatim" in url:
        OSM_LLAMADAS["nominatim"] += 1
        q = params["q"].split(",")[0]
        if q in COORD:
            lat, lon = COORD[q]
            return Resp([{"osm_type": "way", "osm_id": IDS[q], "lat": str(lat + 0.0003), "lon": str(lon), "category": "leisure",
                          "type": "stadium", "display_name": f"{q}, City"}])
        return Resp([])
    OSM_LLAMADAS["v06"] += 1
    wid = int(url.split("/way/")[1].split("/")[0]); n = next(k for k, v in IDS.items() if v == wid); lat, lon = COORD[n]
    nodes = [{"type": "node", "id": i, "lat": lat + dx, "lon": lon + dy} for i, (dx, dy) in enumerate([(0.001,0.001),(-0.001,0.001),(-0.001,-0.001),(0.001,-0.001)])]
    return Resp({"elements": nodes + [{"type": "way", "id": wid, "nodes": [0,1,2,3], "tags": {"name": n, "leisure": "stadium"}}]})
patch(fake_osm)
f_est = TMP / "estadios.xlsx"; f_coord = TMP / "estadios_coord.xlsx"
est = b4.crear_excel_estadios((RAIZ / "datos" / "partidosWC26.xlsx"), f_est)
assert len(est) == 16
res = b4.extraer_coordenadas_estadios(f_est, f_coord, pausa=0)
assert res["latitud"].notna().all() and (res["fuente"] == "OSM API v0.6").all()
for r in res.itertuples():
    lat, lon = COORD[b4.separar_nombre_estadio(r.estadio)[1]]
    assert abs(r.latitud - lat) < 1e-6 and abs(r.longitud - lon) < 1e-6
print("OSM OK · llamadas", OSM_LLAMADAS)

# regex
assert b4.separar_nombre_estadio("Mexico City Stadium (Estadio Azteca)") == ("Mexico City Stadium", "Estadio Azteca")
assert b4.separar_nombre_estadio("Wembley") == ("Wembley", "Wembley")

# resumen por estadio
part = b4.cargar_partidos((RAIZ / "datos" / "partidosWC26.xlsx"))
tot = b4.resumen_estadios(part, res); assert tot.partidos.sum() == 104 and tot.goles.sum() == 308
qf = b4.resumen_estadios(part, res, ["Quarter-finals"]); assert qf.partidos.sum() == 4
print("Resumen estadios OK", tot[["estadio","partidos","goles"]].head(3).to_string())

# dejar ficheros de prueba para el test del dashboard
shutil.copy(out, TMP / "jugadoresWC26_api.xlsx"); shutil.copy(f_coord, TMP / "estadiosWC26_coordenadas.xlsx")
print("\nTODOS LOS TESTS PASAN")

# --- Test 5: football-data.org (ejercicio 4: 5 grandes ligas) ---
sys.path.insert(0, str(RAIZ / "tests"))
from clubes_2025_26 import CLUBES
b4.F_CLUBES_LIGAS, b4.F_PLANTILLAS_LIGAS, b4.F_JUGADORES_LIGAS = TMP / "clubes.xlsx", TMP / "plant.xlsx", TMP / "jug_ligas.xlsx"
ESTADO_FD = {"llamadas": 0, "con_plantillas": True, "bloquea_temporada": False, "tokens": set()}
jug_mundial = pd.read_excel(ENTRADA)

def fake_fd(url, params):
    ESTADO_FD["llamadas"] += 1
    codigo = url.split("/competitions/")[1].split("/")[0]
    if ESTADO_FD["bloquea_temporada"] and "season" in params:
        return Resp({"message": "The resource you are looking for is restricted.", "errorCode": 403}, status=403)
    teams = []
    for i, nombre in enumerate(CLUBES[codigo]):
        corto = {"FC Internazionale Milano": "Inter", "Newcastle United FC": "Newcastle",
                 "Atalanta BC": "Atalanta"}.get(nombre, nombre.replace(" FC", ""))   # como la API real
        t = {"id": hash(nombre) % 10**6, "name": nombre, "shortName": corto}
        if ESTADO_FD["con_plantillas"]:
            sq = [{"id": 10**6 + k, "name": r.nombre_jugador, "position": "X", "dateOfBirth": "1999-02-03",
                   "nationality": ALIAS_API.get(r.seleccion_nacional, r.seleccion_nacional)}
                  for k, r in jug_mundial.iterrows() if b4.puntuacion_club(r.club_jugador, [nombre]) >= 0.8]
            t["squad"] = sq + [{"id": 5 * 10**6 + i, "name": f"Relleno {i}", "position": "X",
                                "dateOfBirth": "2001-01-01", "nationality": "Narnia"}]
        teams.append(t)
    return Resp({"season": {"startDate": "2026-08-15"}, "teams": teams})

def get_fd(self, url, params=None, timeout=None):
    ESTADO_FD["tokens"].add(self.headers.get("X-Auth-Token"))
    return fake_fd(url, params or {})
requests.Session.get = get_fd

jl = b4.extraer_grandes_ligas(ENTRADA, "TOKEN_FD", pausa=0)
assert ESTADO_FD["llamadas"] == 5 and ESTADO_FD["tokens"] == {"TOKEN_FD"}
n5 = (jl["liga"] != b4.OTRAS_LIGAS).sum()
assert 450 <= n5 <= 500, n5
for club, liga in [("Charlton Athletic FC", b4.OTRAS_LIGAS), ("Rangers FC", b4.OTRAS_LIGAS),
                   ("Newcastle United Jets FC", b4.OTRAS_LIGAS), ("Atalanta Bergamo", "Serie A"),
                   ("Inter Miami CF", b4.OTRAS_LIGAS),
                   ("Real Madrid C. F.", "LaLiga"), ("Manchester City FC", "Premier League")]:
    if club in set(jl["club_jugador"]):
        assert set(jl.loc[jl["club_jugador"] == club, "liga"]) == {liga}, club
assert (jl["en_plantilla_api"] == "Sí").sum() >= 0.95 * n5        # cruce por nombre con las plantillas
r = b4.resumen_ligas(b4.leer_jugadores_ligas(b4.F_JUGADORES_LIGAS))
assert r["n_total"] == 1248 and r["por_seleccion"].shape[0] == 48
assert list(r["evolucion"]["mundial"]) == [2018, 2022, 2026] and r["evolucion"]["pct_5_grandes"].iloc[0] == 52.3
print(f"football-data OK · 5 llamadas · en 5 grandes ligas: {n5} ({r['pct5']:.1f} %)")

# segunda ejecución: todo desde caché
antes = ESTADO_FD["llamadas"]; b4.extraer_grandes_ligas(ENTRADA, "TOKEN_FD", pausa=0)
assert ESTADO_FD["llamadas"] == antes; print("football-data caché OK")

# plan sin plantillas y sin acceso a la temporada 2025 -> temporada actual, clasificación solo por club
shutil.rmtree(b4.DIR_CACHE / "football_data"); ESTADO_FD.update(con_plantillas=False, bloquea_temporada=True, llamadas=0)
jl2 = b4.extraer_grandes_ligas(ENTRADA, "TOKEN_FD", pausa=0)
assert ESTADO_FD["llamadas"] == 10 and (jl2["liga"] != b4.OTRAS_LIGAS).sum() == n5
assert set(jl2["en_plantilla_api"]) == {"No disponible"}
print("football-data sin plantillas / temporada bloqueada OK")
print("\nTODOS LOS TESTS PASAN (incluido ejercicio 4)")
