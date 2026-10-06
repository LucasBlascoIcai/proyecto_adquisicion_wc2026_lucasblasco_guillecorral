import pandas as pd


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

