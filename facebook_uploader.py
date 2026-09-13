import os
import time
import requests


API_VERSION = "v25.0"
TAMANO_CHUNK = 10 * 1024 * 1024  # 10 MB por pedazo


def _leer_respuesta(respuesta, paso, logger=None):
    """Loguea status/cuerpo crudo y devuelve el JSON parseado, o None si
    Facebook no devolvió algo utilizable (respuesta vacía o no-JSON). Mismo
    criterio en las 3 fases, para no repetir el bug viejo de asumir que
    respuesta.json() siempre funciona."""
    if logger:
        logger.info(f"Facebook ({paso}) respondió con status {respuesta.status_code}")

    if not respuesta.text.strip():
        if logger:
            logger.error(f"Facebook ({paso}): respuesta vacía (status {respuesta.status_code}).")
        return None

    try:
        return respuesta.json()
    except ValueError:
        if logger:
            logger.error(
                f"Facebook ({paso}): no devolvió JSON (status {respuesta.status_code}). "
                f"Cuerpo crudo: {respuesta.text[:500]}"
            )
        return None


def subir_a_facebook(ruta_video, texto_miniatura, logger=None):
    """Sube el video ya generado a la página de Facebook usando el protocolo
    de subida por fases (upload_phase: start / transfer / finish) directo
    sobre /<PAGE_ID>/videos. No rompe el flujo si falla: siempre devuelve
    True/False, nunca deja pasar la excepción.

    A diferencia de la versión anterior (que usaba el endpoint genérico
    /{app_id}/uploads de la Resumable Upload API), acá se usa el MISMO
    Page Access Token en las 3 fases y el MISMO host (graph.facebook.com)
    en todas -- sin mezclar tipos de token ni hosts entre pasos, que era
    justo lo que quedaba sin descartar de todos los intentos anteriores.
    Ya no hace falta FACEBOOK_APP_ID para esto."""
    try:
        page_id = os.environ.get("FACEBOOK_PAGE_ID")
        page_token = os.environ.get("FACEBOOK_PAGE_TOKEN")

        if not page_id or not page_token:
            if logger:
                logger.warning(
                    "FACEBOOK_PAGE_ID o FACEBOOK_PAGE_TOKEN no configurados, se salta Facebook"
                )
            return False

        descripcion = f"{texto_miniatura}\n\n#historias #reflexion #realidad"
        tamano_bytes = os.path.getsize(ruta_video)
        url_videos = f"https://graph.facebook.com/{API_VERSION}/{page_id}/videos"

        # ---- Fase START: iniciar la sesión ----
        respuesta = requests.post(
            url_videos,
            data={
                "access_token": page_token,
                "upload_phase": "start",
                "file_size": tamano_bytes,
            },
            timeout=60,
        )
        resultado_start = _leer_respuesta(respuesta, "fase start", logger=logger)
        if not resultado_start or "upload_session_id" not in resultado_start:
            if logger:
                logger.error(f"No se pudo iniciar la sesión de subida a Facebook: {resultado_start}")
            return False
        upload_session_id = resultado_start["upload_session_id"]
        video_id = resultado_start.get("video_id")

        # ---- Fase TRANSFER: subir el archivo en chunks de 10 MB ----
        with open(ruta_video, "rb") as archivo_video:
            offset = 0
            while offset < tamano_bytes:
                chunk = archivo_video.read(TAMANO_CHUNK)
                if not chunk:
                    break
                respuesta = requests.post(
                    url_videos,
                    data={
                        "access_token": page_token,
                        "upload_phase": "transfer",
                        "upload_session_id": upload_session_id,
                        "start_offset": offset,
                    },
                    files={"video_file_chunk": chunk},
                    timeout=120,
                )
                resultado_transfer = _leer_respuesta(
                    respuesta, f"fase transfer (offset {offset})", logger=logger
                )
                if not resultado_transfer or (
                    "start_offset" not in resultado_transfer and "end_offset" not in resultado_transfer
                ):
                    if logger:
                        logger.error(
                            f"Fallo subiendo el chunk en offset {offset} a Facebook: {resultado_transfer}"
                        )
                    return False
                offset += len(chunk)
                if logger:
                    porcentaje = min(100, int((offset / tamano_bytes) * 100))
                    logger.info(f"Facebook: subida {porcentaje}% completada ({offset}/{tamano_bytes} bytes)")

        # ---- Fase FINISH: cerrar la sesión y publicar ----
        intentos_finish = 3
        espera_entre_intentos_seg = 15
        resultado_finish = None
        for intento in range(1, intentos_finish + 1):
            respuesta = requests.post(
                url_videos,
                data={
                    "access_token": page_token,
                    "upload_phase": "finish",
                    "upload_session_id": upload_session_id,
                    "description": descripcion,
                },
                timeout=120,
            )
            resultado_finish = _leer_respuesta(
                respuesta, f"fase finish (intento {intento}/{intentos_finish})", logger=logger
            )
            if resultado_finish and (resultado_finish.get("success") or "id" in resultado_finish):
                break
            if logger:
                logger.warning(
                    f"Facebook (fase finish, intento {intento}/{intentos_finish}): "
                    f"no se pudo publicar todavía: {resultado_finish}"
                )
            if intento < intentos_finish:
                time.sleep(espera_entre_intentos_seg)

        if not resultado_finish or not (resultado_finish.get("success") or "id" in resultado_finish):
            if logger:
                logger.error(
                    f"Error publicando el video en Facebook tras {intentos_finish} intentos: {resultado_finish}"
                )
            return False

        if logger:
            logger.info(f"Video subido a Facebook, id: {resultado_finish.get('id', video_id)}")
        return True

    except Exception as error:
        if logger:
            logger.error(f"Excepción subiendo a Facebook: {error}")
        return False
