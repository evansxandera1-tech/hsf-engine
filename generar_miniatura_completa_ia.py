import os
import base64
import sys
import time

import requests

POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")
POLLINATIONS_MODELO_IMAGEN = "nanobanana"


def generar_miniatura_completa_ia(titulo, subtitulo, ruta_salida, logger=None):
    """Genera la miniatura COMPLETA (foto de fondo + logo HSF + titulo en
    blanco/amarillo + cartel rojo con subtitulo + stats) en una sola imagen,
    usando Nanobanana via Pollinations. No usa la plantilla local ni
    ffmpeg drawtext para el texto -- todo lo hace el modelo de imagen."""
    prompt = (
        "Miniatura de YouTube en formato horizontal 16:9, estilo historia "
        "real/confesion dramatica. Fondo: foto realista en primer plano de "
        "una mujer llorando, expresion angustiada, iluminacion cinematica "
        "oscura. Arriba a la izquierda, un logo circular rojo oscuro con las "
        "letras blancas 'HSF' y al lado el texto 'HISTORIA SIN FILTRO' en "
        "blanco negrita con un icono de verificado rojo. En el centro-derecha, "
        f"el titulo en letras enormes: primera linea en blanco '{titulo.split('?')[0].strip()}"
        f"' y ultima palabra en amarillo antes del signo de interrogacion. Debajo, "
        f"un cartel/banner rojo rectangular con el texto en blanco mayuscula: "
        f"'{subtitulo}'. Abajo a la derecha, iconos y numeros de estadisticas "
        "sociales (compartir, me gusta, guardado) en blanco pequeno. "
        "Tipografia impact bold, alto contraste, estilo clickbait profesional. "
        "Texto perfectamente legible y bien escrito, sin errores de tipeo."
    )

    intentos_maximos = 3
    espera = 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                "https://gen.pollinations.ai/v1/images/generations",
                headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
                json={
                    "prompt": prompt,
                    "model": POLLINATIONS_MODELO_IMAGEN,
                    "size": "1280x720",
                    "response_format": "b64_json",
                },
                timeout=90,
            )
            if resp.status_code in (429, 503):
                print(f"Pollinations devolvio {resp.status_code}. Intento {intento}/{intentos_maximos}, reintentando en {espera}s...")
                if intento < intentos_maximos:
                    time.sleep(espera)
                    espera *= 2
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            datos = resp.json()
            datos_b64 = datos["data"][0]["b64_json"]
            with open(ruta_salida, "wb") as f:
                f.write(base64.b64decode(datos_b64))
            print(f"Miniatura completa generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                print(f"Fallo la generacion tras {intentos_maximos} intentos: {e}")
                return None
            print(f"Error generando (intento {intento}/{intentos_maximos}): {e}")
            time.sleep(espera)
            espera *= 2
    return None


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python3 generar_miniatura_completa_ia.py \"titulo\" \"subtitulo\" ruta_salida.png")
        sys.exit(1)
    generar_miniatura_completa_ia(sys.argv[1], sys.argv[2], sys.argv[3])
