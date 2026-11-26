"""
Proyecto Colaborativo · Adquisición y Visualización de Datos · Mundial 2026
BLOQUE 4 — Datos vía API (api-football.com, football-data.org y OpenStreetMap) y visualización

Ejercicios del enunciado (v5) y dónde se resuelven:
  Ej. 3  Fecha de nacimiento de los jugadores del Mundial -> comando 'jugadores' + pestaña 1 del dashboard
  Ej. 4  Jugadores del Mundial en las 5 grandes ligas      -> comando 'ligas'     + pestaña 2 del dashboard
  Ej. 6  Coordenadas de los estadios (OpenStreetMap)        -> comando 'estadios'
  Ej. 7  Mapa de estadios con selector de ronda             -> pestaña 3 del dashboard

Modos de uso:

  1) Ejercicio 3: fecha de nacimiento (y altura y peso) de los jugadores (API-Football):
         python bloque4_WC26.py jugadores --api-key TU_CLAVE
     (o definiendo la variable de entorno APIFOOTBALL_KEY)

  2) Ejercicio 4: jugadores del Mundial en las 5 grandes ligas (football-data.org):
         python bloque4_WC26.py ligas --token TU_TOKEN
     (o definiendo la variable de entorno FOOTBALLDATA_TOKEN)

  3) Extraer latitud y longitud de los estadios (OpenStreetMap):
         python bloque4_WC26.py estadios

  4) Dashboard interactivo (Streamlit + Plotly):
         streamlit run bloque4_WC26.py

Todas las respuestas de las APIs se guardan en una caché local (carpeta cache/),
de modo que repetir la ejecución no gasta llamadas y, si se agota la cuota diaria,
al día siguiente se continúa donde se quedó.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# =============================================================================
# 0. CONFIGURACIÓN GENERAL
# =============================================================================

DIR_BASE = Path(__file__).resolve().parent
DIR_DATOS = DIR_BASE / "datos"
DIR_CACHE = DIR_BASE / "cache"

# Ficheros de entrada (generados en el Bloque 1)
F_JUGADORES = DIR_DATOS / "jugadoresWC26.xlsx"
F_PARTIDOS = DIR_DATOS / "partidosWC26.xlsx"

# Ficheros de salida (Bloque 4)
F_JUGADORES_API = DIR_DATOS / "jugadoresWC26_api.xlsx"
F_ESTADIOS = DIR_DATOS / "estadiosWC26.xlsx"
F_ESTADIOS_COORD = DIR_DATOS / "estadiosWC26_coordenadas.xlsx"

NO_DISPONIBLE = "No disponible"

# API-Football
AF_URL = "https://v3.football.api-sports.io"
AF_LIGA_AMISTOSOS = 10       # "Friendlies" (amistosos de selecciones) en API-Football
AF_TEMPORADAS = (2024, 2023) # el plan gratuito solo permite las temporadas 2022-2024
AF_PAUSA = 6.5               # segundos entre llamadas (respeta el límite por minuto)
AF_MAX_LLAMADAS = 95         # margen sobre las 100 llamadas/día del plan gratuito
AF_MAX_PAGINA = 3            # el plan gratuito no permite pedir más allá de la página 3
AF_UMBRAL = 0.65            # puntuación mínima para dar por bueno un emparejamiento de nombres

# OpenStreetMap
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSM_API_URL = "https://api.openstreetmap.org/api/0.6"
OSM_PAUSA = 1.1              # la política de uso de Nominatim exige máx. 1 petición/s
OSM_USER_AGENT = "WC26-proyecto-ICAI/1.0 (proyecto universitario)"
CODIGOS_PAIS = {"MEX": "mx", "USA": "us", "CAN": "ca"}

# Rondas: nombre en los datos -> etiqueta en español (en orden del torneo)
RONDAS = {
    "Group Stage": "Fase de Grupos",
    "Round of 32": "Dieciseisavos",
    "Round of 16": "Octavos",
    "Quarter-finals": "Cuartos",
    "Semi-finals": "Semifinales",
    "Third-place match": "Tercer puesto",
    "Final": "Final",
}

# Nombres de selección en nuestros datos -> posibles nombres en API-Football
ALIAS_SELECCIONES = {
    "USA": ["USA", "United States"],
    "Türkiye": ["Turkey", "Türkiye"],
    "Czechia": ["Czech Republic", "Czechia"],
    "Côte d'Ivoire": ["Ivory Coast", "Cote D'Ivoire", "Côte d'Ivoire"],
    "Cabo Verde": ["Cape Verde Islands", "Cape Verde", "Cabo Verde"],
    "Congo DR": ["Congo DR", "DR Congo"],
    "IR Iran": ["Iran", "IR Iran"],
    "South Korea": ["South Korea", "Korea Republic"],
    "Bosnia and Herzegovina": ["Bosnia & Herzegovina", "Bosnia and Herzegovina", "Bosnia"],
    "Curaçao": ["Curacao", "Curaçao"],
}


# =============================================================================
# 1. UTILIDADES COMUNES
# =============================================================================

def normalizar(texto) -> str:
    """Minúsculas, sin tildes ni signos: 'Quiñones-Ruíz' -> 'quinones ruiz'."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


class CacheJSON:
    """Caché en disco: una respuesta JSON por consulta (clave = hash de la URL+params)."""

    def __init__(self, carpeta: Path):
        self.carpeta = carpeta
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def _ruta(self, url: str, params: dict) -> Path:
        clave = url + "?" + json.dumps(params, sort_keys=True, ensure_ascii=False)
        return self.carpeta / (hashlib.md5(clave.encode()).hexdigest() + ".json")

    def leer(self, url: str, params: dict):
        ruta = self._ruta(url, params)
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))
        return None

    def guardar(self, url: str, params: dict, datos) -> None:
        self._ruta(url, params).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def cargar_partidos(ruta: Path = F_PARTIDOS) -> pd.DataFrame:
    """Carga partidos y corrige pequeñas inconsistencias de formato heredadas del Bloque 1."""
    partidos = pd.read_excel(ruta)
    partidos["ronda"] = partidos["ronda"].astype(str).str.strip()        # 'Quarter-finals ' -> sin espacio
    partidos["pais_partido"] = partidos["pais_partido"].astype(str).str.strip().str.upper()  # 'usa' -> 'USA'
    partidos["estadio"] = partidos["estadio"].astype(str).str.strip()
    partidos = partidos.drop_duplicates(subset="index_partido")
    return partidos


# =============================================================================
# 2. API-FOOTBALL: FECHA DE NACIMIENTO, ALTURA Y PESO
# =============================================================================

class CuotaAgotada(Exception):
    """Se ha alcanzado el límite diario de llamadas (o el fijado por el usuario)."""


class PlanNoPermite(Exception):
    """El plan contratado no da acceso a la consulta (p. ej. temporada no incluida)."""


class ClienteAPIFootball:
    """Cliente mínimo de API-Football v3 con caché, control de cuota y pausas."""

    def __init__(self, api_key: str, max_llamadas: int = AF_MAX_LLAMADAS, pausa: float = AF_PAUSA):
        self.sesion = requests.Session()
        self.sesion.headers.update({"x-apisports-key": api_key})
        self.cache = CacheJSON(DIR_CACHE / "api_football")
        self.max_llamadas = max_llamadas
        self.pausa = pausa
        self.llamadas = 0              # llamadas reales hechas en esta ejecución
        self.restantes_dia = None      # según la cabecera x-ratelimit-requests-remaining
        self._ultima = 0.0

    def get(self, endpoint: str, params: dict) -> dict:
        url = f"{AF_URL}/{endpoint}"
        en_cache = self.cache.leer(url, params)
        if en_cache is not None:
            return en_cache                                   # coste: 0 llamadas

        if self.llamadas >= self.max_llamadas or self.restantes_dia == 0:
            raise CuotaAgotada(f"Límite de llamadas alcanzado ({self.llamadas} en esta ejecución).")

        for intento in range(3):
            espera = self.pausa - (time.time() - self._ultima)
            if espera > 0:
                time.sleep(espera)
            resp = self.sesion.get(url, params=params, timeout=30)
            self._ultima = time.time()
            self.llamadas += 1

            restantes = resp.headers.get("x-ratelimit-requests-remaining")
            if restantes is not None and str(restantes).isdigit():
                self.restantes_dia = int(restantes)

            if resp.status_code == 429:                       # demasiadas por minuto
                time.sleep(60)
                continue
            resp.raise_for_status()
            datos = resp.json()

            # API-Football devuelve 'errors' como lista vacía o como diccionario
            errores = datos.get("errors") or {}
            if isinstance(errores, list):
                errores = {f"error_{i}": e for i, e in enumerate(errores)}
            if errores:
                texto = " | ".join(f"{k}: {v}" for k, v in errores.items())
                claves = {k.lower() for k in errores}
                if "ratelimit" in claves:
                    time.sleep(60)
                    continue
                if "requests" in claves:
                    raise CuotaAgotada(texto)
                if "plan" in claves:
                    raise PlanNoPermite(texto)
                raise RuntimeError(f"Error de API-Football: {texto}")

            self.cache.guardar(url, params, datos)            # solo se cachean respuestas válidas
            return datos
        raise RuntimeError("API-Football no respondió tras varios reintentos.")

    def get_paginado(self, endpoint: str, params: dict, verbose: bool = True) -> list:
        """Recorre las páginas (paging.current / paging.total) y une las respuestas.
        El plan gratuito solo permite hasta la página 3: se para ahí y se devuelve lo obtenido."""
        resultados, pagina = [], 1
        while True:
            try:
                datos = self.get(endpoint, {**params, "page": pagina})
            except PlanNoPermite:
                if pagina == 1:
                    raise
                return resultados                     # límite de páginas del plan: nos quedamos con lo obtenido
            resultados.extend(datos.get("response", []))
            total = (datos.get("paging") or {}).get("total", 1) or 1
            if verbose:
                print(f"   {endpoint} {params} · página {pagina}/{total} · llamadas reales: {self.llamadas}")
            if pagina >= min(total, AF_MAX_PAGINA):
                return resultados
            pagina += 1


