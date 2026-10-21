#!/usr/bin/env python3
"""Pruebas unitarias para sesion_hija.py.
Todo en carpetas temporales: metadatos falsos, HOME falso, repos de juguete (remoto bare + checkout compartido).
Nunca usa red ni la carpeta real de sesiones.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
SESION_HIJA = AQUI / "sesion_hija.py"
EDICIONES = AQUI / "ediciones.py"
sys.path.insert(0, str(AQUI))
import sesiones_hijas as hs  # noqa: E402
import ediciones as ed  # noqa: E402
import sesion_hija as sh_mod  # noqa: E402

ENV_GIT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@test",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@test",
}


def sh_git(repo, *args, env=None):
    e = dict(os.environ, **ENV_GIT, **(env or {}))
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=e)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló: {r.stderr.strip()}")
    return r.stdout.strip()


class TestSesionHija(unittest.TestCase):
    def setUp(self):
        getattr(hs, "_CACHE", {}).clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self.tmp.name))
        self.home = self.root / "home"
        self.cfg = self.home / ".claude"
        self.ses_dir = self.home / "sesiones"
        self.notas_dir = self.home / "notas"

        (self.cfg / "projects" / "p1").mkdir(parents=True)
        (self.ses_dir / "a" / "b").mkdir(parents=True)
        self.notas_dir.mkdir(parents=True)

        self.remoto = self.root / "remoto.git"
        sh_git(self.root, "init", "-q", "--bare", "-b", "main", str(self.remoto))

        self.repo = self.home / "proyecto"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(self.repo))
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        sh_git(self.repo, "add", "README.md")
        sh_git(self.repo, "commit", "-q", "-m", "base")
        sh_git(self.repo, "push", "-q", "-u", "origin", "main")

        (self.repo / ".claude" / "prompts").mkdir(parents=True)
        (self.repo / ".claude" / "prompts" / "REANUDAR.md").write_text("reanudar base\n", encoding="utf-8")
        sh_git(self.repo, "add", ".claude/prompts/REANUDAR.md")
        sh_git(self.repo, "commit", "-q", "-m", "reanudar base")
        sh_git(self.repo, "push", "-q", "origin", "main")

        self.env_original = dict(os.environ)
        os.environ.update(ENV_GIT)
        os.environ["HOME"] = str(self.home)
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.cfg)
        os.environ["CLAUDE_SESIONES_DIR"] = str(self.ses_dir)
        os.environ["CLAUDE_NOTAS_DIR"] = str(self.notas_dir)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_original)
        getattr(hs, "_CACHE", {}).clear()
        self.tmp.cleanup()

    def sesion(self, sid, cli_id, titulo, cwd=None, **kw):
        d = {
            "sessionId": sid,
            "cliSessionId": cli_id,
            "title": titulo,
            "cwd": str(cwd or self.repo),
            "lastActivityAt": int(time.time() * 1000),
            **kw,
        }
        (self.ses_dir / "a" / "b" / f"local_{sid}.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8"
        )
        getattr(hs, "_CACHE", {}).clear()
        return d

    def hook(self, sid, herramienta, file_path=None, command=None, cwd=None):
        ti = {}
        if file_path:
            ti["file_path"] = str(file_path)
        if command:
            ti["command"] = command
        datos = {
            "session_id": sid,
            "cwd": str(cwd or self.repo),
            "tool_name": herramienta,
            "tool_input": ti,
        }
        env = dict(
            os.environ,
            HOME=str(self.home),
            CLAUDE_CONFIG_DIR=str(self.cfg),
            CLAUDE_CODE_SESSION_ID=sid,
        )
        r = subprocess.run(
            [sys.executable, str(EDICIONES), "registrar"],
            input=json.dumps(datos),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(r.returncode, 0)

    def transcripcion(self, cli_id, texto_user):
        p = self.cfg / "projects" / "p1" / f"{cli_id}.jsonl"
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        line = json.dumps({"timestamp": ts, "type": "user", "message": {"content": texto_user}})
        p.write_text(line + "\n", encoding="utf-8")

    # ---------------- 1) Pruebas de detectar ----------------

    def test_detectar_hija_compartida(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h001",
            "cli-h1",
            "Hija Compartida",
            spawnedFrom={"sessionId": "m001", "name": "hija-comp", "sideSession": True},
            lineageDetached=False,
            worktreePath=None,
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h1"
        res = sh_mod.detectar()
        self.assertEqual(res["modo"], "hija")
        self.assertEqual(res["carpeta"], "compartida")
        self.assertEqual(res["nombre"], "hija-comp")
        self.assertEqual(res["padre"], "m001")

    def test_detectar_hija_con_worktree_propio(self):
        wt_dir = self.home / "wt-propio"
        wt_dir.mkdir(parents=True)
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h002",
            "cli-h2",
            "Hija WT",
            spawnedFrom={"sessionId": "m001", "name": "hija-wt", "sideSession": True},
            lineageDetached=False,
            worktreePath=str(wt_dir),
            cwd=str(wt_dir),
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h2"
        old_cwd = os.getcwd()
        try:
            os.chdir(wt_dir)
            res = sh_mod.detectar()
            self.assertEqual(res["modo"], "hija")
            self.assertEqual(res["carpeta"], "propia")
        finally:
            os.chdir(old_cwd)

    def test_detectar_independizada_en_carpeta_compartida(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h003",
            "cli-h3",
            "Hija Indep",
            spawnedFrom={"sessionId": "m001", "name": "hija-ind", "sideSession": True},
            lineageDetached=True,
            worktreePath=None,
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h3"
        self.transcripcion("cli-h3", "hacé tal refactor")
        res = sh_mod.detectar()
        self.assertEqual(res["modo"], "hija")
        self.assertEqual(res["motivo"], "independizada en carpeta compartida")

    def test_detectar_independizada_arranco_con_arrancar(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h004",
            "cli-h4",
            "Hija Arrancar",
            spawnedFrom={"sessionId": "m001", "name": "hija-arr", "sideSession": True},
            lineageDetached=True,
            worktreePath=None,
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h4"
        self.transcripcion("cli-h4", "skill arrancar en esta carpeta")
        res = sh_mod.detectar()
        self.assertEqual(res["modo"], "normal")

    def test_detectar_sesion_sin_spawned_from(self):
        self.sesion("s005", "cli-s5", "Sesión Principal", spawnedFrom=None)
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-s5"
        res = sh_mod.detectar()
        self.assertEqual(res["modo"], "normal")

    # ---------------- 2) Escenario completo ----------------

    def test_escenario_completo_foto_subir_comparar_y_pull(self):
        # Coordinadora, sesión B y sesión H
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("b001", "cli-b", "Sesión B")
        self.sesion(
            "h001",
            "cli-h",
            "Sesión H",
            spawnedFrom={"sessionId": "m001", "name": "h-trabajo", "sideSession": True},
        )

        # 1. B crea commit local sin subir en shared_repo
        b_commit_file = self.repo / "b_commit.txt"
        b_commit_file.write_text("commit de b\n", encoding="utf-8")
        sh_git(self.repo, "add", "b_commit.txt")
        sh_git(self.repo, "commit", "-q", "-m", "commit de B")
        sha_commit_b = sh_git(self.repo, "rev-parse", "HEAD")

        # 2. B tiene archivo sucio sin guardar
        b_sucio_file = self.repo / "b_sucio.txt"
        b_sucio_file.write_text("sucio de b\n", encoding="utf-8")
        self.hook("cli-b", "Write", file_path="b_sucio.txt")

        # 3. Remoto avanza con commit de un tercero
        tercero_dir = self.root / "tercero"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(tercero_dir))
        (tercero_dir / "tercero.txt").write_text("archivo de tercero\n", encoding="utf-8")
        sh_git(tercero_dir, "add", "tercero.txt")
        sh_git(tercero_dir, "commit", "-q", "-m", "commit de tercero")
        sh_git(tercero_dir, "push", "-q", "origin", "main")
        sha_tercero = sh_git(self.remoto, "rev-parse", "main")

        # 4. H crea archivo nuevo y modifica uno versionado
        (self.repo / "h_nuevo.txt").write_text("nuevo de h\n", encoding="utf-8")
        (self.repo / "README.md").write_text("base modificada por h\n", encoding="utf-8")
        self.hook("cli-h", "Write", file_path="h_nuevo.txt")
        self.hook("cli-h", "Edit", file_path="README.md")

        # 5. Foto desde la perspectiva de H
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        os.environ["SUBIR_HIJA_DIRECTO"] = "remoto"

        ok_foto, lineas_foto = sh_mod.foto([str(self.repo)])
        self.assertTrue(ok_foto)
        self.assertTrue(any("Foto de lo ajeno" in l for l in lineas_foto))

        # 6. Subir directo
        cod, lineas_subir = sh_mod.subir(str(self.repo), "cambios de H", directo=True)
        self.assertEqual(cod, 0, f"subir falló: {lineas_subir}")

        # El remoto tiene el commit de H encima del tercero
        sha_remoto_main = sh_git(self.remoto, "rev-parse", "main")
        sha_remoto_padre = sh_git(self.remoto, "rev-parse", "main~1")
        self.assertEqual(sha_remoto_padre, sha_tercero)

        # El commit de B sigue con el MISMO hash en la rama local
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD~1"), sha_commit_b)

        # El archivo sucio de B sigue intacto
        self.assertTrue(b_sucio_file.is_file())
        self.assertEqual(b_sucio_file.read_text(encoding="utf-8"), "sucio de b\n")

        # 7. Comparar da ✓
        ok_comp, lineas_comp = sh_mod.comparar()
        self.assertTrue(ok_comp, f"comparar falló: {lineas_comp}")
        self.assertFalse(any("✗" in l for l in lineas_comp))

        # 8. B corre pull --rebase --autostash y queda bien (commit local duplicado de H desaparece)
        sh_git(self.repo, "pull", "--rebase", "--autostash", "origin", "main")
        # El HEAD local es ahora el commit de B sobre el main remoto
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD~1"), sha_remoto_main)
        # El archivo sucio de B sigue intacto
        self.assertEqual(b_sucio_file.read_text(encoding="utf-8"), "sucio de b\n")

    # ---------------- 3) subir rechaza archivo ajeno en --incluir ----------------

    def test_subir_rechaza_incluir_ajeno(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("b001", "cli-b", "Sesión B")
        self.sesion("h001", "cli-h", "Sesión H", spawnedFrom={"sessionId": "m001", "sideSession": True})

        (self.repo / "b_otro.txt").write_text("de b\n", encoding="utf-8")
        self.hook("cli-b", "Write", file_path="b_otro.txt")

        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        (self.repo / "h_propio.txt").write_text("de h\n", encoding="utf-8")
        self.hook("cli-h", "Write", file_path="h_propio.txt")

        os.environ["SUBIR_HIJA_DIRECTO"] = "remoto"
        cod, lineas = sh_mod.subir(str(self.repo), "prueba", directo=True, incluir=["b_otro.txt"])
        self.assertEqual(cod, 3)
        self.assertTrue(any("es de otra sesión" in l for l in lineas))

    # ---------------- 4) Conflicto con remoto ----------------

    def test_subir_detecta_conflicto(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("h001", "cli-h", "Sesión H", spawnedFrom={"sessionId": "m001", "sideSession": True})

        # Tercero modifica README.md en remoto
        tercero_dir = self.root / "tercero2"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(tercero_dir))
        (tercero_dir / "README.md").write_text("cambio remoto de tercero\n", encoding="utf-8")
        sh_git(tercero_dir, "add", "README.md")
        sh_git(tercero_dir, "commit", "-q", "-m", "cambio remoto")
        sh_git(tercero_dir, "push", "-q", "origin", "main")
        sha_remoto_antes = sh_git(self.remoto, "rev-parse", "main")

        # H modifica README.md localmente
        (self.repo / "README.md").write_text("cambio local de H\n", encoding="utf-8")
        self.hook("cli-h", "Edit", file_path="README.md")

        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        os.environ["SUBIR_HIJA_DIRECTO"] = "remoto"
        cod, lineas = sh_mod.subir(str(self.repo), "cambios conflicto", directo=True)
        self.assertEqual(cod, 4)
        self.assertTrue(any("cambió en GitHub mientras tanto" in l for l in lineas))
        # Remoto no cambió
        self.assertEqual(sh_git(self.remoto, "rev-parse", "main"), sha_remoto_antes)

    # ---------------- 5) Subir sin directo ----------------

    def test_subir_sin_directo(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h001",
            "cli-h",
            "Sesión H",
            spawnedFrom={"sessionId": "m001", "name": "h-rama", "sideSession": True},
        )
        (self.repo / "h_rama.txt").write_text("rama h\n", encoding="utf-8")
        self.hook("cli-h", "Write", file_path="h_rama.txt")

        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        sha_main_antes = sh_git(self.remoto, "rev-parse", "main")

        cod, lineas = sh_mod.subir(str(self.repo), "subida a rama", directo=False)
        self.assertEqual(cod, 0)
        self.assertTrue(any("gh pr create" in l for l in lineas))

        # Main remoto no cambió
        self.assertEqual(sh_git(self.remoto, "rev-parse", "main"), sha_main_antes)

        # Se creó rama remota hija/h-rama-...
        ramas_remotas = sh_git(self.remoto, "branch", "-l")
        self.assertTrue(any("hija/h-rama-" in r for r in ramas_remotas.splitlines()))

    # ---------------- 6) Comparar detecta commit modificado ----------------

    def test_comparar_detecta_commit_modificado(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("b001", "cli-b", "Sesión B")
        self.sesion("h001", "cli-h", "Sesión H", spawnedFrom={"sessionId": "m001", "sideSession": True})

        (self.repo / "commit_b.txt").write_text("original\n", encoding="utf-8")
        sh_git(self.repo, "add", "commit_b.txt")
        sh_git(self.repo, "commit", "-q", "-m", "commit b original")

        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        sh_mod.foto([str(self.repo)])

        # B hace amend (cambia sha)
        (self.repo / "commit_b.txt").write_text("modificado\n", encoding="utf-8")
        sh_git(self.repo, "add", "commit_b.txt")
        sh_git(self.repo, "commit", "--amend", "-q", "-m", "commit b amend")

        ok, lineas = sh_mod.comparar()
        self.assertFalse(ok)
        self.assertTrue(any("ya no está" in l for l in lineas))

    # ---------------- 7) Traspaso ----------------

    def test_traspaso_validaciones_y_archivos(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h001",
            "cli-h",
            "Sesión H",
            spawnedFrom={"sessionId": "m001", "name": "h-trasp", "sideSession": True},
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"

        borrador_incompleto = self.root / "borrador_inc.md"
        borrador_incompleto.write_text("## Qué se hizo\nTodo bien.\n", encoding="utf-8")

        ok, lineas = sh_mod.traspaso(str(borrador_incompleto))
        self.assertFalse(ok)
        self.assertTrue(any("Traspaso incompleto" in l for l in lineas))

        # Borrador con decisiones sin cita ni "ninguna"
        borrador_sin_cita = self.root / "borrador_sc.md"
        borrador_sin_cita.write_text(
            "## Qué se hizo\nHecho.\n"
            "## Qué sigue\nNada.\n"
            "## Decisiones de la persona\nDecidimos avanzar.\n"
            "## Pendientes\nNinguno.\n"
            "## Sesiones\nNinguna.\n"
            "## Continuación propuesta\nContinuar.\n",
            encoding="utf-8",
        )
        ok, lineas = sh_mod.traspaso(str(borrador_sin_cita))
        self.assertFalse(ok)
        self.assertTrue(any("cita entre «» o la palabra 'ninguna'" in l for l in lineas))

        # Borrador completo
        borrador_ok = self.root / "borrador_ok.md"
        borrador_ok.write_text(
            "## Qué se hizo\nSe implementó todo.\n"
            "## Qué sigue\nVerificar.\n"
            "## Decisiones de diseño\nSe acordó «usar biblioteca estándar».\n"
            "## Pendientes\nDocumentación.\n"
            "## Sesiones\nNinguna activa.\n"
            "## Continuación propuesta\nRevisar pruebas.\n",
            encoding="utf-8",
        )
        ok, lineas = sh_mod.traspaso(str(borrador_ok))
        self.assertTrue(ok)

        # Verificar que se crearon los dos archivos idénticos
        prompts_dir = self.repo / ".claude" / "prompts"
        archivos_prompts = list(prompts_dir.glob("TRASPASO-*-h-trasp.md"))
        self.assertEqual(len(archivos_prompts), 1)
        archivo_p = archivos_prompts[0]

        notas_hija_dir = self.notas_dir / "m001"
        archivos_notas = list(notas_hija_dir.glob("TRASPASO-*-h-trasp.md"))
        self.assertEqual(len(archivos_notas), 1)
        archivo_n = archivos_notas[0]

        self.assertEqual(archivo_p.read_text(encoding="utf-8"), archivo_n.read_text(encoding="utf-8"))
        self.assertNotEqual(archivo_p.name, "REANUDAR.md")

    # ---------------- 8) Recibir ----------------

    def test_recibir_exito_y_fallas(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion(
            "h001",
            "cli-h",
            "Sesión H",
            spawnedFrom={"sessionId": "m001", "name": "h-rec", "sideSession": True},
        )
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"

        borrador_ok = self.root / "borrador_rec.md"
        borrador_ok.write_text(
            "## Qué se hizo\nListo.\n"
            "## Qué sigue\nListo.\n"
            "## Decisiones de persona\n«ok»\n"
            "## Pendientes\nListo.\n"
            "## Sesiones\nListo.\n"
            "## Continuación propuesta\nListo.\n",
            encoding="utf-8",
        )
        sh_mod.traspaso(str(borrador_ok))

        # 8a: Recibir con todo bien
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-m"
        ok, lineas = sh_mod.recibir("h001")
        self.assertTrue(ok, f"recibir falló: {lineas}")
        self.assertTrue(any("Hija lista para archivar" in l for l in lineas))

        # 8b: Falla si se borra la copia de notas
        notas_copia = list((self.notas_dir / "m001").glob("TRASPASO-*-h-rec.md"))[0]
        notas_copia.unlink()
        ok_sin_notas, lineas_sin_notas = sh_mod.recibir("h001")
        self.assertFalse(ok_sin_notas)
        self.assertTrue(any("Falta la copia del traspaso en notas_dir" in l for l in lineas_sin_notas))

        # 8c: Falla si se edita una de las dos copias (difieren)
        notas_copia.write_text("modificado ajeno\n", encoding="utf-8")
        ok_dif, lineas_dif = sh_mod.recibir("h001")
        self.assertFalse(ok_dif)
        self.assertTrue(any("Las dos copias del traspaso difieren" in l for l in lineas_dif))

        # Restaurar copia idéntica
        prompts_copia = list((self.repo / ".claude" / "prompts").glob("TRASPASO-*-h-rec.md"))[0]
        notas_copia.write_text(prompts_copia.read_text(encoding="utf-8"), encoding="utf-8")

        # 8d: Falla si el sha subido no está en el remoto
        texto_original = prompts_copia.read_text(encoding="utf-8")
        texto_sha_falso = texto_original.replace(
            '"subidas": []',
            f'"subidas": [{{"repo": "{self.repo}", "destino": "main", "sha": "1111222233334444555566667777888899990000"}}]',
        )
        prompts_copia.write_text(texto_sha_falso, encoding="utf-8")
        notas_copia.write_text(texto_sha_falso, encoding="utf-8")
        ok_sha, lineas_sha = sh_mod.recibir("h001")
        self.assertFalse(ok_sha)
        self.assertTrue(any("no está en GitHub" in l for l in lineas_sha))

        # Restaurar copias válidas
        prompts_copia.write_text(texto_original, encoding="utf-8")
        notas_copia.write_text(texto_original, encoding="utf-8")

        # 8e: Falla si el registro dice que la hija editó REANUDAR.md
        self.hook("cli-h", "Edit", file_path=str(self.repo / ".claude" / "prompts" / "REANUDAR.md"))
        ok_re, lineas_re = sh_mod.recibir("h001")
        self.assertFalse(ok_re)
        self.assertTrue(any("La hija editó" in l and "REANUDAR.md" in l for l in lineas_re))


    # ---------------- agregados en la revisión (Claude, 2026-10-21) ----------------

    def _escena_compartida(self):
        """B con un commit sin subir y un archivo sucio; H edita un archivo y crea otro. Devuelve el sha del commit de B."""
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("b001", "cli-b", "Sesión B")
        self.sesion("h001", "cli-h", "Sesión H", spawnedFrom={"sessionId": "m001", "name": "h-trabajo", "sideSession": True,
                                                              "sharedFolder": True})
        (self.repo / "b_commit.txt").write_text("commit de b\n", encoding="utf-8")
        sh_git(self.repo, "add", "b_commit.txt")
        sh_git(self.repo, "commit", "-q", "-m", "commit de B")
        sha_b = sh_git(self.repo, "rev-parse", "HEAD")
        (self.repo / "b_sucio.txt").write_text("sucio de b\n", encoding="utf-8")
        self.hook("cli-b", "Write", file_path="b_sucio.txt")
        (self.repo / "h_nuevo.txt").write_text("nuevo de h\n", encoding="utf-8")
        self.hook("cli-h", "Write", file_path="h_nuevo.txt")
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-h"
        os.environ["SUBIR_HIJA_DIRECTO"] = "remoto"
        return sha_b

    def _traspaso(self):
        b = self.root / "borrador.md"
        b.write_text("## Qué se hizo\nX\n## Qué sigue\nY\n## Decisiones de la persona\n«sí, dale» (2026-10-21)\n"
                     "## Pendientes\nninguno\n## Sesiones\nninguna\n## Continuación propuesta\nno, cerrar\n", encoding="utf-8")
        ok, l = sh_mod.traspaso(str(b))
        self.assertTrue(ok, l)

    def test_subir_firma_con_la_identidad_normal_de_git(self):
        self._escena_compartida()
        cod, l = sh_mod.subir(str(self.repo), "cambios de H", directo=True)
        self.assertEqual(cod, 0, l)
        self.assertEqual(sh_git(self.remoto, "log", "-1", "--format=%an <%ae>", "main"), "test <test@test>")

    def test_subir_frena_archivo_editado_tambien_por_otra_sesion(self):
        self._escena_compartida()
        (self.repo / "README.md").write_text("de las dos\n", encoding="utf-8")
        self.hook("cli-b", "Edit", file_path="README.md")
        self.hook("cli-h", "Edit", file_path="README.md")
        cod, l = sh_mod.subir(str(self.repo), "x", directo=True)
        self.assertEqual(cod, 3, l)
        self.assertTrue(any("también lo editó otra sesión" in x for x in l))

    def test_subir_nunca_sube_reanudar_de_carpeta_compartida(self):
        self._escena_compartida()
        (self.repo / ".claude" / "prompts" / "REANUDAR.md").write_text("pisado\n", encoding="utf-8")
        self.hook("cli-h", "Edit", file_path=".claude/prompts/REANUDAR.md")
        cod, l = sh_mod.subir(str(self.repo), "x", directo=True)
        self.assertEqual(cod, 3, l)

    def test_conflicto_no_deja_commit_local(self):
        self._escena_compartida()
        tercero = self.root / "tercero3"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(tercero))
        (tercero / "h_nuevo.txt").write_text("otro contenido\n", encoding="utf-8")
        sh_git(tercero, "add", "h_nuevo.txt")
        sh_git(tercero, "commit", "-q", "-m", "choca")
        sh_git(tercero, "push", "-q", "origin", "main")
        antes = sh_git(self.repo, "rev-parse", "HEAD")
        cod, l = sh_mod.subir(str(self.repo), "x", directo=True)
        self.assertEqual(cod, 4, l)
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD"), antes)

    def test_chequeo_cierre_completo_y_recibir_con_commit_ajeno_sin_subir(self):
        sha_b = self._escena_compartida()
        sh_mod.foto([str(self.repo)])
        cod, l = sh_mod.subir(str(self.repo), "cambios de H", directo=True)
        self.assertEqual(cod, 0, l)
        self._traspaso()
        res = sh_mod.chequeo_cierre(str(self.repo))
        self.assertFalse([t for ok, t in res if ok is False], res)
        # la coordinadora: el commit de B sin subir y la copia local de H no son trabajo de la hija
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-m"
        ok, lineas = sh_mod.recibir("h001")
        self.assertTrue(ok, lineas)
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD~1"), sha_b)

    def test_chequeo_cierre_marca_lo_tuyo_sin_subir_y_sin_traspaso(self):
        self._escena_compartida()
        sh_mod.foto([str(self.repo)])
        res = sh_mod.chequeo_cierre(str(self.repo))
        malos = " | ".join(t for ok, t in res if ok is False)
        self.assertIn("Falta el traspaso", malos)
        self.assertIn("h_nuevo.txt", malos)
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-m"
        ok, lineas = sh_mod.recibir("h001")
        self.assertFalse(ok)
        self.assertTrue(any("Sin subir: h_nuevo.txt" in x for x in lineas), lineas)

    def test_comparar_tolera_que_la_duena_reacomode_su_commit(self):
        sha_b = self._escena_compartida()
        sh_mod.foto([str(self.repo)])
        tercero = self.root / "tercero4"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(tercero))
        (tercero / "t.txt").write_text("t\n", encoding="utf-8")
        sh_git(tercero, "add", "t.txt")
        sh_git(tercero, "commit", "-q", "-m", "t")
        sh_git(tercero, "push", "-q", "origin", "main")
        sh_git(self.repo, "pull", "-q", "--rebase", "--autostash", "origin", "main")  # lo hace B, la dueña
        self.assertNotEqual(sh_git(self.repo, "rev-parse", "HEAD"), sha_b)
        ok, lineas = sh_mod.comparar()
        self.assertTrue(ok, lineas)
        self.assertTrue(any("cambió de huella" in x for x in lineas))

    def test_reanudar_en_la_raiz_tambien_se_protege(self):
        self._escena_compartida()
        (self.repo / "REANUDAR.md").write_text("del hilo principal\n", encoding="utf-8")
        sh_mod.foto([str(self.repo)])
        (self.repo / "REANUDAR.md").write_text("pisado\n", encoding="utf-8")
        ok, lineas = sh_mod.comparar()
        self.assertFalse(ok)
        self.assertTrue(any("REANUDAR.md cambió" in x for x in lineas), lineas)

    def test_subir_por_rama_no_deja_commit_local_y_el_pull_ajeno_absorbe(self):
        sha_b = self._escena_compartida()
        (self.repo / "README.md").write_text("base modificada por h\n", encoding="utf-8")
        self.hook("cli-h", "Edit", file_path="README.md")
        antes = sh_git(self.repo, "rev-parse", "HEAD")
        main_remoto = sh_git(self.remoto, "rev-parse", "main")
        cod, l = sh_mod.subir(str(self.repo), "cambios de H")
        self.assertEqual(cod, 0, l)
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD"), antes)          # sin commit en la carpeta compartida
        self.assertEqual(sh_git(self.remoto, "rev-parse", "main"), main_remoto)  # main no cambió: va por PR
        rama = [x for x in sh_git(self.remoto, "branch", "--format=%(refname:short)").split() if x.startswith("hija/")][0]
        self.assertEqual(sh_git(self.remoto, "show", f"{rama}:h_nuevo.txt"), "nuevo de h")
        self.assertEqual(sh_git(self.remoto, "show", f"{rama}:README.md"), "base modificada por h")
        # se une el PR (como lo haría GitHub) y B, la dueña del commit sin subir, hace su pull de siempre: no se traba
        tercero = self.root / "unir"
        sh_git(self.root, "clone", "-q", str(self.remoto), str(tercero))
        sh_git(tercero, "merge", "-q", "--ff-only", f"origin/{rama}")
        sh_git(tercero, "push", "-q", "origin", "main")
        sh_git(self.repo, "pull", "-q", "--rebase", "--autostash", "origin", "main")
        self.assertEqual(sh_git(self.repo, "log", "-1", "--format=%s"), "commit de B")
        self.assertEqual((self.repo / "b_sucio.txt").read_text(encoding="utf-8"), "sucio de b\n")

    def test_directo_no_permitido_no_toca_nada(self):
        self._escena_compartida()
        os.environ["SUBIR_HIJA_DIRECTO"] = ""
        antes = sh_git(self.repo, "rev-parse", "HEAD")
        cod, l = sh_mod.subir(str(self.repo), "x", directo=True)
        self.assertEqual(cod, 64, l)
        self.assertEqual(sh_git(self.repo, "rev-parse", "HEAD"), antes)
        self.assertNotIn("A ", sh_git(self.repo, "status", "--short"))

    def test_ruta_con_coma(self):
        self._escena_compartida()
        (self.repo / "informe, v1.md").write_text("con coma\n", encoding="utf-8")
        self.hook("cli-h", "Write", file_path="informe, v1.md")
        cod, l = sh_mod.subir(str(self.repo), "x", directo=True)
        self.assertEqual(cod, 0, l)
        self.assertEqual(sh_git(self.remoto, "show", "main:informe, v1.md"), "con coma")

    def test_commit_local_de_la_hija_sin_subir_frena_recibir(self):
        self._escena_compartida()
        sh_git(self.repo, "add", "h_nuevo.txt")
        sh_git(self.repo, "commit", "-q", "-m", "de H sin subir", "--", "h_nuevo.txt")
        res = sh_mod.chequeo_cierre(str(self.repo))
        self.assertTrue(any(ok is False and "commit local" in t for ok, t in res), res)
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-m"
        ok, lineas = sh_mod.recibir("h001")
        self.assertFalse(ok)
        self.assertTrue(any("commit local" in x for x in lineas), lineas)

    def test_continuacion_abierta_por_cerrar_es_normal(self):
        self.sesion("m001", "cli-m", "Coordinadora")
        self.sesion("c001", "cli-c", "Serie - 06", spawnedFrom={"sessionId": "m001", "sideSession": True, "sharedFolder": True},
                    lineageDetached=True)
        (self.cfg / "projects" / "p1" / "cli-c.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": "Ejecutá la skill /arrancar en esta carpeta."}}) + "\n", encoding="utf-8")
        os.environ["CLAUDE_CODE_SESSION_ID"] = "cli-c"
        self.assertEqual(sh_mod.detectar()["modo"], "normal")

if __name__ == "__main__":
    unittest.main()
