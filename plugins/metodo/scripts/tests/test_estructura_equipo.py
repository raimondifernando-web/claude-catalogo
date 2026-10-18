#!/usr/bin/env python3
"""test_estructura_equipo.py — R19-R21 (PM de la caja, skills del PM, conectores) de estructura_equipo.py."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import estructura_equipo as eq

os.environ.setdefault("METODO_SIN_REFRESCO", "1")   # `semanal` lanza la medición del número «X de N» en segundo plano: no en las pruebas (en Windows deja la carpeta temporal tomada)

CUERPO = "\n".join(f"Regla {i} del proyecto, con contenido real." for i in range(20))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.casa = Path(self.tmp.name) / "casa"
        (self.casa / ".claude" / "agents").mkdir(parents=True)
        (self.casa / ".claude" / "skills").mkdir(parents=True)
        self.caja = Path(self.tmp.name) / "Proyectos" / "Turismo"
        self.caja.mkdir(parents=True)
        self._env = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(self.casa)
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def pm(self, nombre, cuerpo=CUERPO, extra=""):
        (self.casa / ".claude" / "agents" / f"{nombre}.md").write_text(
            f"---\nname: {nombre}\ndescription: PM\n{extra}---\n{cuerpo}\n", encoding="utf-8")

    def mcp(self, servidores, habilitados=None):
        (self.casa / ".mcp.json").write_text(json.dumps({"mcpServers": servidores}), encoding="utf-8")
        if habilitados is not None:
            (self.casa / ".claude" / "settings.local.json").write_text(
                json.dumps({"enabledMcpjsonServers": habilitados}), encoding="utf-8")

    def ids(self, texto):
        return [(i, m) for _t, i, m in eq.revisar(self.caja, texto)]


class TestR19(Base):
    def test_pm_cascara(self):
        self.pm("pm-turismo", cuerpo="Hola.\nSoy el PM.")
        r = self.ids("Usa pm-turismo.")
        self.assertEqual([i for i, _ in r], ["R19"])
        self.assertIn("pm-turismo (2 líneas)", r[0][1])

    def test_pm_con_cuerpo_no_avisa(self):
        self.pm("pm-turismo")
        self.assertEqual(self.ids("Usa pm-turismo."), [])

    def test_sin_pm_nombrado_y_hay_uno_que_cita_la_carpeta(self):
        self.pm("pm-turismo", cuerpo=CUERPO + "\nTrabaja en ~/Proyectos/Turismo/ y nada más.")
        r = self.ids("Una carpeta cualquiera sin PM.")
        self.assertEqual([i for i, _ in r], ["R19"])
        self.assertIn("pm-turismo", r[0][1])

    def test_palabra_suelta_no_es_cita_de_ruta(self):
        self.pm("pm-turismo", cuerpo=CUERPO + "\nEl Turismo regenerativo es el tema.")
        self.assertEqual(self.ids("Una carpeta sin PM."), [])

    def test_sin_pm_y_nadie_la_cita(self):
        self.pm("pm-otro", cuerpo=CUERPO + "\nTrabaja en ~/Proyectos/Otro/.")
        self.assertEqual(self.ids("Una carpeta sin PM."), [])


class TestR20(Base):
    def test_skill_precargada_que_no_existe(self):
        (self.casa / ".claude" / "skills" / "existe").mkdir()
        self.pm("pm-turismo", extra="skills:\n  - existe\n  - fantasma\n")
        r = self.ids("Usa pm-turismo.")
        self.assertEqual([i for i, _ in r], ["R20"])
        self.assertIn("pm-turismo→fantasma", r[0][1])
        self.assertNotIn("existe,", r[0][1])

    def test_comentarios_del_encabezado_no_son_skills(self):
        (self.casa / ".claude" / "skills" / "una").mkdir()
        self.pm("pm-turismo", extra="skills:\n  - una  # esta sí\n# Por invocación: otra cosa, y más\n  # otra nota\n")
        self.assertEqual(self.ids("Usa pm-turismo."), [])

    def test_skills_vacias_no_avisan(self):
        (self.casa / ".claude" / "skills" / "una").mkdir()
        self.pm("pm-turismo", extra="skills: []\n")
        self.assertEqual(self.ids("Usa pm-turismo."), [])

    def test_skill_con_prefijo_de_plugin(self):
        (self.casa / ".claude" / "skills" / "plan").mkdir()
        self.pm("pm-turismo", extra="skills: [agent-skills:plan]\n")
        self.assertEqual(self.ids("Usa pm-turismo."), [])


class TestR21(Base):
    def test_conector_citado_sin_configurar(self):
        self.mcp({"n8n-mcp": {"command": "npx"}})
        r = self.ids("Se conecta por el MCP odoo para leer pedidos.")
        self.assertEqual([i for i, _ in r], ["R21"])
        self.assertIn("odoo", r[0][1])

    def test_conector_configurado_no_avisa(self):
        self.mcp({"n8n-mcp": {"command": "npx"}})
        self.assertEqual(self.ids("Usamos el conector n8n para flujos."), [])

    def test_configurado_pero_no_habilitado(self):
        self.mcp({"hostinger": {"url": "https://x"}, "n8n-mcp": {"command": "npx"}}, habilitados=["n8n-mcp"])
        r = self.ids("El MCP hostinger administra el servidor.")
        self.assertEqual([i for i, _ in r], ["R21"])
        self.assertIn("no habilitado", r[0][1])

    def test_adjetivo_despues_de_mcp_no_es_un_conector(self):
        self.mcp({"n8n-mcp": {"command": "npx"}})
        self.assertEqual(self.ids("Usa el MCP read-only de la base."), [])

    def test_conector_de_la_nube_no_se_juzga(self):
        self.mcp({"n8n-mcp": {"command": "npx"}})
        self.assertEqual(self.ids("El conector de Gmail y el conector Meta Ads viven en la nube."), [])

    def test_historico_no_cuenta(self):
        self.mcp({"n8n-mcp": {"command": "npx"}})
        self.assertEqual(self.ids("El MCP odoo está desinstalado."), [])

    def test_herramienta_de_pm_que_no_existe(self):
        self.mcp({"memory": {"command": "npx"}})
        self.pm("pm-turismo", extra="tools: Read, mcp__memory, mcp__meta-ads-official, mcp__ff715de4-dd30-40b4-9495-f9daebedab8d__hf_fs\n")
        r = self.ids("Usa pm-turismo.")
        self.assertEqual([i for i, _ in r], ["R21"])
        self.assertIn("mcp__meta-ads-official", r[0][1])
        self.assertNotIn("mcp__memory", r[0][1])
        self.assertNotIn("ff715de4", r[0][1])

    def test_nunca_muestra_valores_de_llaves(self):
        secreto = "sk-SECRETO-NO-DEBE-SALIR-123456"
        self.mcp({"n8n-mcp": {"command": "npx", "env": {"API_KEY": secreto}}})
        (self.casa / ".claude.json").write_text(json.dumps({"mcpServers": {"x": {"env": {"T": secreto}}}, "oauthAccount": secreto}))
        salida = json.dumps(self.ids("Se conecta por el MCP odoo y el MCP zzzz."))
        self.assertNotIn(secreto, salida)

    def test_json_roto_no_rompe(self):
        (self.casa / ".mcp.json").write_text("{no es json", encoding="utf-8")
        self.assertEqual(self.ids("Texto cualquiera."), [])


if __name__ == "__main__":
    unittest.main()