# ---------- 2.1 Conversión de la respuesta de la API ----------

def extraer_numero(valor):
    """'180 cm' -> 180 ; '75kg' -> 75 ; None -> NaN."""
    if valor is None:
        return np.nan
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(valor))
    return float(m.group(1).replace(",", ".")) if m else np.nan


def a_candidato(item: dict) -> dict:
    """Convierte un elemento 'response' de /players o /players/profiles a un dict plano."""
    jug = item.get("player", {}) or {}
    stats = item.get("statistics") or []
    equipo = (stats[0].get("team") or {}).get("name") if stats else None
    return {
        "id": jug.get("id"),
        "nombre": jug.get("name") or "",
        "nombre_completo": f"{jug.get('firstname') or ''} {jug.get('lastname') or ''}".strip(),
        "equipo": equipo or jug.get("nationality") or "",
        "nacionalidad": jug.get("nationality") or "",
        "fecha_nacimiento": (jug.get("birth") or {}).get("date"),
        "altura": extraer_numero(jug.get("height")),
        "peso": extraer_numero(jug.get("weight")),
    }


# ---------- 2.2 Emparejamiento de nombres ----------

PARTICULAS = {"de", "da", "do", "dos", "das", "del", "la", "van", "der", "den", "von", "el", "al", "bin", "ben", "e", "y"}


# Apellido en mayúsculas pegado al nombre, como en los Excel de la solución: 'GUIMARAESBruno' -> 'GUIMARAES Bruno'
PATRON_PEGADO = re.compile(r"([A-ZÁÉÍÓÚÑÇÃÕÂÊÔÜ]{2,})(?=[A-ZÁÉÍÓÚÑÇÃÕÂÊÔÜ][a-záéíóúñçãõâêôü])")


def tokens_nombre(nombre: str) -> list:
    nombre = PATRON_PEGADO.sub(r"\1 ", str(nombre))
    return [t for t in normalizar(nombre).split() if t not in PARTICULAS]


def _con_uniones(tokens: list) -> list:
    """Añade las uniones de tokens consecutivos: ['ali', 'reza'] -> [..., 'alireza']."""
    return tokens + [a + b for a, b in zip(tokens, tokens[1:]) if len(a) > 1 and len(b) > 1]


def _union_coincide(a: str, b: str) -> bool:
    """Comparación estricta para nombres unidos ('alireza' ~ 'ali'+'reza')."""
    return a == b or (min(len(a), len(b)) >= 6 and SequenceMatcher(None, a, b).ratio() >= 0.9)


def _cubierto(tok: str, propias: list, otro: list, otro_uniones: list) -> bool:
    """¿Está 'tok' (de un nombre) presente en el otro nombre?"""
    if any(_token_coincide(tok, b) for b in otro):
        return True
    if len(tok) > 1 and any(_union_coincide(tok, x) for x in otro_uniones):
        return True                                   # 'alireza' frente a 'ali' + 'reza'
    return any(tok in x and _union_coincide(x, b) for x in propias for b in otro + otro_uniones)


def _token_coincide(a: str, b: str) -> bool:
    if len(a) == 1 or len(b) == 1:                    # inicial: 'r' vs 'raul'
        return a[0] == b[0]
    if a == b:
        return True
    if min(len(a), len(b)) < 4:
        return False
    # Transliteraciones ('saeid'/'saeed', 'mahdi'/'mehdi', 'arya'/'aria'): misma inicial y misma
    # longitud -> más tolerante. Con distinta longitud ('alvaro'/'alvarez') se exige más parecido.
    if a[0] != b[0]:
        umbral = 0.9
    elif len(a) == len(b):
        umbral = 0.75
    else:
        umbral = 0.85
    return SequenceMatcher(None, a, b).ratio() >= umbral


def puntuacion_nombre(nuestro: str, cand: dict) -> float:
    """Similitud [0,1] entre nuestro nombre y un candidato de la API.

    Combina (70 %) la cobertura de tokens en ambos sentidos, que tolera segundos
    nombres, segundos apellidos e iniciales ('J. Quiñones'), con (30 %) la
    similitud de la cadena completa.
    """
    t_nuestro = tokens_nombre(nuestro)
    if not t_nuestro:
        return 0.0
    # Mismo apellido pero distinto nombre de pila (p. ej. 'Ousmane Diomande' vs 'Yan Diomande',
    # o 'Ahmed Mohammad' vs 'Ali Hasan Mohammad'): se decide con el nombre COMPLETO de la API,
    # porque el nombre corto ('A. Mohammad') solo trae la inicial y casaría con cualquiera.
    t_comp = tokens_nombre(cand["nombre_completo"])
    u_nuestro = _con_uniones(t_nuestro)
    penaliza = (len(t_comp) > 1 and len(t_nuestro) > 1 and len(t_comp[0]) > 1 and len(t_nuestro[0]) > 1
                and not any(_token_coincide(t_comp[0], b) or b.startswith(t_comp[0]) for b in u_nuestro)
                and not any(_token_coincide(t_nuestro[0], a) or a.startswith(t_nuestro[0])
                            for a in _con_uniones(t_comp)))
    mejor = 0.0
    for texto in (cand["nombre_completo"], cand["nombre"]):
        t_api = tokens_nombre(texto)
        if not t_api:
            continue
        # al menos un token "real" (no inicial) debe coincidir: evita casar solo por iniciales
        un_api = _con_uniones(t_api)[len(t_api):]          # solo las uniones
        un_nuestro = u_nuestro[len(t_nuestro):]
        # al menos un token "real" (no inicial) debe coincidir: evita casar solo por iniciales
        if not any(len(a) > 1 and _cubierto(a, un_api, [b for b in t_nuestro if len(b) > 1], un_nuestro)
                   for a in t_api):
            continue
        cob_api = sum(_cubierto(a, un_api, t_nuestro, un_nuestro) for a in t_api) / len(t_api)
        cob_nuestro = sum(_cubierto(b, un_nuestro, t_api, un_api) for b in t_nuestro) / len(t_nuestro)
        secuencia = SequenceMatcher(None, " ".join(t_nuestro), " ".join(t_api)).ratio()
        punt = 0.7 * (cob_api + cob_nuestro) / 2 + 0.3 * secuencia
        mejor = max(mejor, punt)
    return mejor * 0.6 if penaliza else mejor


def mapear_selecciones(nuestras: list, de_api: list) -> dict:
    """Asocia cada selección de nuestros datos con su nombre en la API."""
    norm_api = {normalizar(e): e for e in de_api if e}
    mapa = {}
    for sel in nuestras:
        posibles = [normalizar(x) for x in ALIAS_SELECCIONES.get(sel, []) + [sel]]
        encontrado = next((norm_api[p] for p in posibles if p in norm_api), None)
        if encontrado is None and norm_api:                # último recurso: similitud de texto
            mejor = max(norm_api, key=lambda k: SequenceMatcher(None, normalizar(sel), k).ratio())
            if SequenceMatcher(None, normalizar(sel), mejor).ratio() >= 0.8:
                encontrado = norm_api[mejor]
        mapa[sel] = encontrado
    return mapa


