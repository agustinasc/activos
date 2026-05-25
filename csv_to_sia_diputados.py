import pandas as pd
import sys
import os

COLUMNAS = [
    'cuil', 'codobra', 'canthijo', 'conyuge', 'adherente', 'rebpromo',
    'zonageo', 'actividad', 'porcreduc', 'remutotal', 'remuimpo', 'porceadi',
    'aportvolun', 'exessocial', 'asigfliar', 'exeosocial', 'remuimpoos',
    'impoadicos', 'aportejubi', 'aportepatr', 'apafilos', 'appatros',
    'apeynom', 'domicilio', 'fechaing', 'fechabaja', 'conceptono', 'codigo',
    'declara', 'periodo', 'codorigen', 'nroagente', 'ubicacion', 'coseguro',
    'codestado', 'saf', 'd_svco', 'd_ss', 'd_svca', 'd_sc', 'remusueldo',
    'remusac', 'hsextras', 'dias_traba', 'canasta_fl', 'tipoliq', 'funcionari',
    'remu_doc', 'act_doc', 'ap_dcto788', 'aporte_dif', 'cant_hsext',
    'fecha_nac', 'ad_caja_co', 'aporte_caj', 'contrib_ca', 'tiene_deud',
    'deuda_caja', 'trasp_osep', 'tiene_fdo_', 'sexo', 'premios', 'vacaciones',
    'remuimpoto', 'por_retiro', 'rem_retiro', 'apo_vol', 'tras_vol',
    'cos_pro', 'cos_alt', 'cos_int', 'claseycar'
]

# Tope ANSES RS 74/2026 - Abril 2026
TOPE_ANSES = 4162912.57

ENC = 'latin1'

COLS_INT_VALUE    = {'porceadi', 'adherente', 'porcreduc'}
COLS_DECIMAL      = {'dias_traba', 'cos_alt', 'cos_int'}
COLS_DEFAULT_CERO = {
    'ap_dcto788',
    # Campos numéricos que vienen vacíos en el CSV pero que el SIA espera
    # un valor entero o decimal (no espacios en blanco).
    # Sin este default el layout queda con espacios y el SIA lanza
    # "La conversión de la cadena en tipo decimal no es válida".
    #
    # porcreduc (width=2) y porceadi (width=3) deben salir como '0' entero,
    # confirmado contra el archivo de referencia del periodo anterior.
    'porcreduc', 'porceadi',
    'aportvolun', 'exessocial',
    'exeosocial', 'impoadicos', 'coseguro',
    # Otros campos opcionales que también pueden venir vacíos
    'aporte_dif', 'remu_doc', 'cant_hsext', 'remusac',
}

# Campos monetarios de 9 bytes: se les aplica formateo adaptativo para que
# siempre quepan sin truncar (ajusta la cantidad de decimales según el valor).
COLS_MONETARIO = {
    'remutotal', 'remuimpo', 'remuimpoos', 'remusueldo', 'remuimpoto',
    'aportejubi', 'aportepatr', 'apafilos', 'appatros', 'conceptono',
    'aporte_caj', 'contrib_ca', 'deuda_caja', 'trasp_osep',
    'premios', 'vacaciones', 'rem_retiro', 'apo_vol', 'tras_vol',
    'd_svco', 'd_ss', 'd_svca', 'd_sc', 'remusac', 'hsextras', 'canasta_fl',
    'aportvolun', 'exessocial', 'asigfliar', 'exeosocial', 'impoadicos', 'coseguro',
}

