"""ENCOLAR · sube un video a tu Drive (privado) y lo anota en la planilla de la cola para que salga solo a su hora.
  python encolar.py --pagina entrenando-mentes --video ruta/video.mp4 --hora "2026-10-28 20:00" --texto "Texto…"
  (--texto-archivo texto.txt en vez de --texto; --portada portada.jpg es opcional)
La hora es de Chile. Lo puede usar una persona, un agente (DeepSeek Harness, Antigravity…) o el repo privado de
una marca desde GitHub Actions. Necesita, como variables o en un archivo .env al lado de este script:
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH, HOJA_COLA y CARPETA_VIDEOS (ID de la carpeta de Drive)."""
import argparse, datetime, os, re, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from redes import google


def cargar_env():
    ruta = os.path.join(AQUI, ".env")
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main():
    ap = argparse.ArgumentParser(description="Deja un video en la cola del publicador.")
    ap.add_argument("--pagina", required=True, help="nombre del archivo en paginas/ (sin .json)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--hora", required=True, help='hora de Chile, "AAAA-MM-DD HH:MM"')
    ap.add_argument("--texto", default="")
    ap.add_argument("--texto-archivo")
    ap.add_argument("--portada")
    ap.add_argument("--salida", help="archivo donde anotar el link del video en Drive (para avisos y frenar.py)")
    a = ap.parse_args()
    cargar_env()
    falta = [k for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH", "HOJA_COLA") if not os.environ.get(k)]
    if falta:
        sys.exit("Faltan estas claves: " + ", ".join(falta))
    if os.path.isdir(os.path.join(AQUI, "paginas")) and not os.path.exists(os.path.join(AQUI, "paginas", f"{a.pagina}.json")):
        sys.exit(f"No existe la página '{a.pagina}' (falta paginas/{a.pagina}.json).")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}", a.hora.strip()):
        sys.exit('La hora va así: "2026-10-28 20:00".')
    cuando = datetime.datetime.strptime(a.hora.strip(), "%Y-%m-%d %H:%M")
    if not os.path.exists(a.video):
        sys.exit(f"No encuentro el video {a.video}")
    texto = open(a.texto_archivo, encoding="utf-8").read() if a.texto_archivo else a.texto

    token = google.acceso(os.environ["GOOGLE_CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"], os.environ["GOOGLE_REFRESH"])
    carpeta = os.environ.get("CARPETA_VIDEOS", "")
    base = f"{a.pagina}_{cuando:%Y-%m-%d_%H%M}"
    link = google.subir(token, a.video, carpeta, f"{base}.mp4")
    portada = google.subir(token, a.portada, carpeta, f"{base}_portada.jpg", "image/jpeg") if a.portada else ""
    google.agregar(token, os.environ["HOJA_COLA"], "cola!A:F",
                   [[a.pagina, f"{cuando:%Y-%m-%d}", f"{cuando:%H:%M}", link, texto, portada]])
    if a.salida:
        open(a.salida, "w", encoding="utf-8").write(link)
    print(f"En la cola: {a.pagina} el {cuando:%d/%m} a las {cuando:%H:%M} (video en tu Drive: {link})")


if __name__ == "__main__":
    main()
