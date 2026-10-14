#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de disparadores.py con una carpeta de mentira (no toca ~/.claude). Correr: python3 -m unittest test_disparadores -v"""
import json, os, subprocess, sys, tempfile, unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(AQUI, "disparadores.py")):      # en el plugin, los tests viven en scripts/tests/
    AQUI = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import disparadores as d


def escribir(raiz, ruta, texto, ejecutable=False):
    p = os.path.join(raiz, ruta)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(texto)
    if ejecutable:
        os.chmod(p, 0o755)
    return p


def skill(raiz, nombre, desc, extra=""):
    escribir(raiz, f"skills/{nombre}/SKILL.md", f'---\nname: {nombre}\ndescription: "{desc}"\n---\n# {nombre}\n{extra}\n')


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.h = self._t.name
        escribir(self.h, "settings.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/scripts/aviso.py"}]}]}}))

    def tearDown(self):
        self._t.cleanup()

    def letras(self, **kw):
        ps = d.medir(self.h, kw.get("catalogo"), None)
        return {p.id: d.veredicto(p)[0] for p in ps}


class Skills(Base):
    def test_con_disparadores_claros_es_C(self):
        skill(self.h, "armar-logo", "Armá logos para marcas. Usala cuando la persona pida un logo, una identidad visual o 'hacé un logo'.")
        self.assertEqual(self.letras()["skill:armar-logo"], "C")

    def test_sin_disparadores_y_sin_nadie_es_D(self):
        skill(self.h, "misteriosa", "Herramienta interesante.")
        self.assertEqual(self.letras()["skill:misteriosa"], "D")

    def test_control_solo_por_intencion_es_C_con_admiracion(self):
        skill(self.h, "revision-seguridad", "Revisión de seguridad. Usala SIEMPRE que pidan revisar la seguridad antes de publicar o entregar un proyecto.")
        self.assertEqual(self.letras()["skill:revision-seguridad"], "C!")

    def test_enlazada_por_agente_es_B(self):
        skill(self.h, "tonta", "x")
        escribir(self.h, "agents/pm-x.md", "---\nname: pm-x\ndescription: \"PM de la empresa X. Invocar cuando la persona pida coordinar el trabajo de la empresa X.\"\nskills:\n  - tonta\n---\ncuerpo")
        self.assertEqual(self.letras()["skill:tonta"], "B")

    def test_enlazada_por_otra_skill_con_barra_es_B(self):
        skill(self.h, "hija", "x")
        skill(self.h, "madre", "Cierra la sesión de trabajo. Usala cuando la persona diga «terminamos» o «cerrá la sesión».", "Después corré /hija.")
        self.assertEqual(self.letras()["skill:hija"], "B")

    def test_dos_piezas_que_solo_se_nombran_entre_si_no_se_arman(self):
        # El caso que originó la regla: skill de control y agente revisor se nombran mutuamente y nadie las dispara.
        skill(self.h, "revision-seguridad", "Revisión de seguridad. Usala SIEMPRE que pidan revisar la seguridad de un proyecto antes de publicar.",
              "Llamá al agente security-reviewer con `subagent_type: security-reviewer`.")
        escribir(self.h, "agents/security-reviewer.md", '---\nname: security-reviewer\ndescription: "Revisor de seguridad. Invocar cuando haya que revisar código antes de publicar."\n---\nLo llama la skill `revision-seguridad`.')
        r = self.letras()
        self.assertEqual(r["skill:revision-seguridad"], "C!")
        self.assertEqual(r["agent:security-reviewer"], "C!")

    def test_control_enganchado_a_un_hook_si_queda_armado(self):
        skill(self.h, "revision-seguridad", "Revisión de seguridad. Usala SIEMPRE que pidan revisar la seguridad de un proyecto antes de publicar.")
        escribir(self.h, "settings.json", json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "echo /revision-seguridad"}]}]}}))
        self.assertEqual(self.letras()["skill:revision-seguridad"], "A")

    def test_control_encadenado_a_una_skill_armada_es_B(self):
        skill(self.h, "revision-seguridad", "Revisión de seguridad. Usala SIEMPRE que pidan revisar la seguridad de un proyecto antes de publicar.")
        skill(self.h, "cerrar-sesion", "Cierra la sesión de trabajo. Usala cuando la persona diga «terminamos» o «cerrá la sesión».", "Paso 3: corré /revision-seguridad si tocaste código.")
        self.assertEqual(self.letras()["skill:revision-seguridad"], "B")

    def test_solo_nombrada_en_inventario_no_cuenta(self):
        skill(self.h, "listada", "x")
        escribir(self.h, "ORQUESTA.md", "Skills: `listada`, `otra`")
        self.assertEqual(self.letras()["skill:listada"], "D")

    def test_solo_nombrada_en_claude_md_es_R(self):
        skill(self.h, "recordada", "x")
        escribir(self.h, "CLAUDE.md", "Acordate de usar `recordada` antes de publicar.")
        self.assertEqual(self.letras()["skill:recordada"], "R")

    def test_linea_disparador_declarada_es_M(self):
        skill(self.h, "declarada", "x", "**Disparador:** manual a propósito: borra cosas y la persona tiene que confirmar.")
        self.assertEqual(self.letras()["skill:declarada"], "M")

    def test_manual_por_diseno_sin_enlace_es_D(self):
        escribir(self.h, "skills/solo-a-mano/SKILL.md", "---\nname: solo-a-mano\ndescription: \"Hace cosas\"\ndisable-model-invocation: true\n---\n")
        self.assertEqual(self.letras()["skill:solo-a-mano"], "D")

    def test_uso_real_alcanza_para_C(self):
        skill(self.h, "usada", "x")
        with tempfile.TemporaryDirectory() as otra:       # el inventario vive fuera de la carpeta medida
            inv = os.path.join(otra, "inv.json")
            with open(inv, "w") as f:
                json.dump({"uso_real": {"skills": {"usada": {"usos_total": 3}}}}, f)
            ps = d.medir(self.h, None, inv)
            self.assertEqual({p.id: d.veredicto(p)[0] for p in ps}["skill:usada"], "C")


