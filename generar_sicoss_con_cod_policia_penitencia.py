import pandas as pd
import glob
import os
import unicodedata

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

input_folder = "."
output_file  = "salida_sicoss.txt"

# Topes de Seguridad Social (actualizar cada período según ANSES)
TOPE_SS     = 4045590.50  # Base imponible máxima SS (marzo 2026) - actualizar cada período
TOPE_SS_RED = 3505701.40  # Base imponible reducida cuando supera tope - actualizar cada período

# =============================================================================
# CARGA DE CUILES POLICÍA
# Archivo "cuiles_policia.txt" en la misma carpeta, un CUIL por línea.
# Cubre policías en funciones administrativas o comisionados que no se
# detectan automáticamente por la regla de ubicación presupuestaria.
# =============================================================================

def cargar_cuiles(nombre_archivo):
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)
    if not os.path.exists(ruta):
        print(f"  AVISO: No se encontro {nombre_archivo}")
        return set()
    with open(ruta, encoding="utf-8") as f:
        cuiles = {line.strip() for line in f if line.strip()}
    print(f"  OK {nombre_archivo}: {len(cuiles)} CUILes cargados")
    return cuiles

CUILES_POLICIA      = cargar_cuiles("cuiles_policia.txt")
CUILES_PENITENCIARIO = cargar_cuiles("cuiles_penitenciario.txt")

# =============================================================================
# TABLA DE CONVERSIÓN: Tipo de agente -> (Actividad SICOSS, Zona, Cód OS)
#
# Orden de prioridad:
#   1. CSV[48]=='01'                          -> Magistrado      act=100
#   2. CSV[48]=='76'                          -> Docente c/OS    act=76
#   3. CSV[48]=='77' o '75'                   -> Docente s/OS    act=75
#   4. clase_cargo in {'1131'..'1139'}        -> Penitenciario   act=66  ← ANTES que policía
#   5. CUIL en lista O (ubic[:4]='3015' Y cc[:2]='11') -> Policía act=53
#   6. default                                -> Empleado común  act=19
# =============================================================================

def get_actividad(r):
    cuil        = str(r[0]).strip()
    cod_doc     = str(r[48]).strip() if len(r) > 48 else ""
    clase_cargo = str(r[71]).strip() if len(r) > 71 else ""
    ubic_presup = str(r[32]).strip() if len(r) > 32 else ""
    zona_geo    = str(r[6]).strip()  if len(r) >  6 else "09"

    if cod_doc == "01":  return ("100", "08", "000000")  # Magistrado

    # Docentes: OS segun CSV[1] (001102=OSPLAD nacional, cualquier otro=000000)
    cod_os_doc = "001102" if str(r[1]).strip() == "001102" else "000000"
    if cod_doc == "76":  return ("76 ", "08", cod_os_doc)  # Docente con OS
    if cod_doc == "77":  return ("75 ", "08", "000000")    # Docente sin OS
    if cod_doc == "75":  return ("75 ", "08", "000000")    # Docente sin OS (alt)

    # Penitenciario ANTES que policía (prioridad)
    # La regla automática de policía (ubic 3015 + cc 11xx) también aplica a penitenciarios,
    # por eso se evalúa primero: por clase/cargo automático O por lista manual.
    # Penitenciario: códigos 1131-1148 o lista manual
    peni_set = {f"{i}" for i in range(1131, 1149)}
    es_penitenciario = (clase_cargo in peni_set) or (cuil in CUILES_PENITENCIARIO)
    if es_penitenciario:
        return ("66 ", zona_geo, "604707")

    # Policía: códigos 1101-1118, lista manual, o regla automática ubic 3015
    poli_set = {f"{i}" for i in range(1101, 1119)}
    es_policia = (clase_cargo in poli_set) or (cuil in CUILES_POLICIA) or \
                 (ubic_presup[:4] == "3015" and clase_cargo[:2] == "11")
    if es_policia:
        return ("53 ", "09", "604707")

    return ("19 ", "09", "000000")  # Empleado común


# =============================================================================
# UTILIDADES
# =============================================================================

