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

ENC = 'latin1'  # Encoding del TXT de salida

COLS_INT_VALUE    = {'porceadi', 'adherente'}
COLS_DECIMAL      = {'dias_traba', 'cos_alt', 'cos_int'}
COLS_DEFAULT_CERO = {'ap_dcto788'}

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


# ---------------------------------------------------------------------------
# Corrección de doble encoding (UTF-8 leído como latin1)
# ---------------------------------------------------------------------------
def fix_encoding(s):
    """Corrige strings con doble encoding: UTF-8 bytes interpretados como latin1.
    Si el string contiene caracteres fuera del rango latin-1 (ej: \ufffd),
    los elimina para evitar errores al codificar."""
    # Primero intentar corregir doble encoding
    try:
        s = s.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    # Eliminar cualquier carácter que no pueda codificarse en latin-1
    return s.encode('latin1', errors='ignore').decode('latin1')


# ---------------------------------------------------------------------------
# Validación de CUIL
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Recálculo de campos derivados
# ---------------------------------------------------------------------------
def fv(fila, campo):
    v = fila.get(campo, '')
    try:
        return float(str(v).strip()) if pd.notna(v) and str(v).strip() not in ('', 'nan') else 0.0
    except ValueError:
        return 0.0


from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


def fmt_campo(v, ancho=9):
    """Formatea un número al ancho del campo truncando decimales si no entra."""
    v = Decimal(str(v))
    s = str(v.quantize(Decimal('0.01'), rounding=ROUND_DOWN))
    if len(s) <= ancho: return s
    for q in ('0.1', '1'):
        s = str(v.quantize(Decimal(q), rounding=ROUND_DOWN))
        if len(s) <= ancho: return s
    return str(int(v.quantize(Decimal('1'), rounding=ROUND_DOWN)))


def nivel_precision(v, ancho=9):
    """Nivel de precisión mínimo para que v entre en ancho chars."""
    v = Decimal(str(v))
    for q in ('0.01', '0.1', '1'):
        if len(str(v.quantize(Decimal(q), rounding=ROUND_DOWN))) <= ancho:
            return q
    return '1'


def recalcular(fila):
    """Recalcula remuimpo y remutotal garantizando que la suma de los valores
    escritos en el TXT coincida exactamente con el total.
    Aplica el mismo nivel de precisión a todos los componentes — el más
    restrictivo entre los que no entran con 2 decimales — de modo que
    tanto los sumandos como el total sean coherentes."""
    fila = fila.copy()

    rs  = Decimal(str(fv(fila, 'remusueldo')))
    rc  = Decimal(str(fv(fila, 'remusac')))
    hx  = Decimal(str(fv(fila, 'hsextras')))
    con = Decimal(str(fv(fila, 'conceptono')))
    prem= Decimal(str(fv(fila, 'premios')))
    vac = Decimal(str(fv(fila, 'vacaciones')))
    can = Decimal(str(fv(fila, 'canasta_fl')))

    niveles = ['0.01', '0.1']

    # Buscar el nivel de precisión donde todos los sumandos Y la suma entran.
    # Siempre ROUND_DOWN (truncamiento) para no inflar valores.
    for nivel in niveles:
        q = Decimal(nivel)
        rs_t   = rs.quantize(q,   rounding=ROUND_DOWN)
        rc_t   = rc.quantize(q,   rounding=ROUND_DOWN)
        hx_t   = hx.quantize(q,   rounding=ROUND_DOWN)
        con_t  = con.quantize(q,  rounding=ROUND_DOWN)
        prem_t = prem.quantize(q, rounding=ROUND_DOWN)
        vac_t  = vac.quantize(q,  rounding=ROUND_DOWN)
        can_t  = can.quantize(q,  rounding=ROUND_DOWN)

        rs_fmt   = fmt_campo(rs_t);   rc_fmt  = fmt_campo(rc_t)
        hx_fmt   = fmt_campo(hx_t);   con_fmt = fmt_campo(con_t)
        prem_fmt = fmt_campo(prem_t); vac_fmt = fmt_campo(vac_t)
        can_fmt  = fmt_campo(can_t)

        ri = Decimal(rs_fmt) + Decimal(rc_fmt) + Decimal(hx_fmt)
        ri_fmt = fmt_campo(ri)
        rt = (Decimal(ri_fmt) + Decimal(con_fmt) + Decimal(prem_fmt)
              + Decimal(vac_fmt) + Decimal(can_fmt))
        rt_str = fmt_campo(rt)

        # Verificar que la suma de los campos escritos == total escrito
        if Decimal(rt_str) == rt:
            fila['remusueldo'] = rs_fmt;  fila['remusac']    = rc_fmt
            fila['hsextras']   = hx_fmt;  fila['conceptono'] = con_fmt
            fila['premios']    = prem_fmt; fila['vacaciones'] = vac_fmt
            fila['canasta_fl'] = can_fmt;  fila['remuimpo']   = ri_fmt
            fila['remutotal']  = rt_str;   fila['remuimpoos'] = rt_str
            break

    # Aportes sobre remuimpo original (mayor precisión)
    remuimpo_float = float(rs + rc + hx)
    if remuimpo_float <= TOPE_ANSES:
        aportejubi = round(remuimpo_float * 0.11, 2)
    else:
        aportejubi = round(TOPE_ANSES * 0.11 + (remuimpo_float - TOPE_ANSES) * 0.1017, 2)
    fila['aportejubi'] = f"{aportejubi:.2f}"

    rt_float = float(rt)
    fila['apafilos'] = f"{round(rt_float * 0.045, 2):.2f}"
    fila['appatros'] = f"{round(rt_float * 0.09,  2):.2f}"

    return fila


