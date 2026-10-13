#!/usr/bin/env python3
"""test_estructura.py — pruebas de sincronía, control, completar y aviso para estructura.py."""
from contextlib import redirect_stdout
from datetime import date
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

# Asegurar codificación utf-8
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Importar estructura.py
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import estructura


def extraer_texto_visible(html: str) -> str:
    """Extrae todo el texto visible de un documento HTML, normalizando espacios."""
    s = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.DOTALL)
    s = re.sub(r'<[^>]+>', ' ', s)
    return ' '.join(s.split())


def extraer_clases_cajas(html: str) -> list:
    """Extrae la secuencia de clases CSS de las cajas."""
    return re.findall(r'class="([^"]*box[^"]*)"', html)


class TestSincronia(unittest.TestCase):
    """Pruebas de sincronía entre ESTRUCTURA.md y el dibujo HTML."""

    def setUp(self):
        self.raiz_repo = SCRIPTS_DIR.parent.parent.parent
        self.md_real = self.raiz_repo / "plugins" / "metodo" / "estructura" / "ESTRUCTURA.md"
        self.aprobado_html = Path(__file__).resolve().parent / "fixtures" / "estructura-aprobada.html"

    def test_dibujo_coincide_con_aprobado(self):
        """El dibujo generado a partir de ESTRUCTURA.md coincide con el dibujo aprobado."""
        self.assertTrue(self.md_real.is_file(), f"No existe {self.md_real}")
        self.assertTrue(self.aprobado_html.is_file(), f"No existe {self.aprobado_html}")

        md_texto = self.md_real.read_text(encoding="utf-8", errors="replace")
        generado = estructura.generar_dibujo_html(md_texto)
        aprobado = self.aprobado_html.read_text(encoding="utf-8", errors="replace")

        # 1. El texto visible sin etiquetas y con espacios normalizados debe ser idéntico
        texto_generado = extraer_texto_visible(generado)
        texto_aprobado = extraer_texto_visible(aprobado)
        self.assertEqual(texto_generado, texto_aprobado)

        # 2. La secuencia de clases CSS de las cajas debe ser idéntica
        clases_generado = extraer_clases_cajas(generado)
        clases_aprobado = extraer_clases_cajas(aprobado)
        self.assertEqual(clases_generado, clases_aprobado)

    def test_edicion_estructura_cambia_dibujo(self):
        """Si se edita ESTRUCTURA.md (se agrega una fila al molde), el dibujo cambia y la prueba lo detecta."""
        md_texto = self.md_real.read_text(encoding="utf-8", errors="replace")

        # Agregar una fila nueva al molde
        nueva_fila = "| `extra-dir/` | carpeta de prueba extra | E A P | sí | no | no | — |"
        patron_molde = r"(\| `\.env` \| las claves \|[^\n]*\n)"
        md_modificado = re.sub(patron_molde, r"\1" + nueva_fila + "\n", md_texto)
        self.assertIn("extra-dir/", md_modificado)

        generado_modificado = estructura.generar_dibujo_html(md_modificado)
        aprobado = self.aprobado_html.read_text(encoding="utf-8", errors="replace")

        texto_modificado = extraer_texto_visible(generado_modificado)
        texto_aprobado = extraer_texto_visible(aprobado)

        # Deben diferir y el modificado debe contener el texto de la nueva fila
        self.assertNotEqual(texto_modificado, texto_aprobado)
        self.assertIn("extra-dir/", texto_modificado)
        self.assertIn("carpeta de prueba extra", texto_modificado)