# Layout SIA: igual a san fernando pero sin cos_pro, cos_alt, cos_int, claseycar
# Longitud total: 524 bytes
LAYOUT = [
    (0,   11,  'cuil',       'r'),
    (11,  17,  'codobra',    'r'),
    (17,  19,  'canthijo',   'r'),
    (19,  20,  'conyuge',    'r'),
    (20,  22,  'adherente',  'r'),
    (22,  25,  'rebpromo',   'r'),
    (25,  27,  'zonageo',    'r'),
    (27,  31,  'actividad',  'r'),
    (31,  33,  'porcreduc',  'r'),
    (33,  42,  'remutotal',  'r'),
    (42,  51,  'remuimpo',   'r'),
    (51,  54,  'porceadi',   'r'),
    (54,  63,  'aportvolun', 'r'),
    (63,  72,  'exessocial', 'r'),
    (72,  81,  'asigfliar',  'r'),
    (81,  90,  'exeosocial', 'r'),
    (90,  99,  'remuimpoos', 'r'),
    (99,  108, 'impoadicos', 'r'),
    (108, 117, 'aportejubi', 'r'),
    (117, 126, 'aportepatr', 'r'),
    (126, 135, 'apafilos',   'r'),
    (135, 144, 'appatros',   'r'),
    (144, 189, 'apeynom',    'l'),
    (189, 236, 'domicilio',  'l'),
    (236, 244, 'fechaing',   'r'),
    (244, 252, 'fechabaja',  'r'),
    (252, 261, 'conceptono', 'r'),
    (261, 262, '_sep_',      ' '),
    (262, 264, 'codigo',     'r'),
    (264, 265, 'declara',    'r'),
    (265, 271, 'periodo',    'r'),
    (271, 272, 'codorigen',  'r'),
    (272, 280, 'nroagente',  'r'),
    (280, 292, 'ubicacion',  'r'),
    (292, 301, 'coseguro',   'r'),
    (301, 302, 'codestado',  'r'),
    (302, 304, 'saf',        'r'),
    (304, 313, 'd_svco',     'r'),
    (313, 322, 'd_ss',       'r'),
    (322, 331, 'd_svca',     'r'),
    (331, 340, 'd_sc',       'r'),
    (340, 349, 'remusueldo', 'r'),
    (349, 358, 'remusac',    'r'),
    (358, 367, 'hsextras',   'r'),
    (367, 376, 'dias_traba', 'r'),
    (376, 385, 'canasta_fl', 'r'),
    (385, 386, 'tipoliq',    'r'),
    (386, 387, 'funcionari', 'l'),
    (387, 396, 'remu_doc',   'r'),
    (396, 398, 'act_doc',    'r'),
    (398, 407, 'ap_dcto788', 'r'),
    (407, 416, 'aporte_dif', 'r'),
    (416, 419, 'cant_hsext', 'r'),
    (419, 427, 'fecha_nac',  'r'),
    (427, 428, 'ad_caja_co', 'l'),
    (428, 437, 'aporte_caj', 'r'),
    (437, 446, 'contrib_ca', 'r'),
    (446, 447, 'tiene_deud', 'l'),
    (447, 456, 'deuda_caja', 'r'),
    (456, 465, 'trasp_osep', 'r'),
    (465, 466, 'tiene_fdo_', 'l'),
    (466, 467, 'sexo',       'l'),
    (467, 476, 'premios',    'r'),
    (476, 485, 'vacaciones', 'r'),
    (485, 494, 'remuimpoto', 'r'),
    (494, 497, 'por_retiro', 'r'),
    (497, 506, 'rem_retiro', 'r'),
    (506, 515, 'apo_vol',    'r'),
    (515, 524, 'tras_vol',   'r'),
    # SIA termina aquí — sin cos_pro, cos_alt, cos_int, claseycar
]

ANCHO_LINEA = 524


def fix_encoding(s):
    try:
        return s.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def validar_cuil(cuil_str):
    cuil = str(cuil_str).strip().replace('-', '').replace(' ', '')
    if len(cuil) != 11 or not cuil.isdigit():
        return False
    serie = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digitos = [int(c) for c in cuil]
    suma = sum(d * s for d, s in zip(digitos[:10], serie))
    resto = suma % 11
    if resto == 0:
        verificador = 0
    elif resto == 1:
        verificador = 9
    else:
        verificador = 11 - resto
    return digitos[10] == verificador


def fv(fila, campo):
    v = fila.get(campo, '')
    try:
        return float(str(v).strip()) if pd.notna(v) and str(v).strip() not in ('', 'nan') else 0.0
    except ValueError:
        return 0.0


