#!/usr/bin/env python3
"""Regla 26: en cada mensaje recuerda la FORMA de la respuesta (primera línea = la respuesta, pasos cortos, un solo próximo paso).
La regla completa vive una sola vez en el bloque de reglas de la ficha; esto es solo el recordatorio de una línea.
No lee ni escribe nada. Disparador: automático (hook UserPromptSubmit del plugin metodo, hooks/hooks.json).
Se apaga con la variable FORMA_RESPUESTA=0."""
import os
import sys

if os.environ.get("FORMA_RESPUESTA") == "0":
    sys.exit(0)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # consola de Windows en cp1252
print("Forma (regla 26): primera línea = la respuesta o la acción; pasos cortos «paso N de M»; cerrá con UN solo próximo paso.")
