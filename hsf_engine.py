import base64
"""
HSF Engine — núcleo del generador de video (repo hsf-engine).

Motor de generación de video (voz, subtítulos, música, efectos) para el
canal "Historias Sin Filtro". Esta es la primera entrega del proyecto
nuevo: solo el núcleo (texto -> voz -> subtítulos -> video -> miniatura
local), SIN la parte de subida a YouTube todavía — esa se agrega en una
etapa siguiente una vez confirmado que el núcleo corre bien en este repo.
"""

# ============================================================
# ---- módulo original: config.py ----
# ============================================================
import os

# =====================================================================
# CONFIGURACIÓN GLOBAL — carpetas, constantes y versión del programa.
# =====================================================================

# Todas las carpetas se anclan a la ubicación real del paquete (no al
# directorio de trabajo actual del proceso), por la misma razón que estaba
# documentada en el script original: Flask resuelve rutas relativas contra
# el root_path de la app, mientras que os.makedirs las resuelve contra el
# cwd del proceso, y esos dos podían no coincidir según desde dónde se
# lanzara el atajo de Termux. Ahora que todo el código vive en un solo
# archivo, CARPETA_BASE es simplemente la carpeta que contiene a este
# mismo archivo (gen_hsf.py).
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))

CARPETA_SALIDA = os.path.join(CARPETA_BASE, "salidas_hsf")
CARPETA_VIDEOS = os.path.join(CARPETA_BASE, "videos_hsf")
CARPETA_IMAGENES_SUBIDAS = os.path.join(CARPETA_BASE, "imagenes_hsf")
CARPETA_IMAGENES_STOCK = os.path.join(CARPETA_BASE, "imagenes_stock_hsf")
CARPETA_MUSICA = os.path.join(CARPETA_BASE, "musica_hsf")
CARPETA_FUENTES = os.path.join(CARPETA_BASE, "fuentes_hsf")
CARPETA_LOGS = os.path.join(CARPETA_BASE, "logs_hsf")
CARPETA_PREVIEWS_VOZ = os.path.join(CARPETA_BASE, "previews_voz_hsf")

# ---- Fuentes reales de contenido (v5.4): texto ya parafraseado (repo
# "traduce") y gameplay propio (gameplay_slither), ambos sincronizados
# desde Google Drive vía rclone. Reemplazan a Mumsnet/Reddit en vivo y a
# las imágenes de stock (Pexels/Pixabay) para el pipeline automático de
# GitHub Actions -- la interfaz manual /reddit conserva esas fuentes
# viejas por si se quieren usar aparte, pero _pipeline_video_automatico ya
# no las usa.
CARPETA_TEXTOS_LISTOS = os.path.join(CARPETA_BASE, "textos_listos_gdrive")
CARPETA_GAMEPLAY_LOCAL = os.path.join(CARPETA_BASE, "gameplay_local_gdrive")
CARPETA_MINIATURA_LOCAL = os.path.join(CARPETA_BASE, "miniatura_local_gdrive")
RCLONE_REMOTE_TXT_LIMPIO = "gdrive:txt-limpio"
RCLONE_REMOTE_TXT_LIMPIO_USADOS = f"{RCLONE_REMOTE_TXT_LIMPIO}/usados"
RCLONE_REMOTE_GAMEPLAY = "gdrive:gameplay_slither"
RCLONE_REMOTE_MINIATURA = "gdrive:miniatura"
CARPETA_INTRO_LOCAL = os.path.join(CARPETA_BASE, "intro_local_gdrive")
RCLONE_REMOTE_INTRO = "gdrive:intro"

for _c in [CARPETA_TEXTOS_LISTOS, CARPETA_GAMEPLAY_LOCAL]:
    os.makedirs(_c, exist_ok=True)

for c in [CARPETA_SALIDA, CARPETA_VIDEOS, CARPETA_IMAGENES_SUBIDAS, CARPETA_IMAGENES_STOCK,
          CARPETA_MUSICA, CARPETA_FUENTES, CARPETA_LOGS, CARPETA_PREVIEWS_VOZ]:
    os.makedirs(c, exist_ok=True)

# Todo lo que se copia al celular (audio, video, logs) va dentro de esta
# única subcarpeta de Download, en vez de sueltos directo en Download o en
# Movies. El "0_" la manda arriba de todo, ya que Download ordena alfabéticamente.
NOMBRE_CARPETA_DESCARGAS = "0_Papelera_Scripts"

RESOLUCION_ANCHO, RESOLUCION_ALTO = 1920, 1080
FPS = 24
SEGUNDOS_UN_DIA = 24 * 60 * 60
PREFIJO_LOG = "hsf_log_"

# ============================================================================
# BITÁCORA DE CAMBIOS
# ----------------------------------------------------------------------------
# v1.5 - Se quitó el selector de idioma/voz en inglés (VOCES_INGLES, el
#        desplegable "Voz / Idioma" y el botón "Escuchar" de prueba de
#        voces): ahora el narrador usa siempre la voz de Alex en español
#        (es-PE-AlexNeural, vía edge_tts). Quedan intactos los controles
#        de velocidad y tono, y la traducción automática con DeepL (ahora
#        siempre traduce a español).
# v1.6 - Ajustado para historias largas (mínimo ~20 minutos de video):
#        PALABRAS_MIN/MAX_HISTORIA pasó de 250-900 a 2600-7000 palabras,
#        UPVOTES_MINIMOS_HISTORIA bajó de 200 a 80 (las historias largas
#        con muchos upvotes son más raras), y la búsqueda en Reddit ahora
#        trae hasta 50 posts por subreddit del último mes (antes 15 de la
#        última semana) para tener más candidatos que puedan cumplir el
#        filtro de longitud más exigente. También se subió el límite del
#        guion de 30.000 a 60.000 caracteres (texto + campo de la
#        interfaz + truncado del backend), porque una historia de 7000
#        palabras más lo que agrega Gemini podía superar los 30.000.
# v1.7 - Se sacó el filtro de longitud de historias (PALABRAS_MIN/MAX_HISTORIA
#        pasó de 2600-7000 a 1-100000: prácticamente sin filtro) y se bajó
#        UPVOTES_MINIMOS_HISTORIA de 80 a 0, para que por ahora traiga
#        cualquier historia disponible, chica o grande, sin quedarse sin
#        candidatos. El límite del guion (textarea, contador y truncado
#        del backend) subió de 60.000 a 500.000 caracteres.
# v1.8 - Reddit estaba devolviendo 403 (Blocked) en las 5 consultas del
#        JSON público, para todos los subreddits. Se cambió www.reddit.com
#        por old.reddit.com y se reemplazó el User-Agent genérico
#        ("story-engine/1.0") por uno de navegador real (Chrome en
#        Windows) + headers Accept/Accept-Language, para intentar esquivar
#        el bloqueo automático. Si sigue bloqueando, el siguiente paso es
#        migrar a la API oficial con PRAW (credenciales gratuitas de
#        Reddit), como ya estaba previsto en el plan original.
# v1.9 - Se reemplazó el scraping del JSON público de Reddit (que Reddit
#        terminó bloqueando de nuevo) por la API oficial vía PRAW,
#        autenticada con REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET (app tipo
#        "script" creada en reddit.com/prefs/apps). Hay que completar esas
#        dos constantes al principio del bloque de Reddit para que funcione.
# v2.0 - Reddit eliminó la creación de apps de API por autoservicio
#        (Responsible Builder Policy), así que se sacó PRAW y se volvió al
#        scraping, pero más resistente al bloqueo: el JSON ahora prueba
#        varios dominios (www/old/reddit.com) y rota entre 5 User-Agents de
#        navegadores reales en cada intento; si un subreddit sigue sin traer
#        nada por JSON, se cae automáticamente a un segundo método por RSS
#        (que Reddit bloquea menos). Se agregó una pausa corta entre
#        subreddits para no parecer un bot agresivo.
# v2.1 - Se puso la clave de GEMINI_API_KEY, así que ahora "Traer historia
#        de Reddit" (pantalla principal) entrega el guion ya traducido al
#        español y adaptado. En esa misma pantalla: el cuadro de texto se
#        agrandó (de 66px a 220px de alto), los botones Pegar/Borrar pasaron
#        a ser íconos flotantes arriba a la derecha del cuadro (en vez de
#        una fila debajo), y se agregó un tercer ícono "Copiar todo" al
#        lado. El piloto Reddit (pantalla aparte /reddit/piloto) queda sin
#        tocar y sin usarse: todo el flujo real es desde la pantalla
#        principal.
# v2.2 - Ahora "Traer historia de Reddit" apunta a un video de 28-30
#        minutos: si encuentra una sola historia lo bastante larga, la usa
#        sola; si no, combina 2 o 3 historias entre las más votadas hasta
#        que la suma de palabras entre en ese rango (ajustable en
#        PALABRAS_OBJETIVO_MIN/MAX), y arma un solo guion con Gemini que
#        las une con transiciones cortas entre cada una. Si ninguna
#        combinación entra en rango, usa la historia individual más
#        votada igual, para no quedarse sin nada.
# v2.3 - Se corrigió GEMINI_API_KEY: la clave pegada antes estaba
#        duplicada (el mismo código copiado dos veces seguidas), lo que
#        hacía fallar la llamada a Gemini y el script devolvía la historia
#        sin traducir como respaldo. Ahora tiene la clave correcta, una
#        sola vez.
# v2.4 - Prueba real mostró que Gemini resumía bastante al traducir: 3
#        historias que sumaban ~3900-4400 palabras en inglés terminaron en
#        un guion de ~3260 palabras (~21.8 min, no 28-30). Se subió el
#        rango de selección PALABRAS_OBJETIVO_MIN/MAX de 3600-4400 a
#        4400-5400 para compensar esa reducción, y se le pidió explícito
#        a Gemini en los dos prompts que NO resuma de más (solo lo
#        claramente repetitivo), ya que el largo se elige a propósito.
# v2.5 - Reddit cerró en mayo de 2026 el acceso anónimo a los .json (403 en
#        el 100% de los casos) y empezó a limitar fuerte el RSS también
#        (429), incluso en old.reddit.com. Con las 5 vías bloqueadas el
#        mismo día, solo se rescataba 1 historia corta por corrida. Se
#        agregaron dos vías nuevas, en este orden de intento por
#        subreddit: (1) JSON con sesión logueada (cookies de una cuenta
#        real vía REDDIT_USUARIO/REDDIT_CONTRASENA — el bloqueo de mayo
#        2026 es solo para tráfico anónimo, autenticado sigue andando),
#        (2) JSON anónimo rotando dominio/User-Agent (como antes), (3) RSS
#        (como antes), y (4) para r/AITAH específicamente, un dataset
#        local descargado de antemano (RUTA_DATASET_AITA) con ~270.000
#        historias históricas de ese subreddit, como red de seguridad
#        para que nunca falte candidato aunque Reddit bloquee todo ese
#        día. El dataset no cuenta como "usado" hasta que realmente se
#        elige, igual que las demás vías.
# v2.6 - El login de Reddit se intenta una sola vez por arranque del
#        servidor y queda cacheado en memoria: los intentos siguientes no
#        volvían a escribir nada en el log, lo que hacía parecer que el
#        login nunca se ejecutaba. Ahora cada corrida deja explícito en el
#        log si está usando sesión cacheada o no. En la pantalla principal:
#        se sacó el texto de ejemplo (la cita estoica) que venía
#        precargado en el cuadro de guion, se ocultó la caja de vista
#        previa de video con los controles de arrastre (quedó sin uso real
#        para este flujo, enfocado en audio narrado), y se agregó el botón
#        "🔊 Generar audio y descargar" al lado de "Traer historia de
#        Reddit", que arma el audio del guion actual y deja un enlace de
#        descarga + reproductor, reusando el mismo backend que ya usaba la
#        pantalla de piloto.
# v2.7 - El fallback de sesión cacheada de v2.6 avisaba QUE el login había
#        fallado en un arranque anterior, pero no decía POR QUÉ (el motivo
#        real solo se veía en el log del primer intento, que no siempre se
#        guarda). Ahora el motivo del fallo queda guardado en memoria y se
#        repite en el log de cada corrida siguiente también, para poder
#        diagnosticar sin depender de haber capturado justo el primer
#        intento.
# v2.8 - Un solo 429 (límite de pedidos por minuto) de Gemini hacía caer
#        directo al texto sin traducir, algo fácil de pisar en pruebas
#        seguidas. Ahora generar_guion_reddit() reintenta hasta 4 veces
#        con espera creciente (5s, 10s, 20s...), respetando el header
#        Retry-After si Gemini lo manda, antes de rendirse y devolver el
#        texto original. Sigue sin cortar el pipeline si todos los
#        intentos fallan.
# v2.9 - El 429 persistente de Gemini no era por límite de pedidos: el
#        modelo GEMINI_MODELO ("gemini-2.0-flash") fue retirado por Google
#        el 31 de marzo de 2026, así que ninguna espera lo iba a arreglar.
#        Se cambió a "gemini-2.5-flash" (modelo vigente, tier gratis con
#        más margen). Los reintentos de v2.8 quedan igual, por si en el
#        futuro se vuelve a pisar el límite real de pedidos por minuto.
# v2.10 - Los dos prompts de Gemini (PROMPT_GUION_REDDIT y
#         PROMPT_GUION_REDDIT_MULTIPLE) asumían siempre jerga de Reddit
#         (AITA/YTA/NTA). Se agregaron reglas explícitas para que Gemini
#         también traduzca bien historias de foros británicos tipo
#         Mumsnet/AIBU: conversión de AIBU/YABU/YANBU al mismo formato de
#         pregunta-veredicto que ya se usaba, más jerga de foro (WWYD, LTB,
#         STBXH/STBXW, IMHO, HTH/RTFT), acrónimos de parentesco (DH, DD,
#         DS, DP, DC, PIL, MIL, FIL), qué hacer con nombres de usuario
#         citados, y cuándo aclarar referencias culturales locales (NHS,
#         etc.) sin sobre-explicar. Esto es solo el prompt: el script
#         todavía no trae historias de Mumsnet, sigue usando las mismas
#         fuentes de Reddit (obtener_historia_reddit); estas reglas quedan
#         listas para cuando se agregue esa fuente.
# v2.11 - Se integró Mumsnet/AIBU como fuente adicional de historias
#         (funciones _listar_hilos_mumsnet, _traer_hilo_mumsnet,
#         _candidatos_por_mumsnet), sumándose a los subreddits de siempre
#         dentro de obtener_historia_reddit — no los reemplaza. AVISO
#         IMPORTANTE: a diferencia del scraper de Reddit, que se probó
#         contra el JSON real, este scraper de Mumsnet se armó sin poder
#         confirmar el HTML real de mumsnet.com (no hay acceso a internet
#         desde donde se escribió este código: se dedujo el patrón a
#         partir de una lectura de las páginas convertida a texto, no del
#         HTML crudo). Puede que _listar_hilos_mumsnet o
#         _traer_hilo_mumsnet no encuentren nada la primera vez que
#         corran de verdad en Termux. Si eso pasa: el log va a avisar
#         "Mumsnet: el índice no devolvió ningún hilo" o "no se encontró
#         el inicio del post" — mandar ese log de vuelta para ajustar los
#         patrones con el caso real, el mismo proceso iterativo que ya se
#         usó para el scraper de Reddit (v1.8 a v2.6). Mientras tanto, si
#         esta fuente no aporta nada, el pipeline sigue funcionando igual
#         solo con Reddit (nunca corta el programa).
# v2.12 - Se hizo más robusta la generación de voz con edge_tts: antes solo
#         se reintentaba (hasta 3 veces) cuando edge_tts tiraba un error de
#         conexión explícito. Ahora, además, cada parte de audio generada
#         se valida leyendo su duración con ffprobe DENTRO del mismo bucle
#         de reintento (no recién más adelante en otra función): así se
#         detectan tanto audios vacíos como audios cortados a la mitad por
#         un corte de conexión momentáneo, y ambos casos entran al mismo
#         reintento automático en vez de tumbar el video entero. También se
#         agregó el botón "🔄 Otra historia" en el piloto Reddit para
#         descartar la historia mostrada (sin generar video) y traer una
#         distinta, vía la nueva ruta /reddit/descartar_historia.
# v3.9 - Se agregó auto-actualización de edge-tts: al arrancar el servidor
#        se compara en segundo plano la versión instalada contra la última
#        publicada en PyPI y, si hay una más nueva, se instala sola con pip
#        (sin bloquear el arranque). Esto ataca la causa real del error
#        "NoAudioReceived"/audio vacío que venía dando es-PE-AlexNeural: no
#        es un problema de la voz ni del script, sino de la librería
#        edge-tts desactualizada perdiendo sincronía con cambios del lado
#        de Microsoft. Si después de los 3 reintentos normales la
#        generación de voz sigue fallando, ahora se dispara una
#        actualización forzada única y un reintento extra antes de recién
#        ahí devolver el error.
#        Los botones de audio se separaron en 4 botones independientes, sin
#        mezclar y sin desplegables: "Escuchar ES", "Descargar audio ES",
#        "Escuchar EN" y "Descargar audio EN". Antes "Generar audio" hacía
#        escuchar+descargar juntos en un solo botón para español, y el de
#        inglés generaba el audio pero nunca mostraba el guion adaptado en
#        pantalla (por eso no se veían los caracteres en inglés en ningún
#        cuadro de texto: el backend sí lo generaba y lo mandaba en la
#        respuesta, pero el JS nunca lo escribía en el DOM). Ahora "Escuchar
#        EN" también vuelca ese guion en inglés a un cuadro de texto de
#        solo lectura debajo del botón.
# v4.0 - Se corrigió "Invalid pitch '0Hz'." en el audio en inglés: la
#         constante TONO_NARRADOR_INGLES estaba sin el signo (edge_tts
#         exige +/-), pasó de "0Hz" a "+0Hz" (bug viejo, no introducido en
#         la v3.9). Además, el cuadro de guion en inglés ahora muestra un
#         contador de caracteres arriba, y se agregó un cuadro nuevo debajo
#         con la traducción al español de ese guion en inglés (vía DeepL;
#         si falla la traducción, el cuadro queda vacío sin cortar la
#         generación del audio).
# v4.1 - Se agregó un botón "Escuchar ES (voz alt.)" con VOZ_NARRADOR_ALT =
#        "es-MX-JorgeNeural", para probar si el "audio vacío o dañado" es
#        específico de es-PE-AlexNeural o algo más general. Se confirmó
#        además que el pitch en español (TONO="-10Hz", VELOCIDAD="-10%")
#        ya tenía el signo puesto correctamente: ese no era el problema
#        del lado español (a diferencia del de inglés, corregido en v4.0).
# v4.2 - La prueba de v4.1 confirmó que el "audio vacío o dañado" fallaba
#        con la voz principal Y con la alternativa (y también en inglés):
#        no es un problema de una voz puntual ni de este script, sino del
#        servicio no oficial de Microsoft detrás de edge_tts, que a veces
#        deja de responder con audio real para todo el mundo durante un
#        rato, incluso con la librería ya actualizada (la auto-actualización
#        de la v3.9 no alcanza para esos casos). Para que el pipeline NUNCA
#        se quede sin audio por esto, se agregó gTTS (servicio de Google,
#        independiente del de Microsoft) como motor de emergencia: si
#        edge_tts agota los 3 reintentos normales Y el reintento extra tras
#        la actualización forzada, en vez de tirar el error se genera el
#        audio con gTTS automáticamente (instalándolo solo si hace falta).
#        gTTS no soporta tono (pitch), así que en ese modo el audio queda
#        con tono neutro (se avisa en el log); la velocidad configurada sí
#        se le aplica después, vía ffmpeg. Tampoco da tiempos de palabra
#        reales, así que en ese caso los subtítulos usan tiempos repartidos
#        parejo entre las palabras según la duración real del audio, en vez
#        de los tiempos exactos que da edge_tts.
# v4.3 - Se agregó, al final de la página principal, un probador de voces
#        en español: un desplegable con las ~44 voces neuronales en
#        español que ofrece edge_tts (una femenina y una masculina por
#        cada país/variante), un cuadro de texto de ejemplo precargado con
#        100 caracteres (editable), y un botón "▶️ Reproducir ejemplo" que
#        genera y reproduce un audio corto con la voz elegida. Usa la
#        misma función robusta de generación de audio que ya tiene
#        reintentos y el fallback de gTTS de la v4.2 (no la función de
#        preview vieja, que no tenía ninguna de esas protecciones), así
#        que este probador tampoco se queda sin sonido si edge_tts falla.
# v4.4 - Se corrigió que el fallback de gTTS (agregado en la v4.2) tapaba
#        su propio error real: si gTTS también fallaba, se perdía el
#        motivo (se mostraba de nuevo el viejo error de edge_tts) y no
#        había forma de saber por qué. Ahora se loguea el error de gTTS
#        aparte y se junta con el de edge_tts en un solo mensaje final,
#        para poder ver la causa real de ambos fallos.
# v4.5 - Se agregó más registro de diagnóstico al fallback de gTTS: ahora
#        loguea el tamaño en bytes del audio crudo que devuelve gTTS
#        (antes de ajustarle la velocidad con ffmpeg) y el tamaño del
#        archivo final, y si gTTS devuelve un archivo de 0 bytes lo dice
#        explícitamente en vez de dejar que ffmpeg lo procese a ciegas.
#        Esto es solo para terminar de diagnosticar el reporte de "ninguna
#        voz en español funciona" (donde el log de la v4.4 mostró que
#        ffprobe fallaba sobre el archivo final de gTTS, pero sin decir en
#        qué paso se había generado mal: si en gTTS mismo o en el ajuste
#        de velocidad con ffmpeg de después).
# v4.6 - El "Probador de voces en español" (sección de abajo de la página)
#        narraba el texto tal cual, sin traducir: útil para probar una
#        voz con texto ya en español, pero no servía para pegar un guion
#        de Mumsnet/Reddit sin traducir y escucharlo ya en español. Se
#        agregó: (1) casillero "Traducir con Gemini antes de narrar",
#        que llama a la nueva traducir_texto_gemini() (misma lógica de
#        reintentos ante 429 que generar_guion_reddit, pero para texto
#        libre en vez del formato de "grupo" de historias) antes de
#        generar la voz, y vuelca el texto traducido de vuelta al
#        textarea; y (2) controles propios de velocidad y tono debajo
#        del selector de voz (antes ese probador siempre usaba los
#        valores fijos TONO/VELOCIDAD del narrador principal, sin poder
#        ajustarlos ahí).
# v4.7 - Se sacaron las dos herramientas de prueba de voz que se habían ido
#        acumulando para diagnóstico (v4.1 y v4.6): el botón "Escuchar ES
#        (voz alt.)" con VOZ_NARRADOR_ALT, y toda la sección "Probador de
#        voces en español" (selector con las 44 voces de edge_tts,
#        traducción con Gemini y sus propios sliders). Se sacó también el
#        código que quedaba huérfano al sacar eso: VOZ_NARRADOR_ALT,
#        VOCES_ESPANOL, TEXTO_EJEMPLO_VOZ_ES, traducir_texto_gemini()/
#        PROMPT_TRADUCIR_LIBRE, generar_preview_voz()/TEXTO_PRUEBA_VOZ y
#        la ruta /preview_voz_espanol y /generar_audio_prueba_alt. Los
#        sliders de velocidad y tono que tenía el probador se movieron a
#        la sección AUDIO — ESPAÑOL (junto a "Escuchar ES"/"Descargar
#        audio ES"), que ahora los manda al generar/descargar el audio en
#        español en vez de usar siempre los valores fijos TONO/VELOCIDAD.
# v4.8 - Nueva paleta de colores en toda la interfaz web (pantalla principal
#        y pantalla de piloto Reddit): base violeta-azulado muy oscuro
#        (#150e2b), acento principal magenta eléctrico (#ff2e88, antes
#        coral #ff6b6b), y dos acentos nuevos en esquema tríada: cian
#        (#00e5ff, reemplaza --verdigris) y lima (#d4ff3d, --accent3, aún
#        sin usar en ningún elemento). Modo claro actualizado en la misma
#        línea. Colores vívidos pero con jerarquía: violeta domina,
#        magenta para acciones principales, cian/lima quedan disponibles
#        para diferenciar acciones secundarias más adelante.
# v5.0 - Rediseño estructural de la sección "Guion" en dos recuadros
#        independientes y autosuficientes: "Guion (idioma original)"
#        (el cuadro #texto de siempre) con sus propios botones "Generar
#        audio"/"Descargar audio" (voz Ryan) y un botón nuevo "Traducir";
#        y "Guion traducido (español)" (oculto hasta tocar "Traducir"),
#        con los sliders de velocidad/tono arriba y sus propios botones
#        de audio (voz Alex). Cambios de fondo:
#        - "Traer historia" ya NO traduce: /traer_historia ahora arma el
#          guion con generar_guion_ingles() en vez de generar_guion_reddit(),
#          así que carga tal cual en el idioma original.
#        - Nueva ruta /traducir_guion (POST): traduce a español el texto
#          que mande el frontend, con traducir_texto_deepl() (la
#          traducción con Gemini se había sacado en la v4.7; se usa DeepL
#          porque es la que seguía disponible en el código).
#        - /generar_audio_ingles ahora recibe el guion editable desde el
#          frontend (como ya hacía /generar_audio_prueba) en vez de
#          regenerarlo con generar_guion_ingles(), y acepta
#          velocidad_voz/tono_voz: los sliders pasan a compartirse entre
#          los dos idiomas en vez de usar TONO_NARRADOR_INGLES/
#          VELOCIDAD_NARRADOR_INGLES fijos.
#        - Se sacaron los campos de solo lectura textoIngles/
#          textoInglesEspanol y los bloques "AUDIO — ESPAÑOL"/
#          "AUDIO — INGLÉS": todo vive ahora en los dos recuadros nuevos.
# v5.1 - Se reactivó el filtro de longitud de historias (PALABRAS_MIN_HISTORIA,
#        que desde la v1.7 estaba en 1, o sea sin filtro real). Ahora
#        PALABRAS_MIN_HISTORIA = 800: se descartan las historias de texto
#        corto y solo entran las de texto largo (~6 min de narración en
#        adelante). Sin techo (PALABRAS_MAX_HISTORIA sigue en 100000).
# v5.2 - Se sacó toda la interfaz web (Blueprint de Flask reddit_bp, las
#        plantillas PLANTILLA/PLANTILLA_PILOTO, la ruta /piloto y main())
#        de este archivo. Esta versión queda solo para GitHub/la nube; la
#        interfaz web sigue viva en la copia de Termux, que no se toca.
# v5.3 - Se agregaron _pipeline_video_automatico y
#        _subir_ultimo_resultado_a_youtube, que run_once.py necesitaba
#        importar y no existían en ninguna versión anterior (por eso el
#        workflow publicar.yml fallaba con ImportError apenas arrancaba,
#        sin generar ni publicar nunca un video). Encadenan
#        obtener_historia_reddit -> generar_guion_reddit -> procesar_todo
#        de forma síncrona, y suben el resultado a YouTube vía OAuth
#        (refresh token) con googleapiclient. Se sacaron del código todas
#        las credenciales que quedaban en texto plano: REDDIT_USUARIO/
#        REDDIT_CONTRASENA, DEEPL_API_KEY, y los respaldos hardcodeados de
#        PEXELS_API_KEYS/PIXABAY_API_KEYS — todas ahora se leen solo de
#        variables de entorno / GitHub Secrets. Se actualizó también
#        GEMINI_MODELO de "gemini-2.5-flash" (dado de baja por Google) a
#        "gemini-3.5-flash-lite".
# v5.4 - Se sacó por completo el scraping en vivo de Reddit (login, JSON,
#        RSS) y de Mumsnet (listar/traer hilos): Reddit bloqueaba el
#        tráfico anónimo con 403 y Mumsnet dejó de traer historias. La
#        única fuente de historias que queda es el dataset local
#        (RUTA_DATASET_AITA / dataset_aita.csv) — si ese archivo no está
#        subido al dataset de Hugging Face que descarga el workflow, el
#        pipeline automático no va a tener de dónde traer historias.
# ============================================================================

