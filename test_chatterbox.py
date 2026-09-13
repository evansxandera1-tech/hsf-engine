"""Runner del test corto (2 min) de narración con audio de Chatterbox.
Genera el video de prueba con un audio/texto elegido al azar (sin marcarlo
como usado, para poder repetir el test las veces que haga falta) y lo sube
a YouTube en modo "unlisted" (definido por HSF_PRIVACIDAD_YOUTUBE en el
workflow) y a Facebook, igual que hace el video largo real, para confirmar
que todo el circuito funciona de punta a punta antes de dejarlo en manos
del cron de producción."""
import logging

from hsf_engine import (
    crear_logger_video, cerrar_logger_video, _pipeline_test_chatterbox,
    _subir_ultimo_resultado_a_youtube,
)

logger, ruta_log = crear_logger_video()
try:
    ruta_video = _pipeline_test_chatterbox(logger, ruta_log, segundos_test=120)
    print(f"VIDEO_DE_PRUEBA_LISTO: {ruta_video}")
finally:
    cerrar_logger_video(logger)

# Logger nuevo para la subida: el de arriba se cierra solo al terminar de
# generar el video (cerrar_logger_video), y si se reusa se pierden los
# logs de esta parte (mismo criterio que produccion.yml).
logger_subida = logging.getLogger("subida_youtube_test")
logger_subida.addHandler(logging.StreamHandler())
logger_subida.setLevel(logging.INFO)
_subir_ultimo_resultado_a_youtube(logger_subida)
