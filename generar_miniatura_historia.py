"""
generar_miniatura_historia.py (v1.0)

Genera la miniatura split (foto IA a la izquierda + tarjeta blanca con
pregunta-dilema a la derecha) usando Pillow en vez de ffmpeg. Se puede
probar sola y rapido, sin correr el pipeline de video completo.

Prueba rapida (genera una miniatura de ejemplo en segundos):
    cd ~/hsf-engine
    python generar_miniatura_historia.py

Uso real, desde hsf_engine.py:
    from generar_miniatura_historia import generar_miniatura
    generar_miniatura(titulo, historia_completa, ruta_salida, logger=logger)
"""
import os
import math
import random
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont

from hsf_engine import (
    GEMINI_API_KEY, GEMINI_MODELO, RESOLUCION_ANCHO, RESOLUCION_ALTO,
    CARPETA_BASE, FUENTE_POR_DEFECTO, asegurar_fuente,
)

PROMPT_PREGUNTA_MINIATURA = """A partir de este resumen de una historia real narrada en primera persona, escribi UNA pregunta corta en espanol, en primera persona, estilo "Soy la mala por...?" o "Hice mal en...?" -- el tipo de pregunta que alguien haria en un foro de confesiones para que otros opinen si actuo bien o mal.

Historia:
{resumen}

Devolve SOLO la pregunta, sin comillas ni explicacion."""

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


def _llamar_gemini(prompt, logger=None):
    if not GEMINI_API_KEY:
        return None
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
    except Exception as e:
        if logger:
            logger.warning(f"Fallo al llamar a Gemini: {e}")
        return None


def _generar_pregunta(historia, logger=None):
    respuesta = _llamar_gemini(PROMPT_PREGUNTA_MINIATURA.format(resumen=(historia or "")[:600]), logger=logger)
    if not respuesta or "?" not in respuesta:
        return "HICE MAL EN ESTA SITUACION?"
    return respuesta.upper()


def _generar_prompt_imagen(historia, titulo, logger=None):
    if not historia:
        return None
    return _llamar_gemini(
        PROMPT_IMAGEN_MINIATURA.format(titulo=(titulo or "").strip(), historia=historia.strip()[:4000]),
        logger=logger,
    )


def _bajar_imagen_pollinations(prompt_escena, ruta_salida, ancho, alto, logger=None):
    if prompt_escena:
        prompt = (
            f"{prompt_escena}, photorealistic, cinematic photography, film still, "
            f"natural lighting, shallow depth of field, realistic faces, high detail"
        )
    else:
        prompt = (
            "two people confronting each other, dramatic tense argument, "
            "photorealistic, cinematic photography, film still, natural lighting, "
            "shallow depth of field, realistic faces, high detail"
        )
    url = (
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
        f"?width={ancho}&height={alto}&nologo=true"
    )
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        with open(ruta_salida, "wb") as f:
            f.write(r.content)
        return ruta_salida
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo bajar la imagen de Pollinations: {e}")
        return None


def _fuente(size):
    ruta = asegurar_fuente(FUENTE_POR_DEFECTO) or FUENTE_POR_DEFECTO
    try:
        return ImageFont.truetype(ruta, size)
    except Exception:
        return ImageFont.load_default()


