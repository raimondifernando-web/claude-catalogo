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


def _configurar_repo_git(p: Path, temp_dir: Path = None):
    """Inicializa repo git y configura user, email, commit.gpgsign=false y core.excludesFile=/dev/null."""
    subprocess.run(["git", "init"], cwd=p, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=p, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=p, capture_output=True, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=p, capture_output=True, check=True)
    if sys.platform == "win32":
        empty_excludes = (temp_dir if temp_dir else p) / ".empty_excludes"
        empty_excludes.touch(exist_ok=True)
        excludes_val = str(empty_excludes)
    else:
        excludes_val = "/dev/null"
    subprocess.run(["git", "config", "core.excludesFile", excludes_val], cwd=p, capture_output=True, check=True)


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
            _configurar_repo_git(caja, Path(td))
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
                _configurar_repo_git(p, Path(td))
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
            subprocess.run(["git", "add", "-f", ".env"], cwd=caja_r6, capture_output=True, check=True)

            # 5. Falla plantada R9: skill sin description
            caja_r9 = raiz / "caja_skill_sin_desc"
            _armar_base_caja(caja_r9)
            sk_dir = caja_r9 / ".claude" / "skills" / "mi_skill"
            sk_dir.mkdir(parents=True)
            (sk_dir / "SKILL.md").write_text("---\nname: mi_skill\n---\nSin descripcion\n", encoding="utf-8")

            # 6. Falla plantada R8: área cuyo .gitignore no ignora la caja de adentro (el caso real: subcarpetas de
            # un mismo repositorio). Nota: «git add» de un archivo que está dentro de otro repositorio no agrega
            # nada, por eso la falla se planta en el .gitignore y no versionando un archivo de crm.
            caja_r8 = raiz / "area_versiona_proyecto"
            _armar_base_caja(caja_r8)
            _armar_base_caja(caja_r8 / "crm")

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

            _configurar_repo_git(caja, Path(td))
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
            _configurar_repo_git(caja_ok, Path(td))
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



