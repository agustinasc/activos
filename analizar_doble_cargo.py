import pandas as pd
import glob
import os

input_folder = "."

vistos = set()
archivos = []
for patron in ["*.csv", "*.CSV"]:
    for ruta in sorted(glob.glob(os.path.join(input_folder, patron))):
        nombre_lower = os.path.basename(ruta).lower()
        if nombre_lower not in vistos:
            vistos.add(nombre_lower)
            archivos.append(ruta)

cuil_registros = {}
for archivo in archivos:
    nombre = os.path.basename(archivo)
    try:
        df = pd.read_csv(archivo, header=None, dtype=str,
                        encoding="latin-1", quotechar='"').fillna("")
        for _, row in df.iterrows():
            r = list(row)
            cuil = str(r[0]).strip()
            if cuil not in cuil_registros:
                cuil_registros[cuil] = []
            cuil_registros[cuil].append((nombre, r))
    except:
        pass

# Analizar repetidos
mismo_archivo = 0
dist_archivo_mismo_cc = 0
doble_cargo_real = 0

doble_cargo_lista = []

for cuil, registros in cuil_registros.items():
    if len(registros) <= 1:
        continue
    
    archivos_origen = [r[0] for r in registros]
    clase_cargos = [r[1][71] if len(r[1]) > 71 else "" for r in registros]
    
    cc_unicos = set(clase_cargos)
    arch_unicos = set(archivos_origen)
    
    if len(cc_unicos) > 1:
        # Distintos clase/cargo -> doble cargo real
        doble_cargo_real += 1
        nombre_agente = registros[0][1][22] if len(registros[0][1]) > 22 else ""
        doble_cargo_lista.append((cuil, nombre_agente.strip(), list(cc_unicos), list(arch_unicos)))
    elif len(arch_unicos) > 1:
        dist_archivo_mismo_cc += 1
    else:
        mismo_archivo += 1

print(f"Mismo archivo, mismo CC (duplicado real): {mismo_archivo}")
print(f"Distinto archivo, mismo CC (multi-archivo): {dist_archivo_mismo_cc}")
print(f"Distinto CC (doble cargo real): {doble_cargo_real}")
print()
print("Primeros 30 doble cargo real:")
for cuil, nombre, ccs, archs in doble_cargo_lista[:30]:
    print(f"  {cuil} {nombre:<35} CC={ccs}  archivos={archs}")