# Versión del script. Se sube manualmente (1.0 -> 1.1 -> 1.2 ...) cada vez que se hace
# una mejora o se corrige un error, para que se sepa qué versión está corriendo en Termux
# y en la interfaz web sin tener que preguntar.
# Convención de numeración: al llegar a x.9, la siguiente versión pasa al
# entero siguiente (x.9 -> (x+1).0), no sigue a x.10, x.11, etc.
# Story Engine arranca en 1.0: es un proyecto nuevo a partir de Gen HSF V5.5,
# no continúa su numeración.
VERSION_SCRIPT = "5.4"

# Velocidad de los efectos de video animados (ceniza y vela). Solo estos dos
# tienen una noción de "velocidad" porque son los únicos con movimiento en
# el tiempo; el resto de los efectos son estáticos. El valor es un
# multiplicador: 1.0 = velocidad original, <1.0 = más lento, >1.0 = más
# rápido.
VELOCIDAD_EFECTO_MIN, VELOCIDAD_EFECTO_MAX = 0.3, 2.5
VELOCIDAD_EFECTO_POR_DEFECTO = 1.0

# ============================================================
# ---- módulo original: texto.py ----
# ============================================================
import re

# ===================== Procesamiento de Texto =====================


def limpiar_texto_para_voz(texto):
    lineas = texto.split("\n")
    lineas_limpias = []
    for linea in lineas:
        l = linea.replace("\u200b", "").strip()
        if not l: continue
        l = re.sub(r"[*#_`~]", "", l)
        l = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]", "", l)
        if l: lineas_limpias.append(l)
    return re.sub(r"\s+", " ", " ".join(lineas_limpias)).strip()


def dividir_en_bloques(texto_limpio, frases_por_bloque=3):
    frases = re.split(r"(?<=[.!?])\s+", texto_limpio.strip())
    frases = [f.strip() for f in frases if f.strip()]
    bloques, actual, chars_actual = [], [], 0
    LIMITE_CHARS = 220
    for frase in frases:
        if actual and (len(actual) >= frases_por_bloque or chars_actual + len(frase) > LIMITE_CHARS):
            bloques.append(" ".join(actual))
            actual, chars_actual = [], 0
        actual.append(frase)
        chars_actual += len(frase)
    if actual:
        bloques.append(" ".join(actual))
    return bloques

# ============================================================
# ---- módulo original: logs.py ----
# ============================================================
import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime


# =====================================================================
# LOGS: cada video generado tiene su propio archivo de log con hora
# exacta (incluidos milisegundos), que arranca desde el instante en que
# se recibe la orden de generar. Además hay un log general de eventos
# aparte ("..._eventos.txt") que registra cuándo arranca/se cierra el
# servidor, y si el programa se cierra o se actualiza mientras se está
# generando un video, eso también queda anotado ahí y en el log de ese
# video.
# =====================================================================


def _carpeta_logs_real():
    carpeta_download = "/sdcard/Download"
    if os.path.isdir(carpeta_download):
        carpeta = os.path.join(carpeta_download, NOMBRE_CARPETA_DESCARGAS)
        os.makedirs(carpeta, exist_ok=True)
        return carpeta
    return CARPETA_LOGS


def limpiar_logs_antiguos():
    limite = time.time() - SEGUNDOS_UN_DIA
    carpeta = _carpeta_logs_real()
    try:
        for nombre in os.listdir(carpeta):
            if not (nombre.startswith(PREFIJO_LOG) and nombre.endswith(".txt")):
                continue
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta) and os.path.getmtime(ruta) < limite:
                try: os.remove(ruta)
                except Exception: pass
    except Exception: pass


FORMATO_LOG = logging.Formatter("%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s", datefmt="%H:%M:%S")


def crear_logger_video():
    limpiar_logs_antiguos()
    marca = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_log = os.path.join(_carpeta_logs_real(), f"{PREFIJO_LOG}{marca}.txt")

    logger = logging.getLogger(f"hsf_{marca}_{id(threading.current_thread())}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    manejador = logging.FileHandler(ruta_log, encoding="utf-8")
    manejador.setFormatter(FORMATO_LOG)
    logger.addHandler(manejador)

    # También manda todo a consola (stdout): en GitHub Actions el archivo
    # de log local nunca queda visible en la pestaña Actions, así que sin
    # esto no hay forma de ver qué pasó durante la corrida (como ocurrió
    # con el intento de subir la miniatura).
    manejador_consola = logging.StreamHandler()
    manejador_consola.setFormatter(FORMATO_LOG)
    logger.addHandler(manejador_consola)
    return logger, ruta_log


def cerrar_logger_video(logger):
    for h in list(logger.handlers):
        try: h.close()
        except Exception: pass
        logger.removeHandler(h)


# ---- Log general de eventos del servidor (arranques, cierres, actualizaciones) ----
# Este log es distinto al de cada video: queda un solo archivo que junta todos los
# eventos del programa aunque el script se reinicie o se actualice.

RUTA_LOG_EVENTOS = os.path.join(_carpeta_logs_real(), "hsf_eventos.txt")
_logger_eventos = logging.getLogger("hsf_eventos")
_logger_eventos.setLevel(logging.DEBUG)
_logger_eventos.propagate = False
if not _logger_eventos.handlers:
    _manejador_eventos = logging.FileHandler(RUTA_LOG_EVENTOS, encoding="utf-8")
    _manejador_eventos.setFormatter(FORMATO_LOG)
    _logger_eventos.addHandler(_manejador_eventos)


def log_evento(mensaje):
    try:
        _logger_eventos.info(mensaje)
        for h in _logger_eventos.handlers:
            h.flush()
    except Exception:
        pass


# Referencia al logger del video que se está generando en este momento (si hay uno),
# para poder anotar en SU log si el proceso se cae o se actualiza a mitad de camino.
LOGGER_VIDEO_ACTIVO = {"logger": None, "ruta": None}


def _registrar_interrupcion(motivo):
    """Si hay un video generándose cuando el proceso recibe una señal de cierre/actualización,
    deja constancia tanto en el log de ese video como en el log general de eventos."""
    logger_activo = LOGGER_VIDEO_ACTIVO.get("logger")
    if logger_activo:
        try:
            logger_activo.error(f"⚠️ El proceso se detuvo/actualizó mientras se generaba el video ({motivo}).")
            for h in logger_activo.handlers:
                h.flush()
        except Exception:
            pass
    log_evento(f"⚠️ Servidor detenido/actualizado ({motivo}). Video en curso: {LOGGER_VIDEO_ACTIVO.get('ruta')}")


def _manejador_senal(numero_senal, frame):
    _registrar_interrupcion(f"señal {numero_senal}")
    sys.exit(0)


try:
    signal.signal(signal.SIGTERM, _manejador_senal)
    signal.signal(signal.SIGINT, _manejador_senal)
except Exception:
    pass

# ============================================================
# ---- módulo original: fuentes.py ----
# ============================================================
import os
import requests


# ===================== Fuentes =====================

FUENTES_DISPONIBLES = {
    "Montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-SemiBold.ttf",
    "Playfair Display": "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/static/PlayfairDisplay-BoldItalic.ttf",
    "Cormorant Garamond": "https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond-Bold.ttf",
    "EB Garamond": "https://github.com/google/fonts/raw/main/ofl/ebgaramond/static/EBGaramond-Bold.ttf",
    "Lora": "https://github.com/google/fonts/raw/main/ofl/lora/static/Lora-Bold.ttf",
}
# Montserrat SemiBold como nueva fuente por defecto: para historias de Reddit
# en horizontal (1920x1080) se lee mejor una tipografía limpia tipo sans-serif
# que las serif decorativas que traía el proyecto original (esas siguen
# disponibles en el desplegable por si se prefiere ese estilo).
FUENTE_POR_DEFECTO = "Montserrat"


def asegurar_fuente(nombre_fuente):
    url = FUENTES_DISPONIBLES.get(nombre_fuente)
    if not url:
        nombre_fuente = FUENTE_POR_DEFECTO
        url = FUENTES_DISPONIBLES[FUENTE_POR_DEFECTO]

    ruta_destino = os.path.join(CARPETA_FUENTES, url.split("/")[-1])
    if not os.path.exists(ruta_destino) or os.path.getsize(ruta_destino) < 1000:
        try:
            respuesta = requests.get(url, timeout=15)
            respuesta.raise_for_status()
            with open(ruta_destino, "wb") as f: f.write(respuesta.content)
        except Exception:
            if nombre_fuente != FUENTE_POR_DEFECTO: return asegurar_fuente(FUENTE_POR_DEFECTO)
            return None
    return nombre_fuente

# ============================================================
# ---- módulo original: musica.py ----
# ============================================================
import os
import random


# ===================== Música =====================


def seleccionar_musica_fondo(genero):
    if genero == "ninguno": return None
    carpeta = os.path.join(CARPETA_MUSICA, genero)
    if os.path.isdir(carpeta):
        pistas = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith(".mp3")]
        if pistas: return random.choice(pistas)
    return None


for _genero in ["piano", "ambient", "cuerdas"]:
    os.makedirs(os.path.join(CARPETA_MUSICA, _genero), exist_ok=True)

# ============================================================
# ---- módulo original: proyecto.py ----
# ============================================================
import os


# =====================================================================
# CARPETA DE PROYECTO POR VIDEO
# ---------------------------------------------------------------------
# Cada video generado tiene su propia carpeta (estilo carpeta de proyecto
# de edición: voz, imagen, subtítulos y efecto separados), en vez de que
# todos los archivos intermedios queden sueltos y mezclados en una sola
# carpeta general. El video final también queda adentro, en la raíz de la
# carpeta del proyecto.
# =====================================================================


def crear_carpeta_proyecto(nombre_base, marca):
    """Crea (si no existe) la carpeta del proyecto para un video puntual,
    con una subcarpeta por tipo de archivo. Devuelve un diccionario con las
    rutas absolutas de cada subcarpeta más la raíz del proyecto."""
    nombre_proyecto = f"{nombre_base}_{marca}"
    raiz = os.path.join(CARPETA_VIDEOS, nombre_proyecto)
    rutas = {
        "nombre_proyecto": nombre_proyecto,
        "raiz": raiz,
        "voz": os.path.join(raiz, "voz"),
        "imagen": os.path.join(raiz, "imagen"),
        "subtitulos": os.path.join(raiz, "subtitulos"),
        "efecto": os.path.join(raiz, "efecto"),
    }
    for clave, ruta in rutas.items():
        if clave not in ("nombre_proyecto",):
            os.makedirs(ruta, exist_ok=True)
    return rutas

# ============================================================
# ---- módulo original: voz_stock.py ----
# ============================================================
import os
import random
import time
import requests


# ===================== Voz y Stock =====================

VOZ_NARRADOR = "es-PE-AlexNeural"

# Voz para el audio en inglés adaptado (v3.4). Pitch y velocidad quedan
# fijos (no editables desde la interfaz por ahora, a diferencia de la voz
# en español que sí tiene sliders).
VOZ_NARRADOR_INGLES = "en-GB-RyanNeural"
TONO_NARRADOR_INGLES = "+0Hz"
VELOCIDAD_NARRADOR_INGLES = "-10%"


# Pega aquí tu API key gratuita de DeepL (la consigues en https://www.deepl.com/pro-api → plan Free).
# Las keys del plan Free terminan en ":fx"
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")
DEEPL_URL_FREE = "https://api-free.deepl.com/v2/translate"
DEEPL_IDIOMA_DESTINO = {"es": "ES", "en": "EN-US"}


def traducir_texto_deepl(texto, idioma_destino, logger=None):
    """Traduce el texto al idioma del narrador usando la API gratuita de DeepL.
    Si no hay API key configurada o falla la petición, devuelve el texto original sin traducir."""
    if not DEEPL_API_KEY:
        if logger: logger.warning("DEEPL_API_KEY vacía: se omite la traducción, se usa el texto tal cual.")
        return texto
    destino = DEEPL_IDIOMA_DESTINO.get(idioma_destino)
    if not destino:
        return texto
    try:
        resp = requests.post(
            DEEPL_URL_FREE,
            headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
            data={"text": texto, "target_lang": destino},
            timeout=30,
        )
        resp.raise_for_status()
        datos = resp.json()
        return datos["translations"][0]["text"]
    except Exception as e:
        if logger: logger.warning(f"Fallo la traducción con DeepL, se usa el texto original: {e}")
        return texto


TONO = "-10Hz"
VELOCIDAD = "+5%"

# Velocidad y tono de voz ahora se ajustan con una barra deslizante (no con
# opciones predefinidas). El valor por defecto de cada barra coincide con
# TONO/VELOCIDAD de arriba, así que si no se toca nada el resultado es
# idéntico al de siempre. Los límites evitan que edge_tts reciba un valor
# absurdo si algo llega mal formado desde el formulario.
VELOCIDAD_VOZ_MIN, VELOCIDAD_VOZ_MAX = -50, 50
TONO_VOZ_MIN, TONO_VOZ_MAX = -50, 50
VELOCIDAD_VOZ_POR_DEFECTO = 5
TONO_VOZ_POR_DEFECTO = -5


def _formatear_ajuste_voz(valor, sufijo, por_defecto, minimo, maximo):
    """Convierte el número que manda la barra deslizante (ej. -10, 25) al
    formato que espera edge_tts (ej. '-10%', '+25Hz'), recortando a los
    límites permitidos si el valor es inválido o se pasa de rango."""
    try:
        v = int(float(valor))
    except (TypeError, ValueError):
        v = por_defecto
    v = max(minimo, min(maximo, v))
    return f"{v:+d}{sufijo}"


def _lista_claves(var_base, respaldos_fijos):
    claves = []
    for i in range(1, 11):
        var = var_base if i == 1 else f"{var_base}_{i}"
        v = os.environ.get(var)
        if v and v not in claves: claves.append(v)
    for r in respaldos_fijos:
        if r and r not in claves: claves.append(r)
    return claves


PEXELS_API_KEYS = _lista_claves("PEXELS_API_KEY", [])
PIXABAY_API_KEYS = _lista_claves("PIXABAY_API_KEY", [])

_claves_pexels_agotadas, _claves_pixabay_agotadas = set(), set()

# Términos de búsqueda para imágenes de fondo de historias tipo Reddit
# (confesiones, relatos personales). Reemplaza a la lista anterior de temática
# estoica (estatuas, ruinas), pensada para citas filosóficas.
TERMINOS_STOCK_FONDO = [
    "city night lights", "empty room window", "person silhouette thinking",
    "urban street rain", "dramatic storm clouds", "phone screen dark",
    "empty apartment", "car night drive", "coffee shop window",
    "text message screen", "hallway door closed", "city skyline dusk",
]


def _buscar_foto_pexels(consulta, evitar=None):
    evitar = evitar or set()
    claves = [k for k in PEXELS_API_KEYS if k not in _claves_pexels_agotadas]
    for clave in claves:
        try:
            res = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": clave}, params={"query": consulta, "orientation": "landscape", "per_page": 10}, timeout=10)
            if res.status_code == 429:
                _claves_pexels_agotadas.add(clave)
                continue
            if res.status_code != 200: return None
            fotos = res.json().get("photos", [])
            cand = [f["src"]["large2x"] for f in fotos if f.get("src", {}).get("large2x") and f["src"]["large2x"] not in evitar]
            if cand: return random.choice(cand)
        except Exception: return None
    return None


def _buscar_foto_pixabay(consulta, evitar=None):
    evitar = evitar or set()
    claves = [k for k in PIXABAY_API_KEYS if k not in _claves_pixabay_agotadas]
    for clave in claves:
        try:
            res = requests.get("https://pixabay.com/api/", params={"key": clave, "q": consulta, "image_type": "photo", "orientation": "horizontal", "per_page": 10}, timeout=10)
            if res.status_code == 429:
                _claves_pixabay_agotadas.add(clave)
                continue
            if res.status_code != 200: return None
            hits = res.json().get("hits", [])
            cand = [h["largeImageURL"] for h in hits if h.get("largeImageURL") and h["largeImageURL"] not in evitar]
            if cand: return random.choice(cand)
        except Exception: return None
    return None


def obtener_imagen_stock(indice, usadas, logger=None):
    terminos = TERMINOS_STOCK_FONDO[:]
    random.shuffle(terminos)
    for termino in terminos:
        url = _buscar_foto_pexels(termino, evitar=usadas) or _buscar_foto_pixabay(termino, evitar=usadas)
        if url:
            ruta_destino = os.path.join(CARPETA_IMAGENES_STOCK, f"stock_{indice}_{int(time.time())}.jpg")
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                with open(ruta_destino, "wb") as f: f.write(r.content)
                usadas.add(url)
                return ruta_destino
            except Exception: continue
    return None

