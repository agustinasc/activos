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

ENC        = 'latin1'
ANCHO_LINEA = 222

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT COMPLETA SIA (222 bytes por línea, terminador CRLF)
# Mapeado por ingeniería inversa sobre completa_sia.txt (periodo 202603).
#
# [0:6]    ubicacion[0:6]        — prefijo de ubicacion/claseycar (6 chars)
# [6:12]   familia_cnt           — contador beneficiarios (6 chars, cero si no aplica)
# [12:18]  saf_field             — str(saf) + '0.00'  e.g. saf=11 → '110.00'
# [18:26]  nroagente             — 8 chars, zero-padded izq.
# [26:37]  cuil                  — 11 chars
# [37:117] apeynom               — 80 chars, ljust, space-padded
# [117:126] remutotal_pesos      — int(remutotal), 9 chars, zero-padded
# [126:135] remutotal_cents      — centavos de remutotal, 2 dígitos ljust + 7 ceros
#                                  e.g. 823132.29 → cents=29 → '290000000'
#                                       1867200.00 → cents=0  → '000000000'
# [135:185] zeros                — 50 chars de ceros (campos reservados)
# [185:194] aporte_caj_cents     — round(aporte_caj*100), 9 chars, zero-padded
# [194:196] separador            — '00'
# [196:205] contrib_ca_cents     — round(contrib_ca*100), 9 chars, zero-padded
# [205:216] deuda_cents          — deuda_caja*100 si tiene_deud es verdadero,
#                                  caso contrario 11 ceros (sin deuda)
# [216:222] periodo              — AAAAMM (6 chars)
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


def es_verdadero(valor):
    """Interpreta el campo tiene_deud como booleano."""
    s = str(valor).strip().lower()
    return s in ('t', 'true', 'verdadero', 'si', 'sí', 's', '1', '1.0', 'x')


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


def normalizar_periodo(periodo):
    """Devuelve AAAAMM tal como viene en el CSV (sin convertir)."""
    return str(periodo).strip()


def fmt_r(valor, ancho):
    """Entero zero-padded a la izquierda, truncado si excede."""
    s = str(int(valor)).zfill(ancho)
    return s[-ancho:]


def fmt_cents_ljust(valor_float, ancho=9):
    """
    Almacena la parte decimal de un importe como dígitos ljust con ceros.
    e.g. 823132.29 → cents=29 → '290000000'
         1867200.00 → cents=0  → '000000000'
    """
    cents = round((valor_float % 1) * 100)
    if cents == 0:
        return '0' * ancho
    s = str(cents).ljust(ancho, '0')
    return s[:ancho]


def fmt_str_l(valor, ancho):
    """String left-justified, space-padded, truncado a ancho bytes latin1."""
    s = fix_encoding(str(valor).strip()) if pd.notna(valor) else ''
    encoded = s.encode(ENC, errors='replace')
    if len(encoded) >= ancho:
        return encoded[:ancho].decode(ENC, errors='replace')
    return encoded.decode(ENC, errors='replace') + ' ' * (ancho - len(encoded))


def fila_a_linea(fila):
    # ── campos helper ────────────────────────────────────────────────────────
    ubicacion  = str(fila.get('ubicacion', '') or '').strip()
    saf        = str(fila.get('saf', '0') or '0').strip()
    nroagente  = str(fila.get('nroagente', '0') or '0').strip()
    cuil       = str(fila.get('cuil', '')).strip()
    apeynom    = fila.get('apeynom', '')
    periodo    = normalizar_periodo(fila.get('periodo', ''))

    remutotal  = fv(fila, 'remutotal')
    aporte_caj = fv(fila, 'aporte_caj')
    contrib_ca = fv(fila, 'contrib_ca')

    # ── [0:6] ubicacion prefix ───────────────────────────────────────────────
    ubic6 = ubicacion[:6].ljust(6, '0') if ubicacion else '0' * 6

    # ── [6:12] familia_cnt (generalmente 000000; se copia si viene en datos) ─
    familia_cnt = '000000'   # sin campo específico en CSV → siempre cero

    # ── [12:18] saf field: str(saf) + '0.00' ────────────────────────────────
    try:
        saf_int = int(float(saf))
    except (ValueError, TypeError):
        saf_int = 0
    saf_field = str(saf_int).zfill(2) + '0.00'
    saf_field = saf_field[:6].ljust(6, '0')   # asegurar exactamente 6 chars

    # ── [18:26] nroagente (8 chars) ─────────────────────────────────────────
    try:
        nro_int = int(float(nroagente))
    except (ValueError, TypeError):
        nro_int = 0
    nro_field = str(nro_int).zfill(8)[-8:]

    # ── [37:117] apeynom (80 chars, left) ───────────────────────────────────
    apeynom_field = fmt_str_l(apeynom, 80)

    # ── [117:126] remutotal pesos (9 chars) ─────────────────────────────────
    remu_pesos = fmt_r(int(remutotal), 9)

    # ── [126:135] remutotal centavos ljust (9 chars) ─────────────────────────
    remu_cents = fmt_cents_ljust(remutotal, 9)

    # ── [185:194] aporte_caj centavos (9 chars) ─────────────────────────────
    ac_cents = fmt_r(round(aporte_caj * 100), 9)

    # ── [196:205] contrib_ca centavos (9 chars) ──────────────────────────────
    cc_cents = fmt_r(round(contrib_ca * 100), 9)

    # ── [205:216] deuda centavos (11 chars) ──────────────────────────────────
    # Solo se carga si tiene_deud es verdadero; en ese caso va deuda_caja.
    if es_verdadero(fila.get('tiene_deud', '')):
        deuda_caja  = fv(fila, 'deuda_caja')
        total_cents = fmt_r(round(deuda_caja * 100), 11)
    else:
        total_cents = '0' * 11

    # ── armar línea ──────────────────────────────────────────────────────────
    linea = (
        ubic6           +   # [0:6]
        familia_cnt     +   # [6:12]
        saf_field       +   # [12:18]
        nro_field       +   # [18:26]
        cuil            +   # [26:37]
        apeynom_field   +   # [37:117]
        remu_pesos      +   # [117:126]
        remu_cents      +   # [126:135]
        '0' * 50        +   # [135:185]
        ac_cents        +   # [185:194]
        '00'            +   # [194:196]
        cc_cents        +   # [196:205]
        total_cents     +   # [205:216]
        periodo             # [216:222]
    )

    assert len(linea) == ANCHO_LINEA, f'Longitud incorrecta: {len(linea)} (esperado {ANCHO_LINEA})'
    return linea


def main(csv_path, output_path=None):
    if output_path is None:
        base = os.path.splitext(csv_path)[0]
        output_path = base + '_completa_sia.txt'

    df = pd.read_csv(csv_path, header=None, encoding=ENC, dtype=str)
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
        print("Uso: python csv_to_completa_sia.py <archivo.csv> [salida.txt]")
        sys.exit(1)
    csv_path   = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    main(csv_path, output_path)
