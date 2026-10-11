import pandas as pd
from sklearn.linear_model import LinearRegression
import regex as re

def mostrar_informacion_inicial(dic_df:dict) -> None:
    for nombre, df in dic_df.items():
        print(f"=== {nombre} ===")
        print(f"Filas y columnas: {df.shape}")
        print(df.head(2))
        print()


def mostrar_columnas_y_dtypes(dic_df:dict) -> None:
    for nombre, df in dic_df.items():
        print(f'Las columnas de {nombre} son : {df.columns} ')
        print()
        print(f'Y los tipos de dato de cada una de esas columnas son: {df.dtypes} ')


def unificar_fecha(fecha):
    fecha = str(fecha).strip().lower()

    # Tenemos que diferenciar entre todos los posibles casos.

    # Diccionario para pasar los meses a número.

    meses = {"june": "06", "junio": "06", "jun": "06", "july": "07", "julio": "07", "jul": "07"}

    # DD/MM/YYYY o DD.MM.YYYY
    match = re.search(r"^(\d{2})[/\.](\d{2})[/\.](\d{4})$", fecha)  
    if match:
        dia, mes, anio = match.group(1), match.group(2), match.group(3)
        if mes not in ["06", "07"]:
            return f"{mes}/{dia}/{anio}"
        else:
            return f"{dia}/{mes}/{anio}"


    # MM/DD/YYYY
    match = re.search(r"^(\d{2})-(\d{2})-(\d{4})$", fecha)
    if match:
        mes, dia, anio = match.group(1), match.group(2), match.group(3)
        if mes not in ["06", "07"]:
            return f"{mes}/{dia}/{anio}"
        else:
            return f"{dia}/{mes}/{anio}"

    # YYYYMMDD
    match = re.search(r"^(\d{4})(\d{2})(\d{2})$", fecha)
    if match:
        anio, mes, dia = match.group(1), match.group(2), match.group(3)
        return f"{dia}/{mes}/{anio}"

    # YYYY-MM-DDTHH:MM:SSZ
    match =  re.search(r"^(\d{4})-(\d{2})-(\d{2})t", fecha)
    if match:
        anio, mes, dia = match.group(1), match.group(2), match.group(3)
        return f"{dia}/{mes}/{anio}"

    # DD-mes-YY
    match = re.search(r"^(\d{1,2})-([a-z]+)-(\d{2})$", fecha)
    if match:
        dia, mes_texto, anio_corto = match.group(1), match.group(2), match.group(3)
        mes = meses[mes_texto]
        anio = f"20{anio_corto}"
        return f"{dia.zfill(2)}/{mes}/{anio}"

    # DD de mes de YYYY
    match = re.search(r"^(\d{1,2})\s+(de\s+)?([a-z]+)\s+(de\s+)?(\d{4})$", fecha)
    if match:
        dia, mes_texto, anio = match.group(1), match.group(3), match.group(5)
        mes = meses[mes_texto]
        return f"{dia.zfill(2)}/{mes}/{anio}"

    # Mes DD, YYYY
    match = re.search(r"^([a-z]+)\s+(\d{1,2})(?:,)?\s+(\d{4})$", fecha)
    if match:
        mes_texto, dia, anio = match.group(1), match.group(2), match.group(3)
        mes = meses[mes_texto]
        return f"{dia.zfill(2)}/{mes}/{anio}"

    return fecha


def imputar_calificacion_por_regresion(df):
    df_imputed = df.copy()

    # Identificar porteros y jugadores de campo
    es_portero = df_imputed["posicion"].isin(["GK"])
    es_campo = ~es_portero
    # --------------------------------------------
    # 1. Porteros
    vars_gk = ["paradas", "goles_concedidos", "tarjetas_amarillas", "tarjetas_rojas"]

    # Datos completos para entrenar
    train_gk = df_imputed[es_portero].dropna(subset=["calificacion_media"])

    # Entrenar modelo de porteros
    model_gk = LinearRegression().fit(
        train_gk[vars_gk], train_gk["calificacion_media"]
    )

    # Máscara de porteros con calificación faltante
    mask_gk = es_portero & df_imputed["calificacion_media"].isna()

    # Predecir e imputar
    if mask_gk.sum() > 0:
        df_imputed.loc[mask_gk, "calificacion_media"] = model_gk.predict(
            df_imputed.loc[mask_gk, vars_gk]
        )

    #----------------------------------------------
    
    # 2. Jugadores de campo
    vars_campo = [ "goles", "asistencias", "tiros", "tarjetas_amarillas", "tarjetas_rojas"]

    # Datos completos para entrenar
    train_campo = df_imputed[es_campo].dropna(subset=["calificacion_media"])

    # Entrenar modelo de campo
    model_campo = LinearRegression().fit(
        train_campo[vars_campo], train_campo["calificacion_media"]
    )

    # Máscara de jugadores de campo con calificación faltante
    mask_campo = es_campo & df_imputed["calificacion_media"].isna()

    # Predecir e imputar
    if mask_campo.sum() > 0:
        df_imputed.loc[mask_campo, "calificacion_media"] = model_campo.predict(
            df_imputed.loc[mask_campo, vars_campo]
        )

    df_imputed["calificacion_media"] = df_imputed["calificacion_media"].round(2)

    return df_imputed



def imputar_minutos_por_interpolacion(df):
    partidos_listos = []

    for id_partido in df["index_partido"].unique():
        partido = df[df["index_partido"] == id_partido].copy()

        # Interpola los minutos entre el evento anterior y posterior
        partido["minuto_evento"] = partido["minuto_evento"].interpolate(
            method="linear"
        )

        # Si el primer evento era nulo o el último era nulo, rellena con el vecino más cercano
        partido["minuto_evento"] = partido["minuto_evento"].bfill().ffill()

        partidos_listos.append(partido)

    df_resultado = pd.concat(partidos_listos, ignore_index=True)
    df_resultado["minuto_evento"] = (
        df_resultado["minuto_evento"].round().astype(int)
    )

    return df_resultado