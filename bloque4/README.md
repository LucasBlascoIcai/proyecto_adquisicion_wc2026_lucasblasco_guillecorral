# Bloque 4 · Mundial 2026 — Datos vía API y visualización

Ejercicios del Bloque 4 (enunciado v5) resueltos con **API-Football**, **football-data.org** y
**OpenStreetMap**, con un dashboard en **Streamlit + Plotly**. Todo está en un único script:
`bloque4_WC26.py`.

| Ejercicio | Qué pide | Dónde se resuelve |
|---|---|---|
| 1 | Git colaborativo | Repositorio (ramas por bloque, *merges* en `main`) |
| 2 | Analizar la documentación de las APIs de fútbol | Sección *Decisiones técnicas* de este README |
| 3 | Distribución de la fecha de nacimiento de los jugadores del Mundial | `python bloque4_WC26.py jugadores` + pestaña 1 del dashboard |
| 4 | Jugadores del Mundial en las 5 grandes ligas y comparación con 2018/2022 | `python bloque4_WC26.py ligas` + pestaña 2 del dashboard |
| 5 | Analizar la documentación de la API de OpenStreetMap | Sección *Decisiones técnicas* |
| 6 | Latitud y longitud de los estadios | `python bloque4_WC26.py estadios` |
| 7 | Mapa de Norteamérica con burbujas y selector de ronda | Pestaña 3 del dashboard |

## Estructura

```
bloque4_WC26.py          # script único: extracción (CLI) + dashboard (Streamlit)
datos/
  partidosWC26.xlsx, eventosWC26.xlsx, jugadoresWC26.xlsx   # entrada (Excel de la solución del Bloque 1)
  jugadoresWC26_api.xlsx         # SALIDA ej. 3: + fecha_nacimiento, altura_jugador, peso_jugador (API-Football)
  clubes_grandes_ligas.xlsx      # SALIDA ej. 4: clubes de las 5 grandes ligas (football-data.org)
  jugadores_grandes_ligas.xlsx   # SALIDA ej. 4: plantillas de esas ligas (solo si el plan las incluye)
  jugadoresWC26_ligas.xlsx       # SALIDA ej. 4: + liga de cada jugador del Mundial
  estadiosWC26.xlsx              # entrada ej. 6 (se crea sola desde partidosWC26.xlsx)
  estadiosWC26_coordenadas.xlsx  # SALIDA ej. 6: + latitud, longitud
tests/                   # pruebas con APIs simuladas (no gastan llamadas)
cache/                   # respuestas de las APIs (NO se sube a Git)
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso (Windows, Símbolo del sistema)

```bat
:: Ej. 3 · API-Football. Clave en dashboard.api-football.com > Account > My Access
set APIFOOTBALL_KEY=tu_clave
python bloque4_WC26.py jugadores      :: repetir cada día hasta completar (usa la caché)

:: Ej. 4 · football-data.org. El token llega por correo al registrarse
set FOOTBALLDATA_TOKEN=tu_token
python bloque4_WC26.py ligas          :: 5 llamadas, menos de 1 minuto

:: Ej. 6 · OpenStreetMap (sin clave)
python bloque4_WC26.py estadios

:: Dashboard (ejercicios 3, 4 y 7)
streamlit run bloque4_WC26.py