# ---------------------------------------------------------------------------
# Formateo con ancho exacto en bytes UTF-8
# ---------------------------------------------------------------------------
_overflow_log = []   # (cuil, campo, valor, ancho_maximo)
_cuil_actual  = [None]


def formatear_bytes(s, ancho, alineacion, campo=''):
    """Devuelve exactamente `ancho` bytes en latin1, justificado según alineacion.
    Si el valor excede el ancho, registra una advertencia en _overflow_log."""
    encoded = s.encode(ENC)
    if len(encoded) > ancho:
        _overflow_log.append((_cuil_actual[0], campo, s, ancho))
        truncado = encoded[:ancho]
        while True:
            try:
                truncado.decode(ENC)
                break
            except UnicodeDecodeError:
                truncado = truncado[:-1]
        padding = b' ' * (ancho - len(truncado))
        if alineacion == 'r':
            return (padding + truncado).decode(ENC)
        else:
            return (truncado + padding).decode(ENC)
    padding = b' ' * (ancho - len(encoded))
    if alineacion == 'r':
        return (padding + encoded).decode(ENC)
    else:
        return (encoded + padding).decode(ENC)


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
            s = str(int(s))
        except ValueError:
            pass

    return formatear_bytes(s, ancho, alineacion, campo)


def fila_a_linea(fila):
    resultado = bytearray(b' ' * 555)
    for ini, fin, campo, alin in LAYOUT:
        ancho = fin - ini
        if campo == '_sep_':
            resultado[ini] = ord(' ')
            continue
        valor = fila.get(campo, '')
        segmento = formatear_valor(valor, ancho, alin, campo)
        seg_bytes = segmento.encode(ENC)[:ancho]
        resultado[ini:ini + len(seg_bytes)] = seg_bytes
    return resultado.decode(ENC)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
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
        _cuil_actual[0] = cuil  # para el log de overflow

        if not validar_cuil(cuil):
            errores_cuil.append((idx + 1, cuil, str(fila.get('apeynom', '')).strip()))
            continue

        fila = recalcular(fila)
        lineas.append(fila_a_linea(fila))

    # Escribir con CRLF y UTF-8, sin BOM
    with open(output_path, 'w', encoding='latin1', newline='\r\n') as f:
        f.write('\n'.join(lineas))

    # Verificar longitudes
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

    if _overflow_log:
        print(f"\nADVERTENCIA - Valores truncados por exceder el ancho del campo: {len(_overflow_log)}")
        print(f"  {'CUIL':<13} {'Campo':<12} {'Valor':<15} {'Ancho max'}")
        print(f"  {'-'*13} {'-'*12} {'-'*15} {'-'*9}")
        for cuil_ov, campo_ov, valor_ov, ancho_ov in _overflow_log:
            print(f"  {cuil_ov:<13} {campo_ov:<12} {valor_ov:<15} {ancho_ov}")
        log_path2 = os.path.splitext(output_path)[0] + '_overflow.txt'
        with open(log_path2, 'w', encoding='utf-8') as f:
            f.write(f"Valores truncados - {os.path.basename(csv_path)}\n")
            f.write(f"{'CUIL':<13} {'Campo':<12} {'Valor':<15} {'Ancho max'}\n")
            f.write(f"{'-'*13} {'-'*12} {'-'*15} {'-'*9}\n")
            for cuil_ov, campo_ov, valor_ov, ancho_ov in _overflow_log:
                f.write(f"{cuil_ov:<13} {campo_ov:<12} {valor_ov:<15} {ancho_ov}\n")
        print(f"  Log guardado en: {log_path2}")
    else:
        print(f"Overflow         : ninguno ✓")

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
        print("Uso: python csv_to_txt.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    csv_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    main(csv_path, output_path)
