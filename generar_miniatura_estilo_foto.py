import os
import subprocess
import sys

RESOLUCION_ANCHO = 1280
RESOLUCION_ALTO = 720
CARPETA_FUENTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes_hsf")
MARGEN_DERECHO = 25
FACTOR_ANCHO_CHAR = 0.56  # fuentes condensadas ocupan menos ancho por caracter


def _buscar_fuente_bold():
    """Busca primero una fuente condensada/black (mas impactante); si no
    hay, cae a una bold normal; si no hay nada, usa la primera disponible."""
    if not os.path.isdir(CARPETA_FUENTES):
        return None
    archivos = os.listdir(CARPETA_FUENTES)
    if not archivos:
        return None
    prioridades = ["black", "cond", "anton", "bebas", "impact", "bold"]
    for clave in prioridades:
        for nombre in archivos:
            if clave in nombre.lower():
                return os.path.join(CARPETA_FUENTES, nombre)
    return os.path.join(CARPETA_FUENTES, archivos[0])


def _envolver(texto, max_chars):
    palabras = texto.split()
    lineas, actual, largo = [], [], 0
    for palabra in palabras:
        if actual and largo + len(palabra) + 1 > max_chars:
            lineas.append(" ".join(actual))
            actual, largo = [], 0
        actual.append(palabra)
        largo += len(palabra) + 1
    if actual:
        lineas.append(" ".join(actual))
    return lineas


def _max_chars_para(fontsize, x_inicio):
    ancho_disponible = RESOLUCION_ANCHO - x_inicio - MARGEN_DERECHO
    max_chars = int(ancho_disponible / (fontsize * FACTOR_ANCHO_CHAR))
    return max(max_chars, 5)


def _armar_lineas_titulo(texto_titulo, x_titulo):
    """Prueba tamanos de letra de mayor a menor (partiendo de uno grande,
    estilo impactante) hasta que el titulo entra en maximo 5 lineas sin
    pasarse del ancho disponible."""
    candidatos = [
        (72, 76), (64, 68), (56, 60), (48, 52),
        (41, 45), (34, 38), (28, 32), (24, 28),
    ]
    for tamano, alto_linea in candidatos:
        max_chars = _max_chars_para(tamano, x_titulo)
        lineas = _envolver(texto_titulo, max_chars)
        if len(lineas) <= 5:
            return lineas[:5], tamano, alto_linea
    tamano, alto_linea = candidatos[-1]
    max_chars = _max_chars_para(tamano, x_titulo)
    return _envolver(texto_titulo, max_chars)[:5], tamano, alto_linea


def _escapar(texto):
    return texto.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def generar_miniatura_estilo_foto(titulo, subtitulo, ruta_fondo, ruta_logo, ruta_salida, logger=None):
    """Compone la miniatura final: foto de fondo (ya generada, sin texto) +
    logo HSF + titulo en blanco (ultima linea en amarillo) + cartel rojo con
    el subtitulo. Todo el texto lo dibuja ffmpeg (drawtext/drawbox), nunca
    una IA -- para que nunca salga mal escrito."""
    ruta_fuente = _buscar_fuente_bold()
    fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""

    x_titulo = 570

    texto_titulo = titulo.strip().upper()
    lineas, tamano_titulo, alto_linea = _armar_lineas_titulo(texto_titulo, x_titulo)

    y_titulo_inicio = 210 - max(0, len(lineas) - 3) * (alto_linea // 2)

    dibujo_titulo = []
    for i, linea in enumerate(lineas):
        color = "yellow" if i == len(lineas) - 1 else "white"
        y_pos = y_titulo_inicio + i * alto_linea
        dibujo_titulo.append(
            f"drawtext=text='{_escapar(linea)}'{fontfile}:fontcolor={color}:fontsize={tamano_titulo}:"
            f"borderw=3:bordercolor=black:x={x_titulo}:y={y_pos}"
        )

    texto_subtitulo = subtitulo.strip().upper()
    y_cartel = y_titulo_inicio + len(lineas) * alto_linea + 30
    tamano_subtitulo = 30
    ancho_max_cartel = RESOLUCION_ANCHO - x_titulo - MARGEN_DERECHO
    ancho_cartel = min(ancho_max_cartel, 220 + len(texto_subtitulo) * 15)
    alto_cartel = 60

    dibujo_cartel = (
        f"drawbox=x={x_titulo}:y={y_cartel}:w={ancho_cartel}:h={alto_cartel}:color=red@1.0:t=fill,"
        f"drawtext=text='{_escapar(texto_subtitulo)}'{fontfile}:fontcolor=white:fontsize={tamano_subtitulo}:"
        f"borderw=0:x={x_titulo + 20}:y={y_cartel + (alto_cartel - tamano_subtitulo) // 2 - 5}"
    )

    x_logo, y_logo = 30, 25
    tamano_logo = 90
    x_nombre = x_logo + tamano_logo + 15
    y_nombre = y_logo + (tamano_logo // 2) - 20
    dibujo_nombre = (
        f"drawtext=text='HISTORIA SIN FILTRO'{fontfile}:fontcolor=white:fontsize=34:"
        f"borderw=2:bordercolor=black:x={x_nombre}:y={y_nombre}"
    )

    cadena_texto = ",".join(dibujo_titulo) + f",{dibujo_cartel},{dibujo_nombre}"

    filtro_complejo = (
        f"[0:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}[fondo];"
        f"[1:v]scale={tamano_logo}:{tamano_logo}[logo];"
        f"[fondo][logo]overlay={x_logo}:{y_logo}[conlogo];"
        f"[conlogo]{cadena_texto}[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", ruta_fondo,
        "-i", ruta_logo,
        "-filter_complex", filtro_complejo,
        "-map", "[out]", "-frames:v", "1",
        ruta_salida,
    ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        mensaje = f"No se pudo componer la miniatura: {resultado.stderr[-800:]}"
        if logger:
            logger.warning(mensaje)
        else:
            print(mensaje)
        return None
    if logger:
        logger.info(f"Miniatura estilo foto generada: {ruta_salida}")
    else:
        print(f"Miniatura estilo foto generada: {ruta_salida}")
    return ruta_salida


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(
            "Uso: python3 generar_miniatura_estilo_foto.py "
            "\"titulo\" \"subtitulo\" ruta_fondo.png ruta_logo.png ruta_salida.png"
        )
        sys.exit(1)
    generar_miniatura_estilo_foto(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