class Revision(Base):
    """Hallazgos de la revisión externa (2026-10-12) que se confirmaron."""
    def test_gate_dentro_de_otra_palabra_no_es_control(self):
        for nombre in ("delegate-work", "async-runner", "aggregate-data", "investigate-bug"):
            skill(self.h, nombre, "Hace una tarea. Usala cuando la persona pida hacer esa tarea en su proyecto.")
        r = self.letras()
        for nombre in ("delegate-work", "async-runner", "aggregate-data", "investigate-bug"):
            self.assertEqual(r[f"skill:{nombre}"], "C", nombre)

    def test_gate_como_palabra_si_es_control(self):
        skill(self.h, "quality-gate", "Compuerta de calidad. Usala cuando la persona pida pasar la compuerta antes de publicar un proyecto.")
        self.assertEqual(self.letras()["skill:quality-gate"], "C!")

    def test_descripcion_corta_con_disparador_claro_no_es_huerfana(self):
        skill(self.h, "logos", "Usala cuando pidan crear un logo.")
        self.assertEqual(self.letras()["skill:logos"], "C")

    def test_un_test_que_nombra_la_pieza_no_la_dispara(self):
        escribir(self.h, "scripts/solo.sh", "#!/bin/sh\necho\n", ejecutable=True)
        escribir(self.h, "scripts/tests/test_solo.py", "import subprocess\nsubprocess.run(['solo.sh'])")
        self.assertEqual(self.letras()["script:solo.sh"], "D")

    def test_rutas_de_windows_se_clasifican_igual(self):
        co = d.clasificar_origen
        self.assertEqual(co("C:\\u\\.claude\\hooks\\x.py", "C:\\u\\.claude", None), "A")
        self.assertEqual(co("C:\\u\\.claude\\plugins\\m\\tests\\test_a.py", "C:\\u\\.claude", None), "I")
        self.assertEqual(co("C:\\u\\repo\\docs\\guia.md", None, "C:\\u\\repo"), "I")
        self.assertEqual(co("C:\\u\\.claude\\recetas\\ui.md", "C:\\u\\.claude", None), "D")

    def test_script_sin_extension_ni_permiso_pero_con_shebang_se_mide(self):
        escribir(self.h, "scripts/sin-permiso", "#!/usr/bin/env python3\nprint(1)\n")
        self.assertEqual(self.letras()["script:sin-permiso"], "D")

    def test_disparador_de_una_letra(self):
        escribir(self.h, "scripts/x.sh", "#!/bin/sh\n# Disparador: X\n", ejecutable=True)
        self.assertEqual(self.letras()["script:x.sh"], "M")

    def test_comando_con_nombre_comun_no_se_arma_por_la_palabra_suelta(self):
        escribir(self.h, "commands/cerrar.md", "---\ndescription: Cierra\n---\ncierra")
        escribir(self.h, "CLAUDE.md", "Hay que cerrar la sesión al terminar el día.")
        self.assertEqual(self.letras()["command:cerrar"], "D")

    def test_skill_con_nombre_de_carpeta_excluida_si_cuenta_como_referencia(self):
        # ~/.claude/metodo/ es una carpeta de datos (se ignora), pero una skill llamada «metodo» es una pieza y lo que nombra queda armado
        skill(self.h, "metodo", "Método de trabajo. Usala cuando la persona diga «trabajemos con el método» o pida ordenar su forma de trabajar.",
              "Corré `scripts/control-mensual.py` una vez por mes.")
        escribir(self.h, "scripts/control-mensual.py", "print(1)", ejecutable=True)
        escribir(self.h, "metodo/datos.md", "scripts/otra-cosa.py")
        r = self.letras()
        self.assertEqual(r["script:control-mensual.py"], "B")

    def test_script_nombrado_sin_extension_queda_armado(self):
        skill(self.h, "mensual", "Control mensual. Usala cuando la persona pida correr el control del mes de sus herramientas.", "Corré control-de-datos todos los meses.")
        escribir(self.h, "scripts/control-de-datos.py", "print(1)", ejecutable=True)
        self.assertEqual(self.letras()["script:control-de-datos.py"], "B")

    def test_yaml_sin_pyyaml_junta_las_lineas_de_un_valor_multilinea(self):
        f = d.frontmatter_simple("name: x\ndescription: >\n  Usala cuando pidan\n  armar un logo.\nmodel: sonnet")
        self.assertEqual(f["description"], "Usala cuando pidan armar un logo.")
        self.assertEqual(f["model"], "sonnet")


