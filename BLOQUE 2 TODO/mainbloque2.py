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



# 1. Gráfico de barras de eventos por minuto en un partido concreto (ej: partido 1) ---------------
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



# 2. Mapa de calor de eventos por tramo de minutos ---------------------------------------
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




# 3. Gráfico circular de eventos a favor y en contra para una Selección (ej: Mexico) -------------
pais = 'Mexico'
partidos_pais = partidos[(partidos['seleccion_local'] == pais) | (partidos['seleccion_visitante'] == pais)]
ids_pais = partidos_pais['index_partido'].unique()

eventos_pais = eventos[eventos['index_partido'].isin(ids_pais)].copy()
eventos_pais['balance'] = eventos_pais['seleccion_evento'].apply(lambda x: 'A favor' if x == pais else 'En contra')
eventos_pais['detalle'] = eventos_pais['tipo_evento'] + " " + eventos_pais['balance']

conteo_pais = eventos_pais['detalle'].value_counts().reset_index()
conteo_pais.columns = ['evento', 'cantidad']

fig3 = px.pie(
    conteo_pais,
    names='evento',
    values='cantidad',
    hole=0.4,
    title=f"Distribución de Eventos a favor y en contra - {pais}"
)
fig3.show()
# --------------------------------------------------------------------------- FINAL GRAFICO 3.




#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------------------------
# SEGUNDO APARTADO - RENDIMIENTO DE JUGADORES CLAVE- 3 GRAFICOS

# 4. Dispersión: Valor de Mercado vs Calificación Media (Mínimo 180 minutos)
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
jugadores_con_minutos = jugadores[jugadores['minutos_jugados'] > 0].copy()
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


# 6. Gráfico de burbujas: Minutos vs Calificación Media
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