def asignar_voraz(grupo: pd.DataFrame, pool: list, umbral: float, usados: set) -> dict:
    """Asigna jugadores de 'grupo' a candidatos de 'pool' de mayor a menor puntuación.
    Cada candidato se usa una sola vez ('usados' se actualiza en el sitio)."""
    por_id = {c["id"]: c for c in pool}
    pares = sorted(
        ((puntuacion_nombre(nom, c), idx, c["id"]) for idx, nom in grupo["nombre_jugador"].items() for c in pool),
        key=lambda x: x[0], reverse=True,
    )
    res = {}
    for punt, idx, cid in pares:
        if punt < umbral:
            break
        if idx not in res and cid not in usados:
            res[idx] = por_id[cid]
            usados.add(cid)
    return res


def emparejar(jugadores: pd.DataFrame, candidatos: list, umbral: float = 0.6, umbral_global: float = 0.85) -> dict:
    """Devuelve {índice_fila: candidato}.

    1) Dentro de cada selección: asignación voraz por puntuación (cada candidato
       de la API solo se puede asignar a un jugador).
    2) Los jugadores sin pareja se buscan entre todos los candidatos libres con un
       umbral más exigente (por si la API usa un nombre de selección distinto).
    """
    df_c = pd.DataFrame(candidatos).drop_duplicates(subset="id")
    if df_c.empty:
        return {}
    cand_por_id = {c["id"]: c for c in df_c.to_dict("records")}
    mapa_sel = mapear_selecciones(jugadores["seleccion_nacional"].unique().tolist(),
                                  df_c["equipo"].unique().tolist() + df_c["nacionalidad"].unique().tolist())

    asignados, usados = {}, set()
    for sel, grupo in jugadores.groupby("seleccion_nacional"):
        equipo_api = mapa_sel.get(sel)
        if equipo_api is None:
            continue
        pool = df_c[(df_c["equipo"] == equipo_api) | (df_c["nacionalidad"] == equipo_api)].to_dict("records")
        asignados.update(asignar_voraz(grupo, pool, umbral, usados))

    libres = [c for c in cand_por_id.values() if c["id"] not in usados]
    for idx, nom in jugadores["nombre_jugador"].items():
        if idx in asignados or not libres:
            continue
        punt, c = max(((puntuacion_nombre(nom, c), c) for c in libres), key=lambda x: x[0])
        if punt >= umbral_global:
            asignados[idx] = c
            usados.add(c["id"])
            libres.remove(c)
    return asignados


# ---------- 2.3 Proceso completo ----------

def obtener_ids_selecciones(cliente: "ClienteAPIFootball", selecciones: list) -> dict:
    """Devuelve {selección: id_equipo_API}.

    1) Una sola llamada a /teams?league=10&season=2024 (amistosos internacionales)
       devuelve casi todas las selecciones del mundo con su id.
    2) Las que no aparezcan se buscan por nombre con /teams?name=... (1 llamada cada una).
    """
    ids = {}
    try:
        datos = cliente.get("teams", {"league": AF_LIGA_AMISTOSOS, "season": AF_TEMPORADAS[0]})
        nacionales = {t["team"]["name"]: t["team"]["id"]
                      for t in datos.get("response", []) if (t.get("team") or {}).get("national")}
        mapa = mapear_selecciones(selecciones, list(nacionales))
        ids = {sel: nacionales[nom] for sel, nom in mapa.items() if nom is not None}
    except (PlanNoPermite, RuntimeError) as e:
        print(f"   ! No se pudo obtener la lista de selecciones: {e}")
    for sel in selecciones:
        if sel in ids:
            continue
        for nombre in ALIAS_SELECCIONES.get(sel, []) + [sel]:
            try:
                datos = cliente.get("teams", {"name": nombre})
            except (PlanNoPermite, RuntimeError):
                continue
            nac = [t["team"] for t in datos.get("response", []) if (t.get("team") or {}).get("national")]
            if nac:
                ids[sel] = nac[0]["id"]
                break
    return ids


def extraer_datos_jugadores(ruta_entrada: Path, ruta_salida: Path, api_key: str,
                            temporadas: tuple = AF_TEMPORADAS,
                            max_llamadas: int = AF_MAX_LLAMADAS, pausa: float = AF_PAUSA,
                            busqueda_individual: bool = True) -> pd.DataFrame:
    """Añade fecha_nacimiento, altura_jugador y peso_jugador al DataFrame de jugadores.

    El plan gratuito de API-Football solo permite las temporadas 2022-2024, así que
    no se puede pedir la plantilla del Mundial 2026 directamente. Estrategia:
      A) Para cada selección: /players?team=ID&season=2024 devuelve (20 por llamada)
         los jugadores que la selección utilizó ese año, con fecha de nacimiento,
         altura y peso. Si faltan jugadores, se repite con la temporada 2023.
         -> unas 2-3 llamadas por selección (frente a ~26 jugador a jugador).
      B) Solo para los que sigan sin encontrarse: /players/profiles?search=apellido
         (1 llamada por jugador).
    Con 100 llamadas/día no da tiempo en un solo día: la caché guarda cada respuesta,
    así que basta con volver a ejecutar el script al día siguiente para continuar.
    """
    jugadores = pd.read_excel(ruta_entrada)
    cliente = ClienteAPIFootball(api_key, max_llamadas=max_llamadas, pausa=pausa)
    asignados, usados, cuota_agotada = {}, set(), False
    selecciones = sorted(jugadores["seleccion_nacional"].unique())

    # --- Estrategia A: jugadores de cada selección por temporada ---
    print(f"[A] Jugadores de cada selección (temporadas {', '.join(map(str, temporadas))})...")
    try:
        ids = obtener_ids_selecciones(cliente, selecciones)
        print(f"   Selecciones identificadas en la API: {len(ids)}/{len(selecciones)}")
        for sel in selecciones:
            if sel not in ids:
                print(f"   ! {sel}: no encontrada en la API")
                continue
            grupo_total = jugadores[jugadores["seleccion_nacional"] == sel]
            for temporada in temporadas:
                grupo = grupo_total[~grupo_total.index.isin(list(asignados))]
                if grupo.empty:
                    break
                try:
                    pool = [a_candidato(x) for x in cliente.get_paginado(
                        "players", {"team": ids[sel], "season": temporada}, verbose=False)]
                except (PlanNoPermite, RuntimeError) as e:
                    print(f"   ! {sel} {temporada}: {e}")
                    continue
                pool = [c for c in {c["id"]: c for c in pool}.values() if c["id"] not in usados]
                asignados.update(asignar_voraz(grupo, pool, AF_UMBRAL, usados))
            n_ok = int(grupo_total.index.isin(list(asignados)).sum())
            print(f"   {sel:<24} {n_ok:>2}/{len(grupo_total)} · llamadas reales hoy: {cliente.llamadas}")
    except CuotaAgotada as e:
        cuota_agotada = True
        print(f"   ! {e}\n   -> Vuelva a ejecutar mañana: la caché conserva lo ya descargado.")
    print(f"   Emparejados {len(asignados)}/{len(jugadores)} jugadores con la estrategia A.")

    # --- Estrategia B: búsqueda individual de los que faltan ---
    if busqueda_individual and not cuota_agotada:
        pendientes = [i for i in jugadores.index if i not in asignados]
        print(f"[B] Búsqueda individual de {len(pendientes)} jugadores pendientes...")
        for idx in pendientes:
            nombre = jugadores.at[idx, "nombre_jugador"]
            toks = [t for t in tokens_nombre(nombre) if len(t) >= 4]   # la API exige ≥4 letras
            if not toks:
                continue                                                # p. ej. 'Mc'
            try:
                datos = cliente.get("players/profiles", {"search": toks[-1]})
            except CuotaAgotada as e:
                print(f"   ! {e} Vuelva a ejecutar mañana: la caché conserva lo ya descargado.")
                break
            except PlanNoPermite as e:
                print(f"   ! {e}")
                break
            except RuntimeError as e:                                   # un jugador no detiene el proceso
                print(f"   ! {nombre}: {e}")
                continue
            cand = [c for c in (a_candidato(x) for x in datos.get("response", [])) if c["id"] not in usados]
            res = emparejar(jugadores.loc[[idx]], cand, umbral=0.7, umbral_global=0.9)
            if idx in res:
                asignados[idx] = res[idx]
                usados.add(res[idx]["id"])

    # --- Volcado de resultados en el DataFrame original ---
    jugadores["fecha_nacimiento"] = pd.NaT
    jugadores["altura_jugador"] = np.nan
    jugadores["peso_jugador"] = np.nan
    for idx, c in asignados.items():
        jugadores.at[idx, "fecha_nacimiento"] = pd.to_datetime(c["fecha_nacimiento"], errors="coerce")
        jugadores.at[idx, "altura_jugador"] = c["altura"]
        jugadores.at[idx, "peso_jugador"] = c["peso"]
    jugadores["fecha_nacimiento"] = pd.to_datetime(jugadores["fecha_nacimiento"], errors="coerce")

    guardar_jugadores_api(jugadores, ruta_salida)
    resumen = {c: int(jugadores[c].notna().sum()) for c in ["fecha_nacimiento", "altura_jugador", "peso_jugador"]}
    print(f"\nLlamadas reales a la API: {cliente.llamadas} · restantes hoy según la API: {cliente.restantes_dia}")
    print(f"Datos obtenidos (de {len(jugadores)}): {resumen}")
    print(f"Guardado en {ruta_salida}")
    return jugadores