# ============================================================
# ---- módulo original: audio.py ----
# ============================================================
import os
import re
import asyncio
import subprocess

import edge_tts


# ===================== Auto-actualización de edge-tts =====================
# La causa real detrás del error "NoAudioReceived"/audio vacío-dañado que
# venía dando edge_tts (confirmado contra los issues del repo oficial
# rany2/edge-tts) es que Microsoft cambia seguido detalles internos del
# servicio, y una versión vieja de la librería deja de "calzar" con eso:
# la conexión responde pero sin audio real, y ni siquiera reintentar
# soluciona nada si el paquete sigue desactualizado. Estas dos funciones
# atacan esa causa en vez de solo reintentar a ciegas.
_EDGE_TTS_YA_CHEQUEADO = False


def _version_instalada_edge_tts():
    try:
        import importlib.metadata
        return importlib.metadata.version("edge-tts")
    except Exception:
        return None


def _version_mas_nueva_edge_tts(timeout=6):
    """Consulta la API pública de PyPI (sin necesitar pip) para saber la
    última versión publicada de edge-tts. Devuelve None si no hay red o
    falla la consulta, sin cortar nada más del programa."""
    try:
        resp = requests.get("https://pypi.org/pypi/edge-tts/json", timeout=timeout)
        resp.raise_for_status()
        return resp.json()["info"]["version"]
    except Exception:
        return None


def actualizar_edge_tts_si_hace_falta(logger=None, forzar=False):
    """Compara versión instalada vs. la última de PyPI y, si hay una más
    nueva (o si 'forzar' es True, para el reintento de emergencia), corre
    'pip install --upgrade edge-tts' en un subproceso. No bloquea el
    arranque del servidor si algo falla (sin red, pip roto, etc.): solo
    queda un aviso en el log y el programa sigue con la versión que ya
    tenía instalada."""
    global _EDGE_TTS_YA_CHEQUEADO
    if _EDGE_TTS_YA_CHEQUEADO and not forzar:
        return
    _EDGE_TTS_YA_CHEQUEADO = True
    try:
        instalada = _version_instalada_edge_tts()
        ultima = _version_mas_nueva_edge_tts()
        if not ultima:
            if logger: logger.warning("No se pudo chequear la última versión de edge-tts en PyPI (sin red o falló la consulta); se sigue con la versión instalada.")
            return
        if instalada == ultima and not forzar:
            if logger: logger.info(f"edge-tts ya está en su última versión ({instalada}).")
            return
        if logger: logger.info(f"Actualizando edge-tts ({instalada} -> {ultima})...")
        resultado = subprocess.run(
            ["pip", "install", "--upgrade", "edge-tts", "--break-system-packages"],
            capture_output=True, text=True, timeout=90,
        )
        if resultado.returncode == 0:
            if logger: logger.info(f"edge-tts actualizado correctamente a {ultima}.")
        else:
            if logger: logger.warning(f"Falló la actualización de edge-tts (pip devolvió error): {resultado.stderr.strip()[:300]}")
    except Exception as e:
        if logger: logger.warning(f"No se pudo actualizar edge-tts automáticamente: {e}")


# ===================== Fallback: gTTS (motor de emergencia) =====================
# edge_tts depende de un servicio no oficial de Microsoft que puede dejar de
# responder con audio real para todo el mundo durante un rato (confirmado:
# en la v4.1 falló tanto con la voz principal como con la alternativa y con
# la de inglés). La auto-actualización de arriba ataca la causa de "librería
# desactualizada", pero no sirve cuando el problema está del lado de
# Microsoft y no del lado de este script. Para que el video nunca se quede
# sin audio por esto, si edge_tts agota TODOS sus reintentos (incluido el
# extra tras la actualización forzada) se usa gTTS como último recurso: es
# un servicio de Google, totalmente aparte del de Microsoft.
try:
    from gtts import gTTS
    _GTTS_DISPONIBLE = True
except ImportError:
    _GTTS_DISPONIBLE = False


def _instalar_gtts_si_hace_falta(logger=None):
    """Instala gTTS con pip la primera vez que hace falta (recién cuando
    edge_tts ya falló del todo), igual que la auto-actualización de
    edge-tts de más arriba. No bloquea nada más si falla."""
    global _GTTS_DISPONIBLE, gTTS
    if _GTTS_DISPONIBLE:
        return True
    try:
        if logger: logger.info("gTTS no está instalado; instalando (motor de emergencia, edge_tts agotó todos sus reintentos)...")
        resultado = subprocess.run(
            ["pip", "install", "gTTS", "--break-system-packages"],
            capture_output=True, text=True, timeout=90,
        )
        if resultado.returncode != 0:
            if logger: logger.warning(f"No se pudo instalar gTTS: {resultado.stderr.strip()[:300]}")
            return False
        from gtts import gTTS as _gTTS
        gTTS = _gTTS
        _GTTS_DISPONIBLE = True
        if logger: logger.info("gTTS instalado correctamente.")
        return True
    except Exception as e:
        if logger: logger.warning(f"No se pudo instalar gTTS: {e}")
        return False


def _idioma_gtts_desde_voz(voz):
    """Deduce el código de idioma de gTTS a partir del nombre de voz de
    edge_tts (ej. 'es-PE-AlexNeural' -> 'es', 'en-GB-RyanNeural' -> 'en')."""
    return "en" if voz.lower().startswith("en-") else "es"


def _aplicar_velocidad_ffmpeg(ruta_entrada, ruta_salida, velocidad, logger=None):
    """Aplica el % de velocidad (mismo formato que usa edge_tts, ej. '-10%')
    a un audio ya generado, vía el filtro atempo de ffmpeg. gTTS no tiene
    forma de pedir la velocidad al generar, así que se ajusta después."""
    try:
        pct = float(str(velocidad).replace("%", "").replace("+", ""))
    except Exception:
        pct = 0.0
    factor = max(0.5, min(1.0 + (pct / 100.0), 2.0))
    if abs(factor - 1.0) < 0.001:
        if ruta_entrada != ruta_salida:
            shutil.copyfile(ruta_entrada, ruta_salida)
        return
    cmd = ["ffmpeg", "-y", "-i", ruta_entrada, "-filter:a", f"atempo={factor}", ruta_salida]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        # Antes esto quedaba en silencio (solo se copiaba el crudo sin
        # avisar). Ahora se loguea para saber si el archivo final vacío
        # viene de acá o de gTTS mismo.
        if logger: logger.warning(f"ffmpeg no pudo ajustar la velocidad del audio de gTTS (código {resultado.returncode}): {resultado.stderr.strip()[-300:]}. Se usa el audio de gTTS sin ajustar velocidad.")
        shutil.copyfile(ruta_entrada, ruta_salida)


def _generar_chunk_audio_gtts_fallback(texto, voz, ruta_audio, velocidad, logger=None):
    """Último recurso cuando edge_tts (Microsoft) no devolvió audio ni
    actualizando la librería: genera el audio con gTTS (Google). Tira
    RuntimeError si tampoco esto funciona, para que quien llama sepa que
    de verdad no hay forma de generar audio en este momento."""
    if not _instalar_gtts_si_hace_falta(logger=logger):
        raise RuntimeError("gTTS no está disponible y no se pudo instalar.")
    idioma = _idioma_gtts_desde_voz(voz)
    ruta_cruda = f"{ruta_audio}.gtts_crudo.mp3"
    gTTS(text=texto, lang=idioma).save(ruta_cruda)
    # Se registra el tamaño del archivo crudo de gTTS ANTES de tocarlo con
    # ffmpeg, para poder distinguir en el log si el problema es que gTTS
    # (Google) tampoco devolvió audio real, o si el archivo de gTTS estaba
    # bien y el que lo rompió fue el paso de ajuste de velocidad de acá
    # abajo.
    tamano_crudo = os.path.getsize(ruta_cruda) if os.path.exists(ruta_cruda) else 0
    if logger: logger.info(f"gTTS generó {tamano_crudo} bytes en el archivo crudo (antes de ajustar velocidad).")
    if tamano_crudo == 0:
        if os.path.exists(ruta_cruda):
            os.remove(ruta_cruda)
        raise RuntimeError("gTTS devolvió un archivo vacío (0 bytes): probablemente no hay conexión desde este dispositivo hacia el servicio de Google usado por gTTS, o el pedido fue rechazado.")
    try:
        _aplicar_velocidad_ffmpeg(ruta_cruda, ruta_audio, velocidad, logger=logger)
    finally:
        if os.path.exists(ruta_cruda):
            os.remove(ruta_cruda)
    tamano_final = os.path.getsize(ruta_audio) if os.path.exists(ruta_audio) else 0
    if logger: logger.info(f"Audio final de gTTS (después de ajustar velocidad): {tamano_final} bytes.")
    obtener_duracion_audio(ruta_audio)  # valida que haya quedado audio real
    if logger:
        logger.warning("Audio generado con gTTS (fallback): edge_tts (Microsoft) no respondió tras todos los reintentos. El tono configurado no se aplica en este modo (gTTS no lo soporta); la velocidad sí.")


# ===================== Audio y tiempos =====================


def _dividir_texto_en_partes_audio(texto, n_partes):
    """Divide el texto en n_partes trozos lo mas parejos posible en
    caracteres, cortando siempre al final de una frase completa (nunca a
    mitad de una). Si hay menos frases que n_partes, devuelve una parte
    por frase."""
    frases = re.split(r"(?<=[.!?])\s+", texto.strip())
    frases = [f.strip() for f in frases if f.strip()]
    if not frases:
        return [texto] if texto.strip() else []
    if len(frases) <= n_partes:
        return frases
    total_chars = sum(len(f) for f in frases)
    objetivo = total_chars / n_partes
    partes, actual, chars_actual = [], [], 0
    for frase in frases:
        if actual and chars_actual >= objetivo and len(partes) < n_partes - 1:
            partes.append(" ".join(actual))
            actual, chars_actual = [], 0
        actual.append(frase)
        chars_actual += len(frase) + 1
    if actual:
        partes.append(" ".join(actual))
    return partes


async def _generar_chunk_audio_y_tiempos_async(texto, voz, ruta_audio, logger=None, tono=TONO, velocidad=VELOCIDAD, intentos=3):
    """Genera un unico chunk de audio con una sola llamada a edge_tts (sin
    trocear). Es la logica 'de siempre'; se usa tanto para textos cortos
    como para cada parte cuando generar_audio_y_tiempos_async trocea el
    texto largo.

    Reintenta automaticamente ante errores de red/conexion (DNS, socket,
    SSL, stream cortado) hasta 'intentos' veces, con espera creciente entre
    cada intento (2s, 4s, 6s...), antes de darse por vencido y propagar el
    error."""
    ultimo_error = None
    submaker = None
    uso_fallback_gtts = False
    for intento in range(1, intentos + 1):
        try:
            communicate = edge_tts.Communicate(texto, voz, pitch=tono, rate=velocidad, boundary="WordBoundary")
            submaker = edge_tts.SubMaker()
            with open(ruta_audio, "wb") as file:
                async for chunk in communicate.stream():
                    tipo = chunk.get("type")
                    if tipo == "audio":
                        file.write(chunk["data"])
                    elif tipo == "WordBoundary":
                        submaker.feed(chunk)
            # edge_tts a veces responde sin tirar ningún error pero deja un
            # audio vacío o cortado a la mitad (por ejemplo si la conexión
            # se corta un instante durante la descarga): sin esta
            # verificación eso pasaba desapercibido acá y recién tronaba
            # más adelante, en otra función, tumbando el video entero.
            # Probar la duración con ffprobe en este mismo punto detecta
            # ambos casos (vacío o corrupto) y los manda al mismo
            # reintento de acá abajo, sea cual sea la causa exacta.
            try:
                obtener_duracion_audio(ruta_audio)
            except Exception:
                raise RuntimeError("edge_tts devolvió un audio vacío o dañado (no se pudo leer su duración), sin tirar error propio.")
            break
        except Exception as e:
            ultimo_error = e
            if logger:
                logger.warning(f"Intento {intento}/{intentos} fallo generando voz ({e}).")
            if intento < intentos:
                await asyncio.sleep(2 * intento)
            else:
                # Los reintentos normales ya se agotaron. Antes de rendirse
                # del todo, se dispara una actualización forzada de
                # edge-tts (por si la causa es librería desactualizada,
                # que es lo más común según los issues del repo oficial) y
                # se prueba UNA vez más. Si esto también falla, recién ahí
                # se propaga el error como antes.
                if logger: logger.warning("Se agotaron los reintentos normales; se intenta actualizar edge-tts y reintentar una vez más antes de rendirse.")
                actualizar_edge_tts_si_hace_falta(logger=logger, forzar=True)
                try:
                    communicate = edge_tts.Communicate(texto, voz, pitch=tono, rate=velocidad, boundary="WordBoundary")
                    submaker = edge_tts.SubMaker()
                    with open(ruta_audio, "wb") as file:
                        async for chunk in communicate.stream():
                            tipo = chunk.get("type")
                            if tipo == "audio":
                                file.write(chunk["data"])
                            elif tipo == "WordBoundary":
                                submaker.feed(chunk)
                    obtener_duracion_audio(ruta_audio)
                    if logger: logger.info("La generación de voz funcionó tras actualizar edge-tts.")
                except Exception:
                    # edge_tts agotó TODAS las chances, incluida la
                    # actualización forzada de la librería: el problema está
                    # del lado del servicio de Microsoft, no de este script.
                    # Último recurso: gTTS (Google), un servicio aparte.
                    try:
                        _generar_chunk_audio_gtts_fallback(texto, voz, ruta_audio, velocidad, logger=logger)
                        submaker = None
                        uso_fallback_gtts = True
                    except Exception as e_gtts:
                        # Antes acá se perdía el motivo real por el que
                        # gTTS fallaba (se tapaba con el error viejo de
                        # edge_tts). Ahora se loguea aparte y se junta en
                        # el mensaje final, para poder diagnosticar cuál de
                        # los dos motores fue el que falló y por qué.
                        if logger: logger.warning(f"El fallback de gTTS también falló ({e_gtts}).")
                        raise RuntimeError(f"edge_tts falló ({ultimo_error}) y el fallback de gTTS también falló ({e_gtts}).")
    palabras_tiempos = []
    if uso_fallback_gtts:
        # gTTS no da tiempos de palabra reales (a diferencia de edge_tts):
        # se reparten las palabras parejo a lo largo de la duración real
        # del audio, para que los subtítulos sigan funcionando de forma
        # aproximada en vez de quedar sin tiempos.
        try:
            duracion_total = obtener_duracion_audio(ruta_audio)
            palabras = texto.split()
            if palabras:
                paso = duracion_total / len(palabras)
                for i, palabra in enumerate(palabras):
                    palabras_tiempos.append({"texto": palabra, "inicio": i * paso, "fin": (i + 1) * paso})
        except Exception:
            pass
    else:
        try:
            if hasattr(submaker, "offset_and_duration"):
                for offset, duration, text in submaker.offset_and_duration:
                    inicio, dur = offset / 10000000.0, duration / 10000000.0
                    palabras_tiempos.append({"texto": text, "inicio": inicio, "fin": inicio + dur})
            elif hasattr(submaker, "cues"):
                for cue in submaker.cues:
                    inicio = cue.start.total_seconds() if hasattr(cue.start, "total_seconds") else cue.start / 10000000.0
                    fin = cue.end.total_seconds() if hasattr(cue.end, "total_seconds") else cue.end / 10000000.0
                    texto_cue = getattr(cue, "content", None) or getattr(cue, "text", "")
                    palabras_tiempos.append({"texto": texto_cue, "inicio": inicio, "fin": fin})
        except Exception:
            pass
    return palabras_tiempos


async def generar_audio_y_tiempos_async(texto, voz, ruta_audio, logger=None, tono=TONO, velocidad=VELOCIDAD):
    """Si el texto supera los 1000 caracteres, SIEMPRE se trocea en 5 partes
    (cortando por frases completas) y se genera el audio de cada parte por
    separado, para reducir la chance de que edge_tts corte el stream a
    mitad de un texto largo. Despues se concatenan los audios parciales con
    ffmpeg y se ajustan los tiempos de palabra de cada parte sumandoles el
    offset acumulado de las partes anteriores."""
    if len(texto) <= 1000:
        return await _generar_chunk_audio_y_tiempos_async(texto, voz, ruta_audio, logger=logger, tono=tono, velocidad=velocidad)

    partes = _dividir_texto_en_partes_audio(texto, 5)
    if logger:
        logger.info(f"Texto de {len(texto)} caracteres: se trocea en {len(partes)} partes para la generación de voz.")

    rutas_parciales = []
    palabras_tiempos = []
    offset_acumulado = 0.0
    ruta_lista = f"{ruta_audio}.concat.txt"
    try:
        for i, parte in enumerate(partes):
            ruta_parcial = f"{ruta_audio}.parte{i}.mp3"
            if logger:
                logger.info(f"Generando parte {i + 1}/{len(partes)} de la voz ({len(parte)} caracteres).")
            tiempos_parte = await _generar_chunk_audio_y_tiempos_async(parte, voz, ruta_parcial, logger=logger, tono=tono, velocidad=velocidad)
            for pt in tiempos_parte:
                palabras_tiempos.append({"texto": pt["texto"], "inicio": pt["inicio"] + offset_acumulado, "fin": pt["fin"] + offset_acumulado})
            rutas_parciales.append(ruta_parcial)
            offset_acumulado += obtener_duracion_audio(ruta_parcial)

        with open(ruta_lista, "w", encoding="utf-8") as f:
            for r in rutas_parciales:
                f.write(f"file '{os.path.abspath(r)}'\n")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ruta_lista, "-c", "copy", ruta_audio]
        resultado_ffmpeg = subprocess.run(cmd, capture_output=True, text=True)
        if resultado_ffmpeg.returncode != 0:
            raise RuntimeError(f"ffmpeg no pudo unir las {len(partes)} partes de audio: {resultado_ffmpeg.stderr[-500:]}")
    finally:
        for r in rutas_parciales:
            if os.path.exists(r):
                os.remove(r)
        if os.path.exists(ruta_lista):
            os.remove(ruta_lista)

    return palabras_tiempos


def generar_audio_y_tiempos(texto, voz, ruta_audio, logger=None, tono=TONO, velocidad=VELOCIDAD):
    return asyncio.run(generar_audio_y_tiempos_async(texto, voz, ruta_audio, logger=logger, tono=tono, velocidad=velocidad))


def obtener_duracion_audio(ruta_audio):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", ruta_audio], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def calcular_tiempos_de_bloques(bloques, palabras_tiempos, duracion_total_audio):
    resultado = []
    if palabras_tiempos:
        idx = 0
        for bloque in bloques:
            n_palabras = len(bloque.split())
            sub = palabras_tiempos[idx: idx + n_palabras]
            idx += n_palabras
            if sub:
                resultado.append((bloque, sub[0]["inicio"], sub[-1]["fin"], sub))
            else:
                ultimo_fin = resultado[-1][2] if resultado else 0.0
                resultado.append((bloque, ultimo_fin, duracion_total_audio, []))
        return resultado

    total_chars = sum(len(b) for b in bloques) or 1
    t = 0.0
    for bloque in bloques:
        dur = duracion_total_audio * (len(bloque) / total_chars)
        resultado.append((bloque, t, t + dur, []))
        t += dur
    return resultado

# ============================================================
# ---- módulo nuevo: reddit.py ----
# ============================================================
import csv
import json
import itertools

# ===================== Extracción de historias de Reddit =====================

# v5.3: se sacó por completo el scraping en vivo de Reddit (login, JSON,
# RSS) y de Mumsnet — Reddit bloqueaba el tráfico anónimo (403) y Mumsnet
# dejó de traer historias. Ya no se usan credenciales de Reddit en ningún
# lado del código. La única fuente de historias que queda es el dataset
# local (ver RUTA_DATASET_AITA más abajo).

# Dataset local de respaldo: historias históricas de r/AITAH descargadas de
# antemano (no vía scraping en vivo), para que SIEMPRE haya candidatos
# aunque Reddit bloquee ese día por completo. Se usa solo si las otras vías
# no traen nada para ese subreddit. Formato esperado: CSV con columnas
# "id","title","text" (o "body"/"selftext") y opcionalmente "score"/"ups".
# Si el archivo no existe todavía, esta vía simplemente no aporta nada (no
# rompe el resto del programa) hasta que lo descargues y lo coloques ahí.
RUTA_DATASET_AITA = os.path.join(CARPETA_BASE, "dataset_aita.csv")


# Filtros de selección: se descartan historias fuera de este rango de
# palabras, con pocos upvotes, o marcadas como NSFW/borradas.
#
# v5.1: se volvió a activar el filtro de longitud (estaba desactivado
# desde la v1.7, con 1-100000, o sea "aceptar cualquier cosa"). Ahora se
# descartan las historias de texto corto y solo entran las de texto
# largo: mínimo 800 palabras (a ~130-140 palabras por minuto de voz, son
# unos 6 minutos de narración). Sin techo superior (PALABRAS_MAX_HISTORIA
# se deja en 100000, no se puso límite de máximo, solo de mínimo). Si 800
# te deja con pocos candidatos o te trae historias más cortas de lo que
# esperás, subí o bajá este número.
PALABRAS_MIN_HISTORIA, PALABRAS_MAX_HISTORIA = 800, 100000
UPVOTES_MINIMOS_HISTORIA = 0

# Objetivo de duración final del video: 28-30 minutos de narración.
# A ~130-140 palabras por minuto de voz, eso ronda las 3640-4200 palabras
# en el GUION FINAL (ya traducido). Pero Gemini suele resumir bastante al
# traducir/adaptar (en una prueba real, 3 historias que sumaban ~3900-4400
# palabras en inglés terminaron en un guion de ~3260 palabras en español,
# un 20-25% menos). Por eso el rango de selección apunta más alto que el
# objetivo final, para compensar esa reducción. Se usa para: (a) preferir
# una sola historia larga que ya caiga en este rango, o (b) si no hay
# ninguna así, combinar 2 o 3 historias más votadas hasta que la suma entre
# en rango. Si después de una tanda de pruebas el guion sigue quedando
# corto o largo, ajustar estos dos números.
PALABRAS_OBJETIVO_MIN, PALABRAS_OBJETIVO_MAX = 4400, 5400
















