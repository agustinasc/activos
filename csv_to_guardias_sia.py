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

ENC         = 'latin1'
ANCHO_LINEA = 169

# Layout guardias SIA (169 bytes):
# [0:12]    ubicacion (12 chars)
# [12:18]   str(saf).zfill(2) + '0.00'
# [18:26]   nroagente (8 chars, zero-padded)
# [26:37]   cuil (11 chars)
# [37:80]   apeynom (43 chars, left-justified)
# [80:82]   '  ' (2 espacios)
# [82:91]   round(remutotal*100), 9 chars, zero-padded
# [91:137]  46 ceros
# [137:146] round(aporte_caj*1000), 9 chars, zero-padded
# [146:157] round(contrib_ca*100000), 11 chars, zero-padded
# [155:163] 8 ceros
# [163:169] periodo (AAAAMM)
# FILTRO: solo filas con ad_caja_co == 'T'

def fix_encoding(s):
    try:
        return s.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s

def fv(fila, campo):
    v = fila.get(campo, '')
    try:
        return float(str(v).strip()) if pd.notna(v) and str(v).strip() not in ('', 'nan') else 0.0
    except ValueError:
        return 0.0

def validar_cuil(cuil_str):
    cuil = str(cuil_str).strip().replace('-', '').replace(' ', '')
    if len(cuil) != 11 or not cuil.isdigit():
        return False
    serie = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digitos = [int(c) for c in cuil]
    suma = sum(d * s for d, s in zip(digitos[:10], serie))
    resto = suma % 11
    verificador = 0 if resto == 0 else (9 if resto == 1 else 11 - resto)
    return digitos[10] == verificador

def fmt_r(valor_int, ancho):
    return str(int(valor_int)).zfill(ancho)[-ancho:]

def fmt_str_l(valor, ancho):
    s = fix_encoding(str(valor).strip()) if pd.notna(valor) else ''
    encoded = s.encode(ENC, errors='replace')
    if len(encoded) >= ancho:
        return encoded[:ancho].decode(ENC, errors='replace')
    return encoded.decode(ENC, errors='replace') + ' ' * (ancho - len(encoded))

def fila_a_linea(fila):
    ubicacion  = str(fila.get('ubicacion', '') or '').strip()
    saf        = str(fila.get('saf', '0') or '0').strip()
    nroagente  = str(fila.get('nroagente', '0') or '0').strip()
    cuil       = str(fila.get('cuil', '')).strip()
    apeynom    = fila.get('apeynom', '')
    periodo    = str(fila.get('periodo', '')).strip()
    remutotal  = fv(fila, 'remutotal')
    aporte_caj = fv(fila, 'aporte_caj')
    contrib_ca = fv(fila, 'contrib_ca')

    ubic12    = ubicacion[:12].ljust(12, '0') if ubicacion else '0' * 12
    try:
        saf_int = int(float(saf))
    except (ValueError, TypeError):
        saf_int = 0
    saf_field = str(saf_int).zfill(2) + '0.00'
    try:
        nro_int = int(float(nroagente))
    except (ValueError, TypeError):
        nro_int = 0
    nro_field     = str(nro_int).zfill(8)[-8:]
    apeynom_field = fmt_str_l(apeynom, 43)
    remu_cents    = fmt_r(round(remutotal  * 100), 9)
    ac_cents      = fmt_r(round(aporte_caj * 1000), 9)
    cc_field      = fmt_r(round(contrib_ca * 100000), 11)

    linea = (ubic12 + saf_field + nro_field + cuil + apeynom_field +
             '  ' + remu_cents + '0'*46 + ac_cents + cc_field + '0'*6 + periodo)
    assert len(linea) == ANCHO_LINEA, f'Longitud incorrecta: {len(linea)}'
    return linea

def main(csv_path, output_path=None):
    if output_path is None:
        base = os.path.splitext(csv_path)[0]
        output_path = base + '_guardias_sia.txt'

    for enc in ('utf-8', 'latin1'):
        try:
            df = pd.read_csv(csv_path, header=None, encoding=enc, dtype=str)
            break
        except UnicodeDecodeError:
            continue

    df.columns = COLUMNAS[:len(df.columns)]

    total_original = len(df)
    if 'ad_caja_co' in df.columns:
        df = df[df['ad_caja_co'].str.strip() == 'T'].copy()
        excluidos_caja = total_original - len(df)
    else:
        excluidos_caja = 0

    errores_cuil = []
    lineas = []

    for idx, fila in df.iterrows():
        cuil = str(fila.get('cuil', '')).strip()
        if not validar_cuil(cuil):
            errores_cuil.append((idx + 1, cuil, str(fila.get('apeynom', '')).strip()))
            continue
        lineas.append(fila_a_linea(fila))

    with open(output_path, 'w', encoding=ENC, newline='\r\n') as f:
        f.write('\n'.join(lineas))

    with open(output_path, 'rb') as f:
        raw = f.read().split(b'\r\n')
    incorrectas = [(i+1, len(l)) for i, l in enumerate(raw) if l and len(l) != ANCHO_LINEA]

    print(f"Archivo generado : {output_path}")
    print(f"Encoding         : ANSI (latin1) con CRLF")
    print(f"Total en CSV     : {total_original}")
    if excluidos_caja:
        print(f"Excluidos (ad_caja_co=F): {excluidos_caja}")
    print(f"Registros        : {len(lineas)}")
    if incorrectas:
        print(f"ADVERTENCIA - Líneas con longitud incorrecta: {len(incorrectas)}")
        for num, largo in incorrectas:
            print(f"  Línea {num}: {largo} bytes")
    else:
        print(f"Longitud         : {ANCHO_LINEA} bytes por línea ✓")

    if errores_cuil:
        print(f"\nADVERTENCIA - CUILes inválidos omitidos: {len(errores_cuil)}")
        print(f"  {'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}")
        print(f"  {'-'*6} {'-'*13} {'-'*35}")
        for fila_num, cuil, nombre in errores_cuil:
            print(f"  {fila_num:<6} {cuil:<13} {nombre}")
        log_path = os.path.splitext(output_path)[0] + '_errores_cuil.txt'
        with open(log_path, 'w', encoding='utf-8') as lf:
            lf.write(f"CUILes inválidos - {os.path.basename(csv_path)}\n")
            lf.write(f"{'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}\n")
            lf.write(f"{'-'*6} {'-'*13} {'-'*35}\n")
            for fila_num, cuil, nombre in errores_cuil:
                lf.write(f"{fila_num:<6} {cuil:<13} {nombre}\n")
        print(f"  Log guardado en: {log_path}")
    else:
        print(f"CUILes           : todos válidos ✓")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python csv_to_guardias_sia.py <guardias_medicas.csv> [salida.txt]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
