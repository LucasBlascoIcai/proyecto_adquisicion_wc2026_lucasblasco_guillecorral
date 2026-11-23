import pandas as pd
import regex as re
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px


eventos = pd.read_excel('eventosWC26.xlsx')
jugadores = pd.read_excel('jugadoresWC26.xlsx')
partidos = pd.read_excel('partidosWC26.xlsx')


# HEMOS CARGADO LOS EXCEL TAL Y COMO LOS ACABAMOS EN EL APARTADO ANTERIOR, E IMPORTADO LAS LIBRERIAS NECESARIAS PARA ESTE BLOQUE. 
# A PARTIR DE AQUI YA VAMOS CON LO NUEVO DE ESTE APARTADO.


#------------------------------------------------------------------------------------------
#Bloque 1 sobre ventanas de partidos, vamos a hacer los tres graficos por separado marcando el inicio y final de cada uno.



#  GRAFICO 1 --------------------------------------------(ej: partido 1) ---------------
partido_id = 75
eventos_partido = eventos[eventos['index_partido'] == partido_id].copy()    # filtramos un dataframe para quedarnos solo con el id pedido
eventos_partido['ocurrencia'] = 1 # para darle un valor numerico y asi poder cuantificar los eventos en las barras, de esta manera si hay mas de un evento se suman los unos y la barra es mas grande

fig1 = px.bar(
    eventos_partido,
    x='minuto_evento',
    y='ocurrencia',
    color='tipo_evento',
    hover_name='nombre_jugador',
    title=f"Eventos en el Partido {partido_id}"
)
fig1.show()
# ------------------------------------------------------------------------ FINAL GRAFICO 1



# GRAFICO 2 ----------------------------------- ---------------------------------------
# 1. Inputs de filtrado (puedes cambiarlos según lo que te pidan o dejarlos en None para ver todo)
# Ejemplos de rondas: 'Round of 16', 'Quarter-finals ', 'Semi-finals', 'Final', 'Group Stage'
ronda_filtro = None             # ej -- 'Round of 16' (o None para todas las rondas)
eventos_filtro = None           # ej -- ['Goal', 'Yellow Card'] (o None para todos los eventos)

# 2. Traemos la columna 'ronda' desde partidos
df_g2 = eventos.merge(partidos[['index_partido', 'ronda']], on='index_partido', how='left')

# 3. Aplicamos los filtros si se han definido
if ronda_filtro is not None:
    df_g2 = df_g2[df_g2['ronda'] == ronda_filtro]

if eventos_filtro is not None:
    df_g2 = df_g2[df_g2['tipo_evento'].isin(eventos_filtro)]

# 4. Tramos de minutos y crosstab
bins = [0, 15, 30, 45, 60, 75, 90, 105, 120]
labels = ['1-15', '16-30', '31-45', '46-60', '61-75', '76-90', '91-105', '106-120']
df_g2['tramo_minuto'] = pd.cut(df_g2['minuto_evento'], bins=bins, labels=labels)

tabla_calor = pd.crosstab(df_g2['tipo_evento'], df_g2['tramo_minuto'])

fig2 = px.imshow(
    tabla_calor,
    text_auto=True,
    title=f"Densidad de Eventos a lo largo del Partido (Ronda: {ronda_filtro if ronda_filtro else 'Todas'})"
)
fig2.show()
# -------------------------------------------------------------------------- FINAL GRAFICO 2




#GRAFICO 3 ------------------------------------------------------------------------
pais = 'Tunisia'

# Obtenemos los partidos que jugó la selección directamente desde eventos
ids_pais = eventos[eventos['seleccion_evento'] == pais]['index_partido'].unique() # filtramos con el pais que nos hemos quedado al igual que el grafico 1

# Filtramos todos los eventos de esos partidos
eventos_pais = eventos[eventos['index_partido'].isin(ids_pais)].copy() # extramos todos los elementos que le han ocurrido a esa seleccion

# Determinamos si cada evento fue 'A favor' o 'En contra'
balance = []
for seleccion in eventos_pais['seleccion_evento']:
    if seleccion == pais:
        balance.append('A favor')
    else:
        balance.append('En contra')

eventos_pais['balance'] = balance
eventos_pais['detalle'] = eventos_pais['tipo_evento'] + " " + eventos_pais['balance'] # lo concatenamos como string para que quede bien, ejemplo: Roja en contra o Amarilla a favor

# Contamos la cantidad de cada tipo de evento
conteo_pais = eventos_pais['detalle'].value_counts().reset_index()
conteo_pais.columns = ['evento', 'cantidad']

