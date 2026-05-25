import pandas as pd
import glob
import os

ruta = r"F:\Documentos\Activos\Santillan Agustina\NUEVO SISTEMA\.SICOSS\*.csv"

archivos = glob.glob(ruta)

print(f"Se encontraron {len(archivos)} archivos\n")

lista_df = []

for archivo in archivos:
    print(f"Leyendo archivo: {archivo}")  

    try:
        df = pd.read_csv(archivo, sep=",", encoding="utf-8")
    except:
        df = pd.read_csv(archivo, sep=";", encoding="latin1")

    nombre_archivo = os.path.basename(archivo)
    df["archivo_origen"] = nombre_archivo

    df["periodo"] = df["archivo_origen"].str.extract(r'(\d{6})')

    lista_df.append(df)

print("\nUnificando archivos...")

df_final = pd.concat(lista_df, ignore_index=True)

salida = r"F:\Documentos\Activos\Santillan Agustina\NUEVO SISTEMA\.SICOSS\consolidado.xlsx"
df_final.to_excel(salida, index=False)

print(f"\n✔ Consolidado generado en: {salida}")