def _envolver(draw, texto, fnt, max_w):
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = (actual + " " + palabra).strip()
        if draw.textlength(prueba, font=fnt) <= max_w:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def generar_miniatura(titulo, historia_completa, ruta_salida, logger=None):
    """Genera la miniatura split con Pillow. Devuelve ruta_salida si salio
    bien, o None si algo fallo (para que el llamador caiga a un respaldo,
    igual que hacia generar_miniatura_clickbait antes)."""
    W, H = RESOLUCION_ANCHO, RESOLUCION_ALTO
    BORDE = 10
    ancho_mitad = W // 2

    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    prompt_escena = _generar_prompt_imagen(historia_completa, titulo, logger=logger)
    ruta_foto = _bajar_imagen_pollinations(
        prompt_escena, ruta_salida + ".izq.jpg", ancho_mitad, H, logger=logger,
    )
    if ruta_foto and os.path.exists(ruta_foto):
        try:
            foto = Image.open(ruta_foto).convert("RGB").resize((ancho_mitad, H))
            img.paste(foto, (0, 0))
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo abrir la imagen bajada, uso gris de respaldo: {e}")
            draw.rectangle([0, 0, ancho_mitad, H], fill=(90, 85, 80))
    else:
        draw.rectangle([0, 0, ancho_mitad, H], fill=(90, 85, 80))

    draw.rectangle([0, 0, W - 1, H - 1], outline=(200, 20, 20), width=BORDE)
    draw.rectangle([ancho_mitad - 4, 0, ancho_mitad + 4, H], fill=(200, 20, 20))

    px, py = ancho_mitad + 8 + 20, 30
    pw = W - px - 30

    ruta_logo = os.path.join(CARPETA_BASE, "assets", "logo_hsf.png")
    avatar_r = 30
    avatar_cx, avatar_cy = px + avatar_r, py + avatar_r
    if os.path.exists(ruta_logo):
        try:
            logo = Image.open(ruta_logo).convert("RGBA").resize((avatar_r * 2, avatar_r * 2))
            img.paste(logo, (avatar_cx - avatar_r, avatar_cy - avatar_r), logo)
        except Exception:
            draw.ellipse([avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r], fill=(150, 20, 30))
    else:
        draw.ellipse([avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r], fill=(150, 20, 30))
        draw.text((avatar_cx, avatar_cy), "HSF", font=_fuente(18), fill="white", anchor="mm")

    nombre_x = avatar_cx + avatar_r + 12
    fnt_nombre = _fuente(24)
    draw.text((nombre_x, avatar_cy - 14), "Historias Sin Filtro", font=fnt_nombre, fill=(20, 20, 20))
    check_x = nombre_x + draw.textlength("Historias Sin Filtro", font=fnt_nombre) + 8
    draw.ellipse([check_x, avatar_cy - 14, check_x + 22, avatar_cy + 8], fill=(60, 130, 246))
    draw.text((check_x + 11, avatar_cy - 3), "OK", font=_fuente(11), fill="white", anchor="mm")

    row2_y = avatar_cy + avatar_r + 14
    vistas = f"{random.randint(700, 950)}.{random.randint(100, 999)}"
    draw.ellipse([px, row2_y, px + 22, row2_y + 14], outline=(80, 80, 80), width=2)
    draw.ellipse([px + 8, row2_y + 3, px + 14, row2_y + 11], fill=(80, 80, 80))
    fnt_reg = _fuente(20)
    draw.text((px + 30, row2_y - 4), vistas, font=fnt_reg, fill=(70, 70, 70))

    ex = px + 30 + draw.textlength(vistas, font=fnt_reg) + 20
    icon_y = row2_y - 2
    draw.ellipse([ex, icon_y + 4, ex + 18, icon_y + 22], fill=(255, 110, 0))
    draw.polygon([(ex + 9, icon_y - 4), (ex + 2, icon_y + 10), (ex + 16, icon_y + 10)], fill=(255, 110, 0))
    ex += 30
    cx, cy, r_out, r_in = ex + 10, icon_y + 9, 11, 5
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
    draw.polygon(pts, fill=(255, 205, 0))
    ex += 30
    draw.rounded_rectangle([ex, icon_y, ex + 24, icon_y + 16], radius=6, fill=(140, 150, 255))
    draw.polygon([(ex + 4, icon_y + 15), (ex + 4, icon_y + 22), (ex + 11, icon_y + 15)], fill=(140, 150, 255))
    ex += 34
    hr = 8
    draw.ellipse([ex, icon_y + 2, ex + hr * 2, icon_y + 2 + hr * 2], fill=(160, 0, 210))
    draw.ellipse([ex + hr, icon_y + 2, ex + hr * 3, icon_y + 2 + hr * 2], fill=(160, 0, 210))
    draw.polygon([(ex, icon_y + 2 + hr), (ex + hr * 3, icon_y + 2 + hr), (ex + hr * 1.5, icon_y + 2 + hr * 3)], fill=(160, 0, 210))

    pregunta = "\u00bf" + _generar_pregunta(historia_completa or titulo, logger=logger)
    fnt_preg = _fuente(40)
    lineas = _envolver(draw, pregunta, fnt_preg, pw - 10)[:5]
    total_h = len(lineas) * 50
    start_y = (H // 2) - (total_h // 2) + 20
    for i, linea in enumerate(lineas):
        draw.text((px + pw // 2, start_y + i * 50), linea, font=fnt_preg, fill=(10, 10, 10), anchor="mm", align="center")

    row3_y = H - 70
    bm_txt = f"{random.randint(1, 3)}.{random.randint(0, 9)}K"
    sh_txt = str(random.randint(400, 999))
    draw.polygon([(px, row3_y - 10), (px + 20, row3_y - 10), (px + 20, row3_y + 16), (px + 10, row3_y + 6), (px, row3_y + 16)], outline=(60, 60, 60), width=2)
    draw.text((px + 28, row3_y - 6), bm_txt, font=fnt_reg, fill=(70, 70, 70))
    sh_x = px + 28 + draw.textlength(bm_txt, font=fnt_reg) + 30
    draw.line([(sh_x, row3_y + 2), (sh_x + 16, row3_y - 10)], fill=(60, 60, 60), width=3)
    draw.line([(sh_x, row3_y + 2), (sh_x + 16, row3_y + 14)], fill=(60, 60, 60), width=3)
    draw.line([(sh_x + 16, row3_y - 10), (sh_x + 16, row3_y + 14)], fill=(60, 60, 60), width=3)
    draw.text((sh_x + 26, row3_y - 6), sh_txt, font=fnt_reg, fill=(70, 70, 70))

    try:
        img.convert("RGB").save(ruta_salida, quality=92)
        if logger:
            logger.info(f"Miniatura generada con PIL: {ruta_salida}")
        return ruta_salida
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo guardar la miniatura: {e}")
        return None


if __name__ == "__main__":
    TITULO_PRUEBA = "Encontre pruebas de que mi esposo planeaba dejarme sin nada"
    HISTORIA_PRUEBA = """
    Mi esposo Marcos y yo llevabamos 8 anos casados. Todo parecia normal hasta
    que un martes por la noche encontre su telefono desbloqueado en la mesa de
    la cocina. Una notificacion de un banco llamo mi atencion: un retiro de
    15.000 dolares de una cuenta que yo no sabia que existia. Abri el
    historial y encontre meses de mensajes con otra mujer, planeando un
    futuro juntos sin que yo lo supiera.
    """
    ruta = os.path.join(CARPETA_BASE, "miniatura_prueba.jpg")
    resultado = generar_miniatura(TITULO_PRUEBA, HISTORIA_PRUEBA, ruta, logger=None)
    print(f"=== Miniatura de prueba: {resultado} ===")