def limpiar(texto):
    resultado = []
    for c in str(texto):
        try:
            c.encode("cp1252")
            resultado.append(c)
        except (UnicodeEncodeError, UnicodeDecodeError):
            norm = unicodedata.normalize("NFKD", c)
            ascii_c = norm.encode("ascii", "ignore").decode("ascii")
            resultado.append(ascii_c if ascii_c else " ")
    return "".join(resultado)

def new_line(length=500):
    return [" "] * length

def put(buf, start, end, value):
    size = end - start
    value = limpiar(str(value))[:size].ljust(size)
    buf[start:end] = list(value)

def put_num(buf, start, end, value, dec=2):
    size = end - start
    try:
        v = float(value)
    except (ValueError, TypeError):
        v = 0.0
    fmt = f"{v:.{dec}f}".rjust(size)
    buf[start:end] = list(fmt)

def fval(v):
    try:    return float(v)
    except: return 0.0


# =============================================================================
# ACUMULACIÓN (suma de CUILes repetidos entre archivos)
# =============================================================================

CAMPOS_SUMA = [9, 10, 13, 14, 15, 17, 26, 40, 41, 42, 61, 62]

def acumular(registros):
    base = list(registros[0])
    # Preservar marca tribunal: True si algún registro viene del archivo tribunal
    es_trib = any(r[-1] == "T" for r in registros)
    base[-1] = "T" if es_trib else "F"
    for idx in CAMPOS_SUMA:
        if idx == 10:
            # CSV[10]: sumar round() de cada fila para evitar diferencias de centavos
            total = sum(round(fval(r[idx])) for r in registros if idx < len(r))
        else:
            total = sum(fval(r[idx]) for r in registros if idx < len(r))
        base[idx] = str(total)
    # Rem Imponible con tope (CSV[63])
    rem_sin_tope = fval(base[10])
    cod_doc = str(base[48]).strip() if len(base) > 48 else ""
    if cod_doc == "01":  # Magistrados sin tope
        base[63] = str(rem_sin_tope)
    else:
        base[63] = str(min(rem_sin_tope, TOPE_SS))
    return base


# =============================================================================
# GENERACIÓN DE LÍNEA SICOSS
# =============================================================================