def guardar_jugadores_api(jugadores: pd.DataFrame, ruta: Path) -> None:
    """Exporta a Excel indicando 'No disponible' en los datos que no se han encontrado."""
    salida = jugadores.copy()
    salida["fecha_nacimiento"] = salida["fecha_nacimiento"].dt.strftime("%d/%m/%Y")
    for col in ["altura_jugador", "peso_jugador"]:
        salida[col] = salida[col].map(lambda v: int(v) if pd.notna(v) else np.nan).astype(object)
    salida[["fecha_nacimiento", "altura_jugador", "peso_jugador"]] = (
        salida[["fecha_nacimiento", "altura_jugador", "peso_jugador"]].fillna(NO_DISPONIBLE)
    )
    salida.to_excel(ruta, index=False)


def leer_jugadores_api(ruta: Path = F_JUGADORES_API) -> pd.DataFrame:
    """Lee el Excel generado y vuelve a convertir 'No disponible' en nulos."""
    df = pd.read_excel(ruta)
    df = df.replace(NO_DISPONIBLE, np.nan)
    df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], format="%d/%m/%Y", errors="coerce")
    for col in ["altura_jugador", "peso_jugador"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# =============================================================================
# 3. FOOTBALL-DATA.ORG: JUGADORES DEL MUNDIAL EN LAS 5 GRANDES LIGAS
# =============================================================================

FD_URL = "https://api.football-data.org/v4"
FD_PAUSA = 6.5               # plan gratuito: 10 llamadas/minuto
FD_TEMPORADA = 2025          # temporada 2025/26: la de los clubes de los jugadores en el Mundial 2026
GRANDES_LIGAS = {            # código de competición en football-data.org -> nombre
    "PL": "Premier League",
    "PD": "LaLiga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}
OTRAS_LIGAS = "Otras ligas"
MUNDIALES_PREVIOS = {2018: (736, 385), 2022: (831, 417)}   # (jugadores totales, en las 5 grandes ligas)

F_CLUBES_LIGAS = DIR_DATOS / "clubes_grandes_ligas.xlsx"
F_PLANTILLAS_LIGAS = DIR_DATOS / "jugadores_grandes_ligas.xlsx"
F_JUGADORES_LIGAS = DIR_DATOS / "jugadoresWC26_ligas.xlsx"

# Palabras genéricas de los nombres de club que no ayudan a distinguirlos
GENERICOS_CLUB = {"fc", "cf", "afc", "ac", "sc", "ssc", "as", "ss", "sv", "rc", "rcd", "ud", "cd", "sd", "ca",
                  "club", "de", "del", "la", "le", "bc", "fussball", "futbol", "calcio", "football"}


class ClienteFootballData:
    """Cliente mínimo de football-data.org v4 (cabecera X-Auth-Token) con caché y pausas."""

    def __init__(self, token: str, pausa: float = FD_PAUSA):
        self.sesion = requests.Session()
        self.sesion.headers.update({"X-Auth-Token": token})
        self.cache = CacheJSON(DIR_CACHE / "football_data")
        self.pausa = pausa
        self.llamadas = 0
        self._ultima = 0.0

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url, params = f"{FD_URL}/{endpoint}", params or {}
        en_cache = self.cache.leer(url, params)
        if en_cache is not None:
            return en_cache
        for _ in range(3):
            espera = self.pausa - (time.time() - self._ultima)
            if espera > 0:
                time.sleep(espera)
            resp = self.sesion.get(url, params=params, timeout=30)
            self._ultima = time.time()
            self.llamadas += 1
            if resp.status_code == 429:                       # más de 10 llamadas por minuto
                time.sleep(60)
                continue
            try:
                datos = resp.json()
            except ValueError:
                datos = {}
            if resp.status_code == 403:                       # recurso no incluido en el plan
                raise PlanNoPermite(datos.get("message", "Recurso restringido para este plan"))
            if resp.status_code >= 400:
                raise RuntimeError(f"football-data.org {resp.status_code}: {datos.get('message', resp.text[:200])}")
            self.cache.guardar(url, params, datos)
            return datos
        raise RuntimeError("football-data.org no respondió tras varios reintentos.")


def tokens_club(nombre) -> list:
    """Palabras significativas del nombre de un club (sin 'FC', 'CF', años de fundación...)."""
    return [t for t in normalizar(nombre).split() if t not in GENERICOS_CLUB and len(t) > 1 and not t.isdigit()]


def _palabra_club_igual(a: str, b: str) -> bool:
    # casi idénticas: misma inicial y ≥92 % de parecido ('munchen'/'muenchen'); 'celtic' ≠ 'celta'
    return a == b or (a[0] == b[0] and min(len(a), len(b)) >= 6 and SequenceMatcher(None, a, b).ratio() >= 0.92)


def puntuacion_club(nuestro: str, nombres_api: list) -> float:
    """Similitud [0,1] entre el club de nuestro Excel y un club de la API (nombre largo o corto).

    Regla principal: TODAS las palabras de nuestro club deben estar en el nombre de la API, que
    puede tener palabras de más ('Real Betis' ~ 'Real Betis Balompié', 'RC Lens' ~ 'Racing Club
    de Lens'), pero no al revés ('Charlton Athletic' no es 'Athletic Club', 'Newcastle United
    Jets' no es 'Newcastle United FC').
    Excepción: si la API usa una sola palabra y es exactamente la primera de nuestro club
    ('Atalanta BC' ~ 'Atalanta Bergamo').
    """
    t_nuestro, mejor = tokens_club(nuestro), 0.0
    if not t_nuestro:
        return 0.0
    for nombre in nombres_api:
        t_api = tokens_club(nombre)
        if not t_api:
            continue
        secuencia = SequenceMatcher(None, normalizar(nuestro), normalizar(nombre)).ratio()
        if all(any(_palabra_club_igual(a, b) for b in t_api) for a in t_nuestro):
            mejor = max(mejor, 0.8 + 0.2 * secuencia)
        elif len(t_api) == 1 and len(t_api[0]) >= 5 and t_api[0] == t_nuestro[0]:
            mejor = max(mejor, 0.75 + 0.05 * secuencia)
    return mejor


def clasificar_clubes(clubes_nuestros: list, clubes_api: pd.DataFrame, umbral: float = 0.75) -> dict:
    """Devuelve {club de nuestro Excel: fila de clubes_api} para los clubes de las 5 grandes ligas."""
    filas = clubes_api.to_dict("records")
    mapa = {}
    for club in clubes_nuestros:
        punt, fila = max(((puntuacion_club(club, [f["club"], f["club_corto"]]), f) for f in filas),
                         key=lambda x: x[0], default=(0.0, None))
        if punt >= umbral:
            mapa[club] = fila
    return mapa


def extraer_grandes_ligas(ruta_jugadores: Path, token: str, temporada: int = FD_TEMPORADA,
                          pausa: float = FD_PAUSA) -> pd.DataFrame:
    """Ejercicio 4. Con 1 llamada por liga (/competitions/{código}/teams) se obtienen los
    clubes de cada una de las 5 grandes ligas (y, si el plan lo incluye, sus plantillas).
    Cada jugador del Mundial se asigna a la liga de su club; el resto, a 'Otras ligas'."""
    cliente = ClienteFootballData(token, pausa=pausa)
    clubes, plantillas = [], []
    for codigo, liga in GRANDES_LIGAS.items():
        try:
            datos = cliente.get(f"competitions/{codigo}/teams", {"season": temporada})
            temp_usada = temporada
        except PlanNoPermite as e:                            # si no deja pedir esa temporada, la actual
            print(f"   ! {liga} {temporada}: {e} -> se usa la temporada actual")
            datos = cliente.get(f"competitions/{codigo}/teams")
            temp_usada = (datos.get("season") or {}).get("startDate", "actual")[:4]
        equipos = datos.get("teams", [])
        print(f"   {liga:<15} temporada {temp_usada}: {len(equipos)} clubes · llamadas: {cliente.llamadas}")
        for t in equipos:
            clubes.append({"liga": liga, "club_id": t.get("id"), "club": t.get("name"),
                           "club_corto": t.get("shortName") or t.get("name")})
            for p in t.get("squad") or []:
                plantillas.append({"liga": liga, "club": t.get("name"), "jugador_id": p.get("id"),
                                   "nombre": p.get("name"), "posicion": p.get("position"),
                                   "fecha_nacimiento": p.get("dateOfBirth"), "nacionalidad": p.get("nationality")})
    df_clubes = pd.DataFrame(clubes)
    df_clubes.to_excel(F_CLUBES_LIGAS, index=False)
    df_plant = pd.DataFrame(plantillas)
    if not df_plant.empty:
        df_plant.to_excel(F_PLANTILLAS_LIGAS, index=False)
        print(f"   Plantillas descargadas: {len(df_plant)} jugadores en las 5 grandes ligas")
    else:
        print("   ! El plan no incluye plantillas: la clasificación se hace solo por club")

    # --- Liga de cada jugador del Mundial según su club ---
    jugadores = pd.read_excel(ruta_jugadores)
    mapa = clasificar_clubes(jugadores["club_jugador"].dropna().unique().tolist(), df_clubes)
    jugadores["liga"] = jugadores["club_jugador"].map(lambda c: mapa[c]["liga"] if c in mapa else OTRAS_LIGAS)
    jugadores["club_api"] = jugadores["club_jugador"].map(lambda c: mapa[c]["club"] if c in mapa else NO_DISPONIBLE)

    # --- Si hay plantillas: cruce por nombre y nacionalidad (comprobación + fecha de nacimiento) ---
    jugadores["en_plantilla_api"] = NO_DISPONIBLE if df_plant.empty else "No"
    jugadores["fecha_nacimiento_fd"] = pd.NaT
    if not df_plant.empty:
        cand = [{"id": r.jugador_id, "nombre": r.nombre, "nombre_completo": r.nombre, "equipo": r.nacionalidad,
                 "nacionalidad": r.nacionalidad, "fecha_nacimiento": r.fecha_nacimiento}
                for r in df_plant.itertuples()]
        for idx, c in emparejar(jugadores, cand, umbral=0.75, umbral_global=1.1).items():
            jugadores.at[idx, "en_plantilla_api"] = "Sí"
            jugadores.at[idx, "fecha_nacimiento_fd"] = pd.to_datetime(c["fecha_nacimiento"], errors="coerce")
        print(f"   Jugadores del Mundial encontrados en esas plantillas: {(jugadores['en_plantilla_api'] == 'Sí').sum()}")

    salida = jugadores.copy()
    salida["fecha_nacimiento_fd"] = pd.to_datetime(salida["fecha_nacimiento_fd"]).dt.strftime("%d/%m/%Y")
    salida["fecha_nacimiento_fd"] = salida["fecha_nacimiento_fd"].fillna(NO_DISPONIBLE)
    salida.to_excel(F_JUGADORES_LIGAS, index=False)

    n5 = int((jugadores["liga"] != OTRAS_LIGAS).sum())
    print(f"\nClubes de las 5 grandes ligas encontrados en nuestro Excel: {len(mapa)}")
    print(f"Jugadores del Mundial en las 5 grandes ligas: {n5}/{len(jugadores)} ({100 * n5 / len(jugadores):.1f} %)")
    print(jugadores["liga"].value_counts().to_string())
    print(f"Llamadas reales a football-data.org: {cliente.llamadas} · Guardado en {F_JUGADORES_LIGAS}")
    return jugadores


def leer_jugadores_ligas(ruta: Path = F_JUGADORES_LIGAS) -> pd.DataFrame:
    df = pd.read_excel(ruta)
    df["fecha_nacimiento_fd"] = pd.to_datetime(df["fecha_nacimiento_fd"].replace(NO_DISPONIBLE, np.nan),
                                               format="%d/%m/%Y", errors="coerce")
    return df


def resumen_ligas(jugadores: pd.DataFrame) -> dict:
    """Tablas para el análisis del ejercicio 4."""
    orden = list(GRANDES_LIGAS.values()) + [OTRAS_LIGAS]
    por_liga = jugadores["liga"].value_counts().reindex(orden, fill_value=0)
    por_sel = (pd.crosstab(jugadores["seleccion_nacional"], jugadores["liga"])
               .reindex(columns=orden, fill_value=0))
    por_sel["% 5 grandes"] = 100 * por_sel[list(GRANDES_LIGAS.values())].sum(axis=1) / por_sel[orden].sum(axis=1)
    por_sel = por_sel.sort_values("% 5 grandes", ascending=False)
    n_total, n5 = len(jugadores), int(por_liga[list(GRANDES_LIGAS.values())].sum())
    evolucion = pd.DataFrame(
        [(m, t, g) for m, (t, g) in MUNDIALES_PREVIOS.items()] + [(2026, n_total, n5)],
        columns=["mundial", "jugadores_totales", "jugadores_5_grandes"])
    evolucion["otras_ligas"] = evolucion["jugadores_totales"] - evolucion["jugadores_5_grandes"]
    evolucion["pct_5_grandes"] = (100 * evolucion["jugadores_5_grandes"] / evolucion["jugadores_totales"]).round(1)
    return {"por_liga": por_liga, "por_seleccion": por_sel, "evolucion": evolucion,
            "n_total": n_total, "n5": n5, "pct5": 100 * n5 / n_total if n_total else np.nan}


# =============================================================================
# 4. OPENSTREETMAP: LATITUD Y LONGITUD DE LOS ESTADIOS
# =============================================================================

# Los estadios aparecen como "Nombre FIFA (Nombre comercial)". Con una expresión
# regular separamos ambos: el nombre comercial es el que figura en OpenStreetMap.
PATRON_ESTADIO = re.compile(r"^\s*(?P<fifa>[^()]+?)\s*\((?P<comercial>[^()]+)\)\s*$")


def separar_nombre_estadio(nombre: str) -> tuple:
    m = PATRON_ESTADIO.match(str(nombre))
    if m:
        return m.group("fifa").strip(), m.group("comercial").strip()
    return str(nombre).strip(), str(nombre).strip()


def crear_excel_estadios(ruta_partidos: Path = F_PARTIDOS, ruta_salida: Path = F_ESTADIOS) -> pd.DataFrame:
    """Genera el Excel de entrada con los estadios del Mundial a partir de partidosWC26.xlsx."""
    partidos = cargar_partidos(ruta_partidos)
    estadios = (partidos[["estadio", "ciudad_partido", "pais_partido"]]
                .drop_duplicates(subset="estadio").sort_values("estadio").reset_index(drop=True))
    estadios.to_excel(ruta_salida, index=False)
    return estadios


class ClienteOSM:
    """Nominatim (buscador oficial de OSM) para localizar el elemento por nombre y
    API v0.6 para leer ese elemento y calcular sus coordenadas.

    La API v0.6 no permite buscar por nombre (solo por id o por área), por eso el
    id del estadio se obtiene primero con Nominatim.
    """

    def __init__(self, pausa: float = OSM_PAUSA):
        self.sesion = requests.Session()
        self.sesion.headers.update({"User-Agent": OSM_USER_AGENT, "Accept-Language": "en"})
        self.cache = CacheJSON(DIR_CACHE / "osm")
        self.pausa = pausa
        self._ultima = 0.0
        self.llamadas = 0

    def _get(self, url: str, params: dict | None = None):
        params = params or {}
        en_cache = self.cache.leer(url, params)
        if en_cache is not None:
            return en_cache
        espera = self.pausa - (time.time() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        resp = self.sesion.get(url, params=params, timeout=30)
        self._ultima = time.time()
        self.llamadas += 1
        resp.raise_for_status()
        datos = resp.json()
        self.cache.guardar(url, params, datos)
        return datos

    def buscar(self, consulta: str, pais: str | None) -> list:
        params = {"q": consulta, "format": "jsonv2", "limit": 5}
        if pais:
            params["countrycodes"] = pais
        return self._get(NOMINATIM_URL, params)

    def coordenadas_v06(self, osm_type: str, osm_id) -> tuple | None:
        """Lee el elemento con la API v0.6 y devuelve (lat, lon, etiquetas).

        - node: tiene lat/lon directamente.
        - way / relation: se pide '/full' (incluye sus nodos) y se usa el centroide.
        """
        if osm_type == "node":
            datos = self._get(f"{OSM_API_URL}/node/{osm_id}.json")
        else:
            datos = self._get(f"{OSM_API_URL}/{osm_type}/{osm_id}/full.json")
        elementos = datos.get("elements", [])
        nodos = [e for e in elementos if e.get("type") == "node" and "lat" in e]
        if not nodos:
            return None
        principal = next((e for e in elementos if e.get("type") == osm_type and e.get("id") == int(osm_id)), {})
        return (float(np.mean([n["lat"] for n in nodos])),
                float(np.mean([n["lon"] for n in nodos])),
                principal.get("tags", {}))


def _es_estadio(r: dict) -> bool:
    return r.get("category") in ("leisure", "building") and r.get("type") in ("stadium", "sports_centre")


def en_norteamerica(lat: float, lon: float) -> bool:
    return 14 <= lat <= 72 and -170 <= lon <= -50


def geolocalizar_estadio(cliente: ClienteOSM, estadio: str, ciudad: str, pais: str) -> dict:
    fifa, comercial = separar_nombre_estadio(estadio)
    cc = CODIGOS_PAIS.get(str(pais).upper())
    # De más específica a más general; se prefiere un resultado etiquetado como estadio
    consultas = [f"{comercial}, {ciudad}", comercial, f"{fifa}, {ciudad}", f"{comercial} stadium"]
    elegido, consulta_ok = None, None
    for q in consultas:
        try:
            resultados = cliente.buscar(q, cc)
        except requests.RequestException as e:
            print(f"   ! Error en Nominatim ('{q}'): {e}")
            continue
        if not resultados:
            continue
        estadios = [r for r in resultados if _es_estadio(r)]
        elegido, consulta_ok = (estadios or resultados)[0], q
        if estadios:
            break

    fila = {"estadio": estadio, "ciudad_partido": ciudad, "pais_partido": pais,
            "nombre_osm": None, "osm_tipo": None, "osm_id": None,
            "latitud": np.nan, "longitud": np.nan, "fuente": NO_DISPONIBLE}
    if elegido is None:
        return fila

    fila.update(nombre_osm=elegido.get("display_name", "").split(",")[0],
                osm_tipo=elegido.get("osm_type"), osm_id=elegido.get("osm_id"))
    lat, lon, fuente = float(elegido["lat"]), float(elegido["lon"]), "Nominatim"
    try:
        res = cliente.coordenadas_v06(elegido["osm_type"], elegido["osm_id"])
        if res:
            lat, lon, tags = res
            fuente = "OSM API v0.6"
            fila["nombre_osm"] = tags.get("name", fila["nombre_osm"])
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"   ! API v0.6 no disponible para {estadio}: {e}. Se usan las coordenadas de Nominatim.")

    if not en_norteamerica(lat, lon):
        print(f"   ! Coordenadas fuera de Norteamérica para {estadio} ({lat:.3f}, {lon:.3f}); se descartan.")
        return fila
    fila.update(latitud=round(lat, 6), longitud=round(lon, 6), fuente=fuente)
    print(f"   {estadio:<50} -> ({lat:.4f}, {lon:.4f}) [{fuente}] consulta: '{consulta_ok}'")
    return fila


def extraer_coordenadas_estadios(ruta_entrada: Path, ruta_salida: Path, pausa: float = OSM_PAUSA) -> pd.DataFrame:
    """Lee un Excel con la columna 'estadio' (y opcionalmente ciudad_partido / pais_partido)
    y añade latitud y longitud de cada estadio."""
    estadios = pd.read_excel(ruta_entrada)
    for col in ["ciudad_partido", "pais_partido"]:
        if col not in estadios.columns:
            estadios[col] = ""
    cliente = ClienteOSM(pausa=pausa)
    filas = [geolocalizar_estadio(cliente, r.estadio, r.ciudad_partido, r.pais_partido)
             for r in estadios.itertuples(index=False)]
    resultado = pd.DataFrame(filas)
    salida = resultado.copy()
    salida[["latitud", "longitud"]] = salida[["latitud", "longitud"]].astype(object).fillna(NO_DISPONIBLE)
    salida.to_excel(ruta_salida, index=False)
    print(f"\nLlamadas reales a OSM: {cliente.llamadas} · localizados {resultado['latitud'].notna().sum()}/{len(resultado)}")
    print(f"Guardado en {ruta_salida}")
    return resultado


# =============================================================================
# 5. ANÁLISIS (funciones puras, usadas por el dashboard)
# =============================================================================

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS_MES = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])   # 28.25: años bisiestos


