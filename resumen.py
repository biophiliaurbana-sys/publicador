"""RESUMEN · avisos diarios (issues con la etiqueta "resumen") para ver en la app de GitHub qué se creó y qué salió.
Lo llama publicar.py al final de cada vuelta (cada 15 min); cada aviso sale una sola vez al día:
  · desde las 9:30: si a alguna página le faltan videos de hoy (no se crearon), un aviso ⚠️ al tiro.
  · desde las 22:30: el resumen del día, página por página: qué se creó, qué salió y en qué redes, los errores
    y las llaves (Meta, YouTube) que ya no funcionan.
Cuántos videos se esperan al día: columna "por día" de la pestaña paginas (ver config.py).
Las páginas de la pestaña "otros" publican desde su propio repo: se lee su aviso del día (issue con la etiqueta
"video", con marcas dia:AAAA-MM-DD, títulos "### N · … · categoría" y etiquetas publicado-N / fallo-N / aprobado-N…)
con LLAVE_REPOS, si esa llave puede leer los issues de ese repo; si no, el resumen lo dice.
Además, VIGILANTE: si a una página le faltan videos de hoy, manda a armar de nuevo su repo (columnas "armar con" y
"armar desde"). Necesita que LLAVE_REPOS tenga permiso Actions: Read and write en esos repos."""
import datetime, re

HORA_ALERTA = datetime.time(9, 30)
HORA_RESUMEN = datetime.time(22, 30)
ETIQUETA = "resumen"
REARMAR_HASTA = datetime.time(21, 0)   # después ya no vale la pena: casi todos los videos del día pasaron su hora
REARMAR_MAX = 4                        # corridas por día y repo (la normal + 3 intentos): para no gastar minutos de más
PRUEBA = False   # publicar.py --prueba: muestra los dos avisos (a cualquier hora) sin mandarlos
NOMBRE_RED = {"facebook": "Facebook", "instagram": "Instagram", "youtube": "YouTube"}


def redes_txt(redes):
    return ", ".join(NOMBRE_RED.get(r, r) for r in redes)


def ya_enviado(gh, marca):
    if PRUEBA:
        return [], []
    """¿Ya salió hoy este aviso? Se busca su marca oculta en los últimos avisos con la etiqueta "resumen"."""
    avisos = gh("GET", f"/issues?labels={ETIQUETA}&state=all&per_page=20") or []
    return [a for a in avisos if marca in (a.get("body") or "")], avisos


def enviar(gh, titulo, cuerpo, cerrar_anteriores=False):
    if PRUEBA:
        print(f"\n===== (prueba, no se manda) {titulo} =====\n{cuerpo}\n")
        return
    try:
        gh("POST", "/labels", {"name": ETIQUETA, "color": "1D76DB"})
    except Exception:
        pass   # ya existe
    if cerrar_anteriores:   # los resúmenes de días pasados se cierran, así solo queda abierto el de hoy
        for a in gh("GET", f"/issues?labels={ETIQUETA}&state=open&per_page=20") or []:
            if a["title"].startswith("📋"):
                gh("PATCH", f"/issues/{a['number']}", {"state": "closed", "state_reason": "completed"})
    gh("POST", "/issues", {"title": titulo, "body": cuerpo, "labels": [ETIQUETA]})


def del_dia(items, dia, cuando):
    """Los videos de la cola (planilla y repos de marca) que tocan ese día, agrupados por página, en orden de hora."""
    grupos = {}
    for it in items:
        if it.vacia:
            continue
        try:
            momento = cuando(it.fecha, it.hora)
        except ValueError:
            continue
        if momento.date() == dia:
            grupos.setdefault(it.nombre.strip().lower(), []).append((momento, it))
    return {k: sorted(v, key=lambda x: x[0]) for k, v in grupos.items()}


def estado_de(it, momento, pag, ahora):
    e = it.estado
    hechas = e.get("hechas", [])
    faltan = [r for r in (pag or {}).get("redes", []) if r not in hechas]
    if it.resumen.strip().startswith("⛔"):
        return "⛔", "frenado, no se publica"
    if e.get("listo"):
        return "✅", f"salió en {redes_txt(hechas)}"
    if e.get("vencido"):
        return "❌", f"NO salió en {redes_txt(faltan)}" + (f" (sí en {redes_txt(hechas)})" if hechas else "")
    if e.get("error"):
        return "⏳", (f"salió en {redes_txt(hechas)}; " if hechas else "") + f"falta {redes_txt(faltan)}, sigo reintentando"
    if momento > ahora:
        return "🕒", f"sale a las {momento:%H:%M}"
    return "⏳", "le toca ahora, sale en la próxima vuelta"