:: Pruebas con APIs simuladas
python tests\test_bloque4.py
```

En macOS/Linux, `export VARIABLE=valor` en lugar de `set`. Opciones de cada comando: `--help`.

## Decisiones técnicas

### Ej. 2 · API-Football (ejercicio 3: fecha de nacimiento)

Limitaciones del plan gratuito comprobadas al usarla: **100 llamadas/día**, **solo temporadas
2022-2024** (`"Free plans do not have access to this season, try from 2022 to 2024"`) y **como máximo la
página 3** de cada consulta (`"Free plans are limited to a maximum value of 3 for the Page parameter"`).
No se puede descargar directamente la plantilla del Mundial 2026, y consultar jugador a jugador costaría
~1.250 llamadas (13 días). Estrategia:

1. `GET /teams?league=10&season=2024` (amistosos internacionales): **1 llamada** devuelve el id de casi
   todas las selecciones. Las que falten se buscan con `GET /teams?name=...`.
2. `GET /players?team={id}&season=2024`: jugadores utilizados por cada selección en 2024, 20 por página
   (máx. 3 páginas), con fecha de nacimiento, altura y peso. Si faltan jugadores, se repite con 2023.
   La fecha de nacimiento no depende de la temporada.
3. Los que sigan sin encontrarse: `GET /players/profiles?search=apellido` (1 llamada por jugador; la API
   exige al menos 4 letras).

- **Caché en disco** (`cache/`): repetir la ejecución no gasta llamadas; si se agota la cuota, al día
  siguiente se continúa donde se quedó.
- **Control de cuota**: cabecera `x-ratelimit-requests-remaining` y errores `requests`, `rateLimit` y
  `plan` del campo `errors`.
- **Emparejamiento de nombres**: los nombres del Excel ("Ali Reza Beiranvand", "GUIMARAESBruno Bruno")
  no coinciden literalmente con los de la API ("Alireza Safar Beiranvand", "Bruno Guimarães"). Se
  normalizan (sin tildes, separando apellidos pegados en mayúsculas), se comparan palabra a palabra
  tolerando iniciales, segundos nombres, transliteraciones (Saeid/Saeed) y nombres unidos (Ali Reza/Alireza),
  se penaliza que coincida solo el apellido con distinto nombre de pila, se limita la búsqueda a la
  misma selección y cada jugador de la API se asigna a un único jugador.
- Los datos no encontrados se marcan como **"No disponible"**.

### Ej. 2 · football-data.org (ejercicio 4: 5 grandes ligas)

Plan gratuito: **10 llamadas/minuto**, 12 competiciones entre las que están las 5 grandes ligas
(códigos `PL`, `PD`, `BL1`, `SA`, `FL1`). Autenticación con la cabecera `X-Auth-Token`.

1. `GET /v4/competitions/{código}/teams?season=2025`: **1 llamada por liga (5 en total)** devuelve los
   clubes de la temporada 2025/26, la de los clubes de los jugadores en el Mundial 2026. Si el plan no
   permite pedir esa temporada, se usa la actual.
2. Cada jugador del Mundial se asigna a la liga de su club (`club_jugador` del Excel). Regla: todas las
   palabras significativas del club del Excel deben estar en el nombre de la API ("Real Betis" ~ "Real
   Betis Balompié", "RC Lens" ~ "Racing Club de Lens"), pero no al revés ("Charlton Athletic" no es
   "Athletic Club"; "Newcastle United Jets" no es "Newcastle United FC").
3. Si el plan devuelve también las **plantillas**, se guardan los jugadores de las 5 ligas, se comprueba
   por nombre y nacionalidad cuáles disputaron el Mundial y su fecha de nacimiento completa la del
   ejercicio 3.
4. Se compara con los Mundiales anteriores (enunciado): 2018 → 385/736 (52,3 %), 2022 → 417/831 (50,2 %).

### Ej. 5 · OpenStreetMap (ejercicio 6: estadios)

La API v0.6 permite leer elementos por su id, pero **no buscar por nombre**. Por eso:
1. Con una expresión regular se separa el nombre FIFA del comercial:
   `"Mexico City Stadium (Estadio Azteca)"` → `"Estadio Azteca"`.
2. **Nominatim** (buscador oficial de OSM) localiza el elemento (`osm_type`, `osm_id`), dando
   preferencia a resultados etiquetados como estadio y filtrando por país.
3. La **API v0.6** (`/way/{id}/full.json`) devuelve los nodos del contorno del estadio y se calcula su
   centroide. Si falla, se usan las coordenadas de Nominatim.
4. Se respeta la política de uso (1 petición/s y `User-Agent` identificativo) y se valida que el
   punto esté en Norteamérica.

### Dashboard

- **Ej. 3 · Fecha de nacimiento:** nacimientos por mes frente a lo esperado con una distribución
  uniforme (proporcional a los días del mes), porcentaje por trimestre (todos y los que han jugado
  ≥180 min) y test χ² de bondad de ajuste. Combina las fechas de API-Football y football-data.org.
- **Ej. 4 · 5 grandes ligas:** jugadores por liga, reparto de cada selección entre las 5 ligas y el resto
  (barras apiladas al 100 %) y evolución 2018 → 2022 → 2026 (número de jugadores y porcentaje).
- **Ej. 7 · Mapa de estadios:** `scatter_geo` de Norteamérica. Tamaño de la burbuja = partidos jugados,
  color = goles marcados (marcador final, sin tandas de penaltis). Selector de ronda.

Las conclusiones de los ejercicios 3 y 4 se generan a partir de los datos y aparecen bajo cada gráfico.

## Resultados y conclusiones

### Ej. 3 · Fecha de nacimiento

Fecha de nacimiento obtenida para **1.005 de los 1.248 jugadores (80,5 %)**: 946 con API-Football y 59
con football-data.org. Validación cruzada: de los 335 jugadores con fecha en ambas APIs, coinciden 330
(98,5 %).

| Trimestre de nacimiento | Jugadores | % observado | % esperado (nacimientos uniformes) |
|---|---|---|---|
| Enero – marzo | 284 | **28,3 %** | 24,7 % |
| Abril – junio | 273 | 27,2 % | 24,9 % |
| Julio – septiembre | 247 | 24,6 % | 25,2 % |
| Octubre – diciembre | 201 | **20,0 %** | 25,2 % |

- Los nacidos en el **primer trimestre** están sobrerrepresentados (+3,6 puntos) y los del **último**,
  infrarrepresentados (−5,2 puntos). Hay un 41 % más de jugadores nacidos en enero-marzo que en
  octubre-diciembre.
- El test χ² de bondad de ajuste lo confirma: **p = 0,0004** por trimestres (p = 0,005 por meses), así
  que la diferencia no se explica por azar.
- Es el **efecto de la edad relativa**: en las categorías inferiores, con fecha de corte el 1 de enero,
  los nacidos a principio de año son casi un año mayores y más desarrollados que sus compañeros, reciben
  más oportunidades y llegan con más frecuencia a la élite.
- Entre los jugadores que más jugaron en el Mundial (≥180 minutos) la tendencia es la misma (27,5 % frente
  a 21,0 %), pero con menos jugadores no es significativa (p = 0,12): el efecto influye en **llegar** a la
  élite más que en el rendimiento una vez allí.

### Ej. 4 · Las 5 grandes ligas

| Liga | Jugadores del Mundial 2026 | % |
|---|---|---|
| Premier League | 163 | 13,1 % |
| Bundesliga | 101 | 8,1 % |
| LaLiga | 80 | 6,4 % |
| Ligue 1 | 77 | 6,2 % |
| Serie A | 66 | 5,3 % |
| **Total 5 grandes ligas** | **487** | **39,0 %** |
| Otras ligas | 761 | 61,0 % |

| Mundial | Selecciones | Jugadores | En 5 grandes ligas | % |
|---|---|---|---|---|
| 2018 | 32 | 736 | 385 | 52,3 % |
| 2022 | 32 | 831 | 417 | 50,2 % |
| 2026 | 48 | 1.248 | 487 | **39,0 %** |

- La **Premier League** es, con diferencia, la liga más representada: aporta más jugadores (163) que
  LaLiga y la Serie A juntas (146).
- Reparto por selección muy desigual: **España (100 %), Inglaterra (96 %), Alemania (96 %) y Francia
  (92 %)** tienen casi toda la convocatoria en las 5 grandes ligas, mientras que **Curaçao, Panamá, Irak,
  Irán y Catar** no tienen ningún jugador en ellas.
- **Impacto de la ampliación a 48 selecciones:** en número absoluto hay más jugadores de las 5 grandes
  ligas que nunca (+70 respecto a 2022), pero su peso cae **11,2 puntos** (del 50,2 % al 39,0 %). Las
  plazas añadidas fueron sobre todo para selecciones de Asia, África y CONCACAF, cuyos jugadores juegan
  mayoritariamente en sus ligas nacionales: las 5 selecciones sin ningún jugador en las grandes ligas son
  de esas confederaciones.

Nota metodológica: la liga de cada jugador se asigna por su club en la temporada 2025/26 (la del
Mundial), con la lista de clubes de cada liga que devuelve football-data.org.

## Seguridad

La clave de API-Football y el token de football-data.org **nunca se suben al repositorio**: se pasan
por variable de entorno, y `cache/` y `.env` están en `.gitignore`.
