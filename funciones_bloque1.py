import pandas as pd
from sklearn.linear_model import LinearRegression


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