def otro(o, llave, gh_repos, ahora):
    """(líneas del resumen, cuántos videos se crearon, problema) leyendo el aviso del día del repo de una página "otros"."""
    dia, repo = ahora.date(), o["repo"]
    horas = {k: h for k, h in enumerate(o.get("horas") or [], start=1)}
    if not llave:
        return ["No puedo mirarlo: falta la llave LLAVE_REPOS."], None, None
    try:
        avisos = gh_repos.pedir(llave, "GET", f"/repos/{repo}/issues?labels=video&state=all&per_page=5")
    except Exception:
        return ["No puedo mirarlo todavía: la llave LLAVE_REPOS no tiene permiso para leer los avisos (issues) de "
                f"{repo.split('/')[-1]}. Hay que darle ese permiso (ver AGENTS.md)."], None, None
    aviso = next((a for a in avisos if f"dia:{dia.isoformat()}" in (a.get("body") or "")), None)
    if not aviso:
        return ["❌ Hoy **no se crearon** los videos (no hay aviso del día)."], 0, True
    etiquetas = {l["name"] for l in aviso.get("labels", [])}
    videos = [(int(n), cat.strip()) for n, cat in re.findall(r"^### (\d+) · [^·]+· ([^(\n]+)", aviso["body"], re.M)]
    lineas, problema = [], False
    for k, cat in videos:
        if f"publicado-{k}" in etiquetas:
            redes = [r for r, m in (("Instagram", f"ig-{k}"), ("Facebook", f"fb-{k}")) if m in etiquetas] or ["Instagram", "Facebook"]
            txt = f"✅ salió en {', '.join(redes)}"
        elif f"precio-{k}" in etiquetas:
            txt, problema = "✋ no salió: su repo lo frenó", True
        elif f"fallo-{k}" in etiquetas:
            txt, problema = "⏳ Meta no lo aceptó todavía, sigo reintentando", True
        elif f"aprobado-{k}" in etiquetas:
            h, m = map(int, horas.get(k, "23:59").split(":")[:2])
            txt = "🕒 esperando su hora" if ahora.time() < datetime.time(h, m) else "⏳ le toca ahora, sale en la próxima vuelta"
        else:
            txt = "⛔ frenado"
        lineas.append(f"- {horas.get(k, '?')} · {cat} · {txt}")
    lineas.append(f"- [Ver el aviso]({aviso['html_url']})")
    return lineas, len(videos), problema


def alerta_manana(gh, items, paginas, otros, ahora, cuando, llave, gh_repos):
    """Desde las 9:30: si a una página le faltan videos de hoy, avisa al tiro (una vez al día)."""
    marca = f"<!-- creados:{ahora.date().isoformat()} -->"
    if ya_enviado(gh, marca)[0]:
        return
    hoy = del_dia(items, ahora.date(), cuando)
    faltan = []
    for nombre, pag in paginas.items():
        esperados = pag.get("por_dia")
        if esperados and len(hoy.get(nombre, [])) < esperados:
            faltan.append(f"- **{pag['nombre']}**: se crearon {len(hoy.get(nombre, []))} de {esperados} videos de hoy.")
    for o in otros:
        if otro(o, llave, gh_repos, ahora)[1] == 0:
            faltan.append(f"- **{o['nombre']}**: hoy no se crearon los videos (no hay aviso del día).")
    if not faltan:
        return
    cuerpo = ("Esta mañana no se crearon todos los videos de hoy:\n\n" + "\n".join(faltan)
              + "\n\nPara ver qué pasó: en el repo de esa página, pestaña **Actions**, la última corrida (la que tiene ❌)."
              "\nSi quieres que una IA lo arregle, pásale este aviso y el link de esa corrida.\n\n" + marca)
    enviar(gh, f"⚠️ Faltan videos de hoy ({ahora:%d/%m})", cuerpo)