def analisis_nacimientos(jugadores: pd.DataFrame) -> dict:
    """Distribución por mes y trimestre frente a lo esperado si los nacimientos
    fueran uniformes (proporcional a los días de cada mes) + test chi-cuadrado."""
    from scipy.stats import chisquare

    fechas = jugadores["fecha_nacimiento"].dropna()
    n = len(fechas)
    obs_mes = fechas.dt.month.value_counts().reindex(range(1, 13), fill_value=0).to_numpy()
    esp_mes = n * DIAS_MES / DIAS_MES.sum()
    obs_trim = obs_mes.reshape(4, 3).sum(axis=1)
    esp_trim = esp_mes.reshape(4, 3).sum(axis=1)
    p_mes = chisquare(obs_mes, esp_mes).pvalue if n > 0 else np.nan
    p_trim = chisquare(obs_trim, esp_trim).pvalue if n > 0 else np.nan
    return {"n": n, "obs_mes": obs_mes, "esp_mes": esp_mes, "obs_trim": obs_trim,
            "esp_trim": esp_trim, "p_mes": p_mes, "p_trim": p_trim}


def resumen_estadios(partidos: pd.DataFrame, coords: pd.DataFrame, rondas: list | None = None) -> pd.DataFrame:
    """Partidos y goles por estadio (goles = marcador final; no incluye tandas de penaltis)."""
    p = partidos if not rondas else partidos[partidos["ronda"].isin(rondas)]
    agg = (p.assign(goles=p["marcador_local"] + p["marcador_visitante"])
           .groupby("estadio").agg(partidos=("index_partido", "count"), goles=("goles", "sum"))
           .reset_index())
    agg["goles_por_partido"] = (agg["goles"] / agg["partidos"]).round(2)
    return agg.merge(coords, on="estadio", how="inner")


