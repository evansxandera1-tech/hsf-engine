GEMINI_MODELO_IMAGEN = "gemini-2.5-flash-image"


def _generar_ilustracion_fondo_gemini(resumen_texto, ruta_salida, logger=None):
    """Genera una ilustracion de fondo (estilo comic simple y oscuro, en dos
    escenas apiladas) a partir del resumen de la historia, usando Gemini
    Image (Nano Banana). Devuelve la ruta local del PNG generado, o None si
    falla (el llamador cae al fondo de gameplay/negro de siempre)."""
    import base64

    if not GEMINI_API_KEY:
        if logger:
            logger.warning("GEMINI_API_KEY vacia: no se genera ilustracion de fondo.")
        return None

    prompt = (
        "Ilustracion digital estilo comic simple y oscuro, formato vertical, "
        "dividida en dos escenas apiladas separadas por una linea blanca, "
        "representando visualmente esta historia real (SIN texto escrito "
        "dentro de la imagen, sin logos ni marcas de agua):\n\n"
        f"{resumen_texto.strip()[:600]}"
    )

    intentos_maximos = 3
    espera = 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO_IMAGEN}:generateContent",
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=90,
            )
            if resp.status_code == 429:
                espera_real = espera
                try:
                    espera_real = max(espera, int(float(resp.headers.get("Retry-After", espera))))
                except (TypeError, ValueError):
                    pass
                if logger:
                    logger.warning(
                        f"Gemini Image devolvio 429. Intento {intento}/{intentos_maximos}, "
                        f"reintentando en {espera_real}s..."
                    )
                if intento < intentos_maximos:
                    time.sleep(espera_real)
                    espera *= 2
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            datos = resp.json()
            partes = datos["candidates"][0]["content"]["parts"]
            datos_b64 = next(
                (p["inlineData"]["data"] for p in partes if "inlineData" in p), None
            ) or next(
                (p["inline_data"]["data"] for p in partes if "inline_data" in p), None
            )
            if not datos_b64:
                raise ValueError("La respuesta de Gemini Image no trajo ninguna imagen")
            with open(ruta_salida, "wb") as f:
                f.write(base64.b64decode(datos_b64))
            if logger:
                logger.info(f"Ilustracion de fondo generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                if logger:
                    logger.warning(f"Fallo la generacion de la ilustracion tras {intentos_maximos} intentos: {e}")
                return None
            if logger:
                logger.warning(f"Error generando ilustracion (intento {intento}/{intentos_maximos}): {e}")
            time.sleep(espera)
            espera *= 2
    return None


def generar_miniatura_plantilla(titulo_miniatura, ruta_plantilla, ruta_salida, logger=None, ruta_video_fondo=None, resumen_texto=None):
    """Genera la miniatura a partir de una plantilla fija (tarjeta tipo
    'post', con el borde exterior transparente) superpuesta sobre, en este
    orden de prioridad: (1) una ilustracion generada con Gemini Image a
    partir del resumen de la historia si se pasa resumen_texto, (2) un
    frame del gameplay si se pasa ruta_video_fondo, o (3) negro si no hay
    nada de eso disponible. Posicion y tamanos de fuente calibrados a ojo
    para que el titulo quede bien dentro del recuadro. La tarjeta esta
    corrida hacia la derecha del cuadro dejando la izquierda libre para el
    fondo elegido."""
    texto_miniatura = titulo_miniatura.strip().upper()
    if len(texto_miniatura) > 110:
        texto_miniatura = texto_miniatura[:109].rstrip() + "…"

    def envolver(texto, max_chars):
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

    lineas = envolver(texto_miniatura, 34)
    tamano_fuente, y_inicio, alto_linea = 40, 270, 55
    if len(lineas) > 2:
        lineas = envolver(texto_miniatura, 45)
        tamano_fuente, y_inicio, alto_linea = 30, 270, 42
        lineas = lineas[:3]

    nombre_fuente_ok = asegurar_fuente(FUENTE_POR_DEFECTO) or FUENTE_POR_DEFECTO
    ruta_fuente = os.path.join(CARPETA_FUENTES, FUENTES_DISPONIBLES[nombre_fuente_ok].split("/")[-1])
    if not os.path.exists(ruta_fuente):
        ruta_fuente = None

    desplazamiento_tarjeta = 669
    tarjeta_x_izq = 89
    tarjeta_ancho = 1102
    dibujo_texto = []
    for i, linea in enumerate(lineas):
        linea_escapada = linea.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""
        y_pos = y_inicio + i * alto_linea
        x_expr = f"{tarjeta_x_izq + desplazamiento_tarjeta}+({tarjeta_ancho}-text_w)/2"
        dibujo_texto.append(
            f"drawtext=text='{linea_escapada}'{fontfile}:fontcolor=black:fontsize={tamano_fuente}:"
            f"borderw=1.2:bordercolor=black:x={x_expr}:y={y_pos}"
        )
    cadena_texto = ",".join(dibujo_texto)

    ruta_ilustracion = None
    if resumen_texto:
        ruta_ilustracion_tmp = os.path.splitext(ruta_salida)[0] + "_fondo_ia.png"
        ruta_ilustracion = _generar_ilustracion_fondo_gemini(resumen_texto, ruta_ilustracion_tmp, logger=logger)

    if ruta_ilustracion and os.path.exists(ruta_ilustracion):
        filtro_complejo = (
            f"[0:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}[fondo];"
            f"[fondo][1:v]overlay={desplazamiento_tarjeta}:0[con];"
            f"[con]{cadena_texto}[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", ruta_ilustracion,
            "-i", ruta_plantilla,
            "-filter_complex", filtro_complejo, "-map", "[out]",
            "-frames:v", "1", ruta_salida,
        ]
    elif ruta_video_fondo and os.path.exists(ruta_video_fondo):
        try:
            duracion = obtener_duracion_audio(ruta_video_fondo)
        except Exception:
            duracion = 10.0
        instante = min(max(2.0, duracion * 0.15), duracion - 1 if duracion > 1 else 0)
        filtro_complejo = (
            f"[1:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}[tmpl];"
            f"[0:v][tmpl]overlay={desplazamiento_tarjeta}:0[conmpl];"
            f"[conmpl]{cadena_texto}[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-ss", str(instante), "-i", ruta_video_fondo,
            "-i", ruta_plantilla,
            "-filter_complex", filtro_complejo, "-map", "[out]",
            "-frames:v", "1", ruta_salida,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}",
            "-i", ruta_plantilla,
            "-filter_complex", f"[0:v][1:v]overlay={desplazamiento_tarjeta}:0[con];[con]{cadena_texto}[out]",
            "-map", "[out]", "-frames:v", "1", ruta_salida,
        ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo generar la miniatura con plantilla: {resultado.stderr[-500:]}")
        return None
    if logger:
        logger.info(f"Miniatura (plantilla) generada: {ruta_salida}")
    return ruta_salida
