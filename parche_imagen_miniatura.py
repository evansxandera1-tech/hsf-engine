"""
Parche hsf-engine v5.5 -> v5.6: la imagen de la miniatura ahora se genera a
partir de la escena mas intrigante de la HISTORIA COMPLETA (no del resumen
corto), coherente con el titulo ya armado por Gemini.

Uso:
    cd ~/hsf-engine
    python parche_imagen_miniatura.py
"""
import re
import sys

RUTA = "hsf_engine.py"

with open(RUTA, "r", encoding="utf-8") as f:
    contenido = f.read()

original = contenido
cambios = 0

# --- 1) Guardar el guion completo en _ULTIMO_RESULTADO_AUTOMATICO ---
viejo_dict = '''    _ULTIMO_RESULTADO_AUTOMATICO = {
        "ruta_video": ruta_video_absoluta,
        "titulo_resumen": titulo_resumen,
        "subreddits": [],
        "cantidad_historias": 1,
    }'''
nuevo_dict = '''    _ULTIMO_RESULTADO_AUTOMATICO = {
        "ruta_video": ruta_video_absoluta,
        "titulo_resumen": titulo_resumen,
        "guion": guion,
        "subreddits": [],
        "cantidad_historias": 1,
    }'''
if viejo_dict in contenido:
    contenido = contenido.replace(viejo_dict, nuevo_dict, 1)
    cambios += 1
else:
    print("AVISO: no se encontro el bloque _ULTIMO_RESULTADO_AUTOMATICO tal cual (paso 1). Revisar a mano.")

# --- 2) Reemplazar generar_fondo_ia_pollinations completa (agrega prompt_personalizado) ---
patron_pollinations = re.compile(
    r"def generar_fondo_ia_pollinations\(.*?\n\n(?=def )", re.DOTALL
)
nueva_pollinations = '''def generar_fondo_ia_pollinations(resumen_texto, ruta_salida, logger=None, ancho=None, alto=None, prompt_personalizado=None):
    """Genera una imagen con IA (Pollinations, gratis, sin API key). Si
    prompt_personalizado viene armado (escena puntual de la historia,
    generada con _generar_prompt_imagen_miniatura), lo usa; si no, cae al
    prompt generico anterior (dos personas confrontandose) a partir del
    resumen corto."""
    import urllib.parse

    ancho = ancho or RESOLUCION_ANCHO
    alto = alto or RESOLUCION_ALTO

    if prompt_personalizado:
        prompt = (
            f"{prompt_personalizado}, photorealistic, cinematic photography, "
            f"film still, natural lighting, shallow depth of field, realistic "
            f"faces, high detail"
        )
    else:
        resumen_corto = " ".join(resumen_texto.split())[:180]
        prompt = (
            f"{resumen_corto}, two people confronting each other, dramatic tense "
            f"argument, photorealistic, cinematic photography, film still, natural "
            f"lighting, shallow depth of field, realistic faces, high detail"
        )

    prompt_codificado = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        f"?width={ancho}&height={alto}&nologo=true"
    )
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        with open(ruta_salida, "wb") as f:
            f.write(r.content)
        if logger:
            logger.info(f"Imagen IA (Pollinations) generada: {ruta_salida}")
        return ruta_salida
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo generar la imagen con IA (Pollinations): {e}")
        return None


PROMPT_IMAGEN_MINIATURA = """A partir de esta historia real narrada en primera persona y su titulo ya definido, identifica el momento MAS impactante, revelador o intrigante de toda la historia (el giro, la confesion, el hallazgo, la escena que genera mas ganas de saber que paso) y describi ESA escena puntual como prompt de imagen en ingles, para un generador de imagenes fotorrealista.

Reglas del prompt:
- Debe coincidir con lo que promete el titulo, no ser generico
- Personajes con su emocion visible (shocked, guilty, crying, furious, etc.)
- Lugar/escenario concreto segun la historia (kitchen, hospital, courtroom, car, etc.)
- Un objeto o detalle visual que identifique el conflicto (a letter, a phone screen, a pregnancy test, a broken photo frame, etc.) si la historia lo tiene
- NO texto en la imagen, NO logos, NO watermarks
- Una sola escena, no collage

Titulo: {titulo}

Historia completa:
{historia}

Devolve SOLO el prompt en ingles, una sola linea, sin comillas ni explicacion."""


def _generar_prompt_imagen_miniatura(historia_completa, titulo, logger=None):
    """Genera con Gemini un prompt en ingles para Pollinations describiendo
    la escena mas intrigante/reveladora de TODA la historia (no solo el
    resumen corto), coherente con el titulo ya generado. Si Gemini falla
    o no hay API key, devuelve None y generar_fondo_ia_pollinations cae
    al prompt generico de respaldo (dos personas confrontandose)."""
    if not GEMINI_API_KEY or not historia_completa:
        return None

    try:
        prompt = PROMPT_IMAGEN_MINIATURA.format(
            titulo=titulo.strip(),
            historia=historia_completa.strip()[:4000],
        )
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        prompt_imagen = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        return prompt_imagen or None
    except Exception as e:
        if logger:
            logger.warning(f"Fallo al generar prompt de imagen con Gemini, se usa el generico: {e}")
        return None


'''
contenido, n = patron_pollinations.subn(nueva_pollinations, contenido, count=1)
if n == 1:
    cambios += 1
