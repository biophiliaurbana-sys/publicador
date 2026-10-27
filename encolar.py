"""ENCOLAR · deja un video en la cola del publicador para que salga solo a su hora.
  python encolar.py --pagina entrenando-mentes --video ruta/video.mp4 --hora "2026-10-28 20:00" --texto "Texto…"
  (--texto-archivo texto.txt en vez de --texto; --portada portada.jpg es opcional)
La hora es de Chile. Lo puede usar una persona, un agente (DeepSeek Harness, Antigravity…) o el repo privado de
una marca desde GitHub Actions. Necesita una clave de GitHub con permiso de escritura en este repo, en la variable
GITHUB_TOKEN o GH_TOKEN (en el PC: `gh auth token` la entrega si tienes instalado GitHub CLI)."""
import argparse, datetime, json, os, re, sys, urllib.parse, urllib.request

REPO = os.environ.get("PUBLICADOR_REPO", "biophiliaurbana-sys/publicador")
AQUI = os.path.dirname(os.path.abspath(__file__))


def gh(metodo, url, datos=None, cuerpo=None, tipo="application/json"):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Falta la clave de GitHub (variable GITHUB_TOKEN o GH_TOKEN).")
    if datos is not None:
        cuerpo = json.dumps(datos).encode()
    r = urllib.request.Request(url, data=cuerpo, method=metodo, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": tipo})
    with urllib.request.urlopen(r, timeout=900) as resp:
        return json.load(resp)


def main():
    ap = argparse.ArgumentParser(description="Deja un video en la cola del publicador.")
    ap.add_argument("--pagina", required=True, help="nombre del archivo en paginas/ (sin .json)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--hora", required=True, help='hora de Chile, "AAAA-MM-DD HH:MM"')
    ap.add_argument("--texto", default="")
    ap.add_argument("--texto-archivo")
    ap.add_argument("--portada")
    a = ap.parse_args()

    if os.path.isdir(os.path.join(AQUI, "paginas")) and not os.path.exists(os.path.join(AQUI, "paginas", f"{a.pagina}.json")):
        sys.exit(f"No existe la página '{a.pagina}' (falta paginas/{a.pagina}.json).")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}", a.hora.strip()):
        sys.exit('La hora va así: "2026-10-28 20:00".')
    datetime.datetime.strptime(a.hora.strip(), "%Y-%m-%d %H:%M")   # avisa si la fecha no existe
    if not os.path.exists(a.video):
        sys.exit(f"No encuentro el video {a.video}")
    texto = open(a.texto_archivo, encoding="utf-8").read() if a.texto_archivo else a.texto

    etiqueta = f"{a.pagina}-{a.hora.strip().replace('-', '').replace(' ', '-').replace(':', '')}-{os.urandom(2).hex()}"
    rel = gh("POST", f"https://api.github.com/repos/{REPO}/releases",
             {"tag_name": etiqueta, "name": f"{a.pagina} | {a.hora.strip()}", "body": texto,
              "prerelease": True, "draft": False})
    subida = rel["upload_url"].split("{")[0]
    for ruta, nombre, tipo in ((a.video, "video.mp4", "video/mp4"), (a.portada, "portada.jpg", "image/jpeg")):
        if ruta:
            gh("POST", f"{subida}?name={urllib.parse.quote(nombre)}", cuerpo=open(ruta, "rb").read(), tipo=tipo)
    print(f"En la cola: {a.pagina} a las {a.hora.strip()} → {rel['html_url']}")


if __name__ == "__main__":
    main()
