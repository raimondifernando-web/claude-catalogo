"""Módulo compartido (no es un comando): el ÚNICO lugar del código que sabe dónde vive el REANUDAR.md.

Disparador: encadenado — lo importan cerrar-check, arrancar-check, contexto-reanudar (hook de arranque), cierre_estado,
cierre_repo, pendientes-check, estructura (R18), estructura_orden (migración) y freno-hija; no se corre solo.

Un solo lugar de escritura: `<carpeta>/.claude/prompts/REANUDAR.md`. Antes /cerrar lo dejaba en la raíz de la carpeta y los
controles lo buscaban en `.claude/prompts/`: los dos lugares convivían y R18 no revisaba el de la raíz. Los archivos viejos de la
raíz se siguen LEYENDO (lectura tolerante) hasta que el bucle de orden (estructura_orden, grupo «seguro y reversible») los mueve.
Se importa con `sys.path` o, bajo `python -I`, por ruta de archivo (importlib), igual que reanudar_confianza.py."""
import os

NOMBRE = "REANUDAR.md"
RELATIVA = ".claude/prompts/REANUDAR.md"   # lo único que se escribe


def ruta(carpeta):
    """Dónde se ESCRIBE el REANUDAR.md de `carpeta` (existe o no)."""
    return os.path.join(str(carpeta), *RELATIVA.split("/"))


def ruta_vieja(carpeta):
    """Dónde lo dejaban las versiones anteriores del kit (raíz de la carpeta). Solo se lee o se migra; nunca se escribe."""
    return os.path.join(str(carpeta), NOMBRE)


def buscar(carpeta):
    """Ruta del REANUDAR.md a LEER: el canónico si existe; si no, el viejo de la raíz; si no hay ninguno, None."""
    for p in (ruta(carpeta), ruta_vieja(carpeta)):
        if os.path.isfile(p):
            return p
    return None
