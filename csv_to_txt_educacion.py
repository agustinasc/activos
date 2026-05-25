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

TOPE_ANSES = 4162912.57
ENC = 'latin1'

COLS_INT_VALUE    = {'porceadi', 'adherente'}
COLS_DECIMAL      = {'dias_traba', 'cos_alt', 'cos_int', 'apafilos', 'appatros', 'aportejubi'}
COLS_DEFAULT_CERO = {'ap_dcto788'}

# Solo estos 4 campos necesitan ajuste de decimales para caber en 9 chars
COLS_NUMERICO_ANCHO = {'remutotal', 'remuimpo', 'remuimpoos', 'remusueldo', 'remusac', 'hsextras'}

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
    (524, 533, 'cos_pro',    'r'),
    (533, 542, 'cos_alt',    'r'),
    (542, 551, 'cos_int',    'r'),
    (551, 555, 'claseycar',  'r'),
]


def formatear_numerico_ancho(valor_str, ancho):
    """Formatea número respetando el CSV:
    - Si el CSV trae entero -> escribir como entero
    - Si tiene decimales -> 2 dec si entra, si no truncar a 1 dec"""
    try:
        v = float(valor_str)
    except (ValueError, TypeError):
        return valor_str
    s_orig = str(valor_str).strip()
    # Si el CSV trae valor entero (sin dec o terminado en .0), escribir como entero
    if '.' not in s_orig or s_orig.endswith('.0'):
        return str(int(v))
    # Tiene decimales -> intentar 2 decimales
    s2 = f"{v:.2f}"
    if len(s2) <= ancho:
        return s2
    # Truncar a 1 decimal (sin redondear)
    s1 = f"{int(v * 10) / 10:.1f}"
    if len(s1) <= ancho:
        return s1
    return str(int(v))


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
    if resto == 0:   verificador = 0
    elif resto == 1: verificador = 9
    else:            verificador = 11 - resto
    return digitos[10] == verificador


def fv(fila, campo):
    v = fila.get(campo, '')
    try:
        return float(str(v).strip()) if pd.notna(v) and str(v).strip() not in ('', 'nan') else 0.0
    except ValueError:
        return 0.0


def recalcular(fila):
    """Para educacion: trunca componentes consistentemente para que la suma sea exacta."""
    fila = fila.copy()

    def fv(campo):
        v = fila.get(campo, '')
        try:
            return float(str(v).strip()) if pd.notna(v) and str(v).strip() not in ('', 'nan') else 0.0
        except ValueError:
            return 0.0

    def fmt(v, ancho=9):
        s2 = f"{v:.2f}"
        if len(s2) <= ancho: return s2
        return f"{int(v * 10) / 10:.1f}"

    def trunc1(v):
        return f"{int(v * 10) / 10:.1f}"

    rs_csv = fv('remusueldo')
    rc_csv = fv('remusac')
    hx_csv = fv('hsextras')
    suma_csv = rs_csv + rc_csv + hx_csv

    # Si algún componente o la suma no entra con 2 decimales, truncar todos a 1 decimal
    necesita_trunc = (
        len(f"{suma_csv:.2f}") > 9 or
        any(len(f"{v:.2f}") > 9 for v in [rs_csv, rc_csv, hx_csv] if v != 0.0)
    )

    if necesita_trunc:
        rs_fmt = trunc1(rs_csv)
        rc_fmt = trunc1(rc_csv)
        hx_fmt = trunc1(hx_csv)
    else:
        rs_fmt = fmt(rs_csv)
        rc_fmt = fmt(rc_csv)
        hx_fmt = fmt(hx_csv)

    fila['remusueldo'] = rs_fmt
    fila['remusac']    = rc_fmt
    fila['hsextras']   = hx_fmt

    remuimpo = round(float(rs_fmt) + float(rc_fmt) + float(hx_fmt), 2 if not necesita_trunc else 1)
    fila['remuimpo'] = fmt(remuimpo)

    co = fv('conceptono')
    pr = fv('premios')
    va = fv('vacaciones')
    ca = fv('canasta_fl')
    remutotal = round(remuimpo + co + pr + va + ca, 2)
    fila['remutotal']  = fmt(remutotal)
    fila['remuimpoos'] = fmt(remutotal)

    return fila


def formatear_bytes(s, ancho, alineacion):
    encoded = s.encode(ENC, errors='replace')
    if len(encoded) >= ancho:
        encoded = encoded[:ancho]
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

    # Campos numéricos con lógica "caber en el ancho"
    if campo in COLS_NUMERICO_ANCHO and s:
        s = formatear_numerico_ancho(s, ancho)

    # Campos forzados a 2 decimales (aportejubi, apafilos, appatros, dias_traba)
    if campo in COLS_DECIMAL and s:
        try:
            s = f"{float(s):.2f}"
        except ValueError:
            pass

    if campo in COLS_INT_VALUE and s:
        try:
            s = str(int(s))
        except ValueError:
            pass

    return formatear_bytes(s, ancho, alineacion)


def fila_a_linea(fila):
    resultado = bytearray(b' ' * 555)
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
        output_path = base + '_salida.txt'

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

    with open(output_path, 'rb') as f:
        raw_lineas = f.read().split(b'\r\n')
    incorrectas = [(i+1, len(l)) for i, l in enumerate(raw_lineas) if l and len(l) != 555]

    print(f"Archivo generado : {output_path}")
    print(f"Encoding         : ANSI (latin1) con CRLF")
    print(f"Registros        : {len(lineas)}")
    if incorrectas:
        print(f"ADVERTENCIA - Lineas con longitud incorrecta: {len(incorrectas)}")
        for num, largo in incorrectas:
            print(f"  Linea {num}: {largo} bytes")
    else:
        print(f"Longitud         : 555 bytes por linea ✓")

    if errores_cuil:
        print(f"\nADVERTENCIA - CUILes invalidos: {len(errores_cuil)}")
        print(f"  {'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}")
        print(f"  {'-'*6} {'-'*13} {'-'*35}")
        for fila_num, cuil, nombre in errores_cuil:
            print(f"  {fila_num:<6} {cuil:<13} {nombre}")
        log_path = os.path.splitext(output_path)[0] + '_errores_cuil.txt'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"CUILes invalidos - {os.path.basename(csv_path)}\n")
            for fila_num, cuil, nombre in errores_cuil:
                f.write(f"{fila_num:<6} {cuil:<13} {nombre}\n")
        print(f"  Log guardado en: {log_path}")
    else:
        print(f"CUILes           : todos validos ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python csv_to_txt_educacion.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
