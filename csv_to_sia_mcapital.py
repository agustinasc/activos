"""
csv_to_txt_mcapital_v2.py - Municipal Capital
Genera archivo SIA de 524 bytes por línea, encoding latin1, CRLF.

Lógica de recálculo:
  - remuimpo   = int(remusueldo + remusac + hsextras)  -> fmt_ancho
  - remutotal  = int(remuimpo) + int(conceptono) + int(premios) + int(vacaciones) + int(canasta_fl)
                 -> fmt_ancho (2 dec si entra en 9 chars, 1 dec si no)
  - remuimpoos = round(csv_remutotal_original, 1)  -> 1 decimal
  - aportes (aportejubi, aportepatr, apafilos, appatros) -> del CSV, lstrip ceros
  - periodo: se deja tal cual AAAAMM (no se convierte)

Campos numéricos:
  - COLS_TRUNCAR_ENTERO : se trunca a int y se formatea con fmt_ancho
  - COLS_LSTRIP_NUM     : se limpian ceros iniciales, se conservan decimales
  - COLS_LSTRIP_INT     : se convierten a int (lstrip)
  - COLS_INT_VALUE      : porceadi, adherente -> int simple
"""

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

ENC = 'latin1'
ANCHO_LINEA = 524

COLS_INT_VALUE    = {'porceadi', 'adherente'}
COLS_DECIMAL      = {'dias_traba', 'cos_alt', 'cos_int'}
COLS_DEFAULT_CERO = {'ap_dcto788'}

# Campos que se truncan a entero y luego se formatean con fmt_ancho
COLS_TRUNCAR_ENTERO = {
    'remuimpo', 'remusueldo', 'remusac', 'hsextras',
    'conceptono', 'premios', 'vacaciones', 'canasta_fl',
    'aportvolun', 'exessocial', 'exeosocial', 'impoadicos', 'asigfliar',
    'remu_doc',
}

# Campos cuyo valor numérico se escribe con decimales limpios (sin ceros iniciales)
COLS_LSTRIP_NUM = {
    'aportejubi', 'aportepatr', 'apafilos', 'appatros',
    'aporte_caj', 'contrib_ca', 'deuda_caja', 'trasp_osep',
    'apo_vol', 'tras_vol', 'rem_retiro', 'remuimpoto',
    'coseguro', 'd_svco', 'd_ss', 'd_svca', 'd_sc',
    'ap_dcto788', 'aporte_dif',
    'cos_pro', 'cos_alt', 'cos_int',
}

# Campos enteros que solo necesitan lstrip
COLS_LSTRIP_INT = {
    'nroagente', 'codigo', 'saf', 'cant_hsext', 'por_retiro',
    'canthijo', 'rebpromo', 'porcreduc', 'conyuge',
}

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
    # SIA Capital termina aquí (524 bytes)
    # sin cos_pro, cos_alt, cos_int, claseycar
]


def fmt_ancho(v_int, ancho):
    """Formatea un entero: 2 dec si entra en `ancho` chars, 1 dec si no."""
    s2 = f"{v_int:.2f}"
    if len(s2) <= ancho:
        return s2
    return f"{v_int:.1f}"


def lstrip_num(s):
    """Elimina ceros iniciales de un número decimal."""
    s = str(s).strip()
    if not s or s == '0':
        return s
    if '.' in s:
        entero, decimal = s.split('.', 1)
        entero = entero.lstrip('0') or '0'
        return f"{entero}.{decimal}"
    return s.lstrip('0') or '0'


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


def recalcular(fila):
    fila = fila.copy()

    # Guardar remutotal del CSV ANTES de cualquier modificación (para remuimpoos)
    remutotal_csv_orig = fv(fila, 'remutotal')

    # Truncar componentes a entero
    remuimpo_int   = int(fv(fila, 'remusueldo') + fv(fila, 'remusac') + fv(fila, 'hsextras'))
    conceptono_int = int(fv(fila, 'conceptono'))
    premios_int    = int(fv(fila, 'premios'))
    vacaciones_int = int(fv(fila, 'vacaciones'))
    canasta_int    = int(fv(fila, 'canasta_fl'))

    # remuimpo = suma de sueldos truncada a entero
    fila['remuimpo'] = fmt_ancho(remuimpo_int, 9)

    # remutotal = suma de todos los enteros
    remutotal_calc = remuimpo_int + conceptono_int + premios_int + vacaciones_int + canasta_int
    fila['remutotal'] = fmt_ancho(remutotal_calc, 9)

    # remuimpoos = round(csv_remutotal_original, 1) con 1 decimal fijo
    if remutotal_csv_orig == 0.0:
        fila['remuimpoos'] = '0.00'
    else:
        fila['remuimpoos'] = f"{round(remutotal_csv_orig, 1):.1f}"

    # periodo: convertir de AAAAMM a MMAAAA
    periodo = str(fila.get('periodo', '')).strip()
    if len(periodo) == 6 and periodo.isdigit() and 1900 <= int(periodo[:4]) <= 2099:
        fila['periodo'] = periodo[4:6] + periodo[0:4]

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

    # Campos que se truncan a entero y luego se formatean con fmt_ancho
    if campo in COLS_TRUNCAR_ENTERO and s:
        try:
            v_int = int(float(s))
            s = fmt_ancho(v_int, ancho)
        except (ValueError, TypeError):
            pass

    # Campos numéricos con decimales: solo lstrip de ceros iniciales
    elif campo in COLS_LSTRIP_NUM and s:
        s = lstrip_num(s)

    # Campos enteros simples: convertir a int (elimina ceros iniciales)
    elif campo in COLS_LSTRIP_INT and s:
        try:
            s = str(int(float(s)))
        except (ValueError, TypeError):
            s = s.lstrip('0') or '0'

    # Campos forzados a 2 decimales explícitos
    if campo in COLS_DECIMAL and s:
        try:
            s = f"{float(s):.2f}"
        except ValueError:
            pass

    # Campos que se escriben como entero puro (sin decimales)
    if campo in COLS_INT_VALUE and s:
        try:
            s = str(int(float(s)))
        except (ValueError, TypeError):
            pass

    return formatear_bytes(s, ancho, alineacion)


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
        for num, largo in incorrectas[:5]:
            print(f"  Linea {num}: {largo} bytes")
    else:
        print(f"Longitud         : {ANCHO_LINEA} bytes por linea ✓")

    if errores_cuil:
        print(f"\nADVERTENCIA - CUILes invalidos: {len(errores_cuil)}")
        for fn, c, n in errores_cuil[:5]:
            print(f"  Fila {fn}: {c} {n}")
        log_path = os.path.splitext(output_path)[0] + '_errores_cuil.txt'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"CUILes invalidos - {os.path.basename(csv_path)}\n")
            for fn, c, n in errores_cuil:
                f.write(f"{fn:<6} {c:<13} {n}\n")
        print(f"  Log: {log_path}")
    else:
        print(f"CUILes           : todos validos ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python csv_to_txt_mcapital_v2.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
