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
TOPE_SS     = 4162912.57  # Base imponible máxima SS (abril2026) - actualizar cada período
TOPE_SS_RED = TOPE_SS     # Base imponible reducida cuando supera tope - actualizar cada período

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
#   1. CSV[48]=='01'                                    -> Magistrado        act=100 (o 101 si también docente)
#   2. CSV[48]=='76'                                    -> Docente c/dif     act=76  (salvo SAF poli/peni)
#   3. CSV[48]=='77' o '75'                             -> Docente s/dif     act=77/75
#   4. ubic[:6]=='301502' Y cargo 1131-1148             -> Penitenciario     act=66  <- ANTES que policia
#   5. ubic[:6]=='301501' Y cargo 1103-1118             -> Policia           act=53
#   6. CSV[1]=='001102' (OSPLAD, no docente)            -> OSPLAD sin doc    act=46
#   7. default                                          -> Empleado comun    act=19
# =============================================================================

def get_actividad(r):
    cuil        = str(r[0]).strip()
    cod_doc     = str(r[48]).strip() if len(r) > 48 else ""
    clase_cargo = str(r[71]).strip() if len(r) > 71 else ""
    ubic_presup = str(r[32]).strip() if len(r) > 32 else ""
    zona_geo    = str(r[6]).strip()  if len(r) >  6 else "09"

    if cod_doc == "01":
        # Magistrado + docente (col[49] guarda marca de actividad docente)
        cod_doc_extra = str(r[49]).strip() if len(r) > 49 else ""
        if cod_doc_extra == "76":
            return ("101", "08", "000000")  # Magistrado + Docente
        return ("100", "08", "000000")      # Magistrado puro

    # Docentes: OS segun CSV[1] (001102=OSPLAD nacional, cualquier otro=000000)
    # FIX 3: CUITs que comienzan con "24" (extranjeros) no pueden tener actividad 76
    # Se los trata como empleados comunes (act=19)
    # col[48] = act_doc: contiene exactamente el código 76 o 77 que debe ir en SICOSS.
    # Se respeta directamente ese valor sin inferir por r[1] (OS).
    cod_os_doc = "001102" if cod_doc == "77" else "000000"
    if cod_doc == "76":  return ("76 ", "08", cod_os_doc)  # Docente act=76 (con diferencial)
    if cod_doc == "77":  return ("77 ", "08", cod_os_doc)  # Docente act=77 (con OS, sin diferencial)
    if cod_doc == "75":  return ("75 ", "08", "000000")    # Docente act=75 (sin OS, sin diferencial)

    # Penitenciario ANTES que policía (prioridad)
    ubic  = str(r[32]).strip() if len(r) > 32 else ""
    cargo = str(r[71]).strip() if len(r) > 71 else ""
    cargo_num = int(cargo) if cargo.isdigit() else 0

    CARGOS_POLI = {1101,1102,1103,1105,1106,1107,1108,1109,1110,1111,1112,1113,1114,1115,1116,1117,1118}
    CARGOS_PENI = {1131,1132,1133,1135,1136,1137,1138,1139,1140,1141,1142,1143,1144,1145,1146,1147,1148}

    es_penitenciario = (ubic[:6] == "301502" and cargo_num in CARGOS_PENI) or (cuil in CUILES_PENITENCIARIO)
    if es_penitenciario:
        return ("66 ", zona_geo, "604707")

    # Policía Catamarca
    es_policia = (ubic[:6] == "301501" and cargo_num in CARGOS_POLI) or (cuil in CUILES_POLICIA)
    if es_policia:
        return ("53 ", "09", "604707")

    # OSPLAD sin ser docente -> act=46
    cod_os = str(r[1]).strip() if len(r) > 1 else ""
    if cod_os == "001102":
        return ("46 ", "09", "001102")

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
    # Selección del registro base para doble empleo:
    #
    # Regla 1: Si existe al menos un registro NO docente (policía, penitenciario,
    #          empleado común, magistrado), se usa el primero de esos como base.
    #          Esto preserva el comportamiento de la versión anterior para CUILes
    #          con doble empleo (ej: policía + docente -> base = policía).
    #
    # Regla 2: Si TODOS los registros son docentes (76/77/75), se elige el más
    #          específico: 76 > 77 > 75. Esto corrige el caso de docente cod=77
    #          con OSPLAD que antes quedaba como act=75 y debe ser act=76.
    #
    # Regla 3: Magistrado (01) siempre tiene prioridad absoluta.
    DOC_PRIO = {"77": 3, "76": 2, "75": 1}  # 77 gana sobre 76

    def es_docente(r):
        return str(r[48]).strip() if len(r) > 48 else "" in ("76", "77", "75")

    # Primero: ¿hay algún magistrado?
    magistrados = [r for r in registros if str(r[48]).strip() == "01"]
    if magistrados:
        base = list(magistrados[0])
    else:
        # Separar docentes de no-docentes
        no_docentes = [r for r in registros if str(r[48]).strip() not in ("76", "77", "75")]
        docentes    = [r for r in registros if str(r[48]).strip() in ("76", "77", "75")]
        if no_docentes:
            # Doble empleo: policía (SAF=7) y penitenciario (SAF=8) tienen
            # prioridad ABSOLUTA — solo están en COMPLETA.
            # Docente (76/77) gana únicamente si ningún registro tiene SAF 7 u 8.
            saf_vals = {str(r[35]).strip() for r in no_docentes if len(r) > 35}
            es_poli_o_peni = bool(saf_vals & {"7", "8"})
            # Policía/penitenciario: ubic[:6] en {301501,301502} Y cargo en rango 1103-1148
            def es_fuerza(r):
                ubic  = str(r[32]).strip()[:6] if len(r) > 32 else ""
                cargo = str(r[71]).strip()     if len(r) > 71 else ""
                cn    = int(cargo) if cargo.isdigit() else 0
                POLI = {1101,1102,1103,1105,1106,1107,1108,1109,1110,1111,1112,1113,1114,1115,1116,1117,1118}
                PENI = {1131,1132,1133,1135,1136,1137,1138,1139,1140,1141,1142,1143,1144,1145,1146,1147,1148}
                return (ubic == "301501" and cn in POLI) or \
                       (ubic == "301502" and cn in PENI)
            es_poli_o_peni = any(es_fuerza(r) for r in no_docentes)
            doc_77 = [r for r in docentes if str(r[48]).strip() == "77"]
            doc_76 = [r for r in docentes if str(r[48]).strip() == "76"]
            if doc_77 and not es_poli_o_peni:
                base = list(doc_77[0])
            elif doc_76 and not es_poli_o_peni:
                base = list(doc_76[0])
            else:
                base = list(no_docentes[0])
        elif docentes:
            # Solo docentes: elegir el de mayor prioridad (76 > 77 > 75)
            base = list(max(docentes, key=lambda r: DOC_PRIO.get(str(r[48]).strip(), 0)))
        else:
            base = list(registros[0])
    # Preservar marca tribunal: True si algún registro viene del archivo tribunal
    es_trib = any(r[-1] == "T" for r in registros)
    base[-1] = "T" if es_trib else "F"
    for idx in CAMPOS_SUMA:
        total = sum(int(fval(r[idx])) for r in registros if idx < len(r))
        base[idx] = str(total)
    # Rem Imponible con tope (CSV[63])
    rem_sin_tope = fval(base[10])
    cod_doc = str(base[48]).strip() if len(base) > 48 else ""
    if cod_doc == "01":  # Magistrados sin tope
        base[63] = str(rem_sin_tope)
    else:
        base[63] = str(min(rem_sin_tope, TOPE_SS))
    # Para magistrados con doble empleo (ej: magistrado + docente):
    # RI2 debe ser solo r[9] del magistrado + r[10] del no-magistrado.
    # Guardamos esos valores en campos extra (col[73] y col[74]) para usarlos
    # en procesar_fila() sin perder la separación entre registros.
    if cod_doc == "01" and len(registros) > 1:
        mag_r9   = sum(fval(r[9])  for r in registros if str(r[48]).strip() == "01")
        nomag_r10 = sum(fval(r[10]) for r in registros if str(r[48]).strip() != "01")
        while len(base) < 75:
            base.append("")
        base[73] = str(mag_r9)
        base[74] = str(nomag_r10)

    # Si el registro base NO es docente pero hay registros docentes en la combinación,
    # copiar r[47] (base diferencial) y r[50] (ANSAL) del registro docente al base.
    # También guardar el código de actividad docente en col[49] como marca.
    if cod_doc not in ("76", "77", "75"):
        doc_regs = [r for r in registros if str(r[48]).strip() in ("76", "77", "75")]
        if doc_regs:
            doc = doc_regs[0]
            while len(base) < 52:
                base.append("")
            base[47] = doc[47] if len(doc) > 47 else "0"
            base[50] = doc[50] if len(doc) > 50 else "0"
            base[49] = str(doc[48]).strip() if len(doc) > 48 else ""  # marca actividad docente

    # Para doble empleo act=77: guardar col[10] del cargo no-docente en col[75]
    # para poder calcular RI1 (= solo el aporte del cargo no-docente)
    if cod_doc == "77":
        nodoc_regs = [r for r in registros if str(r[48]).strip() not in ("76", "77", "75")]
        nodoc_col10 = sum(int(fval(r[10])) for r in nodoc_regs if len(r) > 10)
        while len(base) < 76:
            base.append("")
        base[75] = str(nodoc_col10)
    elif str(base[49] if len(base) > 49 else "") == "77":
        # Doble empleo donde base es no-docente pero hay registro act=77
        nodoc_col10 = sum(int(fval(r[10])) for r in registros
                          if str(r[48]).strip() not in ("76","77","75") and len(r) > 10)
        while len(base) < 76:
            base.append("")
        base[75] = str(nodoc_col10)

    return base


