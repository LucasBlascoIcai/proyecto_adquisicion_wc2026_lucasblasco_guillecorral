import pandas as pd
import regex as re
import matplotlib.pyplot as plt
import seaborn as sns

eventos_raw = pd.read_excel('eventosWC26.xlsx')
jugadores_raw = pd.read_excel('jugadoresWC26.xlsx')
partidos_raw = pd.read_excel('partidosWC26.xlsx')


# HEMOS CARGADO LOS EXCEL TAL Y COMO LOS ACABAMOS EN EL APARTADO ANTERIOR, E IMPORTADO LAS LIBRERIAS NECESARIAS PARA ESTE BLOQUE. 
# A PARTIR DE AQUI YA VAMOS CON LO NUEVO DE ESTE APARTADO.
