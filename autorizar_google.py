"""AUTORIZAR GOOGLE · se corre UNA vez en tu PC para sacar el "refresh token" de tu cuenta de Google.
  python autorizar_google.py            → Drive + Sheets (para la cola)
  python autorizar_google.py --youtube  → YouTube (una vez por canal)
Busca solo el archivo client_secret_....json que bajaste de Google Cloud (déjalo en la misma carpeta).
También se puede: python autorizar_google.py <CLIENT_ID> <CLIENT_SECRET> [--youtube]
Se abre el navegador, eliges la cuenta (o el canal) y aceptas. Al final se muestra el refresh token:
cópialo como secreto en GitHub (GOOGLE_REFRESH, o YT_<PÁGINA> para un canal). No lo compartas con nadie."""
import glob, http.server, json, os, sys, urllib.parse, urllib.request, webbrowser

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) >= 2:
    CLIENTE, SECRETO = args[0], args[1]
else:
    carpetas = [os.getcwd(), os.path.dirname(os.path.abspath(__file__)), os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Descargas")]
    archivos = [f for c in carpetas for f in sorted(glob.glob(os.path.join(c, "client_secret*.json")), key=os.path.getmtime)]
    if not archivos:
        sys.exit("No encuentro el archivo client_secret_....json. Déjalo en la misma carpeta que este script.\n" + __doc__)
    datos_cliente = json.load(open(archivos[-1], encoding="utf-8"))
    datos_cliente = datos_cliente.get("installed") or datos_cliente.get("web") or {}
    CLIENTE, SECRETO = datos_cliente.get("client_id"), datos_cliente.get("client_secret")
    if not (CLIENTE and SECRETO):
        sys.exit(f"El archivo {archivos[-1]} no tiene client_id/client_secret.")
    print("Usando", os.path.basename(archivos[-1]))
PUERTO = 8765
REDIRECT = f"http://localhost:{PUERTO}"
ALCANCES = (["https://www.googleapis.com/auth/youtube.upload"] if "--youtube" in sys.argv else
            ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"])
codigo = {}


class Recibir(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        codigo["valor"] = (q.get("code") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>Listo. Ya puedes cerrar esta pestaña y volver a la terminal.</h2>".encode())

    def log_message(self, *a):
        pass


url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": CLIENTE, "redirect_uri": REDIRECT, "response_type": "code", "scope": " ".join(ALCANCES),
    "access_type": "offline", "prompt": "consent"})
print("Abriendo el navegador… si no se abre, copia este link:\n", url)
webbrowser.open(url)
http.server.HTTPServer(("localhost", PUERTO), Recibir).handle_request()
if not codigo.get("valor"):
    sys.exit("Google no devolvió el permiso. Vuelve a intentarlo.")
datos = urllib.parse.urlencode({"code": codigo["valor"], "client_id": CLIENTE, "client_secret": SECRETO,
                                "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
r = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=datos)))
print("\nTu refresh token (guárdalo como secreto en GitHub):\n")
print(r.get("refresh_token") or f"Google no lo entregó: {r}")
