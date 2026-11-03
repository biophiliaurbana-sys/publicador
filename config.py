"""CONFIGURACIÓN · qué páginas maneja el publicador. Vive en TU planilla (privada), no en este repo público.

Pestaña "paginas" de la planilla de la cola (fila 1 = títulos; una fila por página):
  A página        → el nombre corto que escribes en la columna "página" de la cola (ej. mi-gimnasio)
  B nombre        → el nombre bonito (sale en los avisos)
  C redes         → facebook, instagram, youtube (separadas por coma)
  D llave Meta    → NOMBRE del secreto con la llave de Facebook/Instagram (ej. META_MI_GIMNASIO)
  E llave YouTube → NOMBRE del secreto con la llave del canal (ej. YT_MI_GIMNASIO)
  F por día       → (opcional) cuántos videos se esperan cada día: si faltan, llega un aviso
  G repo          → (opcional) repo privado donde esta página deja sus videos como releases (dueño/repo)
  H armar con     → (opcional) workflow de ese repo que arma los videos (ej. diario.yml): si faltan, se relanza
  I armar desde   → (opcional) desde qué hora relanzarlo (ej. 07:00)
  J datos         → (opcional) inputs del workflow, en JSON (ej. {"prueba": false})

Pestaña "otros" (opcional): páginas que publican desde su propio repo y dejan un aviso diario (issue con la
etiqueta "video"); el publicador no las sube, solo las cuenta en el resumen y las relanza si no se armaron:
  A nombre · B repo · C horas (ej. 9:00, 13:00, 20:00) · D armar con · E armar desde · F datos (JSON)

Sin planilla (o sin esas pestañas) se usan los archivos de ejemplo de paginas/*.json y repos.json, si existen."""
import json, os

AQUI = os.path.dirname(os.path.abspath(__file__))


def _json(txt, defecto):
    try:
        return json.loads(txt) if txt.strip() else defecto
    except ValueError:
        return defecto


def _armar(repo, wf, desde, datos):
    if not (repo.strip() and wf.strip()):
        return None
    return {"repo": repo.strip(), "workflow": wf.strip(), "desde": desde.strip() or "07:30", "inputs": _json(datos, {})}


def desde_planilla(leer):
    """leer(rango) → filas. Devuelve (paginas, repos, otros) o None si la planilla no tiene la pestaña "paginas"."""
    try:
        filas = leer("paginas!A2:J")
    except Exception:
        return None
    paginas, repos = {}, []
    for f in filas:
        f = (f + [""] * 10)[:10]
        clave = f[0].strip().lower()
        if not clave:
            continue
        pag = {"nombre": f[1].strip() or clave,
               "redes": [r.strip().lower() for r in f[2].replace(";", ",").split(",") if r.strip()]}
        if f[3].strip():
            pag["meta"] = f[3].strip()
        if f[4].strip():
            pag["youtube"] = f[4].strip()
        if f[5].strip().isdigit():
            pag["por_dia"] = int(f[5])
        armar = _armar(f[6], f[7], f[8], f[9])
        if armar:
            pag["armar"] = armar
        if f[6].strip() and f[6].strip() not in repos:
            repos.append(f[6].strip())
        paginas[clave] = pag
    otros = []
    try:
        for f in leer("otros!A2:F"):
            f = (f + [""] * 6)[:6]
            if f[0].strip() and f[1].strip():
                horas = [h.strip() for h in f[2].split(",") if h.strip()]
                otros.append({"nombre": f[0].strip(), "repo": f[1].strip(), "horas": horas,
                              "armar": _armar(f[1], f[3], f[4], f[5])})
    except Exception:
        pass
    return paginas, repos, otros


def desde_archivos():
    carpeta = os.path.join(AQUI, "paginas")
    paginas = {}
    if os.path.isdir(carpeta):
        for f in sorted(os.listdir(carpeta)):
            if f.endswith(".json"):
                paginas[f[:-5]] = json.load(open(os.path.join(carpeta, f), encoding="utf-8"))
    try:
        repos = json.load(open(os.path.join(AQUI, "repos.json"), encoding="utf-8")).get("repos", [])
    except OSError:
        repos = []
    return paginas, repos, []


def cargar(leer=None):
    """(paginas, repos, otros): de la planilla si tiene la pestaña "paginas"; si no, de los archivos."""
    datos = desde_planilla(leer) if leer else None
    if datos and datos[0]:
        print(f"Páginas: {len(datos[0])} (de la planilla)")
        return datos
    datos = desde_archivos()
    print(f"Páginas: {len(datos[0])} (de paginas/*.json)")
    return datos
