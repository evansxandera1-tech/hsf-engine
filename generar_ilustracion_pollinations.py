import base64
import sys
import time

import requests

POLLINATIONS_API_KEY = "sk_d0sZWK22FktH8fTlWbTU1RGpZrLKwSPU"
POLLINATIONS_MODELO_IMAGEN = "nanobanana"


def generar_ilustracion_pollinations(resumen_texto, ruta_salida, logger=None, imagen_referencia=None):
    """Genera una ilustracion de fondo (estilo comic simple y oscuro, en dos
    escenas apiladas) a partir del resumen de la historia, usando Nanobanana
    via Pollinations. Si se pasa imagen_referencia (una URL, o varias
    separadas por '|' o ','), el modelo la usa como referencia de estilo o
    personaje. Devuelve la ruta local del PNG generado, o None si falla."""
    prompt = (
        "Ilustracion digital estilo comic simple y oscuro, formato vertical, "
        "dividida en dos escenas apiladas separadas por una linea blanca, "
        "representando visualmente esta historia real (SIN texto escrito "
        "dentro de la imagen, sin logos ni marcas de agua): "
        + resumen_texto.strip()[:600]
    )

    cuerpo = {
        "prompt": prompt,
        "model": POLLINATIONS_MODELO_IMAGEN,
        "size": "1024x1024",
        "response_format": "b64_json",
    }
    if imagen_referencia:
        cuerpo["image"] = imagen_referencia

    intentos_maximos = 3
    espera = 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                "https://gen.pollinations.ai/v1/images/generations",
                headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
                json=cuerpo,
                timeout=90,
            )
            if resp.status_code in (429, 503):
                if logger:
                    logger.warning(
                        f"Pollinations devolvio {resp.status_code}. "
                        f"Intento {intento}/{intentos_maximos}, reintentando en {espera}s..."
                    )
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
            if logger:
                logger.info(f"Ilustracion generada: {ruta_salida}")
            print(f"Ilustracion generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                print(f"Fallo la generacion tras {intentos_maximos} intentos: {e}")
                return None
            print(f"Error generando ilustracion (intento {intento}/{intentos_maximos}): {e}")
            time.sleep(espera)
            espera *= 2
    return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 generar_ilustracion_pollinations.py \"resumen de la historia\" ruta_salida.png [url_imagen_referencia]")
        sys.exit(1)
    resumen = sys.argv[1]
    salida = sys.argv[2]
    referencia = sys.argv[3] if len(sys.argv) > 3 else None
    generar_ilustracion_pollinations(resumen, salida, imagen_referencia=referencia)
