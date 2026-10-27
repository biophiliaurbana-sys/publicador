"""FRENAR · python frenar.py <link del video en Drive> [--motivo "texto"]
Marca con ⛔ la fila de ese video en la cola para que NO se publique (si todavía no salió).
Lo usan los avisos de los repos de marca ("frenar" en un comentario) o un agente. No borra nada.
Claves igual que encolar.py (variables o .env): GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH, HOJA_COLA."""
import argparse, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from redes import google
from encolar import cargar_env


def main():
    ap = argparse.ArgumentParser(description="Frena un video de la cola.")
    ap.add_argument("video", help="link del video en Drive (columna D)")
    ap.add_argument("--motivo", default="")
    a = ap.parse_args()
    cargar_env()
    token = google.acceso(os.environ["GOOGLE_CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"], os.environ["GOOGLE_REFRESH"])
    buscado = google.id_drive(a.video)
    filas = google.leer(token, os.environ["HOJA_COLA"], "cola!A2:H")
    for n, fila in enumerate(filas, start=2):
        fila = (fila + [""] * 8)[:8]
        if fila[3].strip() and google.id_drive(fila[3]) == buscado:
            if fila[6].startswith("✅"):
                sys.exit(f"Ese video ya se publicó (fila {n}); no se puede frenar.")
            google.escribir(token, os.environ["HOJA_COLA"], f"cola!G{n}", [[f"⛔ frenado {a.motivo}".strip()]])
            print(f"Frenado: fila {n} ({fila[0]} {fila[1]} {fila[2]})")
            return
    sys.exit("No encontré ese video en la cola.")


if __name__ == "__main__":
    main()