# Generamos el gráfico circular
fig3 = px.pie(
    conteo_pais,
    names='evento',
    values='cantidad',
    hole=0.4,
    title=f"Distribución de Eventos a favor y en contra - {pais}"
)
fig3.show()
# ------------------------------------------------------------------------ FINAL GRAFICO 3




#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
# SEGUNDO APARTADO - RENDIMIENTO DE JUGADORES CLAVE- 3 GRAFICOS

#GRAFICO 4
# 1. Selectores de filtrado (puedes indicar un valor específico o None para no filtrar)
seleccion_filtro = None       # Ej: 'Spain', 'Argentina', 'France' (o None para todas)
posicion_filtro = None        # Ej: 'Delantero', 'Centrocampista', 'Defensa', 'Portero' (o None)
partidos_filtro = None        # Ej: 3, 5 (número exacto) o dejar en None

jugadores_filtrados = jugadores[jugadores['minutos_jugados'] >= 180].copy()  # tal y como pide el enunciado, nos quedamos con los jugadores de mas de 90 minutos

# 3. Aplicación de los selectores si están definidos
if seleccion_filtro is not None:
    jugadores_filtrados = jugadores_filtrados[jugadores_filtrados['seleccion_nacional'] == seleccion_filtro]

if posicion_filtro is not None:
    jugadores_filtrados = jugadores_filtrados[jugadores_filtrados['posicion'] == posicion_filtro]

if partidos_filtro is not None:
    jugadores_filtrados = jugadores_filtrados[jugadores_filtrados['partidos_jugados'] == partidos_filtro]

fig4 = px.scatter(
    jugadores_filtrados,
    x='valor_mercado',
    y='calificacion_media',
    color='posicion',
    hover_name='nombre_jugador',
    hover_data=['seleccion_nacional', 'partidos_jugados'],
    title="Valor de Mercado vs Calificación Media (Mínimo 180 min)"
)
fig4.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 4.


jugadores = jugadores.sort_values(by='valor_mercado', ascending=False)
jugadores['ranking_mercado'] = range(1, len(jugadores) + 1)

# Filtramos a los que tienen minutos jugados
jugadores_con_minutos = jugadores[jugadores['minutos_jugados'] > 90].copy() # esto lo he hecho por mi idea, ya que sino filtraba con jugadores que hubiesen jugado
#minimo 90 minutos, obtenia resultados rarisimos, por ejemplo si un jugador habia jugado un minuto y habia metido, su barra se disparaba, pero no me parecia una vision real
mins = jugadores_con_minutos['minutos_jugados']

jugadores_con_minutos['goles/minuto'] = jugadores_con_minutos['goles'] / mins
jugadores_con_minutos['asistencias/minuto'] = jugadores_con_minutos['asistencias'] / mins
jugadores_con_minutos['goles+asistencias/minuto'] = (jugadores_con_minutos['goles'] + jugadores_con_minutos['asistencias']) / mins
jugadores_con_minutos['goles_concedidos/minuto'] = jugadores_con_minutos['goles_concedidos'] / mins
jugadores_con_minutos['tarjetas_amarillas/minuto'] = jugadores_con_minutos['tarjetas_amarillas'] / mins
jugadores_con_minutos['tarjetas_rojas/minuto'] = jugadores_con_minutos['tarjetas_rojas'] / mins

# Métrica agregada
jugadores_con_minutos['metrica_agregada'] = (
    jugadores_con_minutos['goles'] * 3 +
    jugadores_con_minutos['asistencias'] * 2 -
    jugadores_con_minutos['tarjetas_amarillas'] * 0.5 -
    jugadores_con_minutos['tarjetas_rojas'] * 2
) / mins

# Top 15 ordenado por métrica agregada
top15 = jugadores_con_minutos.sort_values(by='metrica_agregada', ascending=False).head(15)

fig5 = px.bar(
    top15.sort_values(by='metrica_agregada', ascending=True),
    x='metrica_agregada',
    y='nombre_jugador',
    orientation='h',
    hover_data=['ranking_mercado'],
    title="Top 15 Jugadores según metrica agregada"
)
fig5.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 5.


#GRAFICO 6
seleccion_g6 = None       # Ej: 'Spain', 'Argentina', 'France' (o None para todas)
posicion_g6 = None        # Ej: 'Delantero', 'Centrocampista', 'Defensa', 'Portero' (o None)

# 2. Copia de trabajo y creación de la columna 'ha_marcado'
df_g6 = jugadores.copy()
df_g6['ha_marcado'] = df_g6['goles'].apply(lambda x: 'Sí' if x > 0 else 'No')


