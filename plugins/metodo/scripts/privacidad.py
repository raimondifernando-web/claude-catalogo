#!/usr/bin/env python3
"""Privacidad al delegar: lista de carpetas sensibles y aviso por planillas con datos de personas.

Disparador: encadenado — lo importa delegar.py antes de mandar nada a otra IA (y su par local en agy-delegar,
claude-api y revision-api). No se corre solo ni a mano.

La lista de sensibles es un archivo LOCAL de cada computadora (nunca viaja ni va a git):
    <config de Claude>/metodo/sensibles.txt      una línea por carpeta: «ruta | motivo»  (# = comentario; ~ = tu carpeta)
Sin archivo, o vacío, no hay nada sensible por contrato. Solo biblioteca estándar.
"""
import os
import re
from pathlib import Path

# Planillas y listados: lo que más seguido trae datos de personas. Es un AVISO, nunca un freno.
EXT_PLANILLA = (".csv", ".tsv", ".xls", ".xlsx", ".xlsm", ".ods", ".numbers")
# Nombres que delatan un listado de personas (clientes, empleados, contactos, sueldos…).
NOMBRE_PERSONAS = re.compile(
    r"(cliente|contacto|empleado|nomina|nómina|sueldo|liquidaci|legajo|paciente|usuario|socio|suscriptor|lead|"
    r"padron|padrón|alumno|candidato|cv_|curriculum|currículum|dni|extracto)", re.I)
COLUMNAS_PERSONAS = re.compile(r"(e-?mail|correo|tel[eé]fono|celular|whatsapp|dni|cuit|cuil|domicilio|direcci[oó]n|apellido)", re.I)


def config_claude():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def archivo_sensibles():
    """METODO_SENSIBLES (ruta de otro archivo) existe para las pruebas; normalmente es el de la config de Claude."""
    return Path(os.environ.get("METODO_SENSIBLES") or (config_claude() / "metodo" / "sensibles.txt"))


def leer_sensibles(archivo=None):
    """[(Path resuelta, motivo)]. Líneas «ruta | motivo»; ignora vacías y #. Un archivo ilegible = sin lista."""
    ruta = Path(archivo) if archivo else archivo_sensibles()
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    salida = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        parte, _, motivo = linea.partition("|")
        parte = parte.strip()
        if not parte:
            continue
        try:
            p = Path(os.path.expanduser(parte)).resolve()
        except (OSError, RuntimeError):
            continue
        salida.append((p, motivo.strip() or "carpeta marcada como sensible"))
    return salida


def _norm(p):
    return str(p).replace("\\", "/").rstrip("/").lower() + "/"


def carpeta_sensible(ruta, lista=None):
    """Motivo (str) si `ruta` es una carpeta sensible, está adentro de una, o CONTIENE una (delegar el repo entero
    mandaría también su contenido). None si no. macOS no distingue mayúsculas."""
    lista = leer_sensibles() if lista is None else lista
    try:
        r = _norm(Path(ruta).resolve())
    except (OSError, RuntimeError):
        r = _norm(ruta)
    for sens, motivo in lista:
        s = _norm(sens)
        if r.startswith(s):
            return "carpeta sensible por contrato (%s): %s" % (sens, motivo)
        if s.startswith(r):
            return "el repo contiene una carpeta sensible por contrato (%s): %s" % (sens, motivo)
    return None


def _cabecera_con_personas(ruta):
    try:
        with open(ruta, "rb") as f:
            primera = f.readline(4096).decode("utf-8", "replace")
    except OSError:
        return False
    return bool(COLUMNAS_PERSONAS.search(primera))


def planillas_con_personas(archivos, raiz=None, tope=5):
    """Hasta `tope` rutas relativas que parecen planillas con datos de personas: extensión de planilla Y (nombre que lo
    delata, o —si es texto— columnas como mail/teléfono/DNI). Solo avisa; no lee más que la primera línea."""
    hallados = []
    for rel in archivos:
        base = os.path.basename(str(rel)).lower()
        if not base.endswith(EXT_PLANILLA):
            continue
        sospechosa = bool(NOMBRE_PERSONAS.search(base))
        if not sospechosa and base.endswith((".csv", ".tsv")) and raiz is not None:
            sospechosa = _cabecera_con_personas(os.path.join(str(raiz), str(rel)))
        if sospechosa:
            hallados.append(str(rel))
            if len(hallados) >= tope:
                break
    return hallados


def aviso_planillas(hallados):
    if not hallados:
        return None
    return ("Aviso: el material trae planillas que parecen tener datos de personas o clientes (%s). Los datos de personas "
            "solo van a una IA con «no entrenar» registrado; si no estás seguro, sacalas o hacelo en esta sesión." % ", ".join(hallados))