def normalizar_periodo(periodo):
    """
    El layout SIA requiere formato MMAAAA.
    - Si viene como AAAAMM (ej. 202604): los primeros 4 dígitos son un año válido → convertir a MMAAAA
    - Si viene como MMAAAA (ej. 042026): ya está en el formato correcto → no tocar
    """
    periodo = str(periodo).strip()
    if len(periodo) != 6 or not periodo.isdigit():
        return periodo  # no se puede determinar, devolver tal cual

    primeros_cuatro = int(periodo[:4])
    primeros_dos    = int(periodo[:2])

    if 1900 <= primeros_cuatro <= 2099:
        # Formato AAAAMM → convertir a MMAAAA
        return periodo[4:6] + periodo[0:4]
    elif 1 <= primeros_dos <= 12:
        # Formato MMAAAA → ya está bien
        return periodo
    else:
        # Ambiguo o inválido: devolver sin cambios
        return periodo


def recalcular(fila):
    fila = fila.copy()

    remusueldo = fv(fila, 'remusueldo')
    remusac    = fv(fila, 'remusac')
    hsextras   = fv(fila, 'hsextras')
    conceptono = fv(fila, 'conceptono')
    premios    = fv(fila, 'premios')
    vacaciones = fv(fila, 'vacaciones')
    canasta    = fv(fila, 'canasta_fl')

    remuimpo = round(remusueldo + remusac + hsextras, 2)
    fila['remuimpo'] = f"{remuimpo:.2f}"

    remutotal = round(remuimpo + conceptono + premios + vacaciones + canasta, 2)
    fila['remutotal'] = f"{remutotal:.2f}"

    fila['remuimpoos'] = f"{remutotal:.2f}"

    if remuimpo <= TOPE_ANSES:
        aportejubi = round(remuimpo * 0.11, 2)
    else:
        aportejubi = round(TOPE_ANSES * 0.11 + (remuimpo - TOPE_ANSES) * 0.1017, 2)
    fila['aportejubi'] = f"{aportejubi:.2f}"

    fila['apafilos'] = f"{round(remutotal * 0.045, 2):.2f}"
    fila['appatros'] = f"{round(remutotal * 0.09, 2):.2f}"

    # Normalizar periodo a MMAAAA (formato requerido por el layout SIA)
    fila['periodo'] = normalizar_periodo(fila.get('periodo', ''))

    return fila


def fmt_monetario(val_str, ancho):
    """
    Formatea un valor monetario para que quepa exactamente en `ancho` bytes,
    ajustando la cantidad de decimales según sea necesario.
    Ej: ancho=9, val=2107501.53 -> '2107501.5'  (1 decimal)
        ancho=9, val=741713.21  -> '741713.21'   (2 decimales)
        ancho=9, val=0.0        -> '0.00'
    """
    try:
        v = float(val_str)
    except (ValueError, TypeError):
        return val_str
    if v == 0.0:
        return '0.00'
    int_digits = len(str(int(abs(v))))
    # ancho = int_digits + 1 (punto) + decimales
    decimales = ancho - int_digits - 1
    if decimales < 0:
        # Valor demasiado grande incluso sin decimales; devolver sin punto
        return str(int(round(v)))
    # Los valores monetarios nunca superan 2 decimales.
    # Sin este límite, valores como 82320.17 en ancho=9 saldrían como '82320.170'
    # en vez de '82320.17' (que luego formatear_bytes padea a ' 82320.17').
    decimales = min(2, decimales)
    return f"{v:.{decimales}f}"


def formatear_bytes(s, ancho, alineacion, campo=''):
    encoded = s.encode(ENC, errors='replace')
    if len(encoded) > ancho:
        print(f"  ADVERTENCIA: campo '{campo}' valor '{s}' ({len(encoded)} bytes) excede el ancho {ancho} — se truncará", file=sys.stderr)
        # Para campos alineados a la derecha conservamos los bytes más a la derecha
        # (los menos significativos quedan), igual que haría un campo numérico de ancho fijo.
        # Para campos alineados a la izquierda conservamos los bytes del inicio.
        encoded = encoded[-ancho:] if alineacion == 'r' else encoded[:ancho]
        padding = b''
    elif len(encoded) == ancho:
        padding = b''
    else:
        padding = b' ' * (ancho - len(encoded))
    if alineacion == 'r':
        return (padding + encoded).decode(ENC, errors='replace')
    else:
        return (encoded + padding).decode(ENC, errors='replace')


