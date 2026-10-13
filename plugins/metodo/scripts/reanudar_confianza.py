"""Módulo compartido (no es un comando): ¿este REANUDAR.md lo dejó /cerrar en ESTA máquina?
Lo usan contexto-reanudar.py (hook de arranque) y arrancar-check.py (/arrancar); lo escribe cerrar-check.py --anotar.
Se importa por ruta de archivo (importlib), porque los hooks pueden correr con `python -I`, que no agrega esta carpeta al path."""
import hashlib
import os


def confiable(crudo):
    """`cerrar-check --anotar` anota el sha256 del archivo en <config>/reanudar-confiables.txt; un archivo de un repo
    clonado nunca está ahí aunque copie la cabecera. Recibe los mismos bytes que se van a mostrar/usar (no vuelve a abrir el archivo)."""
    try:
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        h = hashlib.sha256(crudo).hexdigest()
        with open(os.path.join(base, "reanudar-confiables.txt"), encoding="utf-8", errors="replace") as f:
            return any(l.split()[:1] == [h] for l in f)
    except Exception:
        return False

