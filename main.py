import pandas as pd
import funciones_bloque1 as f # Me creare mis funciones en un fichero de funciones para tener un main mas limpio y facil de entender y seguir.

# Cabe recalcar que hemos usado el dtypes, y el value_counts continuamente para comprobar el contenido todo el rato en la terminal y saber por donde seguir.
# Hemos borrado la mayoria de ellos para tener un main mas limpio.


if __name__ == '__main__':
    #PRIMERO VAMOS A IMPORTAR TODOS LOS CSV Y CREAR UN DATAFRAME POR CADA UNO DE ELLOS

    df_2001_fem_stats = pd.read_csv('2001eurocopa_fem_stats.csv', sep = ',')
    df_2026match_lineups = pd.read_csv('2026match_lineups.csv', sep = ';')
    df_2026_match_register = pd.read_csv('2026match_register.csv', sep = ';')
    df_2026_nationalteams = pd.read_csv('2026nationalteams.csv', sep = ',')
    df_2026_player_stats = pd.read_csv('2026player_stats.csv', sep = ';')
    df_2026_squads_and_players = pd.read_csv('2026squads_and_players.csv', sep = ';')
    df_index_referees = pd.read_csv('index_referees.csv', sep = ';')
    df_matches_mundial202 = pd.read_csv('matches_mundial202.csv', sep = ',')
    df_matches_mundial2026 = pd.read_csv('matches_mundial2026.csv', sep = ';')
    df_tournament_stages = pd.read_csv('tournament_stages.csv', sep = ',')
    df_worldcup_venues = pd.read_csv('worldcup_venues.csv', sep = ';')

    

    # Ahora vamos a crearnos una lista y un diccionario con cada uno de ellos para poder explorarlos con bucles y mas fecilmente, evitando la repeticion de codigo
    lista_dataframes = [df_2001_fem_stats, df_2026match_lineups, df_2026_match_register, df_2026_nationalteams, df_2026_player_stats, df_2026_squads_and_players, df_index_referees,  df_matches_mundial202, df_matches_mundial2026, df_tournament_stages, df_worldcup_venues]
    dic_dataframes = {'df_2001_fem_stats': df_2001_fem_stats,
                  'df_2026match_lineups': df_2026match_lineups,
                  'df_2026_match_register': df_2026_match_register, 
                  'df_2026_nationalteams': df_2026_nationalteams, 
                  'df_2026_player_stats': df_2026_player_stats, 
                  'df_2026_squads_and_players': df_2026_squads_and_players, 
                  'df_index_referees': df_index_referees,
                  'df_matches_mundial202': df_matches_mundial202,
                  'df_matches_mundial2026': df_matches_mundial2026,
                  'df_tournament_stages': df_tournament_stages,
                  'df_worldcup_venues': df_worldcup_venues
                  }

    #f.mostrar_informacion_inicial(dic_dataframes) 
    # usamos funcion que muestra : nombre, tamaño, y primeras dos filas de cada df.
    # de esta manera ya nos hacemos un idea del contenido de cada df para poder empezar a hacer merges y limpiezas.

    #f.mostrar_columnas_y_dtypes(dic_dataframes) 
    # esta funcion nos muestra las columnas de cada dataframe para saber que merges hacer


    #---------------------- Partidos -----------------------------

    df_partidos = df_matches_mundial2026.copy() # Iniciamos el df de partidos con el df_matches_mundial_2026 porque tiene ya la mayoria de datos y los necesarios para traer el resto

    # A partir de aqui empezamos a mezclar.
    df_partidos = pd.merge(left = df_partidos, right = df_worldcup_venues, on = 'venue_id', how = 'left') # mezclamos el id del estadios con el df de estadios.

    df_partidos = pd.merge(left = df_partidos, right = df_tournament_stages, on = 'stage_id', how = 'left') # mezclamos el id de las rondas con el df de rondas.

    df_partidos = pd.merge(left = df_partidos, right = df_index_referees, on = 'referee_id', how = 'left') # mezclamos el id de los arbitros con el df de los arbitros.

    df_partidos = pd.merge(left = df_partidos, right = df_2026_nationalteams, left_on = 'home_team_id', right_on = 'team_id', how = 'left') # mezclamos el id de la seleccion home con el df de las selecciones
    # pero automaticamente debemos cambiarle el nombre a esa columan que nos hemos traido porque hemos traido team_name pero queremos que senos quede como seleccion_local
    df_partidos = df_partidos.rename(columns = {'team_name': 'seleccion_local'})

    #repetimos el ultimo paos para traernos las seleciones visitantes

    df_partidos = pd.merge(left = df_partidos, right = df_2026_nationalteams, left_on = 'away_team_id', right_on = 'team_id', how = 'left') # mezclamos el id de la seleccion home con el df de las selecciones
    # pero automaticamente debemos cambiarle el nombre a esa columan que nos hemos traido porque hemos traido team_name pero queremos que senos quede como seleccion_visitante
    df_partidos = df_partidos.rename(columns = {'team_name': 'seleccion_visitante'})


    #print(df_partidos.dtypes)
    #Usamos el dtypes para comproar que ya tenemos TODA LA INFORMACION NECESARIO, Y LOS TIPOS DE CADA COLUMNA, AHORA SOLO FALTA FORMATEAR / LIMPIAR. Y QUEDARNOS CON LA QUE NOS INTERESA SOLO.
    
    cambios_nombre_df_partidos = {'home_score': 'marcador_local', 'away_score': 'marcador_visitante', 'name': 'arbitro_partido',
                                  'city': 'ciudad_partido', 'country_x': 'pais_partido', 'stage_name' : 'ronda', 'stadium_name': 'estadio',
                                   'result_type': 'prorroga' }
    
    df_partidos = df_partidos.rename(columns = cambios_nombre_df_partidos)

    # REVISAAAAR LIMPIEZA DE FECHAS
    df_partidos['fecha_partido'] = pd.to_datetime(df_partidos["date"], errors = "coerce") # pasamos la fecha a formato fecha y le cambiamos el nombre ya de paso
    df_partidos["fecha_partido"] = df_partidos["fecha_partido"].dt.strftime("%d/%B/%y") # ESTA LINEA ME HA AYUDADO LA IA PARA PONER LA FECHA EN EL FORMATO PEIDDO POR EL ENUNCIADO
    

    df_partidos["penalty_local"] = df_partidos["home_penalty_score"].fillna(0) # home_penalty tiene valores NAN para indicar que no hubo penaltis, por ello lo llenamos con 0 como pide el enunciado
    df_partidos["penalty_local"] = df_partidos["penalty_local"].astype(int)# pasamos todos los valores de float a int porque ya hemos asegurado que son todos numeros y es mas facil trabajar con ints

    df_partidos["penalty_visitante"] = df_partidos["away_penalty_score"].fillna(0) # LO MISMO QUE EL ULTIMO PASO
    df_partidos["penalty_visitante"] = df_partidos["penalty_visitante"].astype(int)

    df_partidos["prorroga"] = df_partidos["prorroga"].replace({'AET': "SI", 'Penalties': 'SI', 'Regular': "NO"}) # por ultimo, nos aprovechamos de que prorroga este en booleanos y tan solo debemos cambiar true por si y false por no


    # YA TENEMOS TODA LA INFORMACION, LIMPIA, Y NOMBRADA BIEN, POR ULTIMO, SOLO DEBEMOS QUEDDARNOS CON LAS COLUMANS QUE NOS INTERESAN
    #PORQUE DEBIDO A TANTOS MERGE, HEMOS INCORPORADO MUCHA INFORMACION QUE NOS SOBRA

    columnas_deseadas = ["fecha_partido", "ronda", "estadio", "ciudad_partido", "pais_partido", "seleccion_local", "seleccion_visitante",
    "marcador_local", "marcador_visitante", "prorroga", "penalty_local", "penalty_visitante", "arbitro_partido",]

    partidos = df_partidos[columnas_deseadas].copy()

    partidos["index_partido"] = range(1, len(partidos) + 1)
    partidos = partidos.set_index("index_partido")

    # He relizado un value counts en cada una de las columnas del df final y tenemos dos cambios que corregir rapidamente:
    partidos['penalty_local'] = partidos['penalty_local'].replace({30: 3, 20: 2, 40: 4})
    partidos['penalty_visitante'] = partidos['penalty_visitante'].replace({30: 3, 40: 4})
    partidos['pais_partido'] = partidos['pais_partido'].replace({'usa': 'USA'})

    
    #print(partidos) # UNA VEZ TENEMOS TODA LA INFORMACION, VAMOS A BORRAR DUPLICADOS Y ANALIZAR NULOS

    
    print("Duplicados totales:", partidos.duplicated().sum()) # HEMOS OBTENIDO 100 DUPLICADOS TOTALES, ASI QUE LOS ELIMINAMOS
    partidos = partidos.drop_duplicates()
    print("Duplicados totales despues de limpieza:", partidos.duplicated().sum())

    #Comprobamos si quedo algun valor nulo en alguna de las 13 columnas
    print("Valores nulos por columna:")
    print(partidos.isnull().sum())

    #print(partidos.dtypes)

    '''
    for col in columnas_deseadas:
        print(partidos[col].value_counts())
        print()
    '''
    # HEMOS ACABADO PARTIDOS ----------------------------------------------------------------------------------------------------


    # -----------------------------JUGADORES ------------------------------

    df_jugadores = df_2026_squads_and_players.copy() # al igual que con jugadores, el 2026 squads and players es el df principal con todo lo necesario.

    #mezclamos las estadisticas de los jugadores segun el id de cada jugador
    df_jugadores = pd.merge(left = df_jugadores, right = df_2026_player_stats, on = "player_id", how = "left" )

    #mezclamos para traer el nombre de la seleccion nacional mediante el id de cada seleccion
    df_jugadores = pd.merge(left = df_jugadores, right = df_2026_nationalteams, left_on="team_id_x", right_on = "team_id", how = "left")


    #Renombramos las columnas para que tengan los nombres exactos pedidos
    cambios_nombre_jugadores = {"team_name": "seleccion_nacional", "club_team": "club_jugador", "caps": "partidos_seleccion",
        "position_x": "posicion", "market_value_eur": "valor_mercado", "matches_played": "partidos_jugados", "minutes_played": "minutos_jugados",
        "goals": "goles", "assists": "asistencias", "shots": "tiros", "yellow_cards": "tarjetas_amarillas","red_cards": "tarjetas_rojas",
        "saves": "paradas", "goals_conceded": "goles_concedidos", "average_rating": "calificacion_media", "player_name_x": "nombre_jugador",}
    df_jugadores = df_jugadores.rename(columns=cambios_nombre_jugadores)


    # tenemos que formatear la columnade valor mercado igual que pide el enunciado
    #print(df_jugadores['valor_mercado'].value_counts()) #tenemos 90 jugadores con valor_mercado = nan M %. Tal y como dice el enunciado, debemos imputarlos
    # para ello, vamos a imputar por la media de todos los jugadores de su misma seleccion.
    medias_por_pais = df_jugadores.groupby("seleccion_nacional")["valor_mercado"].mean()
    df_jugadores["valor_mercado"] = df_jugadores["valor_mercado"].fillna(df_jugadores["seleccion_nacional"].map(medias_por_pais))
    df_jugadores["valor_mercado"] = (df_jugadores["valor_mercado"].round(1).astype(str) + " M€")
    #IMPUTACION DE VALOR_MERCADO HECHAAAAAA



    # todas estas columnas se nos piden en formato numerico, por lo tanto rellenamos todos los nan como 0 ya que interpretamos que un nan = 0 goles por ejemplo
    # una vez eliminados todos los nan podemos convertir en int.
    columnas_numericas = ["goles", "asistencias", "tiros", "tarjetas_amarillas", "tarjetas_rojas", "paradas", "goles_concedidos",]
    for col in columnas_numericas:
        df_jugadores[col] = df_jugadores[col].fillna(0)
        df_jugadores[col] = df_jugadores[col].astype(int)




    # UNA VEZ TENEMOS TODA LA INFORMACION QUE NECESITAMOS CON SU NOMBRE CORRECTO, NOS QUEDAMOS SOLO CON LAS PEDIDAS EN EL ENUNCIADO
    columnas_deseadas_jugadores = ["nombre_jugador", "seleccion_nacional", "club_jugador", "partidos_seleccion", "posicion", "valor_mercado",
    "partidos_jugados", "minutos_jugados", "goles", "asistencias", "tiros", "tarjetas_amarillas", "tarjetas_rojas", "paradas",
    "goles_concedidos", "calificacion_media",]

    jugadores = df_jugadores[columnas_deseadas_jugadores].copy()
    jugadores = jugadores.set_index("nombre_jugador") # fijamos con setindex el indice pedido por el enunciado.


    #print(jugadores.dtypes)

    #print("Duplicados totales:", jugadores.duplicated().sum()) # HEMOS OBTENIDO 208 DUPLICADOS TOTALES, ASI QUE LOS ELIMINAMOS
    jugadores = jugadores.drop_duplicates()
    #print("Duplicados totales despues de limpieza:", jugadores.duplicated().sum())



    #Comprobamos si quedo algun valor nulo en alguna de las 15 columnas
    #print("Valores nulos por columna:")
    #print(jugadores.isnull().sum()) # -----podemos ver que hay 320 calificaciones_medias faltantes, como dice el enunciado, las imputaremos mediante regresion.
    # imputar por regresion en este caso si que tiene sentido ya que falta el 20 % mas o menos y obviamente hay una correlacion entre goles y valor.

    jugadores = f.imputar_calificacion_por_regresion(jugadores)

    #print(jugadores.isnull().sum())


    '''
    for col in columnas_deseadas_jugadores:
            if col == 'nombre_jugador':
                pass
            else:
                print(jugadores[col].value_counts())
                print()
    '''
     # aqui hemos podido comprobar que todas las columnas estan correctamente. Incluidas las dos que hemos imputado

     # HEMOS ACABADO JUGADORES ------------------------------------------------------


     # --------------------------------- EVENTOS --------------------------------------
    df_eventos = df_2026_match_register.copy() # este dataframe es CLARAMENTE EL BASE, tiene todo lo pedido en evntos pero con sus ids, asi que 
    #se trata de hacer merges para ir enganchando

    #print(df_eventos['event_type'].value_counts())
    #nos traemos el nombre de jugador mediante player_id y nos traemos nombre seleccion mediante team_id
    df_eventos = pd.merge(left = df_eventos, right = df_2026_nationalteams, on = 'team_id', how = 'left')
    df_eventos = pd.merge(left = df_eventos, right = df_2026_squads_and_players, on = 'player_id', how = 'left')


    # renombramos las columnas tal y como vienen estipuladas en el enunciado
    cambios_nombre_eventos = { "minute": "minuto_evento", "match_id": "index_partido" , "player_name": "nombre_jugador", "event_type": "tipo_evento", "team_name": "seleccion_evento"}
    df_eventos = df_eventos.rename(columns=cambios_nombre_eventos)

    df_eventos = df_eventos.drop_duplicates()

    # Vamos a eliminar todos los minutos que no entren en el rango valido : 1-120 o que no sean nan. 
    # Los que son NAN los dejamos vivos porque como dice el enunciado, los vamos a tener que interpolar mas tarde.
    df_eventos["minuto_evento"] = pd.to_numeric(df_eventos["minuto_evento"], errors="coerce")
    condicion_minuto_valido = (df_eventos["minuto_evento"].isna()) | ((df_eventos["minuto_evento"] >= 1) & (df_eventos["minuto_evento"] <= 130))
    df_eventos = df_eventos[condicion_minuto_valido].copy()

    # nos quedamos SOLO con las columnas que nos interesan
    columnas_deseadas_eventos = [ "minuto_evento", "index_partido", "nombre_jugador", "tipo_evento", "seleccion_evento"]
    eventos = df_eventos[columnas_deseadas_eventos].copy()

    

    # creamos el indice pedido.
    eventos["index_evento"] = range(1, len(eventos) + 1)
    eventos = eventos.set_index("index_evento")











    




