# 3. Aplicamos los filtros si están definidos
if seleccion_g6 is not None:
    df_g6 = df_g6[df_g6['seleccion_nacional'] == seleccion_g6]

if posicion_g6 is not None:
    df_g6 = df_g6[df_g6['posicion'] == posicion_g6]

fig6 = px.scatter(
    df_g6,
    x='minutos_jugados',
    y='calificacion_media',
    size='valor_mercado',
    color='ha_marcado',
    hover_name='nombre_jugador',
    hover_data=['seleccion_nacional', 'posicion', 'valor_mercado', 'goles'],
    title="Minutos Jugados vs Calificación Media (Tamaño = Valor Mercado)"
)
fig6.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 6.




#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
# TERCER APARTADO - IMPACTO ARBITRAL- 2 GRAFICOS

#GRAFICO 7
columnas_partido = ['fecha_partido', 'ronda', 'seleccion_local', 'seleccion_visitante']
partidos_unicos = partidos.drop_duplicates(subset=columnas_partido).copy() # quitamos los partidos repetidos por si acaso


tarjetas = eventos[eventos['tipo_evento'].isin(['Yellow Card', 'Red Card'])] # filtramos solo los eventos de tarjeta
tarjetas_partido = tarjetas.groupby('index_partido').size().reset_index(name='total_tarjetas') # agrupamos por index , y creamos un nuevo df con el conteo de umero de tarjetas

df_tarjetas = partidos_unicos.merge(tarjetas_partido, on='index_partido', how='left') # mezclamos los dfs que acabamos de crear para darle el conteo de tarjetas al df global
df_tarjetas['total_tarjetas'] = df_tarjetas['total_tarjetas'].fillna(0) # si no hay nada es que hubo cero tarjetas

df_tarjetas['partido'] = df_tarjetas['seleccion_local'] + ' vs ' + df_tarjetas['seleccion_visitante']

fig7 = px.box(
    df_tarjetas,
    x='ronda',
    y='total_tarjetas',
    points="all",
    hover_name = 'partido',
    labels={'ronda': 'Ronda del Torneo', 'total_tarjetas': 'Número de Tarjetas'},
    title="Distribución de Tarjetas por Partido según Ronda"
)
fig7.show()
# ------------------------------------------------------------------------ FINAL GRAFICO 7




#GRAFICO 8
# Filtros solicitados (deja en None para ver todos)
ronda = None        # ej: 'Round of 16', 'Group Stage'
seleccion = None    # ej: 'Spain', 'Argentina', 'Mexico'

# Tarjeta amarilla = 1, Roja = 3, Gol = 0.2
puntos_evento = {'Yellow Card': 1.0, 'Red Card': 3.0, 'Goal': 0.2, 'VAR review': 1.0}
eventos['puntos'] = eventos['tipo_evento'].map(puntos_evento).fillna(0.0) # si no hubo ningun de esos eventos le asignamos un 0

indice_partido = eventos.groupby('index_partido')['puntos'].sum().reset_index(name='indice_partido') # agrupamos segun id y suma la columna de puntos asignada previamente
df_arbitros = partidos.merge(indice_partido, on='index_partido', how='left') # une la tabla de partidos original con la recien creada
df_arbitros['indice_partido'] = df_arbitros['indice_partido'].fillna(0.0) # rellenamos los ausentes con 0 puntos

if ronda is not None:
    df_arbitros = df_arbitros[df_arbitros['ronda'] == ronda]

if seleccion is not None:
    df_arbitros = df_arbitros[(df_arbitros['seleccion_local'] == seleccion) | (df_arbitros['seleccion_visitante'] == seleccion)]



df_puntos = df_arbitros[['arbitro_partido', 'indice_partido']].copy() # nos quedamos con las columnas de interes
df_puntos['tipo'] = 'Partido' # estetico
df_puntos.rename(columns={'indice_partido': 'valor'}, inplace=True)# estetico

media_arbitro = df_arbitros.groupby('arbitro_partido')['indice_partido'].mean().reset_index() # creamos un nuevo df cagrupando por arbitro y calculando su media de puntos
media_arbitro['tipo'] = 'Media'
media_arbitro.rename(columns={'indice_partido': 'valor'}, inplace=True)

df_grafico8 = pd.concat([df_puntos, media_arbitro], ignore_index=True) # concatenamos verticalmente las filas de df_puntos y media_arbitro

fig8 = px.scatter(
    df_grafico8,
    x='valor',
    y='arbitro_partido',
    color='tipo',
    title="Índice de Intervención Arbitral por Partido y Media",
    labels={'arbitro_partido': 'Árbitro', 'valor': 'Índice de Intervención'}
)
fig8.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 8.



