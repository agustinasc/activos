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

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT GUARDIAS SIA (169 bytes por línea, terminador CRLF)
# Mapeado por ingeniería inversa sobre guardias_sia.txt (periodo 202602).
#
# [0:12]   ubicacion         — campo ubicacion completo (12 chars)
# [12:18]  saf_field         — str(saf).zfill(2) + '0.00'  e.g. saf=56 → '560.00'
# [18:26]  nroagente         — 8 chars, zero-padded izq.
# [26:37]  cuil              — 11 chars
# [37:80]  apeynom           — 43 chars, ljust, space-padded
# [80:82]  prefix            — '  ' (2 espacios)
# [82:91]  remutotal_cents   — round(remutotal * 100), 9 chars, zero-padded
# [91:137] zeros             — 46 chars de ceros (campos reservados)
# [137:146] aporte_caj_cents — round(aporte_caj * 100), 9 chars, zero-padded
# [146:155] contrib_ca_cents — round(contrib_ca * 100), 9 chars, zero-padded
# [155:163] zeros            — 8 chars de ceros
# [163:169] periodo          — AAAAMM (6 chars)
# ─────────────────────────────────────────────────────────────────────────────


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
    if resto == 0:
        verificador = 0
    elif resto == 1:
        verificador = 9
    else:
        verificador = 11 - resto
    return digitos[10] == verificador


def fmt_r(valor_int, ancho):
    """Entero zero-padded a la izquierda, truncado por la derecha si excede."""
    s = str(int(valor_int)).zfill(ancho)
    return s[-ancho:]


def fmt_str_l(valor, ancho):
    """String left-justified, space-padded, truncado a ancho bytes latin1."""
    s = fix_encoding(str(valor).strip()) if pd.notna(valor) else ''
    encoded = s.encode(ENC, errors='replace')
    if len(encoded) >= ancho:
        return encoded[:ancho].decode(ENC, errors='replace')
    return encoded.decode(ENC, errors='replace') + ' ' * (ancho - len(encoded))


def fila_a_linea(fila):
    # ── campos helper ─────────────────────────────────────────────────────────
    ubicacion  = str(fila.get('ubicacion', '') or '').strip()
    saf        = str(fila.get('saf', '0') or '0').strip()
    nroagente  = str(fila.get('nroagente', '0') or '0').strip()
    cuil       = str(fila.get('cuil', '')).strip()
    apeynom    = fila.get('apeynom', '')
    periodo    = str(fila.get('periodo', '')).strip()

    remutotal  = fv(fila, 'remutotal')
    aporte_caj = fv(fila, 'aporte_caj')
    contrib_ca = fv(fila, 'contrib_ca')

    # ── [0:12] ubicacion (12 chars) ───────────────────────────────────────────
    ubic12 = ubicacion[:12].ljust(12, '0') if ubicacion else '0' * 12

    # ── [12:18] saf field: str(saf).zfill(2) + '0.00' ────────────────────────
    try:
        saf_int = int(float(saf))
    except (ValueError, TypeError):
        saf_int = 0
    saf_field = str(saf_int).zfill(2) + '0.00'
    saf_field = saf_field[:6]

    # ── [18:26] nroagente (8 chars) ───────────────────────────────────────────
    try:
        nro_int = int(float(nroagente))
    except (ValueError, TypeError):
        nro_int = 0
    nro_field = str(nro_int).zfill(8)[-8:]

    # ── [37:80] apeynom (43 chars, left) ──────────────────────────────────────
    apeynom_field = fmt_str_l(apeynom, 43)

    # ── [82:91] remutotal centavos (9 chars) ─────────────────────────────────
    remu_cents = fmt_r(round(remutotal * 100), 9)

    # ── [137:146] aporte_caj centavos (9 chars) ───────────────────────────────
    ac_cents = fmt_r(round(aporte_caj * 100), 9)

    # ── [146:155] contrib_ca centavos (9 chars) ───────────────────────────────
    cc_cents = fmt_r(round(contrib_ca * 100), 9)

    # ── armar línea ───────────────────────────────────────────────────────────
    linea = (
        ubic12          +   # [0:12]
        saf_field       +   # [12:18]
        nro_field       +   # [18:26]
        cuil            +   # [26:37]
        apeynom_field   +   # [37:80]
        '  '            +   # [80:82]
        remu_cents      +   # [82:91]
        '0' * 46        +   # [91:137]
        ac_cents        +   # [137:146]
        cc_cents        +   # [146:155]
        '0' * 8         +   # [155:163]
        periodo             # [163:169]
    )

    assert len(linea) == ANCHO_LINEA, f'Longitud incorrecta: {len(linea)} (esperado {ANCHO_LINEA})'
    return linea


def main(csv_path, output_path=None):
    if output_path is None:
        base = os.path.splitext(csv_path)[0]
        output_path = base + '_guardias_sia.txt'

    # CSV sin encabezado
    df = pd.read_csv(csv_path, header=None, encoding='utf-8', dtype=str)
    df.columns = COLUMNAS[:len(df.columns)]

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

    # Verificar longitudes
    with open(output_path, 'rb') as f:
        raw = f.read().split(b'\r\n')
    incorrectas = [(i + 1, len(l)) for i, l in enumerate(raw) if l and len(l) != ANCHO_LINEA]

    print(f"Archivo generado : {output_path}")
    print(f"Encoding         : ANSI (latin1) con CRLF")
    print(f"Registros        : {len(lineas)}")
    if incorrectas:
        print(f"ADVERTENCIA - Líneas con longitud incorrecta: {len(incorrectas)}")
        for num, largo in incorrectas:
            print(f"  Línea {num}: {largo} bytes")
    else:
        print(f"Longitud         : {ANCHO_LINEA} bytes por línea ✓")

    if errores_cuil:
        print(f"\nADVERTENCIA - CUILes inválidos: {len(errores_cuil)}")
        print(f"  {'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}")
        print(f"  {'-'*6} {'-'*13} {'-'*35}")
        for fila_num, cuil, nombre in errores_cuil:
            print(f"  {fila_num:<6} {cuil:<13} {nombre}")
        log_path = os.path.splitext(output_path)[0] + '_errores_cuil.txt'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"CUILes inválidos - {os.path.basename(csv_path)}\n")
            f.write(f"{'Fila':<6} {'CUIL':<13} {'Apellido y Nombre'}\n")
            f.write(f"{'-'*6} {'-'*13} {'-'*35}\n")
            for fila_num, cuil, nombre in errores_cuil:
                f.write(f"{fila_num:<6} {cuil:<13} {nombre}\n")
        print(f"  Log guardado en: {log_path}")
    else:
        print(f"CUILes           : todos válidos ✓")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python csv_to_guardias_sia.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    csv_path    = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    main(csv_path, output_path)
