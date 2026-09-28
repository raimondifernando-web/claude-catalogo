"""Retención cero (ZDR) de OpenRouter. Agregado local, no viene del origen (ver ../ORIGEN.txt).

Si el modelo pedido tiene un endpoint ZDR, el pedido lleva `provider: {"zdr": true}` y OpenRouter
solo lo manda a endpoints que no guardan nada. Si no lo tiene, el pedido sale igual que antes y se
avisa en una línea (con `zdr: true` un modelo sin endpoint ZDR fallaría con 404 en vez de caer a otro).

Fuentes: https://openrouter.ai/docs/guides/features/zdr (parámetro `zdr` en `provider`) y la lista
pública https://openrouter.ai/api/v1/endpoints/zdr (sin clave). Solo biblioteca estándar.
"""

import json
import os
import time
import urllib.request
from pathlib import Path

ZDR_URL = "https://openrouter.ai/api/v1/endpoints/zdr"
CACHE_TTL = 600  # segundos: la lista cambia poco; 10 minutos alcanza
CACHE_FILE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "openrouter-zdr" / "endpoints.json"

_ids = None
_loaded = False  # una sola consulta por ejecución


def _read_cache(max_age):
    try:
        if max_age is not None and time.time() - CACHE_FILE.stat().st_mtime > max_age:
            return None
        ids = set(json.loads(CACHE_FILE.read_text(encoding="utf-8")))
        return ids or None
    except Exception:
        return None


def _write_cache(ids):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_name(f"{CACHE_FILE.name}.{os.getpid()}.tmp")  # escritura atómica: sesiones en paralelo
        tmp.write_text(json.dumps(sorted(ids)), encoding="utf-8")
        os.replace(tmp, CACHE_FILE)
    except Exception:
        pass


def _fetch(timeout):
    req = urllib.request.Request(ZDR_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp).get("data") or []
    ids = {e["model_id"] for e in data if isinstance(e, dict) and e.get("model_id")}
    if not ids:
        raise ValueError("lista ZDR vacía o con otro formato")
    return ids


def zdr_model_ids(timeout=8):
    """Modelos con al menos un endpoint ZDR, o None si no se pudo saber."""
    global _ids, _loaded
    if not _loaded:
        _ids = _read_cache(CACHE_TTL)
        if _ids is None:
            try:
                _ids = _fetch(timeout)
                _write_cache(_ids)
            except Exception:
                _ids = _read_cache(None)  # sin red: sirve la última lista guardada, aunque sea vieja
        _loaded = True
    return _ids


def provider_for(model):
    """{"zdr": True} si el modelo tiene endpoint ZDR; si no, avisa en una línea y devuelve None."""
    ids = zdr_model_ids()
    if ids is None:
        print(f"Aviso: no se pudo comprobar si este modelo ({model}) tiene modo sin retención; "
              "el material puede quedar guardado por el proveedor según su política.")
        return None
    if model in ids:
        return {"zdr": True}
    print(f"Aviso: este modelo ({model}) no tiene modo sin retención; "
          "el material queda guardado por el proveedor según su política.")
    return None


class _Completions:
    def __init__(self, completions, provider):
        self._completions, self._provider = completions, provider

    def create(self, *args, **kwargs):
        extra = dict(kwargs.pop("extra_body", None) or {})
        extra["provider"] = {**(extra.get("provider") or {}), **self._provider}
        return self._completions.create(*args, extra_body=extra, **kwargs)

    def __getattr__(self, name):
        return getattr(self._completions, name)


class _Chat:
    def __init__(self, chat, provider):
        self._chat, self.completions = chat, _Completions(chat.completions, provider)

    def __getattr__(self, name):
        return getattr(self._chat, name)


class _Client:
    def __init__(self, client, provider):
        self._client, self.chat = client, _Chat(client.chat, provider)

    def __getattr__(self, name):
        return getattr(self._client, name)


def with_zdr(client, model):
    """Envuelve un cliente OpenAI apuntado a OpenRouter para que cada chat.completions.create lleve ZDR."""
    provider = provider_for(model)
    return _Client(client, provider) if provider else client
