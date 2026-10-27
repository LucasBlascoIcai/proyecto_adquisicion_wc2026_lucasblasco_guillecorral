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

# Limpiar valor de mercado para que sea numérico
jugadores['valor_mercado_num'] = (jugadores['valor_mercado'].str.replace(' M€', '', regex=False).astype(float))

#------------------------------------------------------------------------------------------
#Bloque 1 sobre ventanas de partidos, vamos a hacer los tres graficos por separado marcando el inicio y final de cada uno.



#  GRAFICO 1 --------------------------------------------(ej: partido 1) ---------------
partido_id = 1
eventos_partido = eventos[eventos['index_partido'] == partido_id].copy()
eventos_partido['ocurrencia'] = 1

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
bins = [0, 15, 30, 45, 60, 75, 90, 105, 120] # He seleccionado estas franjas de minutos, cada 15 mins habra un bin - barra
labels = ['1-15', '16-30', '31-45', '46-60', '61-75', '76-90', '91-105', '106-120']
eventos['tramo_minuto'] = pd.cut(eventos['minuto_evento'], bins=bins, labels=labels)

tabla_calor = pd.crosstab(eventos['tipo_evento'], eventos['tramo_minuto'])

fig2 = px.imshow(
    tabla_calor,
    text_auto=True,
    title="Densidad de Eventos a lo largo del Partido"
)
fig2.show()
#-------------------------------------------------------------------------- FINAL GRAFICO 2




#GRAFICO 3 ------------------------------------------------------------------------
pais = 'Spain'

# Obtenemos los partidos que jugó la selección directamente desde eventos
ids_pais = eventos[eventos['seleccion_evento'] == pais]['index_partido'].unique()

# Filtramos todos los eventos de esos partidos
eventos_pais = eventos[eventos['index_partido'].isin(ids_pais)].copy()

# Determinamos si cada evento fue 'A favor' o 'En contra'
balance = []
for seleccion in eventos_pais['seleccion_evento']:
    if seleccion == pais:
        balance.append('A favor')
    else:
        balance.append('En contra')

eventos_pais['balance'] = balance
eventos_pais['detalle'] = eventos_pais['tipo_evento'] + " " + eventos_pais['balance']

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
jugadores_180 = jugadores[jugadores['minutos_jugados'] >= 180]

fig4 = px.scatter(
    jugadores_180,
    x='valor_mercado_num',
    y='calificacion_media',
    color='posicion',
    hover_name='nombre_jugador',
    title="Valor de Mercado vs Calificación Media (Mínimo 180 min)"
)
fig4.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 4.
jugadores = jugadores.sort_values(by='valor_mercado_num', ascending=False)
jugadores['ranking_mercado'] = range(1, len(jugadores) + 1)

# Filtramos a los que tienen minutos jugados
jugadores_con_minutos = jugadores[jugadores['minutos_jugados'] > 90].copy()
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
    title="Top 15 Jugadores según Métrica Agregada"
)
fig5.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 5.


#GRAFICO 6
jugadores['ha_marcado'] = jugadores['goles'].apply(lambda x: 'Sí' if x > 0 else 'No')

fig6 = px.scatter(
    jugadores,
    x='minutos_jugados',
    y='calificacion_media',
    size='valor_mercado_num',
    color='ha_marcado',
    hover_name='nombre_jugador',
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
partidos_unicos = partidos.drop_duplicates(subset=columnas_partido).copy()

partidos_unicos['index_partido'] = range(1, len(partidos_unicos) + 1)

tarjetas = eventos[eventos['tipo_evento'].isin(['Yellow Card', 'Red Card'])]
tarjetas_partido = tarjetas.groupby('index_partido').size().reset_index(name='total_tarjetas')

df_tarjetas = partidos_unicos.merge(tarjetas_partido, on='index_partido', how='left')
df_tarjetas['total_tarjetas'] = df_tarjetas['total_tarjetas'].fillna(0)

fig7 = px.box(
    df_tarjetas,
    x='ronda',
    y='total_tarjetas',
    points="all",
    hover_data=['seleccion_local', 'seleccion_visitante'],
    labels={'ronda': 'Ronda del Torneo', 'total_tarjetas': 'Número de Tarjetas'},
    title="Distribución de Tarjetas por Partido según Ronda"
)
fig7.show()
# ------------------------------------------------------------------------ FINAL GRAFICO 7




#GRAFICO 8
# Tarjeta amarilla = 1, Roja = 3, Gol = 0.2
puntos_evento = {'Yellow Card': 1.0, 'Red Card': 3.0, 'Goal': 0.2}
eventos['puntos'] = eventos['tipo_evento'].map(puntos_evento).fillna(0.0)

indice_partido = eventos.groupby('index_partido')['puntos'].sum().reset_index(name='indice_partido')
df_arbitros = partidos.merge(indice_partido, on='index_partido', how='left')
df_arbitros['indice_partido'] = df_arbitros['indice_partido'].fillna(0.0)

df_puntos = df_arbitros[['arbitro_partido', 'indice_partido']].copy()
df_puntos['tipo'] = 'Partido'
df_puntos.rename(columns={'indice_partido': 'valor'}, inplace=True)

media_arbitro = df_arbitros.groupby('arbitro_partido')['indice_partido'].mean().reset_index()
media_arbitro['tipo'] = 'Media'
media_arbitro.rename(columns={'indice_partido': 'valor'}, inplace=True)

df_grafico8 = pd.concat([df_puntos, media_arbitro], ignore_index=True)

fig8 = px.scatter(
    df_grafico8,
    x='arbitro_partido',
    y='valor',
    color='tipo',
    title="Índice de Intervención Arbitral por Partido y Media",
    labels={'arbitro_partido': 'Árbitro', 'valor': 'Índice de Intervención'}
)
fig8.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 8.