def procesar_fila(r):
    buf = new_line(500)

    cod_act, zona, cod_os = get_actividad(r)

    es_policia      = (cod_act.strip() == "53")
    es_penitenciario = (cod_act.strip() == "66")
    es_magistrado  = (cod_act.strip() == "100")
    es_tipo_policial = es_policia or es_penitenciario  # misma lógica de rem

    # Truncar cada campo individualmente (int) y sumar
    sueldo_int  = int(fval(r[40]))
    sac_int     = int(fval(r[41]))
    hs_int      = int(fval(r[42]))
    cnc_int     = int(fval(r[26]))
    canasta_int = int(fval(r[44]))
    premios_int = int(fval(r[61]))
    es_tribunal  = (r[-1] == "T")  # viene del archivo tribunal
    if es_tribunal:
        premios_int = 0  # Tribunal: premios no se suman a rem imponible
    vacac_int   = int(fval(r[62]))
    rem_imponible = sueldo_int + sac_int + hs_int

    if es_policia:
        rem_total    = int(fval(r[9]))
        rem_sin_tope = round(fval(r[10]))
        rem_con_tope = rem_sin_tope
        rem_imp5     = rem_sin_tope
    elif es_penitenciario:
        # Penitenciario: rem_sin_tope=round(CSV[10]), rem_total=rem_sin_tope+cnc
        rem_sin_tope = round(fval(r[10]))
        rem_total    = rem_sin_tope + int(fval(r[26]))
        rem_con_tope = rem_sin_tope
        rem_imp5     = rem_sin_tope
    elif es_magistrado:
        rem_total    = round(fval(r[9]))
        rem_sin_tope = round(fval(r[10]))
        rem_con_tope = 0
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope
    else:
        # Empleado común y penitenciario
        # Tribunal de Cuentas: usa round(CSV[10]) para evitar diferencias de centavos
        # Los demás: suma de enteros truncados de cada componente
        if es_tribunal:
            # Tribunal de Cuentas: usar int() directo de CSV[9] y CSV[10]
            # premios y canasta no se suman (ya están en 0 por la marca tribunal)
            rem_sin_tope = int(fval(r[10]))
            rem_total    = int(fval(r[9]))
        else:
            rem_sin_tope = rem_imponible
            rem_total    = rem_imponible + cnc_int + canasta_int + premios_int + vacac_int
        rem_con_tope = min(rem_sin_tope, TOPE_SS)
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope

    # FIX BUG 2: Marca Reducción basada en CSV[8] (% Reducción), no en CSV[56]
    # CSV[56] es "Tiene Deuda Caja" y no tiene relación con reducción de zona
    marca_red = "1" if fval(r[8]) > 0 else "0"

    # BLOQUE IDENTIFICADOR (0-68)
    put(buf,  0, 11, r[0])                                    # CUIL
    put(buf, 11, 41, r[22])                                   # Apellido y Nombre
    put(buf, 41, 42, r[3])                                    # Cónyuge
    put(buf, 42, 44, str(r[2]).strip().zfill(2)[:2])          # Cant. Hijos
    put(buf, 44, 46, "01")                                    # Cód. Situación (fijo)
    put(buf, 46, 48, "01")                                    # Cód. Condición (siempre 01)
    put(buf, 48, 51, cod_act)                                 # Cód. Actividad
    put(buf, 51, 53, zona)                                    # Cód. Zona
    put(buf, 53, 58, "000  ")                                 # Porc. Aporte Adic. SS
    put(buf, 58, 61, "25 ")                                   # Cód. Modalidad
    put(buf, 61, 67, cod_os)                                  # Cód. Obra Social
    put(buf, 67, 69, str(r[4]).strip().zfill(2)[:2])          # Cant. Adherentes

    # REMUNERACIONES (69-138)
    put_num(buf,  69,  81, rem_total)                         # Rem. Total
    put_num(buf,  81,  93, 0 if es_tipo_policial else rem_con_tope) # Rem. Imp. 1
    put_num(buf,  93, 102, 0)                                 # Asig. Familiares
    put_num(buf, 102, 111, 0)                                 # Aporte Voluntario
    put_num(buf, 111, 120, int(fval(r[17])))                  # Adicional OS
    put_num(buf, 120, 129, int(fval(r[13])))                  # Excedente SS
    put_num(buf, 129, 138, int(fval(r[15])))                  # Excedente OS

    # LOCALIDAD (138-188)
    put(buf, 138, 188, "CATAMARCA")

    # REM. IMPONIBLES 2, 3, 4 (188-224)
    put_num(buf, 188, 200, rem_total if es_magistrado else rem_sin_tope)  # Rem. Imp. 2
    put_num(buf, 200, 212, 0)                                 # Rem. Imp. 3
    put_num(buf, 212, 224, 0)                                 # Rem. Imp. 4

    # CAMPOS ESPECIALES (224-258)
    put(buf, 224, 226, "00")                                  # Cód. Siniestrado
    put(buf, 226, 227, marca_red)                             # Marca Reducción (FIX BUG 2)
    put_num(buf, 227, 236, 0)                                 # Capital LRT
    put(buf, 236, 237, "3" if es_tipo_policial else "G")            # Tipo Empresa
    put_num(buf, 237, 246, 0)                                 # Aporte Adic. OS
    put(buf, 246, 247, r[45])                                 # Régimen
    put(buf, 247, 249, "1 ")                                  # Situación Revista 1
    put(buf, 249, 251, "1 ")                                  # Día inicio Sit. 1

    # REM. DETALLADAS (259-319)
    put_num(buf, 259, 271, rem_sin_tope if (es_tipo_policial or es_magistrado) else int(fval(r[40])))  # Sueldo
    put_num(buf, 271, 283, int(fval(r[41])))                  # SAC
    put_num(buf, 283, 295, int(fval(r[42])))                  # Horas Extra
    put_num(buf, 295, 307, 0)                                 # Zona Desfavorable
    put_num(buf, 307, 319, vacac_int)                         # Vacaciones

    # DÍAS Y REM. IMPONIBLES 5-9 (319-450)
    put_num(buf, 319, 328, r[43])                             # Días trabajados
    put_num(buf, 328, 340, rem_sin_tope if es_tipo_policial else rem_imp5)   # Rem. Imp. 5
    put(buf, 340, 341, "0")                                   # Trab. Convencionado
    put_num(buf, 341, 353, rem_sin_tope if (es_tipo_policial and cnc_int == 0) else 0)  # Rem. Imp. 6
    put_num(buf, 366, 378, premios_int)                       # Premios
    put_num(buf, 378, 390, 0)                                 # Rem. Dec. 788/05
    put_num(buf, 390, 402, rem_sin_tope if es_tipo_policial else (rem_total if es_magistrado else 0))  # Rem. Imp. 7
    tiene_hs = "  1" if fval(r[42]) > 0 else "  0"
    put(buf, 402, 405, tiene_hs)                              # Cant. Horas Extras
    put_num(buf, 405, 417, cnc_int)                           # Conceptos No Remun.
    put_num(buf, 417, 429, 0)                                 # Maternidad
    put_num(buf, 429, 438, 0)                                 # Rectificación
    put_num(buf, 438, 450, rem_total if es_magistrado else rem_sin_tope)  # Rem. Imp. 9

    return "".join(buf).rstrip()


