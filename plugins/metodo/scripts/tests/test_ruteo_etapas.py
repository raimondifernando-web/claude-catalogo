"""Tests del ruteo por etapa (`radar.py ruteo`) y del freno a start_session sin la línea «Ruteo:».
Solo biblioteca estándar, SIN red; Codex, Claude y Antigravity son binarios falsos (Base de test_radar). Correr desde la raíz:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_ruteo_etapas.py' -v
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest

from test_radar import Base, R, YAML_REAL

ETAPAS = ["explorar", "investigar", "planear", "implementar", "probar", "revisar", "seguridad", "documentar", "cierre"]
SCRIPT = str(R.__file__) if hasattr(R, "__file__") else "radar.py"


def real():
    return R.yaml_cargar(YAML_REAL.read_text(encoding="utf-8"))


def hook(entrada, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    p = subprocess.run([sys.executable, SCRIPT, "recordar"], input=json.dumps(entrada), capture_output=True, text=True, env=env)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip() else {})


class Etapas(Base):
    def test_el_radar_real_trae_las_nueve_etapas_con_fila_valida(self):
        self.assertEqual([e["id"] for e in R.etapas_validas(real())], ETAPAS)

    def test_seguridad_y_planear_nunca_salen_de_claude(self):
        r = real()
        for eid in ("seguridad", "planear"):
            res = R.resolver_etapa(r, R.etapa_para(r, eid))
            self.assertEqual(res["ia"], "Claude")
            self.assertEqual(res["modelo"], "opus")

    def test_implementar_con_cupo_libre_va_a_otra_ia_y_con_datos_privados_queda_en_claude(self):
        r = real()
        e = R.etapa_para(r, "implementar")
        self.assertNotEqual(R.resolver_etapa(r, e)["ia"], "Claude")
        sens = R.resolver_etapa(r, e, sensible=True)
        self.assertEqual((sens["ia"], sens["modelo"]), ("Claude", "sonnet"))
        self.assertIn("se queda en Claude", sens["linea"])

    @unittest.skipIf(os.name == "nt", "scripts falsos de bash/sh")
    def test_con_todo_agotado_implementar_cae_en_claude(self):
        self.cupo_falso(2, "Codex: 98% del cupo — NO lanzar")
        self.agy_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.01}]}]}}}))
        r = real()
        res = R.resolver_etapa(r, R.etapa_para(r, "implementar"))
        self.assertEqual(res["ia"], "Claude")
        self.assertTrue(res["linea"].startswith("Ruteo: Claude/sonnet/low porque"))

    def test_rapido_no_lanza_programas(self):
        antes = subprocess.run
        subprocess.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("rapido no lanza programas"))
        try:
            r = real()
            self.assertEqual(R.resolver_etapa(r, R.etapa_para(r, "implementar"), rapido=True)["ia"], "Claude")
        finally:
            subprocess.run = antes

    def test_etapa_por_descripcion(self):
        r = real()
        self.assertEqual(R.etapa_para(r, "arreglar el script de cupo")["id"], "implementar")
        self.assertEqual(R.etapa_para(r, "revisá el PR 12")["id"], "revisar")
        self.assertIsNone(R.etapa_para(r, "zzz qqq"))

    def test_cmd_ruteo_sin_nada_imprime_la_tabla_y_la_regla_del_escalon(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(R.main(["ruteo"]), 0)
        t = out.getvalue()
        for eid in ETAPAS:
            self.assertIn(eid + " |", t)
        self.assertIn("Un escalón por cada", t)


class Freno(Base):
    def ses(self, **ti):
        return {"tool_name": "mcp__ccd_session__start_session", "session_id": "s1", "tool_input": ti}

    def test_start_session_sin_linea_ruteo_se_frena_una_sola_vez(self):
        e = self.ses(title="Implementar el script", prompt="Implementá el script de cupo y probalo.", model="claude-sonnet-5-5")
        cod, out = hook(e)
        self.assertEqual(cod, 0)
        h = out["hookSpecificOutput"]
        self.assertEqual(h["permissionDecision"], "deny")
        self.assertIn("radar.py ruteo", h["permissionDecisionReason"])
        self.assertIn("implementar", h["permissionDecisionReason"])
        cod, out = hook(e)   # segunda vez: pasa, solo avisa
        self.assertNotIn("permissionDecision", out.get("hookSpecificOutput", {}))

    def test_con_linea_ruteo_no_frena(self):
        e = self.ses(title="x", prompt="Hacé X.\nRuteo: Claude/sonnet/low porque implementar acotado", model="claude-sonnet-5-5")
        _, out = hook(e)
        self.assertNotIn("permissionDecision", out.get("hookSpecificOutput", {}))

    def test_apagado_por_variable_no_frena(self):
        _, out = hook(self.ses(title="x", prompt="Implementá algo"), {"RUTEO_FRENO_OFF": "1"})
        self.assertNotIn("permissionDecision", out.get("hookSpecificOutput", {}))

    def test_agent_sin_linea_solo_avisa_nunca_frena(self):
        _, out = hook({"tool_name": "Agent", "session_id": "s2",
                       "tool_input": {"description": "buscar archivos", "prompt": "Buscá los archivos X", "model": "haiku"}})
        h = out.get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", h)
        self.assertIn("Ruteo:", h.get("additionalContext", ""))

    def test_propuesta_ya_armada_no_frena(self):
        _, out = hook(self.ses(proposal_id="task_123"))
        self.assertNotIn("permissionDecision", out.get("hookSpecificOutput", {}))

    def test_entrada_rota_calla(self):
        p = subprocess.run([sys.executable, SCRIPT, "recordar"], input="{no json", capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
