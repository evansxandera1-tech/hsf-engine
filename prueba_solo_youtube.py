# prueba_solo_youtube.py
# Prueba SOLO la subida a YouTube (sin generar video de nuevo), usando un
# video que ya existe en disco. Sirve para descartar que el problema sea
# falta de memoria al encadenar generación de video + subida en el mismo
# proceso.

import sys
sys.path.insert(0, ".")

print("=== DEBUG: arrancando, antes de importar hsf_engine ===", flush=True)
import hsf_engine as motor
print("=== DEBUG: hsf_engine importado OK ===", flush=True)

if len(sys.argv) < 2:
    print("Uso: python prueba_solo_youtube.py /ruta/al/video.mp4")
    sys.exit(1)

ruta_video = sys.argv[1]

logger, ruta_log = motor.crear_logger_video()

motor._ULTIMO_RESULTADO_AUTOMATICO = {
    "ruta_video": ruta_video,
    "titulo_resumen": "Nunca pensé que algo tan pequeño pudiera cambiarlo todo (prueba)",
    "subreddits": [],
    "cantidad_historias": 1,
    "carpeta_proyecto": ruta_video.rsplit("/", 1)[0],
}

print("=== DEBUG: antes de llamar a _subir_ultimo_resultado_a_youtube ===", flush=True)
try:
    motor._subir_ultimo_resultado_a_youtube(logger)
    print("=== DEBUG: subida terminada sin excepción ===", flush=True)
except Exception as e:
    print(f"=== ERROR subiendo a YouTube: {e} ===", flush=True)