def cargar_fechas_nacimiento() -> pd.DataFrame | None:
    """Jugadores del Mundial con su fecha de nacimiento combinando las dos fuentes:
    API-Football (jugadoresWC26_api.xlsx) y football-data.org (jugadoresWC26_ligas.xlsx)."""
    if not F_JUGADORES_API.exists() and not F_JUGADORES_LIGAS.exists():
        return None
    if F_JUGADORES_API.exists():
        jug = leer_jugadores_api(F_JUGADORES_API)
        jug["fuente_fecha"] = np.where(jug["fecha_nacimiento"].notna(), "API-Football", None)
    else:
        jug = pd.read_excel(F_JUGADORES)
        jug["fecha_nacimiento"], jug["fuente_fecha"] = pd.NaT, None
    if F_JUGADORES_LIGAS.exists():
        fd = leer_jugadores_ligas(F_JUGADORES_LIGAS)
        if len(fd) == len(jug):                                  # mismo orden de filas: el Excel del Bloque 1
            falta = jug["fecha_nacimiento"].isna() & fd["fecha_nacimiento_fd"].notna()
            jug.loc[falta, "fecha_nacimiento"] = fd.loc[falta, "fecha_nacimiento_fd"]
            jug.loc[falta, "fuente_fecha"] = "football-data.org"
    return jug


# =============================================================================
# 6. DASHBOARD (Streamlit + Plotly)
# =============================================================================