def resumen_noche(gh, items, paginas, otros, ahora, cuando, llave, gh_repos, claves_malas):
    dia = ahora.date()
    marca = f"<!-- resumen:{dia.isoformat()} -->"
    if ya_enviado(gh, marca)[0]:
        return
    hoy = del_dia(items, dia, cuando)
    partes, creados, salieron, problemas = [], 0, 0, []
    nombres = list(paginas) + [n for n in hoy if n not in paginas]
    for nombre in nombres:
        pag = paginas.get(nombre)
        lista = hoy.get(nombre, [])
        esperados = (pag or {}).get("por_dia")
        if not lista and not esperados:
            continue   # páginas sin videos hoy (las de cola a mano, cuando no hay nada para hoy)
        titulo = (pag or {}).get("nombre", nombre)
        lineas = []
        if esperados and len(lista) < esperados:
            lineas.append(f"- ❌ Se crearon **{len(lista)} de {esperados}** videos.")
            problemas.append(titulo)
        for momento, it in lista:
            icono, txt = estado_de(it, momento, pag, ahora)
            nombre_video = getattr(it, "titulo", None) or (it.texto.strip().splitlines() or [""])[0][:60]
            # "Página · 2026-10-27 12:00 · N.º 39 …" → "N.º 39 …" (la página y la hora ya se ven)
            nombre_video = re.sub(r"^.*?\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}( · )?", "", nombre_video).strip()
            lineas.append(f"- {momento:%H:%M} · " + (f"{nombre_video} · " if nombre_video else "") + f"{icono} {txt}")
            if icono in ("❌", "⏳") and it.estado.get("error"):
                lineas.append(f"  - Error: `{it.estado['error'][:200]}`")
            if icono in ("❌", "⏳"):
                problemas.append(titulo)
            salieron += icono == "✅"
        creados += len(lista)
        partes.append(f"### {titulo}\n" + "\n".join(lineas))
    for o in otros:
        lineas, n, problema = otro(o, llave, gh_repos, ahora)
        partes.append(f"### {o['nombre']}\n" + "\n".join(l if l.startswith("-") else f"- {l}" for l in lineas))
        if n:
            creados += n
            salieron += sum("✅" in l for l in lineas)
        if problema:
            problemas.append(o["nombre"])

    if claves_malas:   # una llave vencida hace que mañana no salga nada en esa red: se avisa antes
        partes.append("### 🔑 Llaves que no funcionan\n" + "\n".join(f"- ❌ {c}" for c in claves_malas)
                      + "\n- Hay que rehacer esa llave (ver AGENTS.md → Arreglar errores); si no, esos videos no van a salir.")
        problemas += ["llaves"]
    estado = "todo bien ✅" if not problemas else f"{len(set(problemas))} con problemas ⚠️"
    cuerpo = (f"**Hoy se crearon {creados} videos y salieron {salieron}.**\n\n" + "\n\n".join(partes)
              + "\n\n---\n✅ salió · 🕒 aún no le toca · ⏳ reintentando solo · ⛔ frenado · ❌ problema\n\n"
              + ("Si algo tiene ❌: pásale este aviso a una IA (Claude, Codex, Gemini…) y pídele que lo arregle. "
                 "Lo ⏳ se reintenta solo, no tienes que hacer nada.\n\n" if problemas else "")
              + marca)
    enviar(gh, f"📋 Resumen del {ahora:%d/%m}: {estado}", cuerpo, cerrar_anteriores=True)


def rearmar_uno(llave, gh_repos, ahora, nombre, armar):
    """Manda a armar de nuevo el repo de una página (su workflow arma solo los videos que faltan)."""
    h, m = map(int, armar.get("desde", "07:30").split(":")[:2])
    if not (datetime.time(h, m) <= ahora.time() < REARMAR_HASTA):
        return
    repo, wf = armar["repo"], armar["workflow"]
    corridas = gh_repos.pedir(llave, "GET", f"/repos/{repo}/actions/workflows/{wf}/runs?per_page=10")["workflow_runs"]
    fecha = lambda t: datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(ahora.tzinfo)
    if any(c["status"] in ("queued", "in_progress", "waiting", "requested", "pending") for c in corridas):
        return print(f"vigilante: {nombre} ya se está armando")
    hoy = [c for c in corridas if fecha(c["created_at"]).date() == ahora.date()]
    if len(hoy) >= REARMAR_MAX:
        return print(f"vigilante: {nombre} sigue sin videos y ya probó {len(hoy)} veces hoy; no insisto (mira Actions de {repo})")
    if corridas and ahora - fecha(corridas[0]["updated_at"]) < datetime.timedelta(minutes=20):
        return print(f"vigilante: {nombre} terminó hace poco; espero 20 min antes de reintentar")
    if PRUEBA:
        return print(f"vigilante (prueba): mandaría a armar {repo} {wf}")
    gh_repos.pedir(llave, "POST", f"/repos/{repo}/actions/workflows/{wf}/dispatches", {"ref": "main", "inputs": armar.get("inputs", {})})
    print(f"vigilante: a {nombre} le faltan videos de hoy → lo mandé a armar de nuevo ({repo} {wf})")


def rearmar(items, paginas, otros, ahora, cuando, llave, gh_repos):
    if not llave:
        return
    hoy = del_dia(items, ahora.date(), cuando)
    for nombre, pag in paginas.items():
        if pag.get("armar") and pag.get("por_dia") and len(hoy.get(nombre, [])) < pag["por_dia"]:
            try:
                rearmar_uno(llave, gh_repos, ahora, nombre, pag["armar"])
            except Exception as ex:
                print(f"vigilante: no pude revisar {nombre} ({' '.join(str(ex).split())[:200]})")
    for o in otros:
        try:
            if o.get("armar") and otro(o, llave, gh_repos, ahora)[1] == 0:
                rearmar_uno(llave, gh_repos, ahora, o["nombre"], o["armar"])
        except Exception as ex:
            print(f"vigilante: no pude revisar {o['nombre']} ({' '.join(str(ex).split())[:200]})")


def revisar(gh, items, paginas, otros, ahora, cuando, llave, gh_repos, probar_claves):
    hora = ahora.time()
    rearmar(items, paginas, otros, ahora, cuando, llave, gh_repos)
    if PRUEBA or HORA_ALERTA <= hora < HORA_RESUMEN:
        alerta_manana(gh, items, paginas, otros, ahora, cuando, llave, gh_repos)
    if PRUEBA or hora >= HORA_RESUMEN:
        if PRUEBA or not ya_enviado(gh, f"<!-- resumen:{ahora.date().isoformat()} -->")[0]:
            resumen_noche(gh, items, paginas, otros, ahora, cuando, llave, gh_repos, probar_claves())
