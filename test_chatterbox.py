"""Runner del test corto (2 min) de narración con audio de Chatterbox.
No sube nada a YouTube: solo genera el video de prueba y lo deja en
videos_hsf/ para que el workflow lo suba como artifact."""
from hsf_engine import crear_logger_video, cerrar_logger_video, _pipeline_test_chatterbox

logger, ruta_log = crear_logger_video()
try:
    ruta_video = _pipeline_test_chatterbox(logger, ruta_log, segundos_test=120)
    print(f"VIDEO_DE_PRUEBA_LISTO: {ruta_video}")
finally:
    cerrar_logger_video(logger)