# ===================== Guion con Gemini (traducción + transformación) =====================

# Pega aquí tu API key gratuita de Gemini (la consigues en https://aistudio.google.com/apikey).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELO = "gemini-3.5-flash-lite"

# Tono/personalidad del narrador. Placeholder por ahora: ajustar cuando se
# defina el tono final (serio, canchero, sarcástico, neutro-cercano...).



# ----- Guion en inglés adaptado (v3.4) -----
# No traduce (el original ya está en inglés): adapta y transforma para que
# cuente como contenido editado/comentado y no una simple lectura del post
# original, con el mismo criterio de monetización que ya se aplicaba al
# guion en español.






# ============================================================
# ---- módulo original: subtitulos.py ----
# ============================================================

# ===================== Subtítulos ASS Dinámicos y Centrados =====================


def _tiempo_ass(segundos):
    h, m, s = int(segundos // 3600), int((segundos % 3600) // 60), segundos % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


COLORES_SUBTITULO = {
    "blanco": "FFFFFF",
    "amarillo_calido": "D9C27E",
    "gris_claro": "D8D8D8",
    "pergamino": "F4EEDC",
    "oro_viejo": "D4AF37",
    "rojo_carmesi": "8B0000"
}


def _ajustar_texto_a_caja(palabras, tamano_max, ancho_caja_px, alto_max_px, tamano_min=14):
    """Dado un ancho y alto máximos en píxeles, encuentra el mayor tamaño de fuente
    (partiendo de tamano_max) con el que el texto, envuelto en líneas, cabe completo.
    Devuelve (tamano_final, lineas) donde lineas es una lista de listas de palabras."""
    tamano = tamano_max
    lineas = [[palabras[0]]] if palabras else [[]]
    while tamano >= tamano_min:
        ancho_char_aprox = tamano * 0.56  # estimación conservadora para fuentes serif
        alto_linea_aprox = tamano * 1.3
        max_chars_linea = max(1, int(ancho_caja_px / ancho_char_aprox))

        lineas = []
        actual = []
        largo_actual = 0
        for palabra in palabras:
            largo_palabra = len(palabra) + (1 if actual else 0)
            if actual and largo_actual + largo_palabra > max_chars_linea:
                lineas.append(actual)
                actual = [palabra]
                largo_actual = len(palabra)
            else:
                actual.append(palabra)
                largo_actual += largo_palabra
        if actual: lineas.append(actual)

        alto_total = alto_linea_aprox * max(1, len(lineas))
        if alto_total <= alto_max_px:
            return tamano, lineas
        tamano -= 2
    return tamano_min, lineas


def generar_ass_hsf(bloques_con_tiempos, posicion, color, tamano_sub, nombre_fuente, animacion, ruta_ass, opacidad_sub=100, ancho_caja_pct=None, pos_y_pct=None):
    color_hex = COLORES_SUBTITULO.get(color, COLORES_SUBTITULO["blanco"])

    if color in ["blanco", "gris_claro", "pergamino"]:
        color_base = "888888"
    else:
        color_base = "CCCCCC"

    # Opacidad del subtítulo: 100 = totalmente opaco (alpha 00 en ASS), valores
    # menores van subiendo el canal alfa hacia FF (transparente). Se aplica por
    # igual al color principal y al color "atenuado" que se usa antes de que
    # cada palabra se resalte, para que la transparencia sea pareja en todo momento.
    try:
        opacidad_sub = max(10, min(100, int(float(opacidad_sub))))
    except (TypeError, ValueError):
        opacidad_sub = 100
    alpha_hex = f"{int(round((100 - opacidad_sub) / 100 * 255)):02X}"

    primary = f"&H{alpha_hex}{color_hex[4:6]}{color_hex[2:4]}{color_hex[0:2]}&"
    base_bgr = f"&H{alpha_hex}{color_base[4:6]}{color_base[2:4]}{color_base[0:2]}&"

    # Coordenadas ancladas al centro exacto
    x_centro = RESOLUCION_ANCHO // 2
    margen_borde = 40
    try:
        ancho_caja_pct = max(20, min(95, int(float(ancho_caja_pct)))) if ancho_caja_pct is not None else None
    except (TypeError, ValueError):
        ancho_caja_pct = None
    try:
        pos_y_pct = max(5, min(90, int(float(pos_y_pct)))) if pos_y_pct is not None else None
    except (TypeError, ValueError):
        pos_y_pct = None

    ancho_caja = int(RESOLUCION_ANCHO * (ancho_caja_pct / 100)) if ancho_caja_pct else int(RESOLUCION_ANCHO * 0.5)  # ancho de la "caja" (ajustable arrastrando los costados)
    alto_caja_max = int(RESOLUCION_ALTO * 0.65)  # altura máxima permitida para el bloque de texto

    alineacion = 5  # 5 = centro (por defecto, para centro/abajo)
    margen_l, margen_r = 20, 20
    if posicion == "izquierda":
        alineacion = 4  # 4 = medio-izquierda: el texto crece hacia la derecha desde el ancla
        x_centro = margen_borde
        y_centro = int(RESOLUCION_ALTO * (pos_y_pct / 100)) if pos_y_pct is not None else RESOLUCION_ALTO // 2
        margen_l, margen_r = margen_borde, RESOLUCION_ANCHO - ancho_caja - margen_borde
    elif posicion == "derecha":
        alineacion = 6  # 6 = medio-derecha: el texto crece hacia la izquierda desde el ancla
        x_centro = RESOLUCION_ANCHO - margen_borde
        y_centro = int(RESOLUCION_ALTO * (pos_y_pct / 100)) if pos_y_pct is not None else RESOLUCION_ALTO // 2
        margen_l, margen_r = RESOLUCION_ANCHO - ancho_caja - margen_borde, margen_borde
    elif posicion == "centro":
        y_centro = int(RESOLUCION_ALTO * (pos_y_pct / 100)) if pos_y_pct is not None else RESOLUCION_ALTO // 2
        ancho_caja = int(RESOLUCION_ANCHO * (ancho_caja_pct / 100)) if ancho_caja_pct else RESOLUCION_ANCHO - margen_l - margen_r
        margen_l = margen_r = (RESOLUCION_ANCHO - ancho_caja) // 2
    else:  # abajo
        y_centro = int(RESOLUCION_ALTO * (pos_y_pct / 100)) if pos_y_pct is not None else int(RESOLUCION_ALTO * 0.8)
        ancho_caja = int(RESOLUCION_ANCHO * (ancho_caja_pct / 100)) if ancho_caja_pct else RESOLUCION_ANCHO - margen_l - margen_r
        margen_l = margen_r = (RESOLUCION_ANCHO - ancho_caja) // 2

    pos_tag = f"{{\\pos({x_centro},{y_centro})}}"

    encabezado = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {RESOLUCION_ANCHO}\nPlayResY: {RESOLUCION_ALTO}\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Alineación dinámica: 5=centro para centro/abajo, 4/6=izquierda/derecha ancladas a caja fija
        f"Style: Default,{nombre_fuente},{tamano_sub},{primary},&H000000FF&,&H{alpha_hex}000000&,&H{alpha_hex}000000&,"
        f"-1,-1,0,0,100,100,1,0,1,3,1,{alineacion},{margen_l},{margen_r},0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lineas_dialogo = []
    for bloque, inicio, fin, sub_palabras in bloques_con_tiempos:
        palabras_bloque = [p["texto"] for p in sub_palabras] if sub_palabras else bloque.split()
        tamano_final, lineas_palabras = _ajustar_texto_a_caja(palabras_bloque, tamano_sub, ancho_caja, alto_caja_max)
        fs_tag = f"{{\\fs{tamano_final}}}"
        # Mapa palabra -> número de línea, para insertar \N en el lugar correcto durante el karaoke
        linea_de_palabra = {}
        idx = 0
        for n_linea, grupo in enumerate(lineas_palabras):
            for _ in grupo:
                linea_de_palabra[idx] = n_linea
                idx += 1

        if animacion == "dinamico" and sub_palabras:
            tiempo_actual = inicio
            for i, palabra_info in enumerate(sub_palabras):
                p_inicio = palabra_info["inicio"]
                p_fin = palabra_info["fin"]

                if tiempo_actual < p_inicio:
                    texto_base = "\\N".join(" ".join(g) for g in lineas_palabras)
                    lineas_dialogo.append(
                        f"Dialogue: 0,{_tiempo_ass(tiempo_actual)},{_tiempo_ass(p_inicio)},Default,,0,0,0,,{pos_tag}{fs_tag}{{\\blur2\\c{base_bgr}}}{texto_base}\n"
                    )

                texto_karaoke = ""
                for j, p2 in enumerate(sub_palabras):
                    if j > 0 and linea_de_palabra.get(j) != linea_de_palabra.get(j - 1):
                        texto_karaoke += "\\N"
                    elif j > 0:
                        texto_karaoke += " "
                    if j == i:
                        texto_karaoke += f"{{\\c{primary}\\fscx108\\fscy108}}{p2['texto']}{{\\fscx100\\fscy100\\c{base_bgr}}}"
                    else:
                        texto_karaoke += p2['texto']

                lineas_dialogo.append(
                    f"Dialogue: 0,{_tiempo_ass(p_inicio)},{_tiempo_ass(p_fin)},Default,,0,0,0,,{pos_tag}{fs_tag}{{\\blur2\\c{base_bgr}}}{texto_karaoke}\n"
                )
                tiempo_actual = p_fin

            if tiempo_actual < fin:
                texto_base = "\\N".join(" ".join(g) for g in lineas_palabras)
                lineas_dialogo.append(
                    f"Dialogue: 0,{_tiempo_ass(tiempo_actual)},{_tiempo_ass(fin)},Default,,0,0,0,,{pos_tag}{fs_tag}{{\\blur2\\c{base_bgr}}}{texto_base}\n"
                )
        else:
            texto_ass = "\\N".join(" ".join(g) for g in lineas_palabras)
            lineas_dialogo.append(
                f"Dialogue: 0,{_tiempo_ass(inicio)},{_tiempo_ass(fin)},Default,,0,0,0,,{pos_tag}{fs_tag}{{\\blur2\\fad(400,400)\\c{primary}}}{texto_ass}\n"
            )

    with open(ruta_ass, "w", encoding="utf-8") as f:
        f.write(encabezado)
        f.writelines(lineas_dialogo)

# ============================================================
# ---- módulo original: video.py ----
# ============================================================
import os
import time
import random
import shutil
import subprocess


# ===================== Video =====================


def _construir_zoom_multifase(duracion, fps=None, zoom_max=1.16):
    """Arma un movimiento de camara con varias fases (zoom-in, pan izquierda,
    pan derecha, pan arriba, pan abajo, zoom-out) para el fondo estatico.

    La duracion de cada fase se calcula a partir de la duracion total del
    video (mas video, fases un poco mas largas, hasta un tope), y todo el
    ciclo se repite en loop durante el video completo (mod), asi que un
    video de 30 minutos no se queda quieto despues del primer ciclo.
    Devuelve las expresiones de zoompan (z, x, y) listas para usar."""
    fps = fps or FPS
    d_zoom = max(3.0, min(6.0, duracion * 0.15))
    d_pan = max(3.0, min(6.0, duracion * 0.12))

    b1 = d_zoom
    b2 = b1 + d_pan
    b3 = b2 + d_pan
    b4 = b3 + d_pan
    b5 = b4 + d_pan
    b6 = b5 + d_zoom

    f = lambda s: max(1, round(s * fps))
    b1f, b2f, b3f, b4f, b5f, b6f = f(b1), f(b2), f(b3), f(b4), f(b5), f(b6)
    Z = zoom_max
    m = f"mod(on,{b6f})"

    expr_z = (
        f"if(lt({m},{b1f}),1+{Z - 1:.5f}*({m}/{b1f}),"
        f"if(lt({m},{b5f}),{Z:.5f},"
        f"{Z:.5f}-{Z - 1:.5f}*(({m}-{b5f})/{b6f - b5f})))"
    )
    H = (
        f"if(lt({m},{b1f}),0,"
        f"if(lt({m},{b2f}),-0.7*(({m}-{b1f})/{b2f - b1f}),"
        f"if(lt({m},{b3f}),-0.7+1.4*(({m}-{b2f})/{b3f - b2f}),"
        f"if(lt({m},{b4f}),0.7*(1-(({m}-{b3f})/{b4f - b3f})),0))))"
    )
    V = (
        f"if(lt({m},{b3f}),0,"
        f"if(lt({m},{b4f}),-0.6*(({m}-{b3f})/{b4f - b3f}),"
        f"if(lt({m},{b5f}),-0.6*(1-(({m}-{b4f})/{b5f - b4f})),0)))"
    )
    expr_x = f"(iw*(1-1/zoom))/2*(1+({H}))"
    expr_y = f"(ih*(1-1/zoom))/2*(1+({V}))"
    return expr_z, expr_x, expr_y


def generar_segmento_imagen(ruta_imagen, duracion, ruta_salida, logger=None):
    duracion = max(0.5, duracion)
    frames = max(1, int(duracion * FPS))
    zoom_objetivo = round(random.uniform(1.06, 1.10), 3)
    modo = random.choice(["in", "out"])
    if modo == "in": expr_zoom = f"min(zoom+{zoom_objetivo - 1.0:.5f}/{frames},{zoom_objetivo})"
    else: expr_zoom = f"if(eq(on,1),{zoom_objetivo},max(zoom-{zoom_objetivo - 1.0:.5f}/{frames},1.0))"

    # Optimización: Limitamos a 1536 de ancho (un poco más que 720p) para ahorrar RAM
    filtro = (
        f"scale=1536:-1,"
        f"zoompan=z='{expr_zoom}':d={frames}:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:fps={FPS},"
        f"drawbox=x=0:y=0:w={RESOLUCION_ANCHO}:h={RESOLUCION_ALTO}:color=black@0.38:t=fill,"
        f"format=yuv420p"
    )

    cmd = ["ffmpeg", "-y", "-threads", "4", "-loop", "1", "-i", ruta_imagen, "-t", str(duracion), "-vf", filtro, "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18", ruta_salida]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def generar_segmento_imagen_estatico(ruta_imagen, duracion, ruta_salida, logger=None):
    """Genera el fondo para el modo 'fondo fijo': una sola imagen que se mantiene durante
    todo el video, con un movimiento de camara de varias fases (zoom-in, pan
    en las 4 direcciones, zoom-out) que se repite en loop durante todo el
    video, con duracion de fases calculada segun la duracion total."""
    duracion = max(0.5, duracion)
    frames = max(1, int(duracion * FPS))
    expr_z, expr_x, expr_y = _construir_zoom_multifase(duracion)

    filtro = (
        f"scale=1536:-1,"
        f"zoompan=z='{expr_z}':x='{expr_x}':y='{expr_y}':d={frames}:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:fps={FPS},"
        f"drawbox=x=0:y=0:w={RESOLUCION_ANCHO}:h={RESOLUCION_ALTO}:color=black@0.38:t=fill,"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-threads", "4", "-loop", "1", "-i", ruta_imagen, "-t", str(duracion), "-vf", filtro, "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18", ruta_salida]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def obtener_imagen_predeterminada(logger=None, carpeta_imagenes_stock=None):
    """Si no se sube ni configura nada, se usa siempre esta misma imagen: se
    descarga de Pexels UNA sola vez la primera vez que se usa, y de ahí en
    adelante queda guardada para siempre (no se vuelve a descargar)."""
    carpeta_imagenes_stock = carpeta_imagenes_stock or CARPETA_IMAGENES_STOCK
    ruta = os.path.join(carpeta_imagenes_stock, "_predeterminada.jpg")
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        return ruta
    usadas = set()
    for termino in TERMINOS_STOCK_FONDO:
        url = _buscar_foto_pexels(termino, evitar=usadas) or _buscar_foto_pixabay(termino, evitar=usadas)
        if url:
            try:
                import requests
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                with open(ruta, "wb") as f: f.write(r.content)
                if logger: logger.info("Imagen de fondo predeterminada descargada y guardada para siempre.")
                return ruta
            except Exception:
                continue
    return None


def descargar_varias_imagenes_stock(cantidad, logger=None):
    """Descarga 'cantidad' imágenes distintas de Pexels/Pixabay para repartir
    en partes iguales a lo largo del video (no quedan guardadas para siempre,
    se piden nuevas cada vez que se usa esta opción)."""
    usadas = set()
    imagenes = []
    for i in range(max(1, cantidad)):
        ruta = obtener_imagen_stock(i, usadas, logger=logger)
        if ruta: imagenes.append(ruta)
    return imagenes


def generar_video_multi_imagen_transicion(rutas_imagenes, duracion_total, ruta_salida, logger=None, transicion=0.7):
    """Reparte 'duracion_total' en partes iguales entre las imágenes dadas y
    las une con un desvanecimiento suave (0.5 a 1 seg) entre cada una."""
    rutas_imagenes = [r for r in rutas_imagenes if r and os.path.exists(r)]
    n = len(rutas_imagenes)
    if n == 0: return False
    if n == 1: return generar_segmento_imagen_estatico(rutas_imagenes[0], duracion_total, ruta_salida, logger=logger)

    duracion_parte = duracion_total / n
    transicion = max(0.5, min(transicion, 1.0, duracion_parte / 2))
    carpeta_temp = os.path.dirname(ruta_salida)

    segmentos = []
    for i, img in enumerate(rutas_imagenes):
        ruta_seg = os.path.join(carpeta_temp, f"_multi_{i}_{int(time.time())}.mp4")
        if generar_segmento_imagen_estatico(img, duracion_parte + transicion, ruta_seg, logger=logger):
            segmentos.append(ruta_seg)

    if not segmentos: return False
    if len(segmentos) == 1:
        shutil.copy(segmentos[0], ruta_salida)
        return True

    inputs_cmd = []
    for s in segmentos: inputs_cmd += ["-i", s]
    partes_filtro = []
    etiqueta_previa = "0:v"
    offset_acumulado = duracion_parte
    for i in range(1, len(segmentos)):
        etiqueta_salida = f"v{i}" if i < len(segmentos) - 1 else "vout"
        partes_filtro.append(f"[{etiqueta_previa}][{i}:v]xfade=transition=fade:duration={transicion:.2f}:offset={offset_acumulado:.2f}[{etiqueta_salida}]")
        etiqueta_previa = etiqueta_salida
        offset_acumulado += duracion_parte

    cmd = ["ffmpeg", "-y"] + inputs_cmd + ["-filter_complex", ";".join(partes_filtro), "-map", "[vout]", "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "18", ruta_salida]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    ok = resultado.returncode == 0
    if not ok and logger:
        logger.error(f"ffmpeg (transición entre varias imágenes) devolvió error:\n{resultado.stderr[-2000:]}")
    for s in segmentos:
        try: os.remove(s)
        except Exception: pass
    return ok


def _normalizar_velocidad_efecto(velocidad_efecto):
    try:
        v = float(velocidad_efecto)
    except (TypeError, ValueError):
        v = VELOCIDAD_EFECTO_POR_DEFECTO
    return max(VELOCIDAD_EFECTO_MIN, min(VELOCIDAD_EFECTO_MAX, v))


def aplicar_efecto_video(ruta_entrada, ruta_salida, efecto, duracion, velocidad_efecto=VELOCIDAD_EFECTO_POR_DEFECTO, logger=None):
    """Aplica un efecto visual liviano sobre el video ya armado (con subtítulos
    quemados). Si el efecto falla por algún motivo, se sigue con el video
    original sin efecto en vez de romper todo el proceso.

    'velocidad_efecto' solo tiene efecto real en los dos únicos efectos con
    movimiento en el tiempo (ceniza y vela); el resto son filtros estáticos
    y lo ignoran."""
    if not efecto or efecto == "ninguno":
        return ruta_entrada

    velocidad = _normalizar_velocidad_efecto(velocidad_efecto)

    filtros_simples = {
        "vineta": "vignette=PI/4",
        "grano_pelicula": "noise=alls=14:allf=t+u",
        # El período del parpadeo (2s por defecto) se divide por la velocidad:
        # con velocidad 2.0 el parpadeo dura la mitad (más rápido), con 0.5 el doble (más lento).
        "vela": f"eq=brightness='0.05*sin(2*PI*t/{max(0.4, 2.0 / velocidad):.4f})':eval=frame",
        "niebla": "geq=lum='lum(X,Y)+35*(Y/H)':cb='cb(X,Y)':cr='cr(X,Y)'",
        "rayo_luz": "geq=lum='lum(X,Y)+25*exp(-((X-0.5*Y-0.2*W)/180)^2)':cb='cb(X,Y)':cr='cr(X,Y)'",
        "pergamino": "colorbalance=rs=0.15:gs=0.05:bs=-0.15,eq=saturation=0.85",
    }

    if efecto in filtros_simples:
        cmd = ["ffmpeg", "-y", "-i", ruta_entrada, "-vf", filtros_simples[efecto],
               "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy", ruta_salida]
    elif efecto == "ceniza":
        # Rediseño del efecto (2 iteraciones de calibración con ffmpeg real):
        #
        # 1) La primera versión usaba blend=screen directo sobre YUV, lo que
        #    mezcla también la crominancia y termina TIÑENDO toda la pantalla
        #    de violeta parejo (comprobado con ffmpeg real: un blend "screen"
        #    de gris sobre negro puro en YUV da como resultado color, no
        #    gris). Se corrige generando las partículas como una capa blanca
        #    con canal alfa (alphamerge) y componiéndolas con 'overlay'
        #    (compositing por alpha), que no tiene ese problema.
        # 2) El umbral de ruido original (pensado para 'alls', 0-255) estaba
        #    mal calibrado para 'c0s' (que en la práctica nunca pasa de
        #    ~150): con esos valores no aparecía ninguna partícula. Se
        #    recalibraron los umbrales contra el rango real del filtro.
        #    Además, generar el ruido a baja resolución y escalarlo hacia
        #    arriba (en vez de a resolución completa) agrupa el ruido en
        #    motas redondeadas y dispersas en vez de una alfombra de
        #    estática fina — así se ve a partículas de ceniza cayendo, no a
        #    ruido de TV.
        #
        # Dos capas de profundidad: partículas lejanas (chicas, dispersas,
        # lentas) y cercanas (más grandes, un poco más densas y rápidas).
        # 'velocidad' escala la caída de ambas por igual.
        capa_blanco_lejos = f"color=c=white:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:d={duracion}"
        capa_alfa_lejos = (
            f"color=c=black:s=240x135:d={duracion},"
            f"noise=c0s=100:c0f=t,lutyuv=y='if(gt(val,138),255,0)',"
            f"scale={RESOLUCION_ANCHO}x{RESOLUCION_ALTO},gblur=sigma=1.5,"
            f"scroll=vertical={0.012 * velocidad:.5f},format=gray"
        )
        capa_blanco_cerca = f"color=c=white:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:d={duracion}"
        capa_alfa_cerca = (
            f"color=c=black:s=320x180:d={duracion},"
            f"noise=c0s=100:c0f=t,lutyuv=y='if(gt(val,133),255,0)',"
            f"scale={RESOLUCION_ANCHO}x{RESOLUCION_ALTO},gblur=sigma=0.9,"
            f"scroll=vertical={0.030 * velocidad:.5f},format=gray"
        )
        cmd = ["ffmpeg", "-y", "-i", ruta_entrada,
               "-f", "lavfi", "-i", capa_blanco_lejos,
               "-f", "lavfi", "-i", capa_alfa_lejos,
               "-f", "lavfi", "-i", capa_blanco_cerca,
               "-f", "lavfi", "-i", capa_alfa_cerca,
               "-filter_complex",
               "[1:v][2:v]alphamerge,colorchannelmixer=aa=0.55[lejos];"
               "[3:v][4:v]alphamerge,colorchannelmixer=aa=0.7[cerca];"
               "[0:v][lejos]overlay=format=auto[tmp];"
               "[tmp][cerca]overlay=format=auto[vout]",
               "-map", "[vout]", "-map", "0:a?",
               "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy", ruta_salida]
    else:
        return ruta_entrada

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        if logger:
            logger.error(f"ffmpeg (efecto de video '{efecto}') devolvió error, se sigue sin efecto:\n{resultado.stderr[-2000:]}")
        return ruta_entrada
    return ruta_salida


def concatenar_segmentos(rutas_segmentos, ruta_salida, logger=None):
    ruta_lista = ruta_salida + "_lista.txt"
    with open(ruta_lista, "w", encoding="utf-8") as f:
        for ruta in rutas_segmentos: f.write(f"file '{os.path.abspath(ruta)}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ruta_lista, "-c", "copy", ruta_salida]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def quemar_subtitulos(ruta_video_in, ruta_ass, carpeta_fuentes_abs, ruta_video_out, logger=None):
    cmd = ["ffmpeg", "-y", "-threads", "4", "-i", ruta_video_in, "-vf", f"ass={ruta_ass}:fontsdir={carpeta_fuentes_abs}", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy", ruta_video_out]
    return subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def mezclar_audio_final(ruta_video_sin_audio, ruta_voz, ruta_musica, volumen_musica, ruta_salida, logger=None, volumen_gameplay=None):
    """volumen_gameplay (0-100 o None): si el video de fondo ya trae su
    propio audio (ej. el gameplay de Slither.io), se mezcla un tercer canal
    a ese volumen (fijo en 1% para no tapar la voz). Si es None, el video
    de fondo se trata como mudo (comportamiento de siempre)."""
    if ruta_musica and volumen_gameplay is not None:
        filtro = (
            f"[0:a]volume={volumen_gameplay / 100:.3f}[gp];"
            f"[1:a]volume=1.0[voz];"
            f"[2:a]volume={volumen_musica / 100:.2f}[mus];"
            f"[voz][mus][gp]amix=inputs=3:duration=first:dropout_transition=2[aout]"
        )
        cmd = ["ffmpeg", "-y", "-i", ruta_video_sin_audio, "-i", ruta_voz, "-stream_loop", "-1", "-i", ruta_musica, "-filter_complex", filtro, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", ruta_salida]
    elif volumen_gameplay is not None:
        filtro = (
            f"[0:a]volume={volumen_gameplay / 100:.3f}[gp];"
            f"[1:a]volume=1.0[voz];"
            f"[voz][gp]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = ["ffmpeg", "-y", "-i", ruta_video_sin_audio, "-i", ruta_voz, "-filter_complex", filtro, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", ruta_salida]
    elif ruta_musica:
        filtro = f"[1:a]volume=1.0[voz];[2:a]volume={volumen_musica / 100:.2f}[mus];[voz][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        cmd = ["ffmpeg", "-y", "-i", ruta_video_sin_audio, "-i", ruta_voz, "-stream_loop", "-1", "-i", ruta_musica, "-filter_complex", filtro, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest", ruta_salida]
    else:
        cmd = ["ffmpeg", "-y", "-i", ruta_video_sin_audio, "-i", ruta_voz, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", ruta_salida]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 and logger:
        logger.error(f"ffmpeg (mezcla final de audio) devolvió error:\n{resultado.stderr[-2000:]}")
    return resultado.returncode == 0

# ============================================================
# ---- módulo original: procesamiento.py ----
# ============================================================
import os
import re
import time
import subprocess
import threading
import traceback
from datetime import datetime


# ===================== Estado global =====================

CANDADO_ESTADO = threading.Lock()
ESTADO = {
    "activo": False, "terminado": False, "fase": "inactivo", "porcentaje": 0,
    "resultado": {"mensaje": None, "video": None},
    # ---- Cronometraje (tiempos por fase y total) ----
    "tiempo_inicio_video": None,   # epoch: cuándo arrancó este video
    "tiempo_fase_inicio": None,    # epoch: cuándo arrancó la fase actual
    "tiempos_fases": {},           # {"nombre fase": segundos_que_tardó, ...}
    "tiempo_total": None,          # segundos que tardó el video completo (una vez terminado)
}


def _cerrar_fase_actual():
    """Calcula cuánto duró la fase que estaba corriendo y lo suma a
    tiempos_fases. Debe llamarse ya con CANDADO_ESTADO tomado. Devuelve el
    instante actual, para reutilizarlo como inicio de la fase siguiente."""
    ahora = time.time()
    fase_actual = ESTADO.get("fase")
    inicio_fase = ESTADO.get("tiempo_fase_inicio")
    if fase_actual and inicio_fase:
        duracion = round(ahora - inicio_fase, 1)
        tiempos = ESTADO.setdefault("tiempos_fases", {})
        tiempos[fase_actual] = round(tiempos.get(fase_actual, 0) + duracion, 1)
    return ahora


def actualizar_fase(fase, porcentaje, logger=None):
    with CANDADO_ESTADO:
        # Si la fase cambió de nombre, se cierra (cronometra) la anterior y
        # arranca el cronómetro de la nueva. Si es la misma fase avisando un
        # % más alto (como hace _ProgresoSuave), el cronómetro sigue corriendo.
        if ESTADO.get("fase") != fase:
            ESTADO["tiempo_fase_inicio"] = _cerrar_fase_actual()
        ESTADO["fase"] = fase
        ESTADO["porcentaje"] = max(0, min(99, porcentaje))
    if logger:
        logger.info(f"Fase: {fase} ({ESTADO['porcentaje']}%)")


class _ProgresoSuave:
    """Durante un paso largo de ffmpeg (que no avisa su propio avance), esto
    va subiendo el porcentaje solo, de a poquito, para que la barra no se
    quede pegada en un número fijo y luego salte de golpe."""
    def __init__(self, fase, inicio, fin, logger=None, duracion_estimada=25):
        self.fase, self.inicio, self.fin = fase, inicio, fin
        self.logger, self.duracion_estimada = logger, duracion_estimada
        self._detener = threading.Event()
        self._hilo = None

    def __enter__(self):
        actualizar_fase(self.fase, self.inicio, logger=self.logger)
        def _tick():
            paso = 0
            pasos_totales = max(1, self.duracion_estimada * 2)
            while not self._detener.is_set() and paso < pasos_totales:
                time.sleep(0.5)
                paso += 1
                pct = self.inicio + int((self.fin - self.inicio) * (paso / pasos_totales))
                actualizar_fase(self.fase, min(pct, self.fin - 1))
        self._hilo = threading.Thread(target=_tick, daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *a):
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=1)
        actualizar_fase(self.fase, self.fin, logger=self.logger)


def generar_nombre_archivo(texto):
    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    primera = lineas[0][:40] if lineas else "hsf"
    limpio = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ]", "", primera).strip().replace(" ", "_")
    return limpio or "hsf"


def procesar_todo(texto_bruto, frases_por_bloque, posicion, color_sub, tamano_sub, fuente_sub,
                   musica_genero, volumen_musica, rutas_imagenes_subidas, animacion,
                   traducir_auto=False, fondo_fijo=False, velocidad_voz=None, tono_voz=None,
                   opacidad_sub=100, cantidad_imagenes_descargar=0, ancho_sub_pct=None, pos_y_pct=None,
                   efecto_video="ninguno", velocidad_efecto=VELOCIDAD_EFECTO_POR_DEFECTO,
                   fondo_gameplay=False, ruta_gameplay=None, logger=None, ruta_log=None):
    if logger is None:
        logger, ruta_log = crear_logger_video()
    LOGGER_VIDEO_ACTIVO["logger"], LOGGER_VIDEO_ACTIVO["ruta"] = logger, ruta_log
    logger.info("Arrancó el procesamiento del video en el hilo de trabajo.")
    try:
        if traducir_auto:
            actualizar_fase("traduciendo texto", 4, logger=logger)
            texto_bruto = traducir_texto_deepl(texto_bruto, "es", logger=logger)

        actualizar_fase("preparando texto", 8, logger=logger)
        texto_limpio = limpiar_texto_para_voz(texto_bruto)
        bloques = dividir_en_bloques(texto_limpio, frases_por_bloque=frases_por_bloque)
        if not bloques: raise ValueError("El guion quedó vacío.")

        nombre_base = generar_nombre_archivo(texto_bruto)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Carpeta de proyecto de este video: todo lo que se genera para este
        # video en particular (voz, imagen, subtítulos, efecto, y el video
        # final) queda adentro, separado por tipo, en vez de mezclado con
        # los archivos de otros videos.
        proyecto = crear_carpeta_proyecto(nombre_base, marca)

        actualizar_fase("generando voz", 18, logger=logger)
        voz = VOZ_NARRADOR
        velocidad_final = _formatear_ajuste_voz(velocidad_voz, "%", VELOCIDAD_VOZ_POR_DEFECTO, VELOCIDAD_VOZ_MIN, VELOCIDAD_VOZ_MAX)
        tono_final = _formatear_ajuste_voz(tono_voz, "Hz", TONO_VOZ_POR_DEFECTO, TONO_VOZ_MIN, TONO_VOZ_MAX)
        ruta_audio = os.path.join(proyecto["voz"], "voz.mp3")
        logger.info(f"Motor de voz: edge_tts | voz={voz} | velocidad={velocidad_final} | tono={tono_final}")
        palabras_tiempos = generar_audio_y_tiempos(texto_limpio, voz, ruta_audio, logger=logger, tono=tono_final, velocidad=velocidad_final)
        duracion_total = obtener_duracion_audio(ruta_audio)

        tiempos_bloques = calcular_tiempos_de_bloques(bloques, palabras_tiempos, duracion_total)

        # Los intermedios "de imagen" (fondo sin subtítulos todavía) viven en
        # la subcarpeta imagen/ del proyecto.
        carpeta_temp = proyecto["imagen"]
        segmentos = []

        if fondo_gameplay and ruta_gameplay:
            # Fondo de gameplay propio (v5.4): un solo video (Slither.io +
            # bot) recortado/repetido en loop hasta cubrir la duración
            # exacta de la narración, en vez de imágenes estáticas.
            actualizar_fase("preparando gameplay", 25, logger=logger)
            ruta_seg = os.path.join(carpeta_temp, "seg_gameplay.mp4")
            with _ProgresoSuave("generando fondo", 40, 65, logger=logger, duracion_estimada=int(duracion_total / 8)):
                ok = generar_segmento_video_gameplay(ruta_gameplay, duracion_total, ruta_seg, logger=logger)
            if ok: segmentos.append(ruta_seg)
        elif fondo_fijo:
            # Modo "fondo fijo": una o varias imágenes quietas, repartidas en
            # partes iguales según la duración exacta del video, con un
            # desvanecimiento suave entre ellas si hay más de una.
            actualizar_fase("preparando imágenes", 25, logger=logger)
            if rutas_imagenes_subidas:
                imagenes_para_fondo = rutas_imagenes_subidas
            elif cantidad_imagenes_descargar and cantidad_imagenes_descargar > 1:
                imagenes_para_fondo = descargar_varias_imagenes_stock(cantidad_imagenes_descargar, logger=logger)
            else:
                imagenes_para_fondo = [obtener_imagen_predeterminada(logger=logger)]
            imagenes_para_fondo = [p for p in imagenes_para_fondo if p and os.path.exists(p)]

            ruta_seg = os.path.join(carpeta_temp, "seg_fijo.mp4")
            with _ProgresoSuave("generando fondo", 40, 65, logger=logger, duracion_estimada=int(duracion_total / 8)):
                if imagenes_para_fondo:
                    ok = generar_video_multi_imagen_transicion(imagenes_para_fondo, duracion_total, ruta_seg, logger=logger)
                else:
                    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:d={duracion_total}", "-r", str(FPS), ruta_seg]
                    ok = subprocess.run(cmd, capture_output=True, text=True).returncode == 0
            if ok: segmentos.append(ruta_seg)
        else:
            actualizar_fase("preparando imágenes", 25, logger=logger)
            usadas = set()
            rutas_imagenes = []
            for i in range(len(bloques)):
                if rutas_imagenes_subidas:
                    rutas_imagenes.append(rutas_imagenes_subidas[i % len(rutas_imagenes_subidas)])
                else:
                    rutas_imagenes.append(obtener_imagen_stock(i, usadas, logger=logger))

            actualizar_fase("generando fondo", 35, logger=logger)
            for i, (bloque, inicio, fin, sub_palabras) in enumerate(tiempos_bloques):
                duracion_bloque = max(0.5, fin - inicio)
                ruta_seg = os.path.join(carpeta_temp, f"seg_{i}.mp4")
                imagen = rutas_imagenes[i]
                if imagen and os.path.exists(imagen):
                    ok = generar_segmento_imagen(imagen, duracion_bloque, ruta_seg, logger=logger)
                else:
                    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}:d={duracion_bloque}", "-r", str(FPS), ruta_seg]
                    ok = subprocess.run(cmd, capture_output=True, text=True).returncode == 0
                if ok: segmentos.append(ruta_seg)
                actualizar_fase("generando fondo", 35 + int(30 * (i + 1) / len(tiempos_bloques)), logger=logger)

        if not segmentos: raise RuntimeError("No se pudo generar el video.")

        with _ProgresoSuave("uniendo escenas", 68, 76, logger=logger, duracion_estimada=int(duracion_total / 15)):
            ruta_video_base = os.path.join(carpeta_temp, "base.mp4")
            concatenar_segmentos(segmentos, ruta_video_base, logger=logger)

        nombre_fuente_ok = asegurar_fuente(fuente_sub) or FUENTE_POR_DEFECTO
        ruta_ass = os.path.join(proyecto["subtitulos"], "subs.ass")

        generar_ass_hsf(tiempos_bloques, posicion, color_sub, tamano_sub, nombre_fuente_ok, animacion, ruta_ass, opacidad_sub=opacidad_sub, ancho_caja_pct=ancho_sub_pct, pos_y_pct=pos_y_pct)

        with _ProgresoSuave("quemando subtítulos", 78, 86, logger=logger, duracion_estimada=int(duracion_total / 10)):
            ruta_video_subs = os.path.join(proyecto["subtitulos"], "con_subs.mp4")
            quemar_subtitulos(ruta_video_base, ruta_ass, os.path.abspath(CARPETA_FUENTES), ruta_video_subs, logger=logger)

        with _ProgresoSuave("aplicando efecto", 86, 90, logger=logger, duracion_estimada=int(duracion_total / 12)):
            ruta_video_efecto = os.path.join(proyecto["efecto"], "con_efecto.mp4")
            ruta_video_lista = aplicar_efecto_video(ruta_video_subs, ruta_video_efecto, efecto_video, duracion_total, velocidad_efecto=velocidad_efecto, logger=logger)

        ruta_musica = seleccionar_musica_fondo(musica_genero)
        nombre_final = f"{nombre_base}_{marca}_hsf.mp4"
        ruta_final = os.path.join(proyecto["raiz"], nombre_final)
        volumen_gameplay = 1 if fondo_gameplay and ruta_gameplay else None
        with _ProgresoSuave("mezclando audio", 90, 98, logger=logger, duracion_estimada=int(duracion_total / 15)):
            exito_mezcla = mezclar_audio_final(ruta_video_lista, ruta_audio, ruta_musica, volumen_musica, ruta_final, logger=logger, volumen_gameplay=volumen_gameplay)
        if not exito_mezcla or not os.path.exists(ruta_final) or os.path.getsize(ruta_final) == 0:
            raise RuntimeError(
                "Falló la mezcla final de audio y video (ffmpeg no generó el archivo). "
                "Revisá el log de esta corrida para ver el error exacto de ffmpeg."
            )

        # La ruta que ve el navegador incluye la carpeta del proyecto (ej.
        # "mi_video_20260804_195000/mi_video_20260804_195000_hsf.mp4"),
        # ya que el video final ahora vive adentro de esa carpeta y no
        # suelto en videos_hsf/.
        ruta_relativa_video = f"{proyecto['nombre_proyecto']}/{nombre_final}"

        # Intro con la misma tarjeta de la miniatura + un resumen corto,
        # superpuesta sobre los primeros segundos del video (si hay
        # plantilla disponible en Drive). Si falla, no corta el video:
        # simplemente queda sin esa intro.
        ruta_plantilla_intro = _obtener_plantilla_intro_desde_drive(logger=logger)
        if ruta_plantilla_intro:
            resumen_intro = " ".join(texto_bruto.split())[:100]
            if " " in resumen_intro:
                resumen_intro = resumen_intro.rsplit(" ", 1)[0]
            ruta_con_intro = ruta_final + ".intro.mp4"
            ok_intro = agregar_intro_resumen(ruta_final, ruta_plantilla_intro, resumen_intro, ruta_con_intro, duracion_intro=12.0, logger=logger)
            if ok_intro:
                os.replace(ruta_con_intro, ruta_final)

        with CANDADO_ESTADO:
            _cerrar_fase_actual()
            ESTADO["porcentaje"], ESTADO["fase"], ESTADO["terminado"], ESTADO["activo"] = 100, "listo", True, False
            ESTADO["resultado"] = {"mensaje": "Éxito.", "video": ruta_relativa_video}
            if ESTADO.get("tiempo_inicio_video"):
                ESTADO["tiempo_total"] = round(time.time() - ESTADO["tiempo_inicio_video"], 1)
        logger.info(f"✅ Video terminado con éxito: {ruta_relativa_video} (tiempo total: {ESTADO['tiempo_total']}s)")
        logger.info(f"Tiempos por fase: {ESTADO['tiempos_fases']}")
    except Exception as e:
        with CANDADO_ESTADO:
            _cerrar_fase_actual()
            ESTADO["terminado"], ESTADO["activo"], ESTADO["fase"] = True, False, "error"
            ESTADO["resultado"] = {"mensaje": f"Error: {e}", "video": None}
            if ESTADO.get("tiempo_inicio_video"):
                ESTADO["tiempo_total"] = round(time.time() - ESTADO["tiempo_inicio_video"], 1)
        logger.error(f"❌ Falló la generación del video: {e}")
        logger.error(traceback.format_exc())
    finally:
        LOGGER_VIDEO_ACTIVO["logger"], LOGGER_VIDEO_ACTIVO["ruta"] = None, None
        cerrar_logger_video(logger)

# ============================================================
# ---- módulo nuevo v5.2: publicación automática (GitHub Actions) ----
# ============================================================
# Estas dos funciones son las que importa run_once.py. No existían en
# ninguna versión anterior del archivo (por eso el workflow publicar.yml
# fallaba con ImportError apenas arrancaba). Encadenan las mismas
# funciones "motor" que ya usaba la interfaz web (obtener_historia_reddit,
# generar_guion_reddit, procesar_todo) pero de forma síncrona, sin Flask,
# sin hilos y sin pasar por ESTADO más que para leer el resultado final.

# Guarda los datos del último video generado por _pipeline_video_automatico
# para que _subir_ultimo_resultado_a_youtube sepa qué subir. Server/proceso
# de un solo uso por corrida de GitHub Actions, así que una variable simple
# alcanza (mismo criterio que _ULTIMO_GRUPO_HISTORIAS de la interfaz).
_ULTIMO_RESULTADO_AUTOMATICO = {}


# ============================================================
# ---- módulo nuevo v5.4: fuentes reales (texto de txt-limpio, gameplay
# propio de gameplay_slither), sincronizadas vía rclone ----
# ============================================================
import random as _random_fuentes


def _elegir_texto_desde_drive(logger=None):
    """Sincroniza gdrive:txt-limpio hacia una carpeta local (solo lo nuevo,
    --ignore-existing) y elige uno de los .txt ya parafraseados para usar
    como guion. Devuelve (texto, nombre_archivo) o (None, None) si no hay
    ninguno disponible. El archivo elegido se mueve a txt-limpio/usados en
    Drive (rclone moveto) recién cuando el pipeline confirma éxito, para
    que si algo falla después quede disponible para reintentar."""
    try:
        resultado = subprocess.run(
            ["rclone", "copy", RCLONE_REMOTE_TXT_LIMPIO, CARPETA_TEXTOS_LISTOS, "--ignore-existing"],
            capture_output=True, text=True, timeout=300,
        )
        if resultado.returncode != 0:
            if logger:
                logger.error(f"rclone copy (txt-limpio) falló: {resultado.stderr[:300]}")
    except Exception as e:
        if logger:
            logger.error(f"Error sincronizando txt-limpio desde Drive: {e}")
        return None, None

    candidatos = sorted(f for f in os.listdir(CARPETA_TEXTOS_LISTOS) if f.endswith(".txt"))
    if not candidatos:
        if logger:
            logger.warning("txt-limpio: no hay ningún .txt disponible para usar.")
        return None, None

    nombre_archivo = candidatos[0]
    ruta = os.path.join(CARPETA_TEXTOS_LISTOS, nombre_archivo)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            texto = f.read()
    except Exception as e:
        if logger:
            logger.error(f"No se pudo leer {nombre_archivo}: {e}")
        return None, None

    if logger:
        logger.info(f"Texto elegido desde txt-limpio: {nombre_archivo} ({len(texto.split())} palabras)")
    return texto, nombre_archivo


def _marcar_texto_usado_en_drive(nombre_archivo, logger=None):
    """Mueve el .txt ya usado de txt-limpio/ a txt-limpio/usados/ en Drive
    (rclone moveto), y borra la copia local (carpeta de trabajo temporal,
    no almacenamiento). Se llama solo después de que el video terminó con
    éxito, para no perder el texto si algo falla antes."""
    origen = f"{RCLONE_REMOTE_TXT_LIMPIO}/{nombre_archivo}"
    destino = f"{RCLONE_REMOTE_TXT_LIMPIO_USADOS}/{nombre_archivo}"
    try:
        resultado = subprocess.run(
            ["rclone", "moveto", origen, destino],
            capture_output=True, text=True, timeout=120,
        )
        if resultado.returncode == 0:
            if logger:
                logger.info(f"Marcado como usado en Drive: {nombre_archivo}")
        else:
            if logger:
                logger.error(f"rclone moveto (txt-limpio) falló para {nombre_archivo}: {resultado.stderr[:300]}")
    except Exception as e:
        if logger:
            logger.error(f"Error marcando como usado {nombre_archivo}: {e}")
    ruta_local = os.path.join(CARPETA_TEXTOS_LISTOS, nombre_archivo)
    if os.path.exists(ruta_local):
        try:
            os.remove(ruta_local)
        except Exception:
            pass


def _obtener_plantilla_miniatura_desde_drive(logger=None):
    """Descarga (una sola vez, se cachea localmente) la plantilla fija de
    miniatura desde gdrive:miniatura/miniatura_plantilla.png. Devuelve la
    ruta local, o None si no existe/falla la descarga (en ese caso el
    llamador cae al método viejo: frame del video)."""
    os.makedirs(CARPETA_MINIATURA_LOCAL, exist_ok=True)
    ruta_local = os.path.join(CARPETA_MINIATURA_LOCAL, "miniatura_plantilla.png")
    if os.path.exists(ruta_local):
        return ruta_local
    try:
        resultado = subprocess.run(
            ["rclone", "copyto", f"{RCLONE_REMOTE_MINIATURA}/miniatura_plantilla.png", ruta_local],
            capture_output=True, text=True, timeout=120,
        )
        if resultado.returncode != 0 or not os.path.exists(ruta_local):
            if logger:
                logger.warning(f"No se pudo bajar la plantilla de miniatura desde Drive: {resultado.stderr[:300]}")
            return None
    except Exception as e:
        if logger:
            logger.warning(f"Error bajando plantilla de miniatura: {e}")
        return None
    return ruta_local


def _elegir_gameplay_desde_drive(logger=None):
    """Lista los videos disponibles en gdrive:gameplay_slither (sin
    descargar todo el catálogo) y descarga solo UNO, elegido al azar, a la
    carpeta local. Devuelve la ruta local del gameplay elegido, o None si
    no hay ninguno disponible."""
    try:
        resultado = subprocess.run(
            ["rclone", "lsf", RCLONE_REMOTE_GAMEPLAY],
            capture_output=True, text=True, timeout=60,
        )
        if resultado.returncode != 0:
            if logger:
                logger.error(f"rclone lsf (gameplay_slither) falló: {resultado.stderr[:300]}")
            return None
    except Exception as e:
        if logger:
            logger.error(f"Error listando gameplay_slither: {e}")
        return None

    candidatos = [
        n.strip() for n in resultado.stdout.splitlines()
        if n.strip().lower().endswith((".mp4", ".mov", ".mkv"))
    ]
    if not candidatos:
        if logger:
            logger.warning("gameplay_slither: no hay ningún video disponible.")
        return None

    elegido = _random_fuentes.choice(candidatos)
    ruta_local = os.path.join(CARPETA_GAMEPLAY_LOCAL, elegido)
    if not os.path.exists(ruta_local):
        try:
            resultado = subprocess.run(
                ["rclone", "copyto", f"{RCLONE_REMOTE_GAMEPLAY}/{elegido}", ruta_local],
                capture_output=True, text=True, timeout=600,
            )
            if resultado.returncode != 0:
                if logger:
                    logger.error(f"rclone copyto (gameplay {elegido}) falló: {resultado.stderr[:300]}")
                return None
        except Exception as e:
            if logger:
                logger.error(f"Error descargando gameplay {elegido}: {e}")
            return None

    if logger:
        logger.info(f"Gameplay elegido desde gameplay_slither: {elegido}")
    return ruta_local


def generar_segmento_video_gameplay(ruta_gameplay, duracion_total, ruta_salida, logger=None):
    """Recorta/repite (según haga falta) un video de gameplay para que dure
    exactamente duracion_total segundos, escalado y recortado a la
    resolución del video final (crop central, sin franjas negras). Se
    conserva el audio propio del gameplay (a diferencia de v5.4 inicial,
    que lo descartaba con -an): mezclar_audio_final se encarga de bajarlo
    al 1% junto con la voz y la música. Con -stream_loop -1 el gameplay se
    repite en loop tantas veces como haga falta si es más corto que la
    narración."""
    filtro = (
        f"scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}:force_original_aspect_ratio=increase,"
        f"crop={RESOLUCION_ANCHO}:{RESOLUCION_ALTO},"
        f"eq=brightness=0.04:contrast=1.15:saturation=1.35,"
        f"format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-threads", "4", "-stream_loop", "-1", "-i", ruta_gameplay,
        "-t", str(duracion_total), "-vf", filtro, "-r", str(FPS),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100", ruta_salida,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        if logger:
            logger.error(f"ffmpeg (fondo de gameplay) devolvió error:\n{resultado.stderr[-2000:]}")
        return False
    return True


def _pipeline_video_automatico(logger, ruta_log):
    """Genera un video completo sin intervención humana, usando las fuentes
    reales del proyecto (v5.4):
    - Texto: ya parafraseado y listo desde gdrive:txt-limpio (repo
      "traduce" con Gemini) -- NO se vuelve a traducir/adaptar con Gemini
      acá, ya viene terminado.
    - Fondo: gameplay propio (Slither.io + bot) desde
      gdrive:gameplay_slither, en vez de imágenes de stock.
    Corre el mismo pipeline de audio/video/subtítulos que ya usa la
    interfaz manual (procesar_todo), con fondo_gameplay=True. Deja el
    resultado en _ULTIMO_RESULTADO_AUTOMATICO para que la función de
    subida lo encuentre."""
    global _ULTIMO_RESULTADO_AUTOMATICO
    logger.info("Pipeline automático: buscando texto listo en txt-limpio...")
    guion, nombre_archivo_texto = _elegir_texto_desde_drive(logger=logger)
    if not guion:
        raise RuntimeError("No se encontró ningún texto nuevo en txt-limpio para usar.")

    titulo_resumen = os.path.splitext(nombre_archivo_texto)[0].replace("_", " ").strip()
    logger.info(f"Texto elegido: {nombre_archivo_texto} ({len(guion.split())} palabras)")

    logger.info("Pipeline automático: buscando gameplay en gameplay_slither...")
    ruta_gameplay = _elegir_gameplay_desde_drive(logger=logger)
    if not ruta_gameplay:
        raise RuntimeError("No se encontró ningún gameplay disponible en gameplay_slither.")

    logger.info("Pipeline automático: arrancando generación de video (esto tarda varios minutos)...")
    # Llamada directa (sin threading.Thread): en GitHub Actions no hay
    # interfaz esperando /progreso, así que conviene que bloquee acá mismo
    # hasta terminar, en vez de devolver el control antes de tiempo.
    procesar_todo(
        guion, 3, "centro", "oro_viejo", 42, FUENTE_POR_DEFECTO, "piano", 12, [], "dinamico",
        False, False, VELOCIDAD_VOZ_POR_DEFECTO, TONO_VOZ_POR_DEFECTO,
        opacidad_sub=100, cantidad_imagenes_descargar=0, ancho_sub_pct=73, pos_y_pct=50,
        efecto_video="ninguno", velocidad_efecto=VELOCIDAD_EFECTO_POR_DEFECTO,
        fondo_gameplay=True, ruta_gameplay=ruta_gameplay,
        logger=logger, ruta_log=ruta_log,
    )

    with CANDADO_ESTADO:
        resultado = dict(ESTADO.get("resultado") or {})

    if not resultado.get("video"):
        raise RuntimeError(f"El pipeline de video falló: {resultado.get('mensaje', 'sin detalle')}")

    ruta_video_absoluta = os.path.join(CARPETA_VIDEOS, resultado["video"])
    if not os.path.exists(ruta_video_absoluta):
        raise RuntimeError(f"procesar_todo dijo que terminó, pero no existe el archivo: {ruta_video_absoluta}")

    # Recién acá, con el video ya confirmado, se marca el texto como usado
    # en Drive (se mueve a txt-limpio/usados/): si algo hubiera fallado
    # antes, el texto queda disponible para reintentar en la próxima
    # corrida del workflow.
    _marcar_texto_usado_en_drive(nombre_archivo_texto, logger=logger)

    _ULTIMO_RESULTADO_AUTOMATICO = {
        "ruta_video": ruta_video_absoluta,
        "titulo_resumen": titulo_resumen,
        "guion": guion,
        "subreddits": [],
        "cantidad_historias": 1,
    }
    logger.info(f"Pipeline automático: video listo en {ruta_video_absoluta}")

    # Miniatura: se genera acá (no en la subida) porque necesita el título ya
    # armado con Gemini para YouTube, y ese título recién se calcula al
    # subir. Se guarda la carpeta del proyecto para que _subir_ultimo_resultado_a_youtube
    # sepa dónde dejar el archivo de miniatura.
    _ULTIMO_RESULTADO_AUTOMATICO["carpeta_proyecto"] = os.path.dirname(ruta_video_absoluta)


PROMPT_TITULO_YOUTUBE = """Convertí este título de un post de Reddit/foro en un título de YouTube atractivo para un video de historia narrada en español.

Reglas:
- Máximo 90 caracteres (importante, no te pases).
- Generá intriga o curiosidad genuina sobre la historia, sin inventar datos que no estén insinuados en el título original.
- No uses mayúsculas sostenidas, no uses emojis, no uses signos de exclamación de más.
- No copies el título original palabra por palabra: reformulalo como titular de YouTube.
- Nada de clickbait falso ni exagerado que no se corresponda con la historia.

Título original: "{titulo}"

Devolvé ÚNICAMENTE el título final, sin comillas, sin explicaciones."""


PROMPT_PREGUNTA_MINIATURA = """A partir de este resumen de una historia real narrada en primera persona, escribí UNA frase corta, polémica y con gancho de clickbait en español, del tipo que se usa en el cartel rojo de una miniatura de YouTube — algo que genere debate y ganas de opinar en los comentarios (ej: "¿SOY LA MALA POR ESTO?", "LA VERDAD QUE NADIE QUISO CREERME", "ESTO DESTRUYÓ A TODA MI FAMILIA").

Reglas:
- Máximo 10 palabras.
- Tono provocador/polémico, primera persona o afirmación directa (puede ser pregunta o no).
- Sin inventar datos que no estén en el resumen.
- Sin emojis, sin comillas.

Resumen: "{resumen}"

Devolvé ÚNICAMENTE la frase final, sin explicaciones."""


def _obtener_plantilla_intro_desde_drive(logger=None):
    """
    Descarga (si hace falta) la plantilla de la intro de resumen
    desde gdrive:intro/intro_plantilla.png. Devuelve la ruta local,
    o None si no se pudo conseguir."""
    os.makedirs(CARPETA_INTRO_LOCAL, exist_ok=True)
    ruta_local = os.path.join(CARPETA_INTRO_LOCAL, "intro_plantilla.png")
    # Siempre se vuelve a bajar de Drive (no se cachea la primera descarga
    # para siempre): asi si se actualiza la plantilla en Drive, el pipeline
    # usa la version nueva automaticamente en la proxima corrida.
    try:
        resultado = subprocess.run(
            ["rclone", "copyto", f"{RCLONE_REMOTE_INTRO}/intro_plantilla.png", ruta_local],
            capture_output=True, text=True,
        )
        if resultado.returncode != 0 or not os.path.exists(ruta_local):
            if logger:
                logger.warning(f"No se pudo bajar la plantilla de intro: {resultado.stderr[-300:]}")
            return None
        return ruta_local
    except Exception as e:
        if logger:
            logger.warning(f"Error bajando plantilla de intro: {e}")
        return None


def _generar_pregunta_miniatura(resumen_texto, logger=None):
    """Genera con Gemini la pregunta-dilema que va en la miniatura (estilo
    '¿Soy la mala por...?'). Si Gemini falla o no hay API key, arma una
    versión de respaldo genérica a partir del resumen."""
    def _respaldo():
        base = " ".join(resumen_texto.split())[:70].rstrip()
        return "LA HISTORIA QUE NADIE SE ATREVIÓ A CONTAR"

    if not GEMINI_API_KEY:
        return _respaldo()

    try:
        prompt = PROMPT_PREGUNTA_MINIATURA.format(resumen=resumen_texto[:600])
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        pregunta = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        if not pregunta:
            return _respaldo()
        return pregunta.upper()
    except Exception as e:
        if logger:
            logger.warning(f"Fallo al generar la pregunta de miniatura con Gemini: {e}")
        return _respaldo()


def _armar_titulo_youtube(titulo_resumen, subreddits, logger=None):
    """Arma un título para YouTube (límite de 100 caracteres) usando Gemini
    para reformular el título original de la historia en un titular más
    atractivo, en vez de usar el título crudo de Reddit tal cual (que está
    pensado para ese foro, no para YouTube). Si Gemini falla o no hay API
    key, cae al título original recortado como respaldo."""
    sufijo = " | Historia real"
    disponible = 100 - len(sufijo)
    titulo_original = titulo_resumen.strip()

    def _respaldo():
        titulo = titulo_original
        if len(titulo) > disponible:
            titulo = titulo[:disponible - 1].rstrip() + "…"
        return titulo + sufijo

    if not GEMINI_API_KEY:
        return _respaldo()

    try:
        prompt = PROMPT_TITULO_YOUTUBE.format(titulo=titulo_original)
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        titulo_gemini = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        if not titulo_gemini:
            return _respaldo()
        if len(titulo_gemini) > disponible:
            titulo_gemini = titulo_gemini[:disponible - 1].rstrip() + "…"
        return titulo_gemini + sufijo
    except Exception as e:
        if logger:
            logger.warning(f"Fallo al generar título con Gemini, se usa el título original: {e}")
        return _respaldo()


def generar_miniatura(ruta_video, titulo_miniatura, ruta_salida, logger=None):
    """Genera una miniatura (1280x720, formato recomendado por YouTube) a
    partir de un frame del video ya terminado, con el título superpuesto en
    texto grande. Usa ffmpeg (ya es una dependencia del proyecto, no hace
    falta instalar Pillow aparte). Si algo falla, devuelve None y el resto
    del pipeline sigue sin miniatura (YouTube usa un frame automático)."""
    try:
        duracion = obtener_duracion_audio(ruta_video)
    except Exception:
        duracion = 30.0
    instante = min(max(3.0, duracion * 0.15), duracion - 1 if duracion > 1 else 0)

    # Título en mayúsculas, cortado a un largo razonable para miniatura
    # (a diferencia del título completo de YouTube, acá conviene bien corto
    # para que se lea a tamaño chico en la lista de videos).
    texto_miniatura = titulo_miniatura.strip().upper()
    if len(texto_miniatura) > 70:
        texto_miniatura = texto_miniatura[:69].rstrip() + "…"
    # Se parte en hasta 3 líneas para que no quede una sola línea gigante.
    palabras = texto_miniatura.split()
    lineas, actual, largo = [], [], 0
    max_chars_linea = 24
    for palabra in palabras:
        if actual and largo + len(palabra) + 1 > max_chars_linea:
            lineas.append(" ".join(actual))
            actual, largo = [], 0
        actual.append(palabra)
        largo += len(palabra) + 1
    if actual:
        lineas.append(" ".join(actual))
    lineas = lineas[:3]

    nombre_fuente_ok = asegurar_fuente(FUENTE_POR_DEFECTO) or FUENTE_POR_DEFECTO
    ruta_fuente = os.path.join(CARPETA_FUENTES, FUENTES_DISPONIBLES[nombre_fuente_ok].split("/")[-1])
    if not os.path.exists(ruta_fuente):
        ruta_fuente = None

    filtros = [f"scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}", "drawbox=x=0:y=ih*0.55:w=iw:h=ih*0.45:color=black@0.55:t=fill"]
    y_inicial = 68
    for i, linea in enumerate(lineas):
        linea_escapada = linea.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""
        y_pos = f"h-{(len(lineas) - i) * 130}"
        filtros.append(
            f"drawtext=text='{linea_escapada}'{fontfile}:fontcolor=white:fontsize=76:"
            f"borderw=6:bordercolor=black:x=(w-text_w)/2:y={y_pos}"
        )

    cmd = [
        "ffmpeg", "-y", "-ss", str(instante), "-i", ruta_video,
        "-frames:v", "1", "-vf", ",".join(filtros), ruta_salida,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo generar la miniatura, YouTube usará un frame automático: {resultado.stderr[-500:]}")
        return None
    if logger:
        logger.info(f"Miniatura generada: {ruta_salida}")
    return ruta_salida


def generar_fondo_ia_pollinations(resumen_texto, ruta_salida, logger=None, ancho=None, alto=None, prompt_personalizado=None):
    """Genera una imagen con IA (Pollinations, gratis, sin API key). Si
    prompt_personalizado viene armado (escena puntual de la historia,
    generada con _generar_prompt_imagen_miniatura), lo usa; si no, cae al
    prompt generico anterior (dos personas confrontandose) a partir del
    resumen corto."""
    import urllib.parse

    ancho = ancho or RESOLUCION_ANCHO
    alto = alto or RESOLUCION_ALTO

    if prompt_personalizado:
        prompt = (
            f"{prompt_personalizado}, photorealistic, cinematic photography, "
            f"film still, natural lighting, shallow depth of field, realistic "
            f"faces, high detail"
        )
    else:
        resumen_corto = " ".join(resumen_texto.split())[:180]
        prompt = (
            f"{resumen_corto}, two people confronting each other, dramatic tense "
            f"argument, photorealistic, cinematic photography, film still, natural "
            f"lighting, shallow depth of field, realistic faces, high detail"
        )

    prompt_codificado = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{prompt_codificado}"
        f"?width={ancho}&height={alto}&nologo=true"
    )
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        with open(ruta_salida, "wb") as f:
            f.write(r.content)
        if logger:
            logger.info(f"Imagen IA (Pollinations) generada: {ruta_salida}")
        return ruta_salida
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo generar la imagen con IA (Pollinations): {e}")
        return None


PROMPT_IMAGEN_MINIATURA = """A partir de esta historia real narrada en primera persona y su titulo ya definido, identifica el momento MAS impactante, revelador o intrigante de toda la historia (el giro, la confesion, el hallazgo, la escena que genera mas ganas de saber que paso) y describi ESA escena puntual como prompt de imagen en ingles, para un generador de imagenes fotorrealista.

Reglas del prompt:
- Debe coincidir con lo que promete el titulo, no ser generico
- Personajes con su emocion visible (shocked, guilty, crying, furious, etc.)
- Lugar/escenario concreto segun la historia (kitchen, hospital, courtroom, car, etc.)
- Un objeto o detalle visual que identifique el conflicto (a letter, a phone screen, a pregnancy test, a broken photo frame, etc.) si la historia lo tiene
- NO texto en la imagen, NO logos, NO watermarks
- Una sola escena, no collage

Titulo: {titulo}

Historia completa:
{historia}

Devolve SOLO el prompt en ingles, una sola linea, sin comillas ni explicacion."""


def _generar_prompt_imagen_miniatura(historia_completa, titulo, logger=None):
    """Genera con Gemini un prompt en ingles para Pollinations describiendo
    la escena mas intrigante/reveladora de TODA la historia (no solo el
    resumen corto), coherente con el titulo ya generado. Si Gemini falla
    o no hay API key, devuelve None y generar_fondo_ia_pollinations cae
    al prompt generico de respaldo (dos personas confrontandose)."""
    if not GEMINI_API_KEY or not historia_completa:
        return None

    try:
        prompt = PROMPT_IMAGEN_MINIATURA.format(
            titulo=titulo.strip(),
            historia=historia_completa.strip()[:4000],
        )
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        prompt_imagen = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        return prompt_imagen or None
    except Exception as e:
        if logger:
            logger.warning(f"Fallo al generar prompt de imagen con Gemini, se usa el generico: {e}")
        return None


def generar_miniatura_clickbait(titulo_miniatura, resumen_texto, ruta_salida, logger=None, ruta_video_fondo=None, historia_completa=None):
    """Miniatura estilo 'split': mitad izquierda con una imagen realista
    generada con IA (dos personas confrontándose, a partir del resumen de
    la historia) y mitad derecha una tarjeta blanca con el logo HSF, el
    nombre del canal y una pregunta-dilema (generada con Gemini a partir
    del resumen, estilo '¿Hice mal en...?'), en negro y mayúscula. Borde
    rojo grueso alrededor de todo. Si la imagen con IA falla, usa un
    frame del gameplay como respaldo para el lado izquierdo."""
    ancho_mitad = RESOLUCION_ANCHO // 2
    prompt_imagen = _generar_prompt_imagen_miniatura(
        historia_completa or resumen_texto, titulo_miniatura, logger=logger,
    )
    ruta_imagen_izq = generar_fondo_ia_pollinations(
        resumen_texto, ruta_salida + ".izq.jpg", logger=logger,
        ancho=ancho_mitad, alto=RESOLUCION_ALTO,
        prompt_personalizado=prompt_imagen,
    )

    pregunta = _generar_pregunta_miniatura(resumen_texto, logger=logger)

    def envolver_por_ancho(texto, max_chars):
        palabras = texto.split()
        lineas, actual, largo = [], [], 0
        for palabra in palabras:
            if actual and largo + len(palabra) + 1 > max_chars:
                lineas.append(" ".join(actual))
                actual, largo = [], 0
            actual.append(palabra)
            largo += len(palabra) + 1
        if actual:
            lineas.append(" ".join(actual))
        return lineas

    # Calibrado con DejaVu Sans Bold: a fontsize=40, ~27.4px/carácter;
    # panel derecho tiene ~560px útiles de ancho (640 de mitad - 80 de
    # margen), así que 20 caracteres por línea es lo que entra bien.
    lineas = envolver_por_ancho(pregunta, 20)[:5]

    nombre_fuente_ok = asegurar_fuente(FUENTE_POR_DEFECTO) or FUENTE_POR_DEFECTO
    ruta_fuente = os.path.join(CARPETA_FUENTES, FUENTES_DISPONIBLES[nombre_fuente_ok].split("/")[-1])
    if not os.path.exists(ruta_fuente):
        ruta_fuente = None
    fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""

    alto_linea = 58
    x_centro_panel = ancho_mitad + ancho_mitad // 2
    y_inicio = 180 + (420 - len(lineas) * alto_linea) // 2

    ruta_logo = os.path.join(CARPETA_BASE, "assets", "logo_hsf.png")
    tiene_logo = os.path.exists(ruta_logo)

    grosor_borde = 10
    filtros_borde = [
        f"drawbox=x=0:y=0:w={RESOLUCION_ANCHO}:h={grosor_borde}:color=0xDC1414:t=fill",
        f"drawbox=x=0:y={RESOLUCION_ALTO-grosor_borde}:w={RESOLUCION_ANCHO}:h={grosor_borde}:color=0xDC1414:t=fill",
        f"drawbox=x=0:y=0:w={grosor_borde}:h={RESOLUCION_ALTO}:color=0xDC1414:t=fill",
        f"drawbox=x={RESOLUCION_ANCHO-grosor_borde}:y=0:w={grosor_borde}:h={RESOLUCION_ALTO}:color=0xDC1414:t=fill",
        f"drawbox=x={ancho_mitad-grosor_borde//2}:y=0:w={grosor_borde}:h={RESOLUCION_ALTO}:color=0xDC1414:t=fill",
    ]

    dibujo_texto_centrado = []
    for i, linea in enumerate(lineas):
        linea_escapada = linea.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        y_pos = y_inicio + i * alto_linea
        # Centrado manual: se mide el texto con la misma heurística de
        # ancho por carácter usada para el wrap (evita tener que centrar
        # con text_w, que en ffmpeg se calcula respecto a todo el canvas).
        ancho_estimado = int(len(linea_escapada) * 27.4)
        x_pos = x_centro_panel - ancho_estimado // 2
        dibujo_texto_centrado.append(
            f"drawtext=text='{linea_escapada}'{fontfile}:fontcolor=black:fontsize=40:x={x_pos}:y={y_pos}"
        )

    filtros_nombre = []
    if tiene_logo:
        filtros_nombre.append(
            f"drawtext=text='Historias Sin Filtro'{fontfile}:fontcolor=black:fontsize=26:"
            f"x={ancho_mitad + 132}:y=52"
        )

    filtro_vf = ",".join(filtros_borde + filtros_nombre + dibujo_texto_centrado)

    if ruta_imagen_izq:
        entrada_izq = ruta_imagen_izq
    elif ruta_video_fondo and os.path.exists(ruta_video_fondo):
        # Recorta un frame del gameplay como respaldo, ya escalado a la
        # mitad del ancho.
        entrada_izq = ruta_salida + ".izq_respaldo.jpg"
        try:
            duracion = obtener_duracion_audio(ruta_video_fondo)
        except Exception:
            duracion = 10.0
        instante = min(max(2.0, duracion * 0.15), duracion - 1 if duracion > 1 else 0)
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(instante), "-i", ruta_video_fondo,
             "-vf", f"scale={ancho_mitad}:{RESOLUCION_ALTO}", "-frames:v", "1", entrada_izq],
            capture_output=True,
        )
        if not os.path.exists(entrada_izq):
            entrada_izq = None
    else:
        entrada_izq = None

    if not entrada_izq:
        cmd_fondo_izq = ["ffmpeg", "-y", "-f", "lavfi",
                          "-i", f"color=c=gray:s={ancho_mitad}x{RESOLUCION_ALTO}",
                          "-frames:v", "1", ruta_salida + ".izq_gris.jpg"]
        subprocess.run(cmd_fondo_izq, capture_output=True)
        entrada_izq = ruta_salida + ".izq_gris.jpg"

    # Lienzo blanco de fondo + imagen izquierda superpuesta + (logo) +
    # bordes + texto, todo en una sola pasada de ffmpeg con filter_complex.
    entradas = ["-f", "lavfi", "-i", f"color=c=white:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}",
                "-i", entrada_izq]
    mapa_filtro = f"[1:v]scale={ancho_mitad}:{RESOLUCION_ALTO}[izq];[0:v][izq]overlay=0:0[base]"
    entrada_actual = "[base]"
    if tiene_logo:
        entradas += ["-i", ruta_logo]
        mapa_filtro += f";{entrada_actual}[2:v]overlay={ancho_mitad+60}:34[conlogo]"
        entrada_actual = "[conlogo]"
    mapa_filtro += f";{entrada_actual}{filtro_vf}[out]"

    cmd = ["ffmpeg", "-y"] + entradas + ["-filter_complex", mapa_filtro, "-map", "[out]", "-frames:v", "1", ruta_salida]

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo generar la miniatura split: {resultado.stderr[-500:]}")
        return None
    if logger:
        logger.info(f"Miniatura split generada: {ruta_salida}")
    return ruta_salida


GEMINI_MODELO_IMAGEN = "gemini-2.5-flash-image"


def _generar_ilustracion_fondo_gemini(resumen_texto, ruta_salida, logger=None):
    """Genera una ilustracion de fondo (estilo comic simple y oscuro, en dos
    escenas apiladas) a partir del resumen de la historia, usando Gemini
    Image (Nano Banana). Devuelve la ruta local del PNG generado, o None si
    falla (el llamador cae al fondo de gameplay/negro de siempre)."""
    import base64

    if not GEMINI_API_KEY:
        if logger:
            logger.warning("GEMINI_API_KEY vacia: no se genera ilustracion de fondo.")
        return None

    prompt = (
        "Ilustracion digital estilo comic simple y oscuro, formato vertical, "
        "dividida en dos escenas apiladas separadas por una linea blanca, "
        "representando visualmente esta historia real (SIN texto escrito "
        "dentro de la imagen, sin logos ni marcas de agua):\n\n"
        f"{resumen_texto.strip()[:600]}"
    )

    intentos_maximos = 3
    espera = 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO_IMAGEN}:generateContent",
                headers={"x-goog-api-key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=90,
            )
            if resp.status_code == 429:
                espera_real = espera
                try:
                    espera_real = max(espera, int(float(resp.headers.get("Retry-After", espera))))
                except (TypeError, ValueError):
                    pass
                if logger:
                    logger.warning(
                        f"Gemini Image devolvio 429. Intento {intento}/{intentos_maximos}, "
                        f"reintentando en {espera_real}s..."
                    )
                if intento < intentos_maximos:
                    time.sleep(espera_real)
                    espera *= 2
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            datos = resp.json()
            partes = datos["candidates"][0]["content"]["parts"]
            datos_b64 = next(
                (p["inlineData"]["data"] for p in partes if "inlineData" in p), None
            ) or next(
                (p["inline_data"]["data"] for p in partes if "inline_data" in p), None
            )
            if not datos_b64:
                raise ValueError("La respuesta de Gemini Image no trajo ninguna imagen")
            with open(ruta_salida, "wb") as f:
                f.write(base64.b64decode(datos_b64))
            if logger:
                logger.info(f"Ilustracion de fondo generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                if logger:
                    logger.warning(f"Fallo la generacion de la ilustracion tras {intentos_maximos} intentos: {e}")
                return None
            if logger:
                logger.warning(f"Error generando ilustracion (intento {intento}/{intentos_maximos}): {e}")
            time.sleep(espera)
            espera *= 2
    return None


def generar_miniatura_plantilla(titulo_miniatura, ruta_plantilla, ruta_salida, logger=None, ruta_video_fondo=None, resumen_texto=None):
    """Genera la miniatura a partir de una plantilla fija (tarjeta tipo
    'post', con el borde exterior transparente) superpuesta sobre, en este
    orden de prioridad: (1) una ilustracion generada con Gemini Image a
    partir del resumen de la historia si se pasa resumen_texto, (2) un
    frame del gameplay si se pasa ruta_video_fondo, o (3) negro si no hay
    nada de eso disponible. Posicion y tamanos de fuente calibrados a ojo
    para que el titulo quede bien dentro del recuadro. La tarjeta esta
    corrida hacia la derecha del cuadro dejando la izquierda libre para el
    fondo elegido."""
    texto_miniatura = titulo_miniatura.strip().upper()
    if len(texto_miniatura) > 110:
        texto_miniatura = texto_miniatura[:109].rstrip() + "…"

    def envolver(texto, max_chars):
        palabras = texto.split()
        lineas, actual, largo = [], [], 0
        for palabra in palabras:
            if actual and largo + len(palabra) + 1 > max_chars:
                lineas.append(" ".join(actual))
                actual, largo = [], 0
            actual.append(palabra)
            largo += len(palabra) + 1
        if actual:
            lineas.append(" ".join(actual))
        return lineas

    lineas = envolver(texto_miniatura, 34)
    tamano_fuente, y_inicio, alto_linea = 40, 270, 55
    if len(lineas) > 2:
        lineas = envolver(texto_miniatura, 45)
        tamano_fuente, y_inicio, alto_linea = 30, 270, 42
        lineas = lineas[:3]

    nombre_fuente_ok = asegurar_fuente(FUENTE_POR_DEFECTO) or FUENTE_POR_DEFECTO
    ruta_fuente = os.path.join(CARPETA_FUENTES, FUENTES_DISPONIBLES[nombre_fuente_ok].split("/")[-1])
    if not os.path.exists(ruta_fuente):
        ruta_fuente = None

    desplazamiento_tarjeta = 669
    tarjeta_x_izq = 89
    tarjeta_ancho = 1102
    dibujo_texto = []
    for i, linea in enumerate(lineas):
        linea_escapada = linea.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""
        y_pos = y_inicio + i * alto_linea
        x_expr = f"{tarjeta_x_izq + desplazamiento_tarjeta}+({tarjeta_ancho}-text_w)/2"
        dibujo_texto.append(
            f"drawtext=text='{linea_escapada}'{fontfile}:fontcolor=black:fontsize={tamano_fuente}:"
            f"borderw=1.2:bordercolor=black:x={x_expr}:y={y_pos}"
        )
    cadena_texto = ",".join(dibujo_texto)

    ruta_ilustracion = None
    if resumen_texto:
        ruta_ilustracion_tmp = os.path.splitext(ruta_salida)[0] + "_fondo_ia.png"
        ruta_ilustracion = _generar_ilustracion_fondo_gemini(resumen_texto, ruta_ilustracion_tmp, logger=logger)

    if ruta_ilustracion and os.path.exists(ruta_ilustracion):
        filtro_complejo = (
            f"[0:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}[fondo];"
            f"[fondo][1:v]overlay={desplazamiento_tarjeta}:0[con];"
            f"[con]{cadena_texto}[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", ruta_ilustracion,
            "-i", ruta_plantilla,
            "-filter_complex", filtro_complejo, "-map", "[out]",
            "-frames:v", "1", ruta_salida,
        ]
    elif ruta_video_fondo and os.path.exists(ruta_video_fondo):
        try:
            duracion = obtener_duracion_audio(ruta_video_fondo)
        except Exception:
            duracion = 10.0
        instante = min(max(2.0, duracion * 0.15), duracion - 1 if duracion > 1 else 0)
        filtro_complejo = (
            f"[1:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO}[tmpl];"
            f"[0:v][tmpl]overlay={desplazamiento_tarjeta}:0[conmpl];"
            f"[conmpl]{cadena_texto}[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-ss", str(instante), "-i", ruta_video_fondo,
            "-i", ruta_plantilla,
            "-filter_complex", filtro_complejo, "-map", "[out]",
            "-frames:v", "1", ruta_salida,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={RESOLUCION_ANCHO}x{RESOLUCION_ALTO}",
            "-i", ruta_plantilla,
            "-filter_complex", f"[0:v][1:v]overlay={desplazamiento_tarjeta}:0[con];[con]{cadena_texto}[out]",
            "-map", "[out]", "-frames:v", "1", ruta_salida,
        ]

    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo generar la miniatura con plantilla: {resultado.stderr[-500:]}")
        return None
    if logger:
        logger.info(f"Miniatura (plantilla) generada: {ruta_salida}")
    return ruta_salida


def agregar_intro_resumen(ruta_video, ruta_plantilla, resumen_texto, ruta_salida, duracion_intro=10.0, logger=None):
    """Superpone la plantilla real (logo HSF + tarjeta blanca, croma verde
    recortado con colorkey) con 2-3 oraciones de contexto centradas dentro
    del rectangulo blanco, debajo del encabezado. Dura al menos duracion_intro,
    o mas si el texto es largo (para que de tiempo a leerlo)."""
    if not ruta_plantilla or not os.path.exists(ruta_plantilla):
        ruta_plantilla = _obtener_plantilla_intro_desde_drive(logger=logger)
    if not ruta_plantilla:
        if logger:
            logger.warning("No hay plantilla de intro disponible, se omite la tarjeta")
        return False

    texto_limpio = resumen_texto.strip()
    palabras_texto = texto_limpio.split()
    duracion_real = max(duracion_intro, len(palabras_texto) * 0.35)

    # No se trunca a un numero fijo de caracteres a ciegas: se envuelve el
    # texto completo mas abajo, y solo si de verdad no entra en 6 lineas se
    # corta la ULTIMA linea visible con "..." (nunca se descartan lineas
    # completas en silencio).
    texto = texto_limpio.upper()

    ruta_fuente = _mf_buscar_fuente_condensada()
    fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""

    # Zona de texto dentro del rectangulo blanco de la plantilla (medida
    # directamente sobre la plantilla real de 1376x768, y escalada a
    # RESOLUCION_ANCHOxRESOLUCION_ALTO=1920x1080): el blanco va de
    # x 237-1139 / y 76-692 en la plantilla original, y el header (logo +
    # nombre) termina en y=286 de esa misma plantilla. Escalado:
    # x: 237*1.395349=330.7 / 1139*1.395349=1589.4
    # y: header 286*1.40625=402.2 / blanco-abajo 692*1.40625=973.3
    from PIL import ImageFont

    x_izq_texto = 330
    x_der_texto = 1590
    y_arriba_texto = 415  # un poco debajo del header (~402) para no pisarlo
    y_abajo_texto = 930   # un poco arriba del borde blanco (~973) de margen
    ancho_texto_disponible = x_der_texto - x_izq_texto - 160
    alto_texto_disponible = y_abajo_texto - y_arriba_texto

    def _medir_ancho(txt, fontsize):
        try:
            fuente_pil = ImageFont.truetype(ruta_fuente, fontsize) if ruta_fuente else ImageFont.load_default()
        except Exception:
            fuente_pil = ImageFont.load_default()
        bbox = fuente_pil.getbbox(txt)
        return bbox[2] - bbox[0]

    def _envolver_real(txt, fontsize, ancho_max):
        palabras = txt.split()
        lineas_, actual = [], []
        for palabra in palabras:
            prueba = " ".join(actual + [palabra])
            if actual and _medir_ancho(prueba, fontsize) > ancho_max:
                lineas_.append(" ".join(actual))
                actual = [palabra]
            else:
                actual.append(palabra)
        if actual:
            lineas_.append(" ".join(actual))
        return lineas_

    candidatos = [(56, 68), (50, 61), (44, 54), (38, 47), (32, 40), (27, 34), (22, 29), (18, 24)]
    lineas, tamano_texto, alto_linea = None, None, None
    margen_seguridad = 20  # aire extra para que la ultima linea no toque el borde
    for tamano, alto in candidatos:
        prueba = _envolver_real(texto, tamano, ancho_texto_disponible)
        if len(prueba) <= 6 and len(prueba) * alto <= (alto_texto_disponible - margen_seguridad):
            lineas, tamano_texto, alto_linea = prueba, tamano, alto
            break
    if lineas is None:
        # Ni al tamano mas chico entra completo: se usa el tamano mas chico
        # igual, pero el corte a 6 lineas queda marcado con "..." en la
        # ultima linea visible, en vez de desaparecer palabras en silencio.
        tamano_texto, alto_linea = candidatos[-1]
        lineas_completas = _envolver_real(texto, tamano_texto, ancho_texto_disponible)
        if len(lineas_completas) > 6:
            lineas = lineas_completas[:6]
            ultima = lineas[-1].rstrip()
            if ultima.endswith((".", "!", "?", "…")):
                ultima = ultima[:-1]
            lineas[-1] = ultima.rstrip() + "…"
        else:
            lineas = lineas_completas

    centro_y = (y_arriba_texto + y_abajo_texto) // 2
    y_inicio = centro_y - (len(lineas) * alto_linea) // 2
    ventana = f"between(t,0,{duracion_real})"

    dibujo_texto = []
    for i, linea in enumerate(lineas):
        linea_escapada = _mf_escapar(linea)
        y_pos = y_inicio + i * alto_linea
        dibujo_texto.append(
            f"drawtext=text='{linea_escapada}'{fontfile}:fontcolor=black:fontsize={tamano_texto}:"
            f"x=(w-text_w)/2:y={y_pos}:enable='{ventana}'"
        )
    cadena_texto = ",".join(dibujo_texto)

    filtro_complejo = (
        f"[1:v]scale={RESOLUCION_ANCHO}:{RESOLUCION_ALTO},colorkey=0x1FDD77:0.35:0.15[tmpl];"
        f"[0:v][tmpl]overlay=0:0:enable='{ventana}'[conplantilla];"
        f"[conplantilla]{cadena_texto}[vout]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", ruta_video, "-i", ruta_plantilla,
        "-filter_complex", filtro_complejo,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy",
        ruta_salida,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo agregar la intro de resumen al video: {resultado.stderr[-500:]}")
        return False
    if logger:
        logger.info(f"Intro de resumen agregada ({duracion_real:.1f}s): {ruta_salida}")
    return True

HASHTAGS_FIJOS = ["#historiasreales", "#confesiones", "#reddit", "#storytime", "#historiassinfiltro"]

def _armar_descripcion_youtube(subreddits, cantidad_historias):
    partes = [
        "Una historia real que te va a dejar pensando. Confesiones, secretos de familia y relatos que la gente compartió de forma anónima en internet.",
        "",
        f"Fuente: {'r/' + ', r/'.join(subreddits) if subreddits else 'foros de internet'}"
        + (f" ({cantidad_historias} historias combinadas)" if cantidad_historias > 1 else ""),
        "",
        "Los nombres y detalles fueron adaptados para narración; la historia",
        "original fue compartida públicamente por su autor/a.",
        "",
        "🔔 Suscribite para más historias cada semana.",
        "",
        " ".join(HASHTAGS_FIJOS),
    ]
    return "\n".join(partes)


def _armar_tags_youtube(titulo_resumen):
    """Arma la lista de etiquetas (tags) del video: algunas fijas del canal
    más algunas palabras sueltas sacadas del título de la historia, para
    ayudar al algoritmo de YouTube a entender el contenido."""
    tags_fijos = [
        "historias reales", "historias de reddit", "confesiones",
        "historias sin filtro", "relatos reales", "storytime en español",
        "historias narradas", "secretos de familia",
    ]
    palabras_titulo = [
        p.strip(".,!?¿¡\"'").lower()
        for p in titulo_resumen.split()
        if len(p) > 3
    ]
    tags = tags_fijos + palabras_titulo
    # YouTube limita el total de tags a 500 caracteres sumados; se recorta
    # por las dudas para no pasarse.
    tags_final, largo = [], 0
    for t in tags:
        if largo + len(t) + 1 > 480:
            break
        tags_final.append(t)
        largo += len(t) + 1
    return tags_final


def _subir_ultimo_resultado_a_youtube(logger):
    """Sube a YouTube el último video generado por _pipeline_video_automatico
    (debe correr después, en la misma ejecución). Se autentica con un
    refresh token de OAuth (YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN, ya
    generado una única vez de forma manual) — no requiere abrir navegador
    en GitHub Actions."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    resultado = _ULTIMO_RESULTADO_AUTOMATICO
    if not resultado or not resultado.get("ruta_video"):
        raise RuntimeError("No hay ningún video generado en esta corrida para subir a YouTube.")

    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if not (client_id and client_secret and refresh_token):
        raise RuntimeError("Faltan YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN.")

    credenciales = Credentials(
        None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=credenciales)

    titulo = _armar_titulo_youtube(resultado["titulo_resumen"], resultado["subreddits"])
    descripcion = _armar_descripcion_youtube(resultado["subreddits"], resultado["cantidad_historias"])
    logger.info(f"Subiendo a YouTube: {titulo}")

    cuerpo = {
        "snippet": {
            "title": titulo,
            "description": descripcion,
            "tags": _armar_tags_youtube(resultado["titulo_resumen"]),
            "categoryId": "24",  # Entretenimiento
        },
        "status": {
            "privacyStatus": os.environ.get("HSF_PRIVACIDAD_YOUTUBE", "public"),
            "selfDeclaredMadeForKids": False,
            # Declaración obligatoria (política YouTube 2026): la voz es
            # síntesis de audio por IA (edge_tts), así que se marca "Sí" en
            # "Uso de la IA" en vez de dejarlo sin declarar.
            "containsSyntheticMedia": True,
        },
    }
    medio = MediaFileUpload(resultado["ruta_video"], chunksize=-1, resumable=True, mimetype="video/mp4")
    solicitud = youtube.videos().insert(part="snippet,status", body=cuerpo, media_body=medio)

    respuesta = None
    while respuesta is None:
        estado, respuesta = solicitud.next_chunk()
        if estado:
            logger.info(f"Subida a YouTube: {int(estado.progress() * 100)}%")

    video_id = respuesta.get("id")
    logger.info(f"✅ Video publicado en YouTube: https://youtu.be/{video_id}")

    # Miniatura: se genera recién acá porque necesita el título ya armado
    # con Gemini (arriba). Si falla cualquier paso (ffmpeg o la subida),
    # se loguea el motivo y se sigue sin cortar nada: el video ya quedó
    # publicado, YouTube simplemente usa un frame automático como miniatura.
    try:
        carpeta_proyecto = resultado.get("carpeta_proyecto") or os.path.dirname(resultado["ruta_video"])
        ruta_miniatura = os.path.join(carpeta_proyecto, "miniatura.jpg")
        # Se reusa el mismo título ya generado con Gemini, sin el sufijo
        # " | Historia real" (ese sufijo es para la lista de videos, en la
        # miniatura ocupa espacio de más sin aportar nada).
        titulo_para_imagen = titulo.replace(" | Historia real", "")
        # Si hay una plantilla fija en Drive (gdrive:miniatura/miniatura_
        # plantilla.png), se usa esa en vez de sacar un frame del video:
        # mismo diseño siempre, solo cambia el título.
        ok_miniatura = generar_miniatura_nanobanana_pro(
            titulo_para_imagen, resultado["titulo_resumen"], ruta_miniatura, logger=logger,
            historia_completa=resultado.get("guion"),
        )
        ruta_plantilla = _obtener_plantilla_miniatura_desde_drive(logger=logger)
        if not ok_miniatura:
            ok_miniatura = generar_miniatura_nueva(
                titulo_para_imagen, resultado["titulo_resumen"], ruta_miniatura, logger=logger,
                ruta_video_fondo=resultado["ruta_video"],
            )
        if not ok_miniatura:
            ok_miniatura = generar_miniatura_clickbait(
                titulo_para_imagen, resultado["titulo_resumen"], ruta_miniatura, logger=logger,
                ruta_video_fondo=resultado["ruta_video"],
                historia_completa=resultado.get("guion"),
            )
        if not ok_miniatura and ruta_plantilla:
            ok_miniatura = generar_miniatura_plantilla(
                titulo_para_imagen, ruta_plantilla, ruta_miniatura, logger=logger,
                ruta_video_fondo=resultado["ruta_video"],
            )
        if not ok_miniatura:
            ok_miniatura = generar_miniatura(resultado["ruta_video"], titulo_para_imagen, ruta_miniatura, logger=logger)
        if ok_miniatura:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(ruta_miniatura, mimetype="image/jpeg")).execute()
            logger.info("✅ Miniatura subida correctamente.")
    except Exception as e:
        logger.warning(f"No se pudo generar/subir la miniatura (el video ya quedó publicado igual): {e}")


# ============================================================
# ---- prueba rápida del núcleo + YouTube (texto corto -> video corto -> sube) ----
# ============================================================
if __name__ == "__main__":
    import sys

    TEXTO_PRUEBA = """
    Nunca pensé que algo tan pequeño pudiera cambiarlo todo. Esa tarde,
    mientras ordenaba las cosas de mi abuela, encontré una carta que nunca
    debí leer. Estaba guardada en el fondo de un cajón, envuelta en un
    pañuelo viejo, como si alguien hubiera querido esconderla del tiempo
    mismo. La abrí sin pensarlo dos veces. Las primeras líneas me dejaron
    helado. Ahí estaba, escrito de puño y letra, un secreto que había
    cargado sola durante más de cuarenta años.
    """

    logger, ruta_log = crear_logger_video()
    ruta_gameplay_prueba = _elegir_gameplay_desde_drive(logger=logger)
    procesar_todo(
        texto_bruto=TEXTO_PRUEBA,
        frases_por_bloque=3,
        posicion="centro",
        color_sub="oro_viejo",
        tamano_sub=42,
        fuente_sub=None,
        musica_genero="piano",
        volumen_musica=12,
        rutas_imagenes_subidas=[],
        animacion="dinamico",
        traducir_auto=False,
        fondo_fijo=False,
        velocidad_voz=5,
        tono_voz=-5,
        opacidad_sub=100,
        cantidad_imagenes_descargar=0,
        ancho_sub_pct=73,
        pos_y_pct=50,
        efecto_video="ninguno",
        fondo_gameplay=bool(ruta_gameplay_prueba),
        ruta_gameplay=ruta_gameplay_prueba,
        logger=logger,
        ruta_log=ruta_log,
    )

    with CANDADO_ESTADO:
        resultado_bruto = dict(ESTADO.get("resultado") or {})

    if not resultado_bruto.get("video"):
        print(f"=== ERROR: el video no se generó bien: {resultado_bruto.get('mensaje', 'sin detalle')} ===")
        sys.exit(1)

    ruta_video_absoluta = os.path.join(CARPETA_VIDEOS, resultado_bruto["video"])
    print(f"=== Video de prueba generado: {ruta_video_absoluta} ===")

    # Subir a YouTube solo si se pasa el flag --subir (para no gastar cuota
    # ni publicar de más mientras se prueba solo el video).
    if "--subir" in sys.argv:
        _ULTIMO_RESULTADO_AUTOMATICO = {
            "ruta_video": ruta_video_absoluta,
            "titulo_resumen": "Nunca pensé que algo tan pequeño pudiera cambiarlo todo (prueba)",
            "subreddits": [],
            "cantidad_historias": 1,
            "carpeta_proyecto": os.path.dirname(ruta_video_absoluta),
        }
        try:
            _subir_ultimo_resultado_a_youtube(logger)
        except Exception as e:
            logger.error(f"Falló la subida a YouTube: {e}")
            print(f"=== ERROR subiendo a YouTube: {e} ===")
    else:
        print("=== No se subió a YouTube (corré con: python hsf_engine.py --subir) ===")


# ============================================================
# ---- Miniatura estilo foto (v1.0, integrada al pipeline) ----
# Foto real de fondo (Pollinations/Nanobanana, sujeto en tercio
# izquierdo) + logo HSF + titulo (fuente Anton) + cartel rojo con
# el gancho. Es el PRIMER intento en la cadena de miniaturas; si algo
# falla, cae a generar_miniatura_clickbait / plantilla / frame, como ya
# estaba.
# ============================================================


# ============================================================
# ---- Miniatura estilo foto (v1.0, integrada al pipeline) ----
# Foto real de fondo (Pollinations/Nanobanana, sujeto en tercio
# izquierdo) + logo HSF + titulo (fuente Anton) + cartel rojo con
# el gancho. Es el PRIMER intento en la cadena de miniaturas; si algo
# falla, cae a generar_miniatura (frame simple del video).
# ============================================================
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")
POLLINATIONS_MODELO_IMAGEN = "nanobanana"


def generar_ilustracion_pollinations(resumen_texto, ruta_salida, logger=None, imagen_referencia=None):
    """Genera SOLO la foto de fondo (sin texto, sin logo) a partir del
    resumen de la historia: una persona en el tercio izquierdo, el resto
    del cuadro oscuro/vacío para superponer texto después."""
    prompt = (
        "Foto realista, formato horizontal 16:9, estilo fotograma de "
        "pelicula de suspenso/drama, pensada para generar morbo e intriga "
        "en quien la ve (que quiera saber que paso). RECREA EL MOMENTO "
        "EXACTO DE MAYOR TENSION de esta historia real -como si fuera el "
        "segundo justo ANTES de una confrontacion o justo cuando se "
        "descubre un secreto/una traicion-, con 2 o 3 PERSONAS (los "
        "involucrados directos segun el resumen: la protagonista y la "
        "otra/s persona/s con las que tiene el conflicto): "
        + resumen_texto.strip()[:600] +
        ". Miradas cargadas de tension/acusacion/culpa entre los personajes "
        "(no mirando a camara), lenguaje corporal de secreto o confrontacion "
        "(brazos cruzados, alguien dando la espalda, alguien tapandose la "
        "cara, alguien mostrando algo en un celular o una foto sin que se "
        "lea el contenido). La escena/las personas deben ocupar la MITAD "
        "IZQUIERDA del cuadro; la mitad derecha queda oscura/fuera de "
        "foco/vacia, para superponer texto despues. Iluminacion cinematica "
        "oscura y dramatica, alto contraste, como en un thriller. NO "
        "incluir ningun texto, letras, logos, marcas de agua, ni interfaz "
        "de ningun tipo en la imagen."
    )
    cuerpo = {
        "prompt": prompt, "model": POLLINATIONS_MODELO_IMAGEN,
        "size": "1280x720", "response_format": "b64_json",
    }
    if imagen_referencia:
        cuerpo["image"] = imagen_referencia
    intentos_maximos, espera = 3, 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                "https://gen.pollinations.ai/v1/images/generations",
                headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
                json=cuerpo, timeout=90,
            )
            if resp.status_code in (429, 503) and intento < intentos_maximos:
                if logger:
                    logger.warning(f"Pollinations {resp.status_code}, reintentando en {espera}s...")
                time.sleep(espera); espera *= 2; continue
            resp.raise_for_status()
            datos_b64 = resp.json()["data"][0]["b64_json"]
            with open(ruta_salida, "wb") as f:
                f.write(base64.b64decode(datos_b64))
            if logger:
                logger.info(f"Ilustracion (estilo foto) generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                if logger:
                    logger.warning(f"Fallo generar_ilustracion_pollinations tras {intentos_maximos} intentos: {e}")
                return None
            time.sleep(espera); espera *= 2
    return None


def generar_miniatura_nanobanana_pro(titulo_miniatura, resumen_texto, ruta_salida, logger=None, historia_completa=None):
    """Genera la miniatura COMPLETA (foto + titulo + franja + logo, todo
    'quemado' directamente por el modelo de IA en una sola imagen) usando
    nanobanana-pro via Pollinations. El propio modelo decide si mostrar 1,
    2 o 3 personas segun el conflicto del titulo/franja, manteniendo
    identidad visual fija (logo, tipografia, colores) entre miniaturas.
    Si falla o no hay API key, devuelve None y la cadena de miniaturas cae
    al siguiente metodo (generar_miniatura_nueva)."""
    if not POLLINATIONS_API_KEY:
        if logger:
            logger.warning("POLLINATIONS_API_KEY vacia: no se genera miniatura nanobanana-pro.")
        return None

    titular = titulo_miniatura.strip().upper()
    if len(titular) > 70:
        titular = titular[:69].rstrip() + "…"

    franja = _generar_pregunta_miniatura(historia_completa or resumen_texto, logger=logger)

    prompt = (
        "Miniatura de YouTube fotorrealista, una sola imagen a pantalla completa "
        "(sin paneles ni tarjetas separadas). Analiza el titular y la frase de la "
        "franja roja que se muestran abajo, interpreta de que trata el conflicto, "
        "y genera una escena fotorrealista que represente ese conflicto de forma "
        "dramatica: si el texto sugiere una confrontacion directa entre dos "
        "personas (traicion, pelea, acusacion), muestra 2 personas cara a cara; "
        "si el texto sugiere un conflicto con un tercero involucrado, muestra 3 "
        "personas con roles claros; si el texto sugiere un descubrimiento o "
        "momento intimo y solitario, muestra 1 sola persona en primer plano. "
        "La escena debe ser SIEMPRE en primer plano o medio plano, con el/los "
        "rostro(s) ocupando gran parte del frame (nunca personas chicas o "
        "lejanas). Debe ocurrir dentro de una casa, con iluminacion dramatica de "
        "cine tipo thriller usando siempre luz lateral proveniente de una "
        "ventana, sombras marcadas, y SIEMPRE el mismo tono de color "
        "frio/desaturado con tinte azulado en las sombras, para mantener "
        "identidad visual consistente entre miniaturas. Expresiones faciales de "
        "dolor, ira contenida o shock genuino (no actuadas). Con un degradado "
        "oscuro semitransparente que cubre la parte superior e inferior de la "
        "imagen para que el texto se lea bien encima de la foto. "
        "Arriba a la izquierda, chico: un logo circular rojo/bordo con las letras "
        "'HSF' y al lado el texto blanco 'Historia Sin Filtro', SIEMPRE del mismo "
        "tamano y posicion exacta. "
        "Debajo de eso, ocupando la parte superior, un titular en mayuscula, "
        "fuente gruesa tipo impact, SIEMPRE color blanco con la ultima palabra "
        f"clave en amarillo, texto exacto: '{titular}'. "
        "Abajo del todo, SIEMPRE una franja roja solida (mismo tono de rojo) de "
        f"ancho completo con texto blanco en mayuscula: '{franja}'. "
        "Estilo miniatura de YouTube clickbait de historias reales tipo true "
        "crime/drama familiar, sin marco ni borde de color, sin panel blanco, "
        "todo el texto quemado directamente sobre la foto, letras grandes con "
        "buen espacio entre lineas para que no se pisen entre si. Resolucion "
        "1280x720."
    )

    cuerpo = {
        "prompt": prompt, "model": "flux",
        "size": "1280x720", "response_format": "b64_json",
    }
    intentos_maximos, espera = 3, 5
    for intento in range(1, intentos_maximos + 1):
        try:
            resp = requests.post(
                "https://gen.pollinations.ai/v1/images/generations",
                headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
                json=cuerpo, timeout=120,
            )
            if resp.status_code in (429, 503) and intento < intentos_maximos:
                if logger:
                    logger.warning(f"Pollinations {resp.status_code} (nanobanana-pro), reintentando en {espera}s...")
                time.sleep(espera); espera *= 2; continue
            resp.raise_for_status()
            datos_b64 = resp.json()["data"][0]["b64_json"]
            with open(ruta_salida, "wb") as f:
                f.write(base64.b64decode(datos_b64))
            if logger:
                logger.info(f"Miniatura nanobanana-pro generada: {ruta_salida}")
            return ruta_salida
        except Exception as e:
            if intento >= intentos_maximos:
                if logger:
                    logger.warning(f"Fallo generar_miniatura_nanobanana_pro tras {intentos_maximos} intentos: {e}")
                return None
            time.sleep(espera); espera *= 2
    return None


def _mf_buscar_fuente_condensada():
    if not os.path.isdir(CARPETA_FUENTES):
        return None
    archivos = os.listdir(CARPETA_FUENTES)
    if not archivos:
        return None
    for clave in ["black", "cond", "anton", "bebas", "impact", "bold"]:
        for nombre in archivos:
            if clave in nombre.lower():
                return os.path.join(CARPETA_FUENTES, nombre)
    return os.path.join(CARPETA_FUENTES, archivos[0])


def _mf_envolver(texto, max_chars):
    palabras = texto.split()
    lineas, actual, largo = [], [], 0
    for palabra in palabras:
        if actual and largo + len(palabra) + 1 > max_chars:
            lineas.append(" ".join(actual)); actual, largo = [], 0
        actual.append(palabra); largo += len(palabra) + 1
    if actual:
        lineas.append(" ".join(actual))
    return lineas


def _mf_max_chars(fontsize, x_inicio, ancho_canvas, margen_derecho=25, factor=0.56):
    ancho_disponible = ancho_canvas - x_inicio - margen_derecho
    return max(int(ancho_disponible / (fontsize * factor)), 5)


def _mf_armar_lineas_titulo(texto_titulo, x_titulo, ancho_canvas):
    candidatos = [(72, 90), (64, 80), (56, 70), (48, 60), (41, 51), (34, 43), (28, 35), (24, 30)]
    for tamano, alto_linea in candidatos:
        max_chars = _mf_max_chars(tamano, x_titulo, ancho_canvas)
        lineas = _mf_envolver(texto_titulo, max_chars)
        if len(lineas) <= 5:
            return lineas[:5], tamano, alto_linea
    tamano, alto_linea = candidatos[-1]
    max_chars = _mf_max_chars(tamano, x_titulo, ancho_canvas)
    return _mf_envolver(texto_titulo, max_chars)[:5], tamano, alto_linea


def _mf_escapar(texto):
    return texto.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def generar_miniatura_estilo_foto(titulo, subtitulo, ruta_fondo, ruta_logo, ruta_salida, logger=None):
    """Compone la miniatura final: foto de fondo + logo HSF + titulo
    (fuente condensada/Anton, ultima linea amarilla) + cartel rojo con
    el subtitulo (tambien envuelto en 1-2 lineas, nunca se sale del
    cuadro). Todo el texto lo dibuja ffmpeg, nunca una IA."""
    ancho_mini, alto_mini = 1280, 720
    ruta_fuente = _mf_buscar_fuente_condensada()
    fontfile = f":fontfile='{ruta_fuente}'" if ruta_fuente else ""

    x_titulo = 570
    texto_titulo = titulo.strip().upper()
    lineas, tamano_titulo, alto_linea = _mf_armar_lineas_titulo(texto_titulo, x_titulo, ancho_mini)
    y_titulo_inicio = 210 - max(0, len(lineas) - 3) * (alto_linea // 2)

    dibujo_titulo = []
    for i, linea in enumerate(lineas):
        color = "yellow" if i == len(lineas) - 1 else "white"
        y_pos = y_titulo_inicio + i * alto_linea
        dibujo_titulo.append(
            f"drawtext=text='{_mf_escapar(linea)}'{fontfile}:fontcolor={color}:fontsize={tamano_titulo}:"
            f"borderw=3:bordercolor=black:x={x_titulo}:y={y_pos}"
        )

    texto_subtitulo = subtitulo.strip().upper()
    ancho_max_cartel = ancho_mini - x_titulo - 25
    tamano_subtitulo = 30
    lineas_subtitulo = _mf_envolver(
        texto_subtitulo, _mf_max_chars(tamano_subtitulo, 0, ancho_max_cartel, margen_derecho=40)
    )
    while len(lineas_subtitulo) > 2 and tamano_subtitulo > 18:
        tamano_subtitulo -= 2
        lineas_subtitulo = _mf_envolver(
            texto_subtitulo, _mf_max_chars(tamano_subtitulo, 0, ancho_max_cartel, margen_derecho=40)
        )
    lineas_subtitulo = lineas_subtitulo[:2]

    alto_linea_subtitulo = tamano_subtitulo + 14
    alto_cartel = alto_linea_subtitulo * len(lineas_subtitulo) + 20
    ancho_texto_max = max((len(l) for l in lineas_subtitulo), default=0)
    ancho_cartel = int(min(ancho_max_cartel, max(220, ancho_texto_max * (tamano_subtitulo * 0.62) + 40)))
    y_cartel = y_titulo_inicio + len(lineas) * alto_linea + 30

    dibujos_texto_subtitulo = []
    for j, linea_sub in enumerate(lineas_subtitulo):
        y_linea = y_cartel + 15 + j * alto_linea_subtitulo
        dibujos_texto_subtitulo.append(
            f"drawtext=text='{_mf_escapar(linea_sub)}'{fontfile}:fontcolor=white:fontsize={tamano_subtitulo}:"
            f"borderw=0:x={x_titulo + 20}:y={y_linea}"
        )
    dibujo_cartel = f"drawbox=x={x_titulo}:y={y_cartel}:w={ancho_cartel}:h={alto_cartel}:color=red@1.0:t=fill"
    if dibujos_texto_subtitulo:
        dibujo_cartel += "," + ",".join(dibujos_texto_subtitulo)

    x_logo, y_logo, tamano_logo = 30, 25, 90
    x_nombre, y_nombre = x_logo + tamano_logo + 15, y_logo + (tamano_logo // 2) - 20
    dibujo_nombre = (
        f"drawtext=text='HISTORIA SIN FILTRO'{fontfile}:fontcolor=white:fontsize=34:"
        f"borderw=2:bordercolor=black:x={x_nombre}:y={y_nombre}"
    )

    cadena_texto = ",".join(dibujo_titulo) + f",{dibujo_cartel},{dibujo_nombre}"
    filtro_complejo = (
        f"[0:v]scale={ancho_mini}:{alto_mini}[fondo];"
        f"[1:v]scale={tamano_logo}:{tamano_logo}[logo];"
        f"[fondo][logo]overlay={x_logo}:{y_logo}[conlogo];"
        f"[conlogo]{cadena_texto}[out]"
    )
    cmd = ["ffmpeg", "-y", "-i", ruta_fondo, "-i", ruta_logo,
           "-filter_complex", filtro_complejo, "-map", "[out]", "-frames:v", "1", ruta_salida]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(ruta_salida):
        if logger:
            logger.warning(f"No se pudo componer la miniatura estilo foto: {resultado.stderr[-800:]}")
        return None
    if logger:
        logger.info(f"Miniatura estilo foto generada: {ruta_salida}")
    return ruta_salida


def generar_miniatura_nueva(titulo_miniatura, resumen_texto, ruta_salida, logger=None, ruta_video_fondo=None):
    """Wrapper: genera la foto de fondo con Pollinations y arma la
    miniatura estilo foto. Si la foto falla, usa un frame del video como
    respaldo. Devuelve la ruta si salio bien, o None (para que la cadena
    de miniaturas en _subir_ultimo_resultado_a_youtube caiga al siguiente
    metodo)."""
    ruta_fondo = ruta_salida + ".fondo.png"
    ruta_fondo_generada = generar_ilustracion_pollinations(resumen_texto, ruta_fondo, logger=logger)

    if not ruta_fondo_generada and ruta_video_fondo and os.path.exists(ruta_video_fondo):
        ruta_fondo_generada = ruta_salida + ".fondo_frame.jpg"
        try:
            duracion = obtener_duracion_audio(ruta_video_fondo)
        except Exception:
            duracion = 10.0
        instante = min(max(2.0, duracion * 0.15), duracion - 1 if duracion > 1 else 0)
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(instante), "-i", ruta_video_fondo,
             "-vf", "scale=1280:720", "-frames:v", "1", ruta_fondo_generada],
            capture_output=True,
        )
        if not os.path.exists(ruta_fondo_generada):
            ruta_fondo_generada = None

    if not ruta_fondo_generada:
        if logger:
            logger.warning("generar_miniatura_nueva: no hay foto de fondo ni frame de respaldo.")
        return None

    subtitulo = _generar_pregunta_miniatura(resumen_texto, logger=logger)
    if not subtitulo or not subtitulo.strip():
        subtitulo = resumen_texto.strip()[:90]
    ruta_logo = os.path.join(CARPETA_BASE, "assets", "logo_hsf.png")

    return generar_miniatura_estilo_foto(
        titulo_miniatura, subtitulo, ruta_fondo_generada, ruta_logo, ruta_salida, logger=logger,
    )
