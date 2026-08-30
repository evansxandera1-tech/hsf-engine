#!/usr/bin/env python3
"""
generar_miniatura.py (v2.2) - proyecto hsf-engine
Recorre todos los guiones (.txt) en la carpeta txt-limpio de Drive y
genera una miniatura para cada uno que todavia no la tenga:
1) Lista los .txt en txt-limpio y los .jpg ya generados en miniatura.
2) Por cada .txt sin su .jpg correspondiente (mismo nombre base):
   - Descarga el guion con rclone.
   - Gemini (texto) lee el guion completo, inventa el titulo del video
     y saca "la mejor parte" para armar un prompt de imagen en ingles.
   - Gemini 2.5 Flash Image genera la imagen 1280x720.
   - Se superpone el titulo en texto grande.
   - Sube la miniatura a Drive con el MISMO nombre base que el .txt
     (ej: terremoto_colombia.txt -> terremoto_colombia.jpg), para que
     se pueda emparejar despues con el video/audio correspondiente.
No mueve ni borra los .txt de txt-limpio (se siguen usando para el audio).

======= LO UNICO QUE HAY QUE EDITAR =======
GEMINI_API_KEY   -> tu API key de Gemini
RCLONE_REMOTE    -> nombre del remote de rclone (ej "gdrive")
CARPETA_GUIONES  -> carpeta de Drive con los guiones (txt-limpio)
CARPETA_SALIDA   -> carpeta de Drive donde se suben las miniaturas
============================================

Uso:
    python generar_miniatura.py
"""

import os
import base64
import logging
import subprocess
import tempfile
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont

# =================== CONFIG (editar aca) ===================
GEMINI_API_KEY = "AQ.Ab8RN6JuQSaL_2-7PDmoCZ2bcdgeKvi3GrBtTHZfLiLG66TVdQ"
RCLONE_REMOTE = "gdrive"
CARPETA_GUIONES = f"{RCLONE_REMOTE}:txt-limpio"
CARPETA_SALIDA = f"{RCLONE_REMOTE}:miniatura"
# =============================================================

TEXT_MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"
CARPETA_TEMP = tempfile.gettempdir()

# ---------- Logging ----------
log = logging.getLogger("generar_miniatura")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(handler)


def verificar_config():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "PON_TU_API_KEY_AQUI":
        log.error("Falta configurar GEMINI_API_KEY arriba en el script")
        raise SystemExit(1)


def listar_archivos(carpeta_drive: str) -> list:
    resultado = subprocess.run(
        ["rclone", "lsf", carpeta_drive], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        log.error("Error al listar %s: %s", carpeta_drive, resultado.stderr)
        raise SystemExit(1)
    return [linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()]


def obtener_guiones_pendientes() -> list:
    """Devuelve la lista de nombres base (.txt) que todavia no tienen
    su miniatura correspondiente en CARPETA_SALIDA."""
    guiones = [f for f in listar_archivos(CARPETA_GUIONES) if f.lower().endswith(".txt")]
    miniaturas_existentes = {
        os.path.splitext(f)[0] for f in listar_archivos(CARPETA_SALIDA) if f.lower().endswith(".jpg")
    }
    pendientes = [g for g in guiones if os.path.splitext(g)[0] not in miniaturas_existentes]
    log.info("Guiones encontrados: %d | Ya con miniatura: %d | Pendientes: %d",
              len(guiones), len(miniaturas_existentes), len(pendientes))
    return pendientes


def descargar_guion(nombre_archivo: str) -> str:
    ruta_drive = f"{CARPETA_GUIONES}/{nombre_archivo}"
    log.info("Descargando guion: %s", nombre_archivo)
    resultado = subprocess.run(
        ["rclone", "cat", ruta_drive], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        log.error("Error al leer %s: %s", nombre_archivo, resultado.stderr)
        raise RuntimeError(resultado.stderr)
    return resultado.stdout


def subir_miniatura(ruta_local: str, nombre_archivo_jpg: str):
    destino = f"{CARPETA_SALIDA}/{nombre_archivo_jpg}"
    log.info("Subiendo miniatura: %s", destino)
    resultado = subprocess.run(
        ["rclone", "copyto", ruta_local, destino], capture_output=True, text=True
    )
    if resultado.returncode != 0:
        log.error("Error al subir %s: %s", nombre_archivo_jpg, resultado.stderr)
        raise RuntimeError(resultado.stderr)
    log.info("Miniatura subida: %s", nombre_archivo_jpg)


def inventar_titulo_y_prompt(texto_guion: str) -> tuple:
    """Le pide a Gemini que invente el titulo del video Y arme el
    prompt de imagen para la miniatura, en un solo llamado."""
    log.info("Generando titulo + prompt de imagen con Gemini text (%s)...", TEXT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent"
    instruccion = (
        "Sos un experto en YouTube (titulos virales) y en diseño de miniaturas. "
        "Te paso el guion completo de un video narrado de historias de Reddit. "
        "Tarea 1: inventa un TITULO llamativo y corto para el video (en español). "
        "Tarea 2: identifica la escena o momento MAS IMPACTANTE del guion y "
        "arma un PROMPT en ingles para un generador de imagenes IA, describiendo "
        "una imagen de miniatura de YouTube basada en esa escena: estilo dramatico, "
        "alto contraste, composicion pensada para 1280x720, SIN texto ni letras "
        "en la imagen (el texto se agrega despues por separado).\n\n"
        "Respondé EXACTAMENTE en este formato, sin nada mas:\n"
        "TITULO: <el titulo aca>\n"
        "PROMPT: <el prompt en ingles aca>"
    )
    payload = {"contents": [{"parts": [{"text": f"{instruccion}\n\nGUION:\n{texto_guion}"}]}]}
    resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, timeout=60)
    resp.raise_for_status()
    texto_respuesta = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    titulo, prompt_imagen = "", ""
    for linea in texto_respuesta.splitlines():
        if linea.upper().startswith("TITULO:"):
            titulo = linea.split(":", 1)[1].strip()
        elif linea.upper().startswith("PROMPT:"):
            prompt_imagen = linea.split(":", 1)[1].strip()

    if not titulo or not prompt_imagen:
        raise RuntimeError(f"Respuesta de Gemini con formato inesperado: {texto_respuesta}")

    log.info("Titulo generado: %s", titulo)
    log.info("Prompt de imagen: %s", prompt_imagen)
    return titulo, prompt_imagen


def generar_imagen(prompt_imagen: str) -> Image.Image:
    log.info("Generando imagen con %s...", IMAGE_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt_imagen}]}]}
    resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, timeout=120)
    resp.raise_for_status()
    partes = resp.json()["candidates"][0]["content"]["parts"]
    for parte in partes:
        if "inlineData" in parte:
            img_bytes = base64.b64decode(parte["inlineData"]["data"])
            ruta_tmp = os.path.join(CARPETA_TEMP, "_tmp_base_miniatura.png")
            with open(ruta_tmp, "wb") as f:
                f.write(img_bytes)
            imagen = Image.open(ruta_tmp).convert("RGB")
            os.remove(ruta_tmp)
            log.info("Imagen generada correctamente (%sx%s)", imagen.width, imagen.height)
            return imagen
    raise RuntimeError("Gemini no devolvio ninguna imagen en la respuesta")