class Scripts(Base):
    def test_script_en_settings_es_A(self):
        escribir(self.h, "scripts/aviso.py", "print('hola')", ejecutable=True)
        self.assertEqual(self.letras()["script:aviso.py"], "A")

    def test_script_huerfano_es_D(self):
        escribir(self.h, "scripts/solo.sh", "#!/bin/sh\necho hola\n", ejecutable=True)
        self.assertEqual(self.letras()["script:solo.sh"], "D")

    def test_script_con_disparador_declarado_es_M(self):
        escribir(self.h, "scripts/manual.sh", "#!/bin/sh\n# Disparador: manual — lo corre la persona una vez por trimestre; lo recuerda la tarea trimestral.\n", ejecutable=True)
        self.assertEqual(self.letras()["script:manual.sh"], "M")

    def test_script_llamado_por_otro_script_es_B(self):
        escribir(self.h, "scripts/principal.py", "import subprocess\nsubprocess.run(['sub-tarea'])", ejecutable=True)
        escribir(self.h, "scripts/sub-tarea", "#!/bin/sh\necho", ejecutable=True)
        escribir(self.h, "settings.json", json.dumps({"hooks": {"x": "principal.py"}}))
        r = self.letras()
        self.assertEqual(r["script:principal.py"], "A")
        self.assertEqual(r["script:sub-tarea"], "B")

    def test_los_tests_no_se_miden(self):
        escribir(self.h, "scripts/test_algo.py", "pass", ejecutable=True)
        self.assertNotIn("script:test_algo.py", self.letras())

    def test_hook_git_cuenta_como_automatico(self):
        os.makedirs(os.path.join(self.h, "scripts"))
        escribir(self.h, "scripts/custodia", "#!/bin/sh\n", ejecutable=True)
        escribir(self.h, "hooks/pre-push", "#!/bin/sh\nexec custodia\n", ejecutable=True)
        r = self.letras()
        self.assertEqual(r["script:custodia"], "A")