# =============================================================================
# LECTURA DE TODOS LOS CSV (sin duplicados por nombre)
# =============================================================================

vistos = set()
archivos = []
for patron in ["*.csv", "*.CSV"]:
    for ruta in sorted(glob.glob(os.path.join(input_folder, patron))):
        nombre_lower = os.path.basename(ruta).lower()
        if nombre_lower not in vistos:
            vistos.add(nombre_lower)
            archivos.append(ruta)

if not archivos:
    print(f"No se encontraron archivos CSV en: {os.path.abspath(input_folder)}")
    exit(1)

print(f"Archivos encontrados: {len(archivos)}")
for a in archivos:
    print(f"  - {os.path.basename(a)}")

# Agrupar registros por CUIL
cuil_registros = {}
total_leidos = 0

for archivo in archivos:
    nombre = os.path.basename(archivo)
    try:
        df = pd.read_csv(
            archivo, header=None, dtype=str,
            encoding="latin-1", quotechar='"',
        ).fillna("")
        es_tribunal = "tribunal" in nombre.lower()
        if es_tribunal:
            print(f"  -> Archivo TRIBUNAL detectado: {nombre}")
        for _, row in df.iterrows():
            r = list(row)
            cuil = str(r[0]).strip()
            if cuil not in cuil_registros:
                cuil_registros[cuil] = []
            r.append("T" if es_tribunal else "F")  # campo extra: origen tribunal
            cuil_registros[cuil].append(r)
            total_leidos += 1
        print(f"  OK {nombre}: {len(df)} registros")
    except Exception as e:
        print(f"  ERROR {nombre}: {e}")

repetidos = sum(1 for v in cuil_registros.values() if len(v) > 1)
print(f"\nTotal leídos:   {total_leidos}")
print(f"CUILes únicos:  {len(cuil_registros)}")
print(f"CUILes repetidos: {repetidos}")

# =============================================================================
# GENERAR Y GUARDAR
# =============================================================================

out = []
errores = 0

for cuil, registros in cuil_registros.items():
    try:
        r = acumular(registros)
        rem10 = fval(r[10])
        rem40 = fval(r[40])
        if rem10 == 0 and rem40 == 0:
            continue
        linea = procesar_fila(r)
        out.append(linea)
    except Exception as e:
        errores += 1
        nombre = registros[0][22] if registros else "?"
        print(f"  ERROR CUIL={cuil} {nombre}: {e}")

with open(output_file, "w", encoding="cp1252", errors="replace") as f:
    for linea in out:
        f.write(linea + "\n")

print(f"\nSICOSS generado: {output_file}")
print(f"  Registros: {len(out)}")
if errores:
    print(f"  Errores:   {errores}")
