import os
import requests


def subir_a_facebook(ruta_video, texto_miniatura, logger=None):
    """Sube el video ya generado a la página de Facebook. No rompe el flujo si falla."""
    try:
        page_id = os.environ.get("FACEBOOK_PAGE_ID")
        page_token = os.environ.get("FACEBOOK_PAGE_TOKEN")

        if not page_id or not page_token:
            if logger:
                logger.warning("FACEBOOK_PAGE_ID o FACEBOOK_PAGE_TOKEN no configurados, se salta Facebook")
            return False

        descripcion = f"{texto_miniatura}\n\n#historias #reflexion #realidad"

        url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"

        with open(ruta_video, "rb") as archivo_video:
            respuesta = requests.post(
                url,
                data={
                    "access_token": page_token,
                    "description": descripcion,
                },
                files={"source": archivo_video},
                timeout=1800,
            )

        # Antes se llamaba respuesta.json() directo, y si Facebook devolvía
        # algo vacío o no-JSON (timeout intermedio, error 5xx sin cuerpo,
        # token vencido, etc.) esto reventaba con un error generico
        # ("Expecting value: line 1 column 1") que no decia nada util.
        # Ahora se loguea SIEMPRE el status code y el cuerpo crudo primero,
        # para poder diagnosticar la proxima vez que falle.
        if logger:
            logger.info(f"Facebook respondio con status {respuesta.status_code}")

        if not respuesta.text.strip():
            if logger:
                logger.error(f"Facebook devolvió una respuesta vacía (status {respuesta.status_code}).")
            return False

        try:
            resultado = respuesta.json()
        except ValueError:
            if logger:
                logger.error(
                    f"Facebook no devolvió JSON (status {respuesta.status_code}). "
                    f"Cuerpo crudo: {respuesta.text[:500]}"
                )
            return False

        if "id" in resultado:
            if logger:
                logger.info(f"Video subido a Facebook, id: {resultado['id']}")
            return True
        else:
            if logger:
                logger.error(f"Error subiendo a Facebook: {resultado}")
            return False

    except Exception as error:
        if logger:
            logger.error(f"Excepción subiendo a Facebook: {error}")
        return False