class Catalogo(unittest.TestCase):
    def test_comando_nuevo_sin_nadie_es_D_y_el_revisor_sin_skill_tambien_es_aviso(self):
        with tempfile.TemporaryDirectory() as c:
            escribir(c, "plugins/p/commands/hazlo.md", "---\ndescription: Hace algo\n---\nhaz")
            escribir(c, "plugins/p/skills/a/SKILL.md", '---\nname: a\ndescription: "Usala cuando pidan armar una propuesta comercial para un cliente."\n---\n')
            escribir(c, "plugins/p/hooks/hooks.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [{"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/avisa.sh"}]}]}}))
            escribir(c, "plugins/p/scripts/avisa.sh", "#!/bin/sh\n", ejecutable=True)
            escribir(c, "plugins/p/scripts/olvidado.sh", "#!/bin/sh\n", ejecutable=True)
            ps = d.medir(None, c, None)
            r = {p.id: d.veredicto(p)[0] for p in ps}
            self.assertEqual(r["command:hazlo"], "D")
            self.assertEqual(r["skill:a"], "C")
            self.assertEqual(r["script:avisa.sh"], "A")
            self.assertEqual(r["script:olvidado.sh"], "D")


class LineaDeComandos(Base):
    def correr(self, *args):
        return subprocess.run([sys.executable, os.path.join(AQUI, "disparadores.py"), *args], capture_output=True, encoding="utf-8", errors="replace")

    def test_check_sale_1_con_rojo_y_0_con_excepcion(self):
        skill(self.h, "misteriosa", "Herramienta.")
        r = self.correr("--home", self.h, "--check")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("misteriosa", r.stdout)
        exc = os.path.join(self.h, "exc.txt")
        with open(exc, "w") as f:
            f.write("# comentario\npersonal/skill:misteriosa | de terceros, se dispara por palabra clave\n")
        r = self.correr("--home", self.h, "--check", "--excepciones", exc)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("OK", r.stdout)

    def test_recientes_solo_cuenta_lo_nuevo(self):
        skill(self.h, "vieja", "Herramienta.")
        skill(self.h, "nueva", "Otra herramienta.")
        viejo = os.path.join(self.h, "skills", "vieja", "SKILL.md")
        os.utime(viejo, (1_000_000_000, 1_000_000_000))
        r = self.correr("--home", self.h, "--check", "--recientes", "36")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("skill:nueva", r.stdout)
        self.assertNotIn("- personal/skill:vieja", r.stdout)
        self.assertIn("(aviso) 1 pieza(s) más antiguas", r.stdout)
        os.utime(os.path.join(self.h, "skills", "nueva", "SKILL.md"), (1_000_000_000, 1_000_000_000))
        self.assertEqual(self.correr("--home", self.h, "--check", "--recientes", "36").returncode, 0)

    def test_sin_piezas_rojas_sale_0(self):
        skill(self.h, "buena", "Usala cuando la persona pida resumir una reunión larga en puntos.")
        self.assertEqual(self.correr("--home", self.h, "--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()
