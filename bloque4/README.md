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
python bloque4_WC26.py jugadores

# 2) Estadios (OpenStreetMap, sin clave)
python bloque4_WC26.py estadios

# 3) Dashboard
streamlit run bloque4_WC26.py

# Pruebas (APIs simuladas)
python tests/test_bloque4.py
```

Opciones útiles: `--temporada`, `--liga`, `--max-llamadas`, `--entrada`, `--salida` (ver `--help`).

## Decisiones técnicas

**API-Football: límite de 100 llamadas/día.** En lugar de consultar jugador a jugador (~1.250 llamadas),
se usa `GET /players?league=1&season=2026`, que devuelve 20 jugadores por llamada con fecha de
nacimiento, altura y peso: unas 65 llamadas para todo el Mundial. Los jugadores que no aparezcan se
buscan individualmente con `GET /players/profiles?search=apellido` hasta agotar el presupuesto
(`--max-llamadas`, 95 por defecto).

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