class TestControl(unittest.TestCase):
    """Pruebas del control (subcomando revisar y reglas R1-R11)."""

    def test_caja_completa_sin_fallas(self):
        """Una caja que cumple todas las reglas muestra 'Estructura al día ✓' y sale 0."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "mi_proyecto"
            caja.mkdir()

            # Configurar git y remoto
            subprocess.run(["git", "init"], cwd=caja, capture_output=True, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=caja, capture_output=True, check=True)

            # Archivos obligatorios
            (caja / "CLAUDE.md").write_text("# Proyecto\n\nReglas válidas.\n", encoding="utf-8")
            (caja / ".claude").mkdir()
            (caja / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
            (caja / ".gitignore").write_text(".env\n.claude/settings.local.json\nCLAUDE.local.md\n", encoding="utf-8")

            # Ejecutar revisión
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = estructura.comando_revisar(carpeta_arg=str(caja), nivel_arg="proyecto")

            salida = buf.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Estructura al día ✓", salida)
            self.assertNotIn("✗", salida)

    def test_fallas_plantadas(self):
        """En un entorno con fallas plantadas, sale exactamente una línea ✗ por cada falla con su Rnn."""
        with tempfile.TemporaryDirectory() as td:
            raiz = Path(td) / "Proyectos"
            raiz.mkdir()

            # 1. Falla plantada R11: raíz ~/Proyectos es un repositorio git
            (raiz / ".git").mkdir()

            def _armar_base_caja(p):
                p.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "init"], cwd=p, capture_output=True, check=True)
                subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=p, capture_output=True, check=True)
                (p / "CLAUDE.md").write_text("# Test\n", encoding="utf-8")
                (p / ".claude").mkdir(exist_ok=True)
                (p / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
                (p / ".gitignore").write_text(".env\n", encoding="utf-8")

            # 2. Falla plantada R2: sin CLAUDE.md
            caja_r2 = raiz / "caja_sin_claude"
            _armar_base_caja(caja_r2)
            (caja_r2 / "CLAUDE.md").unlink()

            # 3. Falla plantada R4: settings.json con JSON roto
            caja_r4 = raiz / "caja_json_roto"
            _armar_base_caja(caja_r4)
            (caja_r4 / ".claude" / "settings.json").write_text("{este json no cierra", encoding="utf-8")

            # 4. Falla plantada R6: .env versionado
            caja_r6 = raiz / "caja_env_versionado"
            _armar_base_caja(caja_r6)
            (caja_r6 / ".env").write_text("CLAVE=secreta\n", encoding="utf-8")
            subprocess.run(["git", "add", ".env"], cwd=caja_r6, capture_output=True, check=True)

            # 5. Falla plantada R9: skill sin description
            caja_r9 = raiz / "caja_skill_sin_desc"
            _armar_base_caja(caja_r9)
            sk_dir = caja_r9 / ".claude" / "skills" / "mi_skill"
            sk_dir.mkdir(parents=True)
            (sk_dir / "SKILL.md").write_text("---\nname: mi_skill\n---\nSin descripcion\n", encoding="utf-8")

            # 6. Falla plantada R8: área que versiona la carpeta de un proyecto
            caja_r8 = raiz / "area_versiona_proyecto"
            _armar_base_caja(caja_r8)
            # Agregar patrón de ignorar para que no falle por falta de patrón
            (caja_r8 / ".gitignore").write_text(".env\n/*/\n!/.claude/\n!/plugins/\n!/docs/\n", encoding="utf-8")
            # Proyecto crm adentro es válido en sí mismo
            _armar_base_caja(caja_r8 / "crm")
            # Pero el área erróneamente versiona un archivo dentro de crm
            (caja_r8 / "crm" / "archivo.txt").write_text("hola", encoding="utf-8")
            subprocess.run(["git", "add", "-f", "crm/archivo.txt"], cwd=caja_r8, capture_output=True, check=True)

            # Ejecutar revisión con --todas
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = estructura.comando_revisar(todas=True, raiz_arg=str(raiz))

            salida = buf.getvalue()
            lineas_falla = [l for l in salida.splitlines() if l.startswith("✗")]

            # Debe haber salido código 1
            self.assertEqual(code, 1)

            # Debe haber exactamente una falla por cada regla plantada
            self.assertEqual(len(lineas_falla), 6, f"Se esperaban 6 fallas, salieron {len(lineas_falla)}: {lineas_falla}")

            fallas_r = [re.search(r"✗\s+(R\d+)", l).group(1) for l in lineas_falla]
            self.assertIn("R11", fallas_r)
            self.assertIn("R2", fallas_r)
            self.assertIn("R4", fallas_r)
            self.assertIn("R6", fallas_r)
            self.assertIn("R9", fallas_r)
            self.assertIn("R8", fallas_r)

            # Al final debe decir "Falta: 6 cosas ✗"
            self.assertIn("Falta: 6 cosas ✗", salida)

            # Verificar también cada caja individualmente: sale exactamente una línea ✗ por cada falla con su Rnn
            for caja_falla, r_esperada, niv in [
                (caja_r2, "R2", "proyecto"),
                (caja_r4, "R4", "proyecto"),
                (caja_r6, "R6", "proyecto"),
                (caja_r9, "R9", "proyecto"),
                (caja_r8, "R8", "area"),
            ]:
                buf_ind = io.StringIO()
                with redirect_stdout(buf_ind):
                    c_code = estructura.comando_revisar(carpeta_arg=str(caja_falla), nivel_arg=niv)
                out_ind = buf_ind.getvalue()
                self.assertEqual(c_code, 1)
                errs_ind = [l for l in out_ind.splitlines() if l.startswith("✗")]
                self.assertEqual(len(errs_ind), 1, f"Fallo en {caja_falla.name}: {errs_ind}")
                self.assertIn(f"✗ {r_esperada}", errs_ind[0])
                self.assertIn("Falta: 1 cosa ✗", out_ind)


class TestCompletar(unittest.TestCase):
    """Pruebas del subcomando completar."""

    def test_completar_carpeta_vacia(self):
        """Sobre una carpeta vacía -> después revisar no da ✗ salvo R1 (git y remoto)."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "nueva_caja"
            caja.mkdir()

            # Ejecutar completar
            buf_c = io.StringIO()
            with redirect_stdout(buf_c):
                code_c = estructura.comando_completar(str(caja), nivel="proyecto")
            self.assertEqual(code_c, 0)

            # Verificar que se crearon los archivos obligatorios
            self.assertTrue((caja / "CLAUDE.md").is_file())
            self.assertTrue((caja / ".claude" / "settings.json").is_file())
            self.assertTrue((caja / ".gitignore").is_file())

            # settings.json debe ser {}
            st = json.loads((caja / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(st, {})

            # Ahora ejecutar revisar
            buf_r = io.StringIO()
            with redirect_stdout(buf_r):
                code_r = estructura.comando_revisar(carpeta_arg=str(caja), nivel_arg="proyecto")

            salida_r = buf_r.getvalue()
            lineas_falla = [l for l in salida_r.splitlines() if l.startswith("✗")]

            # Solo debe fallar R1 (git no inicializado)
            self.assertEqual(len(lineas_falla), 1)
            self.assertIn("✗ R1", lineas_falla[0])

    def test_completar_no_pisa_archivo_existente(self):
        """Sobre una carpeta con un CLAUDE.md propio -> el archivo queda byte a byte igual."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "caja_existente"
            caja.mkdir()

            contenido_original = "# Mi CLAUDE propio\n\nTexto único e irrepetible.\n"
            claude_file = caja / "CLAUDE.md"
            claude_file.write_text(contenido_original, encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                estructura.comando_completar(str(caja), nivel="proyecto")

            salida = buf.getvalue()
            self.assertIn("= Ya existe: CLAUDE.md", salida)

            # Verificar byte a byte
            contenido_despues = claude_file.read_text(encoding="utf-8")
            self.assertEqual(contenido_original, contenido_despues)


class TestAviso(unittest.TestCase):
    """Pruebas del modo --aviso."""

    def test_aviso_todo_bien(self):
        """Con todo bien, no imprime nada y sale 0."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "caja_ok"
            caja.mkdir()

            subprocess.run(["git", "init"], cwd=caja, capture_output=True, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=caja, capture_output=True, check=True)
            (caja / "CLAUDE.md").write_text("# Ok\n", encoding="utf-8")
            (caja / ".claude").mkdir()
            (caja / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
            (caja / ".gitignore").write_text(".env\n", encoding="utf-8")

            # Evitar que dispare --todas por semana ISO
            os.environ["CLAUDE_PLUGIN_DATA"] = td
            iso_year, iso_week, _ = date.today().isocalendar()
            (Path(td) / "semana-revisar.txt").write_text(f"{iso_year}-W{iso_week:02d}", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = estructura.comando_revisar(carpeta_arg=str(caja), nivel_arg="proyecto", aviso=True)

            self.assertEqual(code, 0)
            self.assertEqual(buf.getvalue().strip(), "")

    def test_aviso_con_fallas(self):
        """Con fallas sale 0 igual y reporta lo que falta."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "caja_rota"
            caja.mkdir()

            # Evitar disparo semanal
            os.environ["CLAUDE_PLUGIN_DATA"] = td
            iso_year, iso_week, _ = date.today().isocalendar()
            (Path(td) / "semana-revisar.txt").write_text(f"{iso_year}-W{iso_week:02d}", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = estructura.comando_revisar(carpeta_arg=str(caja), nivel_arg="proyecto", aviso=True)

            salida = buf.getvalue()
            # En modo aviso el código de salida siempre es 0
            self.assertEqual(code, 0)
            self.assertIn("✗ R1", salida)

    def test_aviso_semana_iso_dispara_todas(self):
        """La primera vez en la semana ISO dispara --todas y anota el estado."""
        with tempfile.TemporaryDirectory() as td:
            raiz = Path(td) / "Proyectos"
            raiz.mkdir()

            caja_ok = raiz / "caja_ok"
            caja_ok.mkdir()
            subprocess.run(["git", "init"], cwd=caja_ok, capture_output=True, check=True)
            subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=caja_ok, capture_output=True, check=True)
            (caja_ok / "CLAUDE.md").write_text("# Ok\n", encoding="utf-8")
            (caja_ok / ".claude").mkdir()
            (caja_ok / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
            (caja_ok / ".gitignore").write_text(".env\n", encoding="utf-8")

            # Otra caja con falla en la raíz
            caja_rota = raiz / "caja_rota"
            caja_rota.mkdir()

            # Sin archivo de estado previo: primera vez en la semana
            estado_dir = Path(td) / "estado"
            os.environ["CLAUDE_PLUGIN_DATA"] = str(estado_dir)

            # Revisar solo caja_ok con aviso -> como es primera vez en la semana, dispara --todas sobre raiz
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = estructura.comando_revisar(carpeta_arg=str(caja_ok), aviso=True, raiz_arg=str(raiz))

            salida = buf.getvalue()
            self.assertEqual(code, 0)
            # Debe haber revisado caja_rota y detectado su falla
            self.assertIn("caja_rota", salida)

            # Debe haber creado el archivo de estado con la semana ISO actual
            iso_year, iso_week, _ = date.today().isocalendar()
            semana_esperada = f"{iso_year}-W{iso_week:02d}"
            estado_file = estado_dir / "semana-revisar.txt"
            self.assertTrue(estado_file.is_file())
            self.assertEqual(estado_file.read_text(encoding="utf-8").strip(), semana_esperada)

            # Segunda vez en la misma semana: ya no dispara --todas, solo revisa caja_ok (que está bien) -> salida vacía
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                code2 = estructura.comando_revisar(carpeta_arg=str(caja_ok), aviso=True, raiz_arg=str(raiz))

            self.assertEqual(code2, 0)
            self.assertEqual(buf2.getvalue().strip(), "")


if __name__ == "__main__":
    unittest.main()
