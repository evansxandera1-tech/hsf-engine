import os
import time
import requests


API_VERSION = "v25.0"


def _leer_respuesta(respuesta, paso, logger=None):
    """Loguea status/cuerpo crudo y devuelve el JSON parseado, o None si
    Facebook no devolvió algo utilizable (respuesta vacía o no-JSON). Mismo
    criterio en los 3 pasos, para no repetir el bug viejo de asumir que
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
    """Sube el video ya generado a la página de Facebook usando la Resumable
    Upload API (obligatoria para videos de más de 20 min / 1GB, que es el
    caso de los videos largos de producción). No rompe el flujo si falla:
    siempre devuelve True/False, nunca deja pasar la excepción.

    El host graph-video.facebook.com (usado antes) está deprecado según la
    documentación oficial de Meta; todo pasa ahora por graph.facebook.com."""
    try:
        app_id = os.environ.get("FACEBOOK_APP_ID")
        page_id = os.environ.get("FACEBOOK_PAGE_ID")
        page_token = os.environ.get("FACEBOOK_PAGE_TOKEN")

        if not app_id or not page_id or not page_token:
            if logger:
                logger.warning(
                    "FACEBOOK_APP_ID, FACEBOOK_PAGE_ID o FACEBOOK_PAGE_TOKEN no "
                    "configurados, se salta Facebook"
                )
            return False

        descripcion = f"{texto_miniatura}\n\n#historias #reflexion #realidad"
        tamano_bytes = os.path.getsize(ruta_video)
        nombre_archivo = os.path.basename(ruta_video)

        # ---- Paso 1: iniciar la sesión de subida ----
        url_sesion = f"https://graph.facebook.com/{API_VERSION}/{app_id}/uploads"
        respuesta = requests.post(
            url_sesion,
            params={
                "file_name": nombre_archivo,
                "file_length": tamano_bytes,
                "file_type": "video/mp4",
                "access_token": page_token,
            },
            timeout=60,
        )
        resultado_sesion = _leer_respuesta(respuesta, "paso 1: iniciar sesión", logger=logger)
        if not resultado_sesion or "id" not in resultado_sesion:
            if logger:
                logger.error(f"No se pudo iniciar la sesión de subida a Facebook: {resultado_sesion}")
            return False
        session_id = resultado_sesion["id"]  # viene como "upload:<ID>"

        # ---- Paso 2: subir el archivo completo a esa sesión ----
        url_subida = f"https://graph.facebook.com/{API_VERSION}/{session_id}"
        with open(ruta_video, "rb") as archivo_video:
            respuesta = requests.post(
                url_subida,
                headers={
                    "Authorization": f"OAuth {page_token}",
                    "file_offset": "0",
                },
                data=archivo_video,
                timeout=3600,
            )
        resultado_subida = _leer_respuesta(respuesta, "paso 2: subir archivo", logger=logger)
        if not resultado_subida or "h" not in resultado_subida:
            if logger:
                logger.error(f"No se pudo subir el archivo de video a Facebook: {resultado_subida}")
            return False
        handle_archivo = resultado_subida["h"]

        # ---- Paso 3: publicar el video en la página con ese handle ----
        # Con reintentos: este paso puede fallar con "code 6000 / 1363019"
        # (glitch transitorio de Facebook o el archivo aún no asentado del
        # todo del lado de Meta) incluso cuando los pasos 1 y 2 ya dieron
        # 200 -- o sea, el archivo se subió bien, pero Facebook todavía no
        # pudo procesarlo para publicarlo. Reintentar con espera resuelve
        # la mayoría de estos casos sin tocar nada más del flujo.
        url_publicar = f"https://graph.facebook.com/{API_VERSION}/{page_id}/videos"
        intentos_publicar = 3
        espera_entre_intentos_seg = 15
        resultado_publicar = None
        for intento in range(1, intentos_publicar + 1):
            respuesta = requests.post(
                url_publicar,
                data={
                    "access_token": page_token,
                    "description": descripcion,
                    "fbuploader_video_file_chunk": handle_archivo,
                },
                timeout=120,
            )
            resultado_publicar = _leer_respuesta(
                respuesta, f"paso 3: publicar (intento {intento}/{intentos_publicar})", logger=logger
            )
            if resultado_publicar and "id" in resultado_publicar:
                break
            if logger:
                logger.warning(
                    f"Facebook (paso 3, intento {intento}/{intentos_publicar}): "
                    f"no se pudo publicar todavía: {resultado_publicar}"
                )
            if intento < intentos_publicar:
                time.sleep(espera_entre_intentos_seg)

        if not resultado_publicar or "id" not in resultado_publicar:
            if logger:
                logger.error(
                    f"Error publicando el video en Facebook tras {intentos_publicar} intentos: {resultado_publicar}"
                )
            return False

        if logger:
            logger.info(f"Video subido a Facebook, id: {resultado_publicar['id']}")
        return True

    except Exception as error:
        if logger:
            logger.error(f"Excepción subiendo a Facebook: {error}")
        return False