def buscar_fuente(tamano: int) -> ImageFont.FreeTypeFont:
    rutas_posibles = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/data/data/com.termux/files/usr/share/fonts/DejaVuSans-Bold.ttf",
    ]
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tamano)
    log.warning("No se encontro una fuente .ttf, usando fuente por defecto (baja calidad)")
    return ImageFont.load_default()


def agregar_titulo(imagen: Image.Image, titulo: str) -> Image.Image:
    imagen = imagen.resize((1280, 720))
    draw = ImageDraw.Draw(imagen)
    tamano_fuente = 90
    fuente = buscar_fuente(tamano_fuente)

    palabras = titulo.upper().split()
    lineas, linea_actual = [], ""
    max_ancho = 1150
    for palabra in palabras:
        prueba = (linea_actual + " " + palabra).strip()
        ancho = draw.textbbox((0, 0), prueba, font=fuente)[2]
        if ancho > max_ancho and linea_actual:
            lineas.append(linea_actual)
            linea_actual = palabra
        else:
            linea_actual = prueba
    if linea_actual:
        lineas.append(linea_actual)

    alto_linea = tamano_fuente + 20
    y = 720 - (alto_linea * len(lineas)) - 40

    for linea in lineas:
        ancho_linea = draw.textbbox((0, 0), linea, font=fuente)[2]
        x = (1280 - ancho_linea) / 2
        for dx in range(-4, 5, 2):
            for dy in range(-4, 5, 2):
                draw.text((x + dx, y + dy), linea, font=fuente, fill="black")
        draw.text((x, y), linea, font=fuente, fill="white")
        y += alto_linea

    return imagen


def procesar_guion(nombre_archivo_txt: str):
    nombre_base = os.path.splitext(nombre_archivo_txt)[0]
    log.info("=== Procesando: %s ===", nombre_archivo_txt)

    texto_guion = descargar_guion(nombre_archivo_txt)
    titulo, prompt_imagen = inventar_titulo_y_prompt(texto_guion)
    imagen_base = generar_imagen(prompt_imagen)
    imagen_final = agregar_titulo(imagen_base, titulo)

    nombre_archivo_jpg = f"{nombre_base}.jpg"
    ruta_local = os.path.join(CARPETA_TEMP, nombre_archivo_jpg)
    imagen_final.save(ruta_local, quality=92)

    subir_miniatura(ruta_local, nombre_archivo_jpg)
    os.remove(ruta_local)
    log.info("=== Listo: %s ===", nombre_archivo_jpg)


def main():
    verificar_config()
    pendientes = obtener_guiones_pendientes()

    if not pendientes:
        log.info("No hay guiones pendientes, nada para hacer.")
        return

    for nombre_archivo_txt in pendientes:
        try:
            procesar_guion(nombre_archivo_txt)
        except Exception as e:
            log.error("Fallo procesando %s: %s", nombre_archivo_txt, e)
            continue


if __name__ == "__main__":
    main()
