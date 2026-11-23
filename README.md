# Proyecto Colaborativo · Mundial 2026

**Adquisición y Visualización de Datos** · Grado IMAT · Comillas ICAI · Curso 2026/27
**Grupo 5:** Lucas Blasco y Guille Corral

Análisis del Mundial 2026 a partir de datasets de partidos, eventos y jugadores, complementados con
datos obtenidos vía API (api-football.com y OpenStreetMap).

## Estructura del repositorio

| Carpeta | Bloque | Contenido |
|---|---|---|
| `bloque1/` | Recopilación, limpieza e imputación | `main.py`, los 11 CSV originales y los 3 Excel que genera |
| `bloque2/` | Análisis visual (Plotly) | `mainbloque2.py`, los 3 Excel de partida y la presentación con gráficos y conclusiones |
| `bloque3/` | Cuadro de mando | `power_bi_bloque3.pbix` y los 3 Excel que usa como fuente |
| `bloque4/` | Datos vía API + dashboard | `bloque4_WC26.py`, tests y datos (ver `bloque4/README.md`) |

## Sobre los Excel de partida

- `bloque1/*.xlsx` son los Excel **generados por nuestro script** del Bloque 1.
- Tras la entrega del Bloque 1 se facilitaron los Excel de la solución (`partidosWC26.xlsx`,
  `eventosWC26.xlsx`, `jugadoresWC26.xlsx`). **A partir del Bloque 2 trabajamos sobre esos Excel**,
  para que los análisis partan de datos validados. Por eso los Excel de `bloque2/`, `bloque3/` y
  `bloque4/datos/` no coinciden con los de `bloque1/`.
- Diferencias conocidas de nuestro Bloque 1 respecto a la solución: no incluye los eventos de revisión
  VAR ni de tandas de penaltis, mantiene las posiciones y el valor de mercado en el formato original
  (`GK`, `"8.9 M€"`) y la imputación de la calificación media difiere.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

Cada script se ejecuta **desde su propia carpeta** (lee los ficheros con rutas relativas):

```bash
# Bloque 1: genera partidosWC26.xlsx, eventosWC26.xlsx y jugadoresWC26.xlsx
cd bloque1 && python main.py

# Bloque 2: análisis y gráficos
cd bloque2 && python mainbloque2.py

# Bloque 3: abrir bloque3/power_bi_bloque3.pbix con Power BI Desktop
#   (si se mueve la carpeta: Transformar datos > Configuración de origen de datos > Cambiar origen)

# Bloque 4: extracción vía API y dashboard
cd bloque4
python bloque4_WC26.py jugadores --api-key TU_CLAVE   # o variable de entorno APIFOOTBALL_KEY
python bloque4_WC26.py estadios
streamlit run bloque4_WC26.py
```

## Flujo de trabajo en Git

- **`main`**: versión integrada del proyecto. Solo recibe cambios mediante *merge* de las ramas de trabajo.
- **`bloque1`, `bloque-2`, `bloque-3`, `bloque-4`**: una rama por bloque, cada una con únicamente la
  carpeta de su bloque.
- **`documentacion`**: README, dependencias y configuración del repositorio.
- Cada rama se integra en `main` con un *merge* (`--no-ff`) para conservar el historial de cada bloque.
- La clave de API-Football nunca se sube al repositorio (variable de entorno; `.env` en `.gitignore`).
