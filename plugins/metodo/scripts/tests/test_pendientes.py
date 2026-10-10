"""Tests de pendientes-check.py, pendientes.py y su enchufe en cerrar-check.py (plugin metodo).
Solo biblioteca estándar + git, sin red. Cada test arma carpetas temporales.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CHECK = AQUI.parent / "pendientes-check.py"
LISTAR = AQUI.parent / "pendientes.py"
CERRAR = AQUI.parent / "cerrar-check.py"
PLANTILLA = AQUI.parent.parent / "templates" / "PENDIENTES.plantilla.md"

CAB = "| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |\n|---|---|---|---|---|---|---|---|\n"


def lista(filas, cambios="2026-10-10 · creada"):
    return "# PENDIENTES — prueba\n\n## A · Tema\n" + CAB + "\n".join(filas) + "\n\n## Hechos\nnada\n\n## Cambios\n- " + cambios + "\n"


def fila(i, texto="hacer algo", prio="1", estado="pendiente", quien="C"):
    return f"| {i} | {texto} | {prio} | {estado} | — | chico | {quien} | prueba |"


def correr(script, carpeta, *extra):
    return subprocess.run([sys.executable, str(script), str(carpeta), *extra], capture_output=True, text=True, timeout=30)


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.dir = Path(self._t.name)
        (self.dir / ".claude").mkdir()

    def tearDown(self):
        self._t.cleanup()

    def escribir(self, texto):
        (self.dir / ".claude" / "PENDIENTES.md").write_text(texto, encoding="utf-8")


class CheckTest(Base):
    def test_sin_lista_y_sin_git_no_rompe(self):
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("no hay en esta carpeta", r.stdout)

    def test_lista_valida(self):
        self.escribir(lista([fila("A1"), fila("A2", estado="en curso", prio="2")]))
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("2 filas", r.stdout)

    def test_la_plantilla_es_valida(self):
        (self.dir / ".claude" / "PENDIENTES.md").write_text(PLANTILLA.read_text(encoding="utf-8"), encoding="utf-8")
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_estados_validos_y_viejos_con_de(self):
        for est in ("pendiente", "en curso", "hecho", "espera dato", "espera OK", "espera dato de Ana", "espera OK de F"):
            with self.subTest(estado=est):
                self.escribir(lista([fila("A1", estado=est)]))
                self.assertEqual(correr(CHECK, self.dir).returncode, 0)

    def test_estado_invalido(self):
        self.escribir(lista([fila("A1", estado="medio hecho")]))
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("estado", r.stdout)

    def test_prioridad_invalida(self):
        self.escribir(lista([fila("A1", prio="9")]))
        self.assertEqual(correr(CHECK, self.dir).returncode, 1)

    def test_columnas_y_id(self):
        self.escribir(lista(["| A1 | solo tres | 1 |", fila("xx")]))
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("columnas", r.stdout)

    def test_id_repetido(self):
        self.escribir(lista([fila("A2"), fila("A2", "otra cosa")]))
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("repetido", r.stdout)

    def test_marca_de_conflicto(self):
        t = lista([fila("A1")]).replace("## Hechos", "<<<<<<< HEAD\n## Hechos")
        self.escribir(t)
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("conflicto", r.stdout)

    def test_aviso_si_el_cierre_es_mas_nuevo_que_cambios(self):
        self.escribir(lista([fila("A1")], cambios="2026-10-10 · creada"))
        (self.dir / ".claude" / "prompts").mkdir()
        (self.dir / ".claude" / "prompts" / "REANUDAR.md").write_text("<!-- cierre 2026-10-14-x · lo escribe /metodo:cerrar -->\n", encoding="utf-8")
        r = correr(CHECK, self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("AVISO", r.stdout)
        self.assertIn("se cerró sin tocar la lista", r.stdout)

    def test_sin_aviso_si_cambios_esta_al_dia(self):
        self.escribir(lista([fila("A1")], cambios="2026-10-14 · sin cambios"))
        (self.dir / ".claude" / "prompts").mkdir()
        (self.dir / ".claude" / "prompts" / "REANUDAR.md").write_text("<!-- cierre 2026-10-14-x · lo escribe /metodo:cerrar -->\n", encoding="utf-8")
        self.assertNotIn("AVISO", correr(CHECK, self.dir).stdout)

    def test_aviso_si_cambios_sin_fecha(self):
        self.escribir(lista([fila("A1")], cambios="sin fecha"))
        self.assertIn("AVISO", correr(CHECK, self.dir).stdout)

    def test_subcarpeta_de_un_repo_usa_la_lista_de_la_raiz(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(["git", "-C", str(self.dir), "init", "-q"], check=True, env=env)
        self.escribir(lista([fila("A1")]))
        (self.dir / "sub").mkdir()
        r = correr(CHECK, self.dir / "sub")
        self.assertEqual(r.returncode, 0)
        self.assertIn("1 filas", r.stdout)


class ListarTest(Base):
    def test_sin_lista(self):
        r = correr(LISTAR, self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Esta carpeta no tiene lista todavía", r.stdout)

    def test_prio1_primero_y_oculta_hechos(self):
        hoy = date.today().isoformat()
        self.escribir(lista([fila("A1", "tercero", prio="3"), fila("A2", "primero", prio="1"),
                             fila("A3", "listo", prio="1", estado="hecho"), fila("A4", "segundo", prio="2")],
                            cambios=f"{hoy} · cambios"))
        out = correr(LISTAR, self.dir).stdout
        self.assertIn("actualizada hoy", out)
        self.assertLess(out.index("primero"), out.index("segundo"))
        self.assertLess(out.index("segundo"), out.index("tercero"))
        self.assertNotIn("listo", out)
        self.assertIn("| ID | Pendiente | Prio | Estado | Quién |", out)

    def test_hace_n_dias_y_vieja(self):
        d = (date.today() - timedelta(days=20)).isoformat()
        self.escribir(lista([fila("A1")], cambios=f"{d} · viejo"))
        out = correr(LISTAR, self.dir).stdout
        self.assertIn("hace 20 día(s)", out)
        self.assertIn("puede estar vieja", out)

    def test_prio1_para_arrancar_son_3_y_cuenta_el_resto(self):
        self.escribir(lista([fila(f"A{i}", f"urgente {i}") for i in range(1, 6)] + [fila("A9", "no urgente", prio="2")]))
        out = correr(LISTAR, self.dir, "--prio1").stdout.strip().splitlines()
        self.assertEqual(len(out), 4)
        self.assertTrue(out[-1].startswith("y 2 más"))
        self.assertNotIn("no urgente", "\n".join(out))

    def test_prio1_sin_lista_no_imprime(self):
        self.assertEqual(correr(LISTAR, self.dir, "--prio1").stdout.strip(), "")

    def test_lista_con_problemas_igual_se_muestra(self):
        self.escribir(lista([fila("A1", "uno"), fila("A1", "dos")]))
        out = correr(LISTAR, self.dir).stdout
        self.assertIn("uno", out)
        self.assertIn("problemas de formato", out)


class CerrarCheckTest(Base):
    def test_cerrar_check_corre_pendientes_sin_lista_ni_git(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.dir / "cfg"))
        r = subprocess.run([sys.executable, str(CERRAR), "2026-10-10-prueba"], cwd=self.dir, capture_output=True, text=True, env=env, timeout=60)
        self.assertIn("PENDIENTES.md: no hay en esta carpeta", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_cerrar_check_marca_lista_rota(self):
        self.escribir(lista([fila("A1", estado="raro")]))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.dir / "cfg"))
        r = subprocess.run([sys.executable, str(CERRAR), "2026-10-10-prueba"], cwd=self.dir, capture_output=True, text=True, env=env, timeout=60)
        self.assertIn("✗ PENDIENTES.md", r.stdout)
        self.assertIn("PENDIENTES:", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
