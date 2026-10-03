#!/usr/bin/env python3
"""reglas.py — mantiene al día, solo, el bloque de reglas del método en la ficha global del usuario.

Lo llama el hook SessionStart del paquete `metodo`. No pregunta nada y no muestra nada si no cambió nada.
- Las reglas viven en ~/.claude/CLAUDE.md entre <!-- reglas-del-metodo:inicio --> y <!-- reglas-del-metodo:fin -->.
- Si la plantilla del paquete instalado es distinta, reemplaza SOLO lo que está entre las marcas.
- Bloque viejo sin marcas (copiado a mano): lo migra solo si cada línea coincide con la plantilla; si no, no toca.
- Antes de cambiar guarda una copia con fecha y hora. Escritura atómica (archivo temporal + rename) y candado:
  si otra sesión está escribiendo, esta no hace nada.
Uso: python3 reglas.py sincronizar [--plantilla RUTA] [--ficha RUTA]
"""
import fcntl, os, re, sys, tempfile, time
from pathlib import Path

INI = "<!-- reglas-del-metodo:inicio -->"
FIN = "<!-- reglas-del-metodo:fin -->"
TITULO = re.compile(r"^# Las [0-9]+ reglas del método\s*$")
FIN_LEGADO = "Lo corre quien verifica, no el mismo agente que hizo la copia."


def bloque_nuevo(plantilla: Path) -> list:
    lineas = plantilla.read_text(encoding="utf-8").splitlines()
    # línea 1 = título; líneas 3-4 = nota para quien copia (no van); desde la 5 en adelante, el texto
    return [INI, lineas[0]] + lineas[4:] + [FIN]


def numero(bloque: list) -> str:
    m = re.search(r"[0-9]+", bloque[1])
    return m.group(0) if m else "?"


def sin_vacias(lineas):
    return [l for l in lineas if l.strip()]


def escribir_atomico(ficha: Path, lineas: list, fin_de_linea: str = "\n"):
    destino = ficha.resolve() if ficha.is_symlink() else ficha
    modo = destino.stat().st_mode & 0o777 if destino.exists() else 0o644
    fd, tmp = tempfile.mkstemp(prefix=".CLAUDE.md.", dir=str(destino.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(fin_de_linea.join(lineas) + fin_de_linea)
        os.chmod(tmp, modo)
        os.replace(tmp, destino)
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def respaldo(ficha: Path, guardar: int = 5):
    if ficha.exists():
        copia = ficha.with_name(ficha.name + ".antes-reglas-" + time.strftime("%Y%m%d-%H%M%S"))
        copia.write_bytes(ficha.read_bytes())
        viejas = sorted(ficha.parent.glob(ficha.name + ".antes-reglas-*"))[:-guardar]
        for v in viejas:
            try: v.unlink()
            except OSError: pass


def sincronizar(plantilla: Path, ficha: Path) -> str:
    """Devuelve '' si no hizo nada, o una línea para mostrar."""
    if not plantilla.is_file():
        return ""
    nuevo = bloque_nuevo(plantilla)
    crudo = ficha.read_bytes().decode("utf-8") if ficha.exists() else ""
    eol = "\r\n" if "\r\n" in crudo else "\n"
    actual = crudo.splitlines()
    ni, nf = actual.count(INI), actual.count(FIN)
    if ni or nf:
        if ni != 1 or nf != 1 or actual.index(INI) > actual.index(FIN):
            return "Reglas del método: las marcas de tu ficha están incompletas, no toqué nada. Avisale a Fernando ✗"
        a, b = actual.index(INI), actual.index(FIN)
        if actual[a:b + 1] == nuevo:
            return ""
        respaldo(ficha)
        escribir_atomico(ficha, actual[:a] + nuevo + actual[b + 1:], eol)
        return "Reglas del método actualizadas a {} ✓".format(numero(nuevo))
    titulos = [i for i, l in enumerate(actual) if TITULO.match(l)]
    if titulos:
        a = titulos[0]
        fin = next((i for i in range(a + 1, len(actual)) if FIN_LEGADO in actual[i]), None)
        permitidas = set(sin_vacias(nuevo))
        if fin is None or any(l not in permitidas for l in sin_vacias(actual[a + 1:fin + 1])):
            return "Reglas del método: tu ficha tiene algo distinto a la plantilla, no toqué nada. Avisale a Fernando ✗"
        respaldo(ficha)
        escribir_atomico(ficha, actual[:a] + nuevo + actual[fin + 1:], eol)
        return "Reglas del método actualizadas a {} ✓".format(numero(nuevo))
    ficha.parent.mkdir(parents=True, exist_ok=True)
    respaldo(ficha)
    escribir_atomico(ficha, actual + [""] + nuevo, eol)
    return "Reglas del método agregadas ({}) ✓".format(numero(nuevo))


def main(argv):
    if not argv or argv[0] != "sincronizar":
        print(__doc__); return 2
    args = dict(zip(argv[1::2], argv[2::2]))
    raiz = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent))
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    plantilla = Path(args.get("--plantilla", str(Path(raiz) / "templates" / "REGLAS-DEL-METODO.md")))
    ficha = Path(args.get("--ficha", str(base / "CLAUDE.md")))
    ficha.parent.mkdir(parents=True, exist_ok=True)
    with open(str(ficha.parent / ".reglas-del-metodo.lock"), "w") as candado:
        try:
            fcntl.flock(candado, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return 0  # otra sesión está escribiendo: ella se encarga
        linea = sincronizar(plantilla, ficha)
    if linea:
        print(linea)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)  # nunca trabar el arranque de una sesión