else:
    print("AVISO: no se pudo reemplazar generar_fondo_ia_pollinations (paso 2). Revisar a mano.")

# --- 3) generar_miniatura_clickbait: nuevo parametro + usar el prompt personalizado ---
vieja_firma = 'def generar_miniatura_clickbait(titulo_miniatura, resumen_texto, ruta_salida, logger=None, ruta_video_fondo=None):'
nueva_firma = 'def generar_miniatura_clickbait(titulo_miniatura, resumen_texto, ruta_salida, logger=None, ruta_video_fondo=None, historia_completa=None):'
if vieja_firma in contenido:
    contenido = contenido.replace(vieja_firma, nueva_firma, 1)
    cambios += 1
else:
    print("AVISO: no se encontro la firma de generar_miniatura_clickbait (paso 3). Revisar a mano.")

vieja_llamada = '''    ancho_mitad = RESOLUCION_ANCHO // 2
    ruta_imagen_izq = generar_fondo_ia_pollinations(
        resumen_texto, ruta_salida + ".izq.jpg", logger=logger,
        ancho=ancho_mitad, alto=RESOLUCION_ALTO,
    )'''
nueva_llamada = '''    ancho_mitad = RESOLUCION_ANCHO // 2
    prompt_imagen = _generar_prompt_imagen_miniatura(
        historia_completa or resumen_texto, titulo_miniatura, logger=logger,
    )
    ruta_imagen_izq = generar_fondo_ia_pollinations(
        resumen_texto, ruta_salida + ".izq.jpg", logger=logger,
        ancho=ancho_mitad, alto=RESOLUCION_ALTO,
        prompt_personalizado=prompt_imagen,
    )'''
if vieja_llamada in contenido:
    contenido = contenido.replace(vieja_llamada, nueva_llamada, 1)
    cambios += 1
else:
    print("AVISO: no se encontro la llamada a generar_fondo_ia_pollinations dentro de generar_miniatura_clickbait (paso 4). Revisar a mano.")

# --- 4) Call site en _subir_ultimo_resultado_a_youtube: pasar historia_completa ---
vieja_call_site = '''        ok_miniatura = generar_miniatura_clickbait(
            titulo_para_imagen, resultado["titulo_resumen"], ruta_miniatura, logger=logger,
            ruta_video_fondo=resultado["ruta_video"],
        )'''
nueva_call_site = '''        ok_miniatura = generar_miniatura_clickbait(
            titulo_para_imagen, resultado["titulo_resumen"], ruta_miniatura, logger=logger,
            ruta_video_fondo=resultado["ruta_video"],
            historia_completa=resultado.get("guion"),
        )'''
if vieja_call_site in contenido:
    contenido = contenido.replace(vieja_call_site, nueva_call_site, 1)
    cambios += 1
else:
    print("AVISO: no se encontro el call site en _subir_ultimo_resultado_a_youtube (paso 5). Revisar a mano.")

if contenido == original:
    print("\\nNADA SE MODIFICO. No se toco el archivo. Mandale a Claude los AVISOS de arriba.")
    sys.exit(1)

with open(RUTA, "w", encoding="utf-8") as f:
    f.write(contenido)

print(f"\\nListo: {cambios}/5 cambios aplicados a {RUTA}.")
if cambios < 5:
    print("Ojo: no fueron los 5. Revisa los AVISOS de arriba y mandaselos a Claude para ajustar a mano lo que falto.")
