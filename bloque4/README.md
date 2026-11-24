# Bloque 4 · Mundial 2026 — Datos vía API y visualización

Extracción de datos de **API-Football** (fecha de nacimiento, altura y peso de los jugadores) y de
**OpenStreetMap** (coordenadas de los estadios), con un dashboard en **Streamlit + Plotly**.

## Estructura

```
bloque4_WC26.py          # script único: extracción (CLI) + dashboard (Streamlit)
datos/
  partidosWC26.xlsx      # Bloque 1 (entrada)
  eventosWC26.xlsx       # Bloque 1
  jugadoresWC26.xlsx     # Bloque 1 (entrada)
  jugadoresWC26_api.xlsx         # SALIDA: + fecha_nacimiento, altura_jugador, peso_jugador
  estadiosWC26.xlsx              # entrada para OSM (se crea sola desde partidosWC26.xlsx)
  estadiosWC26_coordenadas.xlsx  # SALIDA: + latitud, longitud
tests/test_bloque4.py    # pruebas con APIs simuladas (no gasta llamadas)
cache/                   # respuestas de las APIs (NO se sube a Git)
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# 1) Jugadores (API-Football). La clave está en dashboard.api-football.com > Account > My Access
export APIFOOTBALL_KEY="tu_clave"          # Windows (PowerShell): $env:APIFOOTBALL_KEY="tu_clave"
python bloque4_WC26.py jugadores    # repetir cada día hasta completar (usa la caché)

# 2) Estadios (OpenStreetMap, sin clave)
python bloque4_WC26.py estadios

# 3) Dashboard
streamlit run bloque4_WC26.py

# Pruebas (APIs simuladas)
python tests/test_bloque4.py
```

Opciones útiles: `--temporadas`, `--max-llamadas`, `--entrada`, `--salida` (ver `--help`).

## Decisiones técnicas

**API-Football: plan gratuito (100 llamadas/día y solo temporadas 2022-2024).** La API no permite
consultar la temporada 2026 con el plan gratuito (`"Free plans do not have access to this season, try
from 2022 to 2024"`), así que no se puede descargar directamente la plantilla del Mundial. Además,
consultar jugador a jugador costaría ~1.250 llamadas (13 días). Solución:

1. `GET /teams?league=10&season=2024` (amistosos internacionales): **1 llamada** devuelve el id de casi
   todas las selecciones. Las que falten se buscan con `GET /teams?name=...`.
2. `GET /players?team={id}&season=2024`: jugadores que utilizó cada selección en 2024, 20 por llamada,
   con fecha de nacimiento, altura y peso (unas 2-3 llamadas por selección). Si faltan jugadores, se
   repite con la temporada 2023. La fecha de nacimiento, la altura y el peso no dependen de la temporada.
3. Los que sigan sin encontrarse: `GET /players/profiles?search=apellido` (1 llamada por jugador; la API
   exige al menos 4 letras).

El proceso completo necesita unas 3 ejecuciones (una por día).

- **Caché en disco:** cada respuesta válida se guarda en `cache/`. Repetir la ejecución no gasta llamadas.
  Si se agota la cuota, al día siguiente se continúa donde se quedó.
- **Control de cuota:** se lee la cabecera `x-ratelimit-requests-remaining` y se gestionan los errores
  `requests`, `rateLimit` y `plan` que devuelve la API en el campo `errors`.
- **Emparejamiento de nombres:** los nombres de nuestro Excel ("Julián Andrés Quinones") no coinciden
  literalmente con los de la API ("J. Quiñones" / "Julián Andrés Quiñones Quiñones"). Se normalizan
  (sin tildes, minúsculas), se comparan por tokens (tolerando iniciales, segundos nombres y apellidos),
  se restringe la búsqueda a la misma selección (con alias: Türkiye→Turkey, Côte d'Ivoire→Ivory Coast…)
  y cada jugador de la API se asigna como mucho a uno de los nuestros.
- Los datos no encontrados se marcan como **"No disponible"**.

**OpenStreetMap.** La API v0.6 permite leer elementos por su id, pero **no buscar por nombre**. Por eso:
1. Con una expresión regular se separa el nombre FIFA del comercial:
   `"Mexico City Stadium (Estadio Azteca)"` → `"Estadio Azteca"`.
2. **Nominatim** (buscador oficial de OSM) localiza el elemento (`osm_type`, `osm_id`), dando
   preferencia a resultados etiquetados como estadio y filtrando por país.
3. La **API v0.6** (`/way/{id}/full.json`) devuelve los nodos del contorno del estadio y se calcula su
   centroide. Si falla, se usan las coordenadas de Nominatim.
4. Se respeta la política de uso (1 petición/s y `User-Agent` identificativo) y se valida que el
   punto esté en Norteamérica.

**Dashboard.**
- *Fecha de nacimiento:* nacimientos por mes frente a lo esperado con una distribución uniforme
  (proporcional a los días del mes), porcentaje por trimestre (todos y los que han jugado ≥180 min) y
  test χ² de bondad de ajuste. La conclusión se genera a partir de los datos.
- *Mapa de estadios:* `scatter_geo` de Norteamérica. Tamaño de la burbuja = partidos jugados,
  color = goles marcados (marcador final, sin tandas de penaltis). Selector de ronda.

## Flujo de trabajo en Git

- `main`: solo código integrado y que funciona.
- `develop`: rama de integración.
- Una rama por tarea: `feature/bloque1-limpieza`, `feature/bloque2-analisis`, `feature/bloque3-powerbi`,
  `feature/bloque4-api-football`, `feature/bloque4-osm`, `feature/bloque4-dashboard`.
- Cada integrante trabaja en su rama y abre un *pull request* a `develop`; otro miembro lo revisa
  antes del *merge*. Al cerrar cada bloque, `develop` → `main` con una etiqueta (`v1.0-bloque1`…).
- Commits pequeños y descriptivos (`feat: paginación de /players con caché`,
  `fix: penalizar coincidencias solo por apellido`).
- **La API key nunca se sube**: se pasa por variable de entorno y `.env` está en `.gitignore`.