def formatear_valor(valor, ancho, alineacion, campo=''):
    if alineacion == ' ':
        return ' '

    es_vacio = not pd.notna(valor) or str(valor).strip() in ('', 'nan', 'None')

    if es_vacio and campo in COLS_DEFAULT_CERO:
        s = '0.00'
    elif es_vacio:
        s = ''
    else:
        s = fix_encoding(str(valor).strip())

    if campo in COLS_DECIMAL and s:
        try:
            s = f"{float(s):.2f}"
        except ValueError:
            pass

    if campo in COLS_INT_VALUE and s:
        try:
            s = str(int(float(s)))
        except ValueError:
            pass

    # Formateo adaptativo para campos monetarios: ajusta decimales para que
    # el valor siempre quepa en el ancho disponible sin truncar dígitos.
    if campo in COLS_MONETARIO and s:
        s = fmt_monetario(s, ancho)

    return formatear_bytes(s, ancho, alineacion, campo)


def fila_a_linea(fila):
    resultado = bytearray(b' ' * ANCHO_LINEA)
    for ini, fin, campo, alin in LAYOUT:
        ancho = fin - ini
        if campo == '_sep_':
            resultado[ini] = ord(' ')
            continue
        valor = fila.get(campo, '')
        segmento = formatear_valor(valor, ancho, alin, campo)
        seg_bytes = segmento.encode(ENC, errors='replace')[:ancho]
        resultado[ini:ini + len(seg_bytes)] = seg_bytes
    return resultado.decode(ENC, errors='replace')


def main(csv_path, output_path=None):
    if output_path is None:
        base = os.path.splitext(csv_path)[0]
        output_path = base + '_sia.txt'

    df = pd.read_csv(csv_path, header=None, encoding='latin1', dtype=str)
    df.columns = COLUMNAS[:len(df.columns)]

    errores_cuil = []
    lineas = []

    for idx, fila in df.iterrows():
        cuil = str(fila.get('cuil', '')).strip()

        if not validar_cuil(cuil):
            errores_cuil.append((idx + 1, cuil, str(fila.get('apeynom', '')).strip()))
            continue

        fila = recalcular(fila)
        lineas.append(fila_a_linea(fila))

    with open(output_path, 'w', encoding=ENC, newline='\r\n') as f:
        f.write('\n'.join(lineas))

    # Verificar longitudes
    with open(output_path, 'rb') as f:
        raw_lineas = f.read().split(b'\r\n')
    incorrectas = [(i+1, len(l)) for i, l in enumerate(raw_lineas) if l and len(l) != ANCHO_LINEA]

    print(f"Archivo generado : {output_path}")
    print(f"Encoding         : ANSI (latin1) con CRLF")
    print(f"Registros        : {len(lineas)}")
    if incorrectas:
        print(f"ADVERTENCIA - Lineas con longitud incorrecta: {len(incorrectas)}")
        for num, largo in incorrectas:
            print(f"  Linea {num}: {largo} bytes")
    else:
        print(f"Longitud         : {ANCHO_LINEA} bytes por linea ✓")

    if errores_cuil:
        print(f"\nADVERTENCIA - CUILes invalidos: {len(errores_cuil)}")
        print(f"  {'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}")
        print(f"  {'-'*6} {'-'*13} {'-'*35}")
        for fila_num, cuil, nombre in errores_cuil:
            print(f"  {fila_num:<6} {cuil:<13} {nombre}")
        log_path = os.path.splitext(output_path)[0] + '_errores_cuil.txt'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"CUILes invalidos - {os.path.basename(csv_path)}\n")
            f.write(f"{'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}\n")
            f.write(f"{'-'*6} {'-'*13} {'-'*35}\n")
            for fila_num, cuil, nombre in errores_cuil:
                f.write(f"{fila_num:<6} {cuil:<13} {nombre}\n")
        print(f"  Log guardado en: {log_path}")
    else:
        print(f"CUILes           : todos validos ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python csv_to_sia.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    csv_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    main(csv_path, output_path)