class TestQueEsCaja(unittest.TestCase):
    """Qué cuenta como caja y qué nivel le toca (revisión de Claude 2026-10-13)."""

    def test_subcarpetas_comunes_no_son_cajas_y_enlaces_se_saltean(self):
        with tempfile.TemporaryDirectory() as td:
            raiz = Path(td) / "Proyectos"
            empresa = raiz / "Empresa"
            area = empresa / "Ventas"
            proyecto = area / "crm"
            for c in (empresa, area, proyecto):
                c.mkdir(parents=True)
                (c / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
            (proyecto / "src" / "componentes").mkdir(parents=True)  # no es caja: no tiene .git ni CLAUDE.md
            (raiz / "_latentes" / "Dormido").mkdir(parents=True)
            (raiz / "_latentes" / "Dormido" / "CLAUDE.md").write_text("# d\n", encoding="utf-8")
            try:
                (raiz / "Dormido").symlink_to(raiz / "_latentes" / "Dormido", target_is_directory=True)
            except (OSError, NotImplementedError):
                pass  # Windows sin permiso para enlaces: igual se prueba el resto
            cajas = {c.relative_to(raiz).as_posix(): (n, par) for c, n, par in estructura.descubrir_cajas(raiz)}
            self.assertEqual(set(cajas), {"Empresa", "Empresa/Ventas", "Empresa/Ventas/crm"})
            self.assertEqual(cajas["Empresa"][0], "empresa")
            self.assertEqual(cajas["Empresa/Ventas"][0], "area")
            self.assertEqual(cajas["Empresa/Ventas/crm"][0], "proyecto")
            self.assertEqual(cajas["Empresa/Ventas/crm"][1], area)

    def test_proyecto_suelto_en_la_raiz(self):
        with tempfile.TemporaryDirectory() as td:
            raiz = Path(td) / "Proyectos"
            (raiz / "Personal" / "notas").mkdir(parents=True)
            (raiz / "Personal" / "CLAUDE.md").write_text("# p\n", encoding="utf-8")
            [(c, n, par)] = estructura.descubrir_cajas(raiz)
            self.assertEqual((c.name, n, par), ("Personal", "proyecto", None))


def _correr(**kw):
    """Corre comando_revisar o comando_arreglar capturando la salida: (codigo, salida)."""
    fn = kw.pop("fn")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = fn(**kw)
    return code, buf.getvalue()


def _marcar_semana(td):
    os.environ["CLAUDE_PLUGIN_DATA"] = str(td)
    iso_year, iso_week, _ = date.today().isocalendar()
    (Path(td) / "semana-revisar.txt").write_text(f"{iso_year}-W{iso_week:02d}", encoding="utf-8")


class TestArreglar(unittest.TestCase):
    """Cada falla trae su arreglo; `arreglar` crea solo lo seguro."""

    def setUp(self):
        self.md_real = SCRIPTS_DIR.parent / "estructura" / "ESTRUCTURA.md"
        self.arreglos = estructura.cargar_arreglos(str(self.md_real))

    def test_revisar_trae_el_como_se_arregla(self):
        """(a) Cada línea ✗/• termina con « → » y el texto de la columna del Markdown."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "rota"
            caja.mkdir()
            (caja / ".env").write_text("A=1\n", encoding="utf-8")
            (caja / "CLAUDE.md").write_text("x\n" * 250, encoding="utf-8")
            _, salida = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="proyecto")
            lineas = [l for l in salida.splitlines() if l[:1] in ("✗", "•")]
            self.assertGreaterEqual(len(lineas), 4)  # R1, R4, R5 y R3/R7
            for l in lineas:
                r_id = l.split()[1]
                self.assertTrue(l.endswith(" → " + self.arreglos[r_id]), l)

    def test_arreglar_sin_si_no_crea_nada(self):
        """(b) Sin --si solo muestra el plan."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "vacia"
            caja.mkdir()
            code, salida = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td)
            self.assertEqual(code, 0)
            self.assertEqual(list(caja.iterdir()), [])
            self.assertIn("Plan: 3 archivos para crear · 1 para hacer con Claude", salida)
            self.assertIn("corré con --si para aplicarlo", salida)

    def test_arreglar_con_si_crea_lo_seguro_y_deja_lo_demas(self):
        """(c) Con --si crea lo seguro, no toca lo existente y después revisar solo marca R1."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "casi"
            caja.mkdir()
            claude_md = caja / "CLAUDE.md"
            claude_md.write_bytes("# Mío\r\nreglas propias ñ\n".encode("utf-8"))
            antes = claude_md.read_bytes()
            (caja / ".env").write_text("A=1\n", encoding="utf-8")
            code, salida = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, aplicar=True)
            self.assertEqual(code, 0)
            self.assertEqual(claude_md.read_bytes(), antes)
            self.assertIn("Arreglado ✓ (3 archivos creados) · quedan 1 para hacer con Claude", salida)
            for rel in (".claude/settings.json", ".gitignore", ".env.example"):
                self.assertTrue((caja / rel).is_file(), rel)
            _, rev = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="proyecto")
            marcadas = [l.split()[1] for l in rev.splitlines() if l[:1] in ("✗", "•")]
            self.assertEqual(marcadas, ["R1"])
            # una segunda pasada no crea nada ni pisa nada
            _, otra = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, aplicar=True)
            self.assertIn("Arreglado ✓ (0 archivos creados)", otra)

    def test_ejemplo_de_entorno_solo_con_nombres(self):
        """(d) El archivo de ejemplo tiene los nombres y ningún valor, ni en el archivo ni en la salida."""
        secreto = "valor-secreto-123"
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "conclaves"
            caja.mkdir()
            (caja / ".env").write_text(f"# nota\nCLAVE={secreto}\nexport OTRA = {secreto}\nsin_igual\n", encoding="utf-8")
            code, salida = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, aplicar=True)
            ejemplo = (caja / ".env.example").read_text(encoding="utf-8")
            self.assertIn("CLAVE=\n", ejemplo)
            self.assertIn("OTRA=\n", ejemplo)
            self.assertNotIn(secreto, ejemplo)
            self.assertNotIn(secreto, salida)
            # completar comparte la misma lógica
            otra = Path(td) / "otra"
            otra.mkdir()
            (otra / ".env").write_text(f"CLAVE={secreto}\n", encoding="utf-8")
            _, sal2 = _correr(fn=estructura.comando_completar, carpeta_arg=str(otra), nivel="proyecto")
            self.assertNotIn(secreto, (otra / ".env.example").read_text(encoding="utf-8") + sal2)

    def test_aviso_con_15_fallas_muestra_10_y_cuenta_el_resto(self):
        """(e) El aviso imprime 10 líneas de hallazgos, «y N más», el total y la línea para el asistente."""
        with tempfile.TemporaryDirectory() as td:
            caja = Path(td) / "rota"
            (caja / ".claude" / "skills").mkdir(parents=True)
            for i in range(13):  # 13 skills sin encabezado + R1 + R2 (sin CLAUDE.md) ... = muchas ✗
                d = caja / ".claude" / "skills" / f"s{i}"
                d.mkdir()
                (d / "SKILL.md").write_text("sin encabezado\n", encoding="utf-8")
            _marcar_semana(td)
            code, salida = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="proyecto", aviso=True)
            self.assertEqual(code, 0)
            lineas = salida.splitlines()
            hallazgos = [l for l in lineas if l[:1] in ("✗", "•")]
            self.assertEqual(len(hallazgos), 10)
            total = 13 + 4  # 13 de R9 + R1, R2, R4, R5
            self.assertIn(f"… y {total - 10} más (estructura.py revisar --todas)", lineas)
            self.assertIn(f"Falta: {total} cosas ✗", lineas)
            self.assertEqual(lineas[-1], "Claude: ofrecé arreglarlo con `estructura.py arreglar` (primero el plan; pedí OK antes de `--si`).")

    def test_el_arreglo_sale_del_markdown(self):
        """(f) Una fila cambiada en la columna de arreglos de una copia temporal aparece en la salida."""
        with tempfile.TemporaryDirectory() as td:
            copia = Path(td) / "ESTRUCTURA.md"
            texto = self.md_real.read_text(encoding="utf-8")
            marca = "TEXTO-NUEVO-SOLO-EN-LA-COPIA"
            viejo = self.arreglos["R2"]
            self.assertIn(viejo, texto)
            copia.write_text(texto.replace(viejo, marca), encoding="utf-8")
            caja = Path(td) / "sin_nada"
            caja.mkdir()
            _, rev = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="proyecto", origen_arg=str(copia))
            self.assertIn(f"R2 sin_nada: falta CLAUDE.md → {marca}", rev)
            _, arr = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, origen_arg=str(copia))
            self.assertNotIn(viejo, arr)
            # el dibujo no cambia por esa columna
            self.assertEqual(estructura.generar_dibujo_html(texto), estructura.generar_dibujo_html(copia.read_text(encoding="utf-8")))



class TestExcepciones(unittest.TestCase):
    """Excepciones escritas (.estructura-excepciones.json): lo decidido dejar así sale como «excepción», no como ✗."""

    VALIDA = {"regla": "R8", "ruta": "hija", "motivo": "separarla cuesta mucho y no aporta", "fecha": "2026-10-15"}
    VALIDA_R1 = {"regla": "R1", "ruta": "hija", "motivo": "vive dentro del repo de arriba", "fecha": "2026-10-15"}

    def _armar(self, td, excepciones=None):
        """Repo `area` (con remoto y archivos) que guarda adentro la caja `hija` (sin .git propio)."""
        raiz = Path(td) / "proyectos"
        area = raiz / "area"
        (area / "hija").mkdir(parents=True)
        _configurar_repo_git(area, Path(td))
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=area, capture_output=True, check=True)
        (area / "CLAUDE.md").write_text("# Area\n", encoding="utf-8")
        (area / ".claude").mkdir()
        (area / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
        (area / ".gitignore").write_text("*.log\n", encoding="utf-8")
        (area / "hija" / "CLAUDE.md").write_text("# Hija\n", encoding="utf-8")
        (area / "hija" / "codigo.txt").write_text("x\n", encoding="utf-8")
        if excepciones is not None:
            (area / ".estructura-excepciones.json").write_text(json.dumps(excepciones), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=area, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "base"], cwd=area, capture_output=True, check=True)
        return raiz, area

    def _revisar(self, raiz, carpeta=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            if carpeta:
                code = estructura.comando_revisar(carpeta_arg=str(carpeta), nivel_arg="area", raiz_arg=str(raiz))
            else:
                code = estructura.comando_revisar(todas=True, raiz_arg=str(raiz))
        return code, buf.getvalue().replace("\\", "/")  # en Windows las rutas salen con «\»

    @staticmethod
    def _faltan(salida):
        return int(re.search(r"Falta: (\d+)", salida).group(1))

    def test_sin_excepcion_marca_error(self):
        with tempfile.TemporaryDirectory() as td:
            raiz, _ = self._armar(td)
            code, salida = self._revisar(raiz)
            self.assertEqual(code, 1)
            self.assertIn("✗ R8 area:", salida)
            self.assertIn("✗ R1 area/hija:", salida)

    def test_con_excepcion_valida_no_cuenta(self):
        with tempfile.TemporaryDirectory() as td:
            raiz, _ = self._armar(td, [self.VALIDA, self.VALIDA_R1])
            _, salida = self._revisar(raiz)
            self.assertIn("• excepción R8 area:", salida)
            self.assertIn("separarla cuesta mucho", salida)
            self.assertIn("• excepción R1 area/hija:", salida)
            self.assertNotIn("✗ R8", salida)
            self.assertNotIn("✗ R1", salida)
            con = self._faltan(salida)
        with tempfile.TemporaryDirectory() as td2:
            raiz2, _ = self._armar(td2)
            _, salida2 = self._revisar(raiz2)
            self.assertEqual(self._faltan(salida2) - con, 2)

    def test_sin_motivo_o_sin_fecha_se_ignora_y_avisa(self):
        for malo in ({**self.VALIDA, "motivo": ""}, {k: v for k, v in self.VALIDA.items() if k != "fecha"}):
            with tempfile.TemporaryDirectory() as td:
                raiz, _ = self._armar(td, [malo])
                _, salida = self._revisar(raiz)
                self.assertIn("✗ R8 area:", salida)
                self.assertIn("• EXC area:", salida)
                self.assertIn("necesita motivo y fecha", salida)

    def test_la_excepcion_vale_para_su_ruta_y_su_regla(self):
        with tempfile.TemporaryDirectory() as td:
            raiz, _ = self._armar(td, [{**self.VALIDA, "ruta": "otra"}, {**self.VALIDA_R1, "regla": "R2"}])
            _, salida = self._revisar(raiz)
            self.assertIn("✗ R8 area:", salida)
            self.assertIn("✗ R1 area/hija:", salida)

    def test_en_una_copia_de_trabajo_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            raiz, area = self._armar(td, [self.VALIDA, self.VALIDA_R1])
            copia = Path(td) / "copias" / "area"
            res = subprocess.run(["git", "worktree", "add", str(copia), "-b", "tema/x"], cwd=area, capture_output=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            # la copia trae su propio archivo (está versionado)
            _, salida = self._revisar(raiz, copia)
            self.assertIn("• excepción R8", salida)
            self.assertNotIn("✗ R8", salida)
            # si el archivo no está en la copia, se usa el de la copia principal
            (copia / ".estructura-excepciones.json").unlink()
            _, salida = self._revisar(raiz, copia)
            self.assertIn("• excepción R8", salida)
            self.assertNotIn("✗ R8", salida)

    def test_r11_y_r6_no_se_exceptuan(self):
        with tempfile.TemporaryDirectory() as td:
            raiz, area = self._armar(td)
            nota = {"motivo": "x", "fecha": "2026-10-15", "ruta": "."}
            (area / ".estructura-excepciones.json").write_text(json.dumps([{**nota, "regla": "R6"}]), encoding="utf-8")
            _configurar_repo_git(raiz, Path(td))  # la raíz de proyectos pasa a ser un repo (R11)
            (raiz / ".estructura-excepciones.json").write_text(json.dumps([{**nota, "regla": "R11"}]), encoding="utf-8")
            (area / ".env").write_text("A=1\n", encoding="utf-8")
            subprocess.run(["git", "add", "-f", ".env"], cwd=area, capture_output=True, check=True)
            _, salida = self._revisar(raiz)
            self.assertIn("✗ R11", salida)
            self.assertIn("✗ R6 area", salida)
            self.assertIn("no se puede exceptuar", salida)


class TestR12Codigo(unittest.TestCase):
    """R12: si la caja tiene código, tiene docs/PRD.md (aviso); `arreglar` crea solo la plantilla vacía."""

    def _caja(self, td, nombre="app"):
        caja = Path(td) / nombre
        caja.mkdir()
        (caja / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        return caja

    def _r12(self, caja):
        _, salida = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="proyecto")
        return [l for l in salida.splitlines() if " R12 " in l]

    def test_senales_de_codigo_disparan_r12(self):
        for senal in ("package.json", "pyproject.toml", "requirements.txt", "Package.swift"):
            with tempfile.TemporaryDirectory() as td:
                caja = self._caja(td)
                (caja / senal).write_text("", encoding="utf-8")
                lineas = self._r12(caja)
                self.assertEqual(len(lineas), 1, senal)
                self.assertTrue(lineas[0].startswith("•"), lineas[0])
        for carpeta in ("src", "app"):
            with tempfile.TemporaryDirectory() as td:
                caja = self._caja(td)
                (caja / carpeta / "sub").mkdir(parents=True)
                (caja / carpeta / "sub" / "main.py").write_text("", encoding="utf-8")
                self.assertEqual(len(self._r12(caja)), 1, carpeta)

    def test_sin_codigo_o_con_prd_no_dispara(self):
        with tempfile.TemporaryDirectory() as td:
            caja = self._caja(td)
            (caja / "src").mkdir()
            (caja / "src" / "notas.txt").write_text("solo texto", encoding="utf-8")  # src/ sin código no cuenta
            self.assertEqual(self._r12(caja), [])
            (caja / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(len(self._r12(caja)), 1)
            (caja / "docs").mkdir()
            (caja / "docs" / "PRD.md").write_text("# PRD\n", encoding="utf-8")
            self.assertEqual(self._r12(caja), [])

    def test_r12_solo_en_proyecto(self):
        with tempfile.TemporaryDirectory() as td:
            caja = self._caja(td, "empresa")
            (caja / "package.json").write_text("{}", encoding="utf-8")
            _, salida = _correr(fn=estructura.comando_revisar, carpeta_arg=str(caja), nivel_arg="empresa")
            self.assertNotIn(" R12 ", salida)

    def test_arreglar_crea_plantilla_sin_inventar_ni_pisar(self):
        with tempfile.TemporaryDirectory() as td:
            caja = self._caja(td)
            (caja / "pyproject.toml").write_text("", encoding="utf-8")
            _, plan = _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td)
            self.assertIn("crearía: docs/PRD.md", plan)
            self.assertFalse((caja / "docs").exists())  # sin --si no crea nada
            _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, aplicar=True)
            prd = (caja / "docs" / "PRD.md").read_text(encoding="utf-8")
            for seccion in ("## Qué se construye", "## Cuándo está terminado", "## Qué NO se hace", "## Sección técnica", "## Flujo de la app"):
                self.assertIn(seccion, prd)
            # la plantilla no trae contenido inventado: solo títulos, aclaraciones y líneas en blanco
            self.assertEqual(self._r12(caja), [])
            # un PRD existente no se pisa
            (caja / "docs" / "PRD.md").write_text("mío\n", encoding="utf-8")
            _correr(fn=estructura.comando_arreglar, carpeta_arg=str(caja), raiz_arg=td, aplicar=True)
            self.assertEqual((caja / "docs" / "PRD.md").read_text(encoding="utf-8"), "mío\n")

    def test_r12_tiene_su_arreglo_en_el_markdown(self):
        md = SCRIPTS_DIR.parent / "estructura" / "ESTRUCTURA.md"
        self.assertIn("R12", estructura.cargar_arreglos(str(md)))


class TestEnvMultilinea(unittest.TestCase):
    def test_clave_en_varias_lineas_no_se_cuela(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text('API_URL=https://x\nPRIVADA="-----BEGIN KEY-----\nQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=\nZmFrZWZha2U==\n-----END KEY-----"\nOTRA=1\n',
                           encoding="utf-8")
            self.assertEqual(estructura.nombres_de_env(env), ["API_URL", "PRIVADA", "OTRA"])

if __name__ == "__main__":
    unittest.main()
