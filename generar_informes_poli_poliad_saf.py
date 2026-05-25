import pandas as pd
import numpy as np
import os

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
COMPLETA = 'COMPLETA_042026.csv'   # ajustar path si es necesario
FONAVI   = 'FONAVI_042026.csv'     # ajustar path si es necesario
ENCODING = 'latin1'
PERIODO  = '0426'                  # se usa en el nombre de los archivos de salida

# =============================================================================
# COLUMNAS DE SALIDA (orden del formato XLS/informe)
# =============================================================================
XLS_COLS = [
    'cuil','codobra','canthijo','conyuge','adherente','rebpromo','zonageo','actividad',
    'porcreduc','remutotal','remuimpo','porceadi','aportvolun','exessocial','asigfliar',
    'exeosocial','remuimpoos','impoadicos','aportejubi','aportepatr','apafilos','appatros',
    'apeynom','domicilio','fechaing','fechabaja','conceptono','codigo','declara','periodo',
    'codorigen','nroagente','ubicacion','coseguro','codestado','saf',
    'claseycar','bandera','cod_181','cod_298',
    'd_svco','d_ss','d_svca','d_sc',
    'hsextras','remusueldo','remusac','dias_traba','canasta_fl','trasp_osep',
    'act_doc','remu_doc','ap_dcto788','aporte_dif','cant_hsext',
    'tipo_doc','fecha_nac','sexo','cod_orgpol','cod_cargo','disp_nomb',
    'porcosep','remuosep','apsolosep','consolosep'
]

# =============================================================================
# MAPEO: posición en XLS -> posición en CSV fuente
# Columnas 0-35: misma posición en ambos
# Columnas 36-64: reordenadas según el siguiente mapa
# None = columna no presente en CSV (se rellena con NaN/0)
# =============================================================================
EXTRA_MAP = {
    36: 71,   # claseycar
    37: None, # bandera      (siempre 0)
    38: None, # cod_181      (siempre 0)
    39: None, # cod_298      (siempre 0)
    40: 36,   # d_svco
    41: 37,   # d_ss
    42: 38,   # d_svca
    43: 39,   # d_sc
    44: 42,   # hsextras
    45: 40,   # remusueldo
    46: 41,   # remusac
    47: 43,   # dias_traba
    48: 44,   # canasta_fl
    49: 58,   # trasp_osep
    50: 48,   # act_doc
    51: 47,   # remu_doc
    52: None, # ap_dcto788   (siempre 0)
    53: 50,   # aporte_dif
    54: 51,   # cant_hsext
    55: None, # tipo_doc     (NaN)
    56: 52,   # fecha_nac
    57: 60,   # sexo
    58: None, # cod_orgpol   (NaN)
    59: None, # cod_cargo    (NaN)
    60: None, # disp_nomb    (NaN)
    61: None, # porcosep     (NaN)
    62: None, # remuosep     (NaN)
    63: None, # apsolosep    (NaN)
    64: None, # consolosep   (NaN)
}

# Columnas del CSV fuente usadas para filtrar
CSV_COL_SAF       = 35   # código SAF
CSV_COL_CLASEYCAR = 71   # clase y cargo

# =============================================================================
# CARGA
# =============================================================================
print("Cargando archivos fuente...")
completa = pd.read_csv(COMPLETA, header=None, encoding=ENCODING)
fonavi   = pd.read_csv(FONAVI,   header=None, encoding=ENCODING)
all_csv  = pd.concat([completa, fonavi], ignore_index=True)
print(f"  COMPLETA: {len(completa)} registros")
print(f"  FONAVI:   {len(fonavi)} registros")
print(f"  TOTAL:    {len(all_csv)} registros")

# =============================================================================
# FUNCIÓN: reordenar columnas al formato de salida
# =============================================================================
def reordenar_columnas(df_csv):
    out = {}
    for xi, col in enumerate(XLS_COLS):
        if xi <= 35:
            out[col] = df_csv.iloc[:, xi].values
        else:
            ci = EXTRA_MAP.get(xi)
            out[col] = df_csv.iloc[:, ci].values if ci is not None else np.nan
    return pd.DataFrame(out)

# =============================================================================
# FILTROS
# Policía (POLI):  saf = 7 u 8  AND  claseycar entre 1101 y 1199
# Pol. Admin (POAD): saf = 7 u 8  AND  claseycar fuera de 1101-1199
# SAF:             saf distinto de 7 y 8
# =============================================================================
mask_poli = all_csv[CSV_COL_SAF].isin([7, 8]) &  all_csv[CSV_COL_CLASEYCAR].between(1101, 1199)
mask_poad = all_csv[CSV_COL_SAF].isin([7, 8]) & ~all_csv[CSV_COL_CLASEYCAR].between(1101, 1199)
mask_saf  = ~all_csv[CSV_COL_SAF].isin([7, 8])

# =============================================================================
# GENERACIÓN
# =============================================================================
archivos = [
    ('POLI', mask_poli, f'POLI{PERIODO}.csv'),
    ('POAD', mask_poad, f'POAD{PERIODO}.csv'),
    ('SAF',  mask_saf,  f'SAF{PERIODO}.csv'),
]

for nombre, mask, archivo_salida in archivos:
    df_filtrado  = all_csv[mask].reset_index(drop=True)
    df_salida    = reordenar_columnas(df_filtrado)
    df_salida.to_csv(archivo_salida, index=False, header=False, encoding=ENCODING)
    print(f"\n{nombre}: {len(df_salida)} registros -> {archivo_salida}")

print("\nListo.")