# =============================================================================
# GENERACIÓN DE LÍNEA SICOSS
# =============================================================================

def procesar_fila(r):
    buf = new_line(500)

    cod_act, zona, cod_os = get_actividad(r)

    es_policia       = (cod_act.strip() == "53")
    es_penitenciario = (cod_act.strip() == "66")
    es_magistrado    = (cod_act.strip() == "100")
    es_tipo_policial = es_policia or es_penitenciario
    es_docente_76 = (cod_act.strip() == "76")
    es_docente_77 = (cod_act.strip() == "77")

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
        rem_sin_tope = round(fval(r[10]))
        rem_total    = rem_sin_tope + int(fval(r[26]))
        rem_con_tope = rem_sin_tope
        rem_imp5     = rem_sin_tope
    elif es_magistrado:
        # Si tiene doble empleo, acumular() guardó en col[73] y col[74]:
        #   col[73] = sum(r[9]) solo del magistrado
        #   col[74] = sum(r[10]) de los registros no-magistrado
        # RI2 = rem_total = mag_r9 + nomag_r10
        mag_r9    = fval(r[73]) if len(r) > 73 and r[73] else 0
        nomag_r10 = fval(r[74]) if len(r) > 74 and r[74] else 0
        if mag_r9 > 0:
            rem_total    = round(mag_r9 + nomag_r10)
            rem_sin_tope = round(fval(r[10]))  # suma total de r[10] acumulado
        else:
            rem_total    = round(fval(r[9]))
            rem_sin_tope = round(fval(r[10]))
        rem_con_tope = 0
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope
    else:
        rem_sin_tope = int(fval(r[10]))  # tribunal: usar col10 directamente
        rem_total    = int(fval(r[9]))
        rem_con_tope = min(rem_sin_tope, TOPE_SS)
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope

    # Para act=77 con doble empleo: col[75] tiene el col10 del cargo no-docente
    es_doc77_doble_empleo = es_docente_77 and len(r) > 75 and fval(r[75]) > 0
    nodoc_col10 = int(fval(r[75])) if es_doc77_doble_empleo else 0

    if es_doc77_doble_empleo:
        # Doble empleo act=77: rem_sin_tope = col10 acumulado (ambos cargos sin cnc)
        # rem_total = rem_sin_tope + cnc del cargo no-docente (ya en cnc_int acumulado)
        rem_sin_tope = int(fval(r[10]))   # = col10_COMP + col10_EDUC
        rem_total    = rem_sin_tope + cnc_int
        rem_con_tope = min(rem_sin_tope, TOPE_SS)
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope
    elif not (es_policia or es_penitenciario or es_magistrado or es_tribunal):
        rem_sin_tope = sueldo_int + sac_int + hs_int + premios_int + vacac_int
        rem_total    = rem_sin_tope + cnc_int + canasta_int
        rem_con_tope = min(rem_sin_tope, TOPE_SS)
        rem_imp5     = TOPE_SS_RED if rem_sin_tope > TOPE_SS else rem_sin_tope

    # Marca Reducción basada en CSV[8] (% Reducción)
    marca_red = "1" if fval(r[8]) > 0 else "0"

    # FIX 1: Días trabajados - mínimo 1 si hay remuneración
    dias_raw = fval(r[43])
    if dias_raw == 0 and (sueldo_int > 0 or fval(r[10]) > 0):
        dias_trabajados = 1
    else:
        dias_trabajados = dias_raw

    # FIX 2: Adicional OS - solo cuando corresponde OS (cod_os != "000000")
    adicional_os = int(fval(r[17])) if cod_os != "000000" else 0

    # FIX 5: Docentes con aporte diferencial (act=76)
    # r[47] = base remunerativa para el diferencial OS (Rem Imp 6)
    # ANSAL = 0,45% de r[47] para cod=77 (el CSV usa 2% en r[50], incorrecto)
    # cod=76: RI6=r[47], ANSAL=0
    # cod=77: RI6=0,     ANSAL=0.45% de r[47]
    rem_imp6_docente = int(fval(r[47])) if (es_docente_76 and len(r) > 47) else 0
    # RI6 no puede superar RI2 (AFIP error 491) - limitar por redondeo
    # Se aplica después de calcular rem_sin_tope para docentes
    # ANSAL = 0.45% del (rem_sin_tope + cnc) si hay cargo act=77 (directo o doble empleo)
    # En doble empleo, acumular() guarda la actividad docente en col[49]
    es_doc77_directo = es_docente_77
    es_doc77_doble = (not es_docente_77 and not es_docente_76
                      and len(r) > 49 and str(r[49]).strip() == "77")
    tiene_cargo_77 = es_doc77_directo or es_doc77_doble
    base_ansal = rem_sin_tope + cnc_int
    ansal_docente = round(base_ansal * 0.0045, 2) if tiene_cargo_77 else 0

    # FIX 4b: Régimen - validar que sea "0" o "1", si no forzar a "1"
    regimen_raw = str(r[45]).strip() if len(r) > 45 else "1"
    regimen = regimen_raw if regimen_raw in ("0", "1") else "1"

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
    put(buf, 61, 67, "403700" if cod_act.strip() == "101" else cod_os)  # Cód. Obra Social
    put(buf, 67, 69, str(r[4]).strip().zfill(2)[:2])          # Cant. Adherentes

    # REMUNERACIONES (69-138)
    put_num(buf,  69,  81, rem_total)                         # Rem. Total
    ri1 = 0 if (es_tipo_policial or es_docente_76 or es_docente_77) else rem_con_tope
    if es_doc77_doble_empleo:
        ri1 = nodoc_col10  # solo el cargo no-docente va a SIPA
    put_num(buf,  81,  93, ri1)                               # Rem. Imp. 1
    put_num(buf,  93, 102, 0)                                 # Asig. Familiares
    put_num(buf, 102, 111, 0)                                 # Aporte Voluntario
    put_num(buf, 111, 120, adicional_os)                      # Adicional OS (FIX 2)
    put_num(buf, 120, 129, int(fval(r[13])))                  # Excedente SS
    put_num(buf, 129, 138, int(fval(r[15])))                  # Excedente OS

    # LOCALIDAD (138-188)
    put(buf, 138, 188, "CATAMARCA")

    # REM. IMPONIBLES 2, 3, 4 (188-224)
    # FIX 4c: Rem Imp 2 para policía = rem_sin_tope + hs_extra (r[42] acumulado)
    # Para empleados comunes rem_sin_tope ya incluye r[42] en el calculo
    rem_imp2_policia = rem_sin_tope + hs_int if es_tipo_policial else None
    if es_magistrado:
        ri2 = rem_total
    elif es_tipo_policial:
        ri2 = rem_imp2_policia
    elif es_doc77_doble_empleo:
        ri2 = rem_sin_tope   # col10_COMP + col10_EDUC (sin cnc)
    else:
        ri2 = rem_sin_tope
    put_num(buf, 188, 200, ri2)                               # Rem. Imp. 2
    put_num(buf, 200, 212, 0)                                 # Rem. Imp. 3
    if es_doc77_doble_empleo:
        ri4 = rem_total      # RemTotal completo
    else:
        ri4 = rem_sin_tope if es_docente_77 else 0
    put_num(buf, 212, 224, ri4)                               # Rem. Imp. 4

    # CAMPOS ESPECIALES (224-258)
    put(buf, 224, 226, "00")                                  # Cód. Siniestrado
    put(buf, 226, 227, marca_red)                             # Marca Reducción
    put_num(buf, 227, 236, 0)                                 # Capital LRT
    put(buf, 236, 237, "3" if es_tipo_policial else "G")      # Tipo Empresa
    put_num(buf, 237, 246, ansal_docente)                       # Aporte Adic. OS / ANSAL (FIX 5: docentes act=76)
    put(buf, 246, 247, regimen)                               # Régimen (FIX 4b)
    put(buf, 247, 249, "1 ")                                  # Situación Revista 1
    put(buf, 249, 251, "1 ")                                  # Día inicio Sit. 1

    # REM. DETALLADAS (259-319)
    put_num(buf, 259, 271, rem_sin_tope if (es_tipo_policial or es_magistrado) else int(fval(r[40])))  # Sueldo
    put_num(buf, 271, 283, int(fval(r[41])))                  # SAC
    put_num(buf, 283, 295, int(fval(r[42])))                  # Horas Extra
    put_num(buf, 295, 307, 0)                                 # Zona Desfavorable
    put_num(buf, 307, 319, vacac_int)                         # Vacaciones

    # DÍAS Y REM. IMPONIBLES 5-9 (319-450)
    put_num(buf, 319, 328, dias_trabajados)                   # Días trabajados (FIX 1)
    # RI5: policia/peni/docentes = rem_sin_tope; otros = rem_imp5 (con tope)
    ri5 = rem_sin_tope if (es_tipo_policial or es_docente_76 or es_docente_77) else rem_imp5
    put_num(buf, 328, 340, ri5)                               # Rem. Imp. 5
    put(buf, 340, 341, "0")                                   # Trab. Convencionado

    ri6_final = min(rem_imp6_docente, rem_sin_tope) if es_docente_76 else \
                (int(fval(r[47])) if (es_docente_77 and len(r) > 47) else 0)
    put_num(buf, 341, 353, ri6_final)                         # Rem. Imp. 6

    put_num(buf, 366, 378, premios_int)                       # Premios

    # RI8: act=77 -> rem_total (doble empleo) o rem_sin_tope (puro); otros -> 0
    ri8 = rem_total if es_doc77_doble_empleo else (rem_sin_tope if es_docente_77 else 0)
    put_num(buf, 378, 390, ri8)                               # Rem. Imp. 8

    # RI7: docentes/policia/peni -> ri6_final o rem_sin_tope; magistrado -> rem_total; otros -> 0
    if es_doc77_doble_empleo:
        ri7 = int(fval(r[47])) if len(r) > 47 else 0
    elif es_docente_76 or es_docente_77 or es_tipo_policial:
        ri7 = rem_sin_tope
    elif es_magistrado:
        ri7 = rem_total
    else:
        ri7 = 0
    put_num(buf, 390, 402, ri7)                               # Rem. Imp. 7
    tiene_hs = "  1" if fval(r[42]) > 0 else "  0"
    put(buf, 402, 405, tiene_hs)                              # Cant. Horas Extras
    put_num(buf, 405, 417, cnc_int)                           # Conceptos No Remun.
    put_num(buf, 417, 429, 0)                                 # Maternidad
    put_num(buf, 429, 438, 0)                                 # Rectificación
    ri9 = rem_total if es_magistrado else (rem_sin_tope if es_doc77_doble_empleo else rem_sin_tope)
    put_num(buf, 438, 450, ri9)                               # Rem. Imp. 9

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
        # Ignorar archivos con menos de 48 columnas (no son archivos de liquidación)
        if len(df.columns) < 48:
            print(f"  IGNORADO {nombre}: solo {len(df.columns)} columnas (mínimo esperado: 48)")
            continue
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
avisos_dias = 0

for cuil, registros in cuil_registros.items():
    try:
        r = acumular(registros)
        rem10 = fval(r[10])
        rem40 = fval(r[40])
        if rem10 == 0 and rem40 == 0:
            continue
        # Aviso si se corrigieron días
        if fval(r[43]) == 0 and (rem40 > 0 or rem10 > 0):
            nombre = r[22] if len(r) > 22 else "?"
            print(f"  AVISO días=0 corregido a 1: CUIL={cuil} {nombre}")
            avisos_dias += 1
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
if avisos_dias:
    print(f"  Días corregidos (0->1): {avisos_dias}")
if errores:
    print(f"  Errores:   {errores}")