def dashboard() -> None:
    import plotly.express as px
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="Mundial 2026 · Bloque 4", page_icon="⚽", layout="wide")
    st.title("Mundial 2026 · Datos obtenidos vía API")
    tab_nac, tab_ligas, tab_map = st.tabs(["📅 Ej. 3 · Fecha de nacimiento", "🏆 Ej. 4 · 5 grandes ligas",
                                           "🏟️ Ej. 7 · Mapa de estadios"])

    # ---------------------- Ej. 3: fecha de nacimiento ----------------------
    with tab_nac:
        jug = st.cache_data(cargar_fechas_nacimiento)()
        if jug is None:
            st.warning("No hay fechas de nacimiento. Ejecute primero:  "
                       "`python bloque4_WC26.py jugadores` y/o `python bloque4_WC26.py ligas`")
        else:
            fuentes = jug["fuente_fecha"].value_counts()
            st.caption("Fuente de las fechas de nacimiento: " + " · ".join(f"{k}: {v}" for k, v in fuentes.items()))
            c1, c2 = st.columns(2)
            posiciones = sorted(jug["posicion"].dropna().unique())
            sel_pos = c1.multiselect("Posición", posiciones, default=posiciones)
            min_min = c2.slider("Minutos mínimos jugados en el Mundial", 0, int(jug["minutos_jugados"].max()), 0, step=30)
            filtro = jug[jug["posicion"].isin(sel_pos) & (jug["minutos_jugados"] >= min_min)]
            r = analisis_nacimientos(filtro)

            if r["n"] == 0:
                st.info("No hay jugadores con fecha de nacimiento para este filtro.")
            else:
                pct_q1 = 100 * r["obs_trim"][0] / r["n"]
                pct_q1_esp = 100 * r["esp_trim"][0] / r["n"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Jugadores con fecha", f"{r['n']} / {len(filtro)}")
                m2.metric("Nacidos en ene–mar", f"{pct_q1:.1f} %", f"{pct_q1 - pct_q1_esp:+.1f} pp vs esperado")
                m3.metric("Nacidos en oct–dic", f"{100 * r['obs_trim'][3] / r['n']:.1f} %")
                m4.metric("p-valor χ² (trimestres)", f"{r['p_trim']:.4f}")

                # Gráfico 1: barras por mes + línea de lo esperado con nacimientos uniformes
                fig = go.Figure()
                fig.add_bar(x=MESES, y=r["obs_mes"], name="Jugadores nacidos", marker_color="#2563eb",
                            hovertemplate="%{x}: %{y} jugadores<extra></extra>")
                fig.add_scatter(x=MESES, y=r["esp_mes"], name="Esperado (distribución uniforme)",
                                mode="lines+markers", line=dict(color="#dc2626", dash="dash"),
                                hovertemplate="%{x}: %{y:.1f} esperados<extra></extra>")
                fig.update_layout(title="Mes de nacimiento de los jugadores del Mundial 2026",
                                  xaxis_title="Mes de nacimiento", yaxis_title="Nº de jugadores",
                                  legend=dict(orientation="h", y=1.1), height=420)
                st.plotly_chart(fig, width="stretch")

                # Gráfico 2: % por trimestre (todos vs. los que más juegan) frente al 25 % teórico
                trim = ["T1 (ene–mar)", "T2 (abr–jun)", "T3 (jul–sep)", "T4 (oct–dic)"]
                titulares = filtro[filtro["minutos_jugados"] >= max(min_min, 180)]
                r_tit = analisis_nacimientos(titulares)
                fig2 = go.Figure()
                fig2.add_bar(x=trim, y=100 * r["obs_trim"] / r["n"], name="Jugadores filtrados",
                             marker_color="#2563eb", text=[f"{v:.1f}%" for v in 100 * r["obs_trim"] / r["n"]],
                             textposition="outside")
                if r_tit["n"] > 0:
                    fig2.add_bar(x=trim, y=100 * r_tit["obs_trim"] / r_tit["n"], name="Con ≥180 minutos",
                                 marker_color="#16a34a", text=[f"{v:.1f}%" for v in 100 * r_tit["obs_trim"] / r_tit["n"]],
                                 textposition="outside")
                fig2.add_scatter(x=trim, y=100 * r["esp_trim"] / r["n"], name="Esperado", mode="lines+markers",
                                 line=dict(color="#dc2626", dash="dash"))
                fig2.update_layout(title="Porcentaje de jugadores por trimestre de nacimiento", barmode="group",
                                   yaxis_title="% de jugadores", legend=dict(orientation="h", y=1.1), height=420)
                st.plotly_chart(fig2, width="stretch")

                # Conclusión generada a partir de los datos
                signif = r["p_trim"] < 0.05
                tendencia = r["obs_trim"][0] > r["obs_trim"][3]
                st.subheader("Conclusión")
                st.markdown(
                    f"- El **{pct_q1:.1f} %** de los jugadores nació en el primer trimestre, frente al "
                    f"**{pct_q1_esp:.1f} %** esperado si los nacimientos fueran uniformes; en el último "
                    f"trimestre nació el **{100 * r['obs_trim'][3] / r['n']:.1f} %**.\n"
                    f"- Test χ² de bondad de ajuste por trimestres: p = {r['p_trim']:.4f} → la diferencia "
                    f"**{'es' if signif else 'no es'} estadísticamente significativa** (α = 0,05).\n"
                    f"- {'Los datos apoyan' if signif and tendencia else 'Los datos no permiten confirmar'} el "
                    "*efecto de la edad relativa*: en categorías inferiores los nacidos a principios de año "
                    "(con corte el 1 de enero) son mayores y más desarrollados que sus compañeros, reciben más "
                    "oportunidades y llegan con más frecuencia a la élite."
                )

    # ---------------------- Ej. 4: 5 grandes ligas ----------------------
    with tab_ligas:
        if not F_JUGADORES_LIGAS.exists():
            st.warning(f"No existe {F_JUGADORES_LIGAS.name}. Ejecute primero:  "
                       "`python bloque4_WC26.py ligas --token TU_TOKEN`")
        else:
            jl = st.cache_data(leer_jugadores_ligas)(F_JUGADORES_LIGAS)
            r = resumen_ligas(jl)
            ligas5 = list(GRANDES_LIGAS.values())
            colores = dict(zip(ligas5 + [OTRAS_LIGAS],
                               ["#3d195b", "#ee2737", "#d20515", "#008fd7", "#dae025", "#b0b7c3"]))
            ev = r["evolucion"].set_index("mundial")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Jugadores del Mundial 2026", r["n_total"])
            m2.metric("En las 5 grandes ligas", r["n5"], f"{r['pct5']:.1f} %", delta_color="off")
            m3.metric("% en 2022", f"{ev.loc[2022, 'pct_5_grandes']:.1f} %")
            m4.metric("Variación 2022 → 2026", f"{r['pct5'] - ev.loc[2022, 'pct_5_grandes']:+.1f} pp")

            # Gráfico 1: jugadores por liga
            pl_ = r["por_liga"]
            fig1 = go.Figure(go.Bar(x=pl_.index, y=pl_.values, marker_color=[colores[x] for x in pl_.index],
                                    text=[f"{v} ({100 * v / r['n_total']:.1f} %)" for v in pl_.values],
                                    textposition="outside"))
            fig1.update_layout(title="Jugadores del Mundial 2026 según la liga de su club",
                               yaxis_title="Nº de jugadores", height=420)
            st.plotly_chart(fig1, width="stretch")

            # Gráfico 2: reparto por selección (100 % apilado), ordenado por peso de las 5 grandes ligas
            ps = r["por_seleccion"]
            pct = ps[ligas5 + [OTRAS_LIGAS]].div(ps[ligas5 + [OTRAS_LIGAS]].sum(axis=1), axis=0) * 100
            fig2 = go.Figure()
            for liga in ligas5 + [OTRAS_LIGAS]:
                fig2.add_bar(y=pct.index, x=pct[liga], name=liga, orientation="h", marker_color=colores[liga],
                             customdata=ps[liga], hovertemplate="%{y}: %{customdata} jugadores (%{x:.0f} %)<extra>"
                             + liga + "</extra>")
            fig2.update_layout(barmode="stack", title="Reparto de los jugadores de cada selección por liga",
                               xaxis_title="% de la convocatoria", height=1150,
                               yaxis=dict(autorange="reversed", automargin=True, dtick=1),
                               legend=dict(orientation="h", y=1.0, yanchor="bottom", traceorder="normal"),
                               margin=dict(t=110))
            st.plotly_chart(fig2, width="stretch")

            # Gráfico 3: comparación con los Mundiales anteriores
            fig3 = go.Figure()
            fig3.add_bar(x=ev.index.astype(str), y=ev["jugadores_5_grandes"], name="5 grandes ligas",
                         marker_color="#2563eb")
            fig3.add_bar(x=ev.index.astype(str), y=ev["otras_ligas"], name="Otras ligas", marker_color="#b0b7c3")
            fig3.add_scatter(x=ev.index.astype(str), y=ev["pct_5_grandes"], name="% en 5 grandes ligas",
                             yaxis="y2", mode="lines+markers+text", text=[f"{v:.1f} %" for v in ev["pct_5_grandes"]],
                             textposition="top center", line=dict(color="#dc2626"))
            fig3.update_layout(barmode="stack", title="Evolución: Mundiales 2018, 2022 y 2026",
                               xaxis=dict(type="category", title="Mundial"),
                               yaxis=dict(title="Nº de jugadores"),
                               yaxis2=dict(title="% en 5 grandes ligas", overlaying="y", side="right",
                                           range=[0, 100], dtick=20, ticksuffix=" %", showgrid=False),
                               legend=dict(orientation="h", y=1.1), height=450)
            st.plotly_chart(fig3, width="stretch")

            # Conclusiones generadas a partir de los datos
            top = pl_[ligas5].sort_values(ascending=False)
            sin5 = ps[ps["% 5 grandes"] == 0].index.tolist()
            todo5 = ps[ps["% 5 grandes"] >= 90].index.tolist()
            st.subheader("Conclusiones")
            st.markdown(
                f"- **{r['n5']} de {r['n_total']}** jugadores ({r['pct5']:.1f} %) juegan en las 5 grandes ligas, "
                f"frente al {ev.loc[2018, 'pct_5_grandes']:.1f} % de 2018 y el {ev.loc[2022, 'pct_5_grandes']:.1f} % de 2022.\n"
                f"- La liga más representada es la **{top.index[0]}** ({top.iloc[0]} jugadores), seguida de "
                f"{top.index[1]} ({top.iloc[1]}) y {top.index[2]} ({top.iloc[2]}).\n"
                f"- Selecciones con ≥90 % de la convocatoria en las 5 grandes ligas: {', '.join(todo5) or 'ninguna'}. "
                f"Sin ningún jugador en ellas: {', '.join(sin5) or 'ninguna'}.\n"
                f"- Al pasar de 32 a 48 selecciones entran equipos con ligas menos potentes, por lo que el peso "
                f"relativo de las 5 grandes ligas {'baja' if r['pct5'] < ev.loc[2022, 'pct_5_grandes'] else 'no baja'} "
                f"({r['pct5'] - ev.loc[2022, 'pct_5_grandes']:+.1f} puntos respecto a 2022), aunque en número absoluto "
                f"{'aumenta' if r['n5'] > ev.loc[2022, 'jugadores_5_grandes'] else 'no aumenta'} "
                f"({r['n5'] - ev.loc[2022, 'jugadores_5_grandes']:+d} jugadores)."
            )
            with st.expander("Tabla por selección"):
                st.dataframe(ps.round(1), width="stretch")

    # ---------------------- Ej. 7: mapa de estadios ----------------------
    with tab_map:
        if not F_ESTADIOS_COORD.exists():
            st.warning(f"No existe {F_ESTADIOS_COORD.name}. Ejecute primero:  `python bloque4_WC26.py estadios`")
            return
        partidos = st.cache_data(cargar_partidos)(F_PARTIDOS)
        coords = pd.read_excel(F_ESTADIOS_COORD).replace(NO_DISPONIBLE, np.nan)
        coords[["latitud", "longitud"]] = coords[["latitud", "longitud"]].apply(pd.to_numeric, errors="coerce")
        coords = coords.dropna(subset=["latitud", "longitud"])

        presentes = [r for r in RONDAS if r in set(partidos["ronda"])]
        opciones = ["Todas las rondas"] + [RONDAS[r] for r in presentes]
        eleccion = st.selectbox("Ronda", opciones)
        rondas = None if eleccion == "Todas las rondas" else [r for r in presentes if RONDAS[r] == eleccion]
        datos = resumen_estadios(partidos, coords, rondas)

        if datos.empty:
            st.info("No hay partidos para esta ronda.")
            return
        m1, m2, m3 = st.columns(3)
        m1.metric("Partidos", int(datos["partidos"].sum()))
        m2.metric("Goles", int(datos["goles"].sum()))
        m3.metric("Goles por partido", f"{datos['goles'].sum() / datos['partidos'].sum():.2f}")

        datos["nombre"] = datos["estadio"].map(lambda s: separar_nombre_estadio(s)[1])
        fig = px.scatter_geo(
            datos, lat="latitud", lon="longitud", size="partidos", color="goles",
            hover_name="nombre",
            hover_data={"ciudad_partido": True, "partidos": True, "goles": True, "goles_por_partido": True,
                        "latitud": ":.3f", "longitud": ":.3f"},
            labels={"ciudad_partido": "Ciudad", "partidos": "Partidos", "goles": "Goles",
                    "goles_por_partido": "Goles/partido"},
            color_continuous_scale="YlOrRd", size_max=40, scope="north america",
            title=f"Estadios del Mundial 2026 · {eleccion} (tamaño = partidos, color = goles)",
        )
        fig.update_traces(marker=dict(line=dict(width=1, color="#1f2937"), opacity=0.85))
        fig.update_geos(showcountries=True, countrycolor="#9ca3af", showsubunits=True, subunitcolor="#d1d5db",
                        showland=True, landcolor="#f3f4f6", lataxis_range=[14, 55], lonaxis_range=[-130, -60])
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(datos[["nombre", "ciudad_partido", "pais_partido", "partidos", "goles", "goles_por_partido"]]
                     .sort_values("partidos", ascending=False).rename(columns={
                         "nombre": "Estadio", "ciudad_partido": "Ciudad", "pais_partido": "País",
                         "partidos": "Partidos", "goles": "Goles", "goles_por_partido": "Goles/partido"}),
                     hide_index=True, width="stretch")


# =============================================================================
# 7. LÍNEA DE COMANDOS
# =============================================================================

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Bloque 4 · Mundial 2026: extracción vía API")
    sub = parser.add_subparsers(dest="modo", required=True)

    pj = sub.add_parser("jugadores", help="Fecha de nacimiento, altura y peso desde API-Football")
    pj.add_argument("--entrada", type=Path, default=F_JUGADORES)
    pj.add_argument("--salida", type=Path, default=F_JUGADORES_API)
    pj.add_argument("--api-key", default=os.getenv("APIFOOTBALL_KEY"),
                    help="Clave de API-Football (por defecto, variable de entorno APIFOOTBALL_KEY)")
    pj.add_argument("--temporadas", type=int, nargs="+", default=list(AF_TEMPORADAS),
                    help="Temporadas a consultar por selección (plan gratuito: 2022-2024)")
    pj.add_argument("--max-llamadas", type=int, default=AF_MAX_LLAMADAS)
    pj.add_argument("--sin-busqueda-individual", action="store_true",
                    help="No usar /players/profiles para los jugadores no encontrados")

    pl = sub.add_parser("ligas", help="Ejercicio 4: jugadores del Mundial en las 5 grandes ligas (football-data.org)")
    pl.add_argument("--entrada", type=Path, default=F_JUGADORES)
    pl.add_argument("--token", default=os.getenv("FOOTBALLDATA_TOKEN"),
                    help="Token de football-data.org (por defecto, variable de entorno FOOTBALLDATA_TOKEN)")
    pl.add_argument("--temporada", type=int, default=FD_TEMPORADA,
                    help="Temporada de los clubes (2025 = 2025/26, la del Mundial)")

    pe = sub.add_parser("estadios", help="Latitud y longitud de los estadios desde OpenStreetMap")
    pe.add_argument("--entrada", type=Path, default=F_ESTADIOS,
                    help="Excel con la columna 'estadio' (si no existe, se crea desde partidosWC26.xlsx)")
    pe.add_argument("--salida", type=Path, default=F_ESTADIOS_COORD)

    args = parser.parse_args(argv)
    if args.modo == "jugadores":
        if not args.api_key:
            parser.error("Falta la clave: use --api-key o la variable de entorno APIFOOTBALL_KEY")
        extraer_datos_jugadores(args.entrada, args.salida, args.api_key,
                                temporadas=tuple(args.temporadas), max_llamadas=args.max_llamadas,
                                busqueda_individual=not args.sin_busqueda_individual)
    elif args.modo == "ligas":
        if not args.token:
            parser.error("Falta el token: use --token o la variable de entorno FOOTBALLDATA_TOKEN")
        extraer_grandes_ligas(args.entrada, args.token, temporada=args.temporada)
    elif args.modo == "estadios":
        if not args.entrada.exists():
            print(f"Creando {args.entrada.name} a partir de {F_PARTIDOS.name}...")
            crear_excel_estadios(F_PARTIDOS, args.entrada)
        extraer_coordenadas_estadios(args.entrada, args.salida)


def _ejecutando_en_streamlit() -> bool:
    try:
        from streamlit.runtime import exists
        return exists()
    except Exception:
        return False


if __name__ == "__main__":
    if _ejecutando_en_streamlit():
        dashboard()
    else:
        main()
