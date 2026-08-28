import sys
sys.path.insert(0, ".")
import os

import hsf_engine as motor


def main():
    if len(sys.argv) < 3:
        print('Uso: python arreglar_miniatura.py <VIDEO_ID> "Título"')
        sys.exit(1)

    video_id = sys.argv[1]
    titulo = sys.argv[2]

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

    credenciales = Credentials(
        None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=credenciales)

    ruta_miniatura = os.path.join(motor.CARPETA_MINIATURA_LOCAL, f"reparada_{video_id}.jpg")
    os.makedirs(motor.CARPETA_MINIATURA_LOCAL, exist_ok=True)

    print("Buscando plantilla en Drive...")
    ruta_plantilla = motor._obtener_plantilla_miniatura_desde_drive(logger=None)
    if not ruta_plantilla:
        print("=== ERROR: no se encontró la plantilla en gdrive:miniatura/miniatura_plantilla.png ===")
        sys.exit(1)

    print(f"Generando miniatura para: {titulo}")
    ok = motor.generar_miniatura_plantilla(titulo, ruta_plantilla, ruta_miniatura, logger=None)
    if not ok:
        print("=== ERROR: no se pudo generar la miniatura ===")
        sys.exit(1)

    print(f"Subiendo miniatura a video {video_id}...")
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(ruta_miniatura, mimetype="image/jpeg"),
    ).execute()
    print("=== ✅ Miniatura arreglada correctamente ===")


if __name__ == "__main__":
    main()
