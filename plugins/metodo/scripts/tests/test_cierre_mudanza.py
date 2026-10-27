"""test_cierre_mudanza.py — pruebas completas de cierre_estado.py y cierre-mudanza.py.

Usa exclusivamente carpetas temporales (tempfile) y metadatos de sesiones falsos
a través de CLAUDE_SESIONES_DIR. Nunca toca la configuración real ni las sesiones de la app.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent  # plugins/metodo/scripts
sys.path.insert(0, str(AQUI))

import cartas  # noqa: E402
import cierre_estado  # noqa: E402
import sesiones_hijas as hs  # noqa: E402


class TestCierreMudanza(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(os.path.realpath(self._tmp.name))
        self.raiz = self.t / "sesiones"
        (self.raiz / "a" / "b").mkdir(parents=True)
        self.carpeta = self.t / "proyecto"
        self.carpeta.mkdir(parents=True)
        os.environ["CLAUDE_SESIONES_DIR"] = str(self.raiz)

    def tearDown(self):
        os.environ.pop("CLAUDE_SESIONES_DIR", None)
        try:
            self._tmp.cleanup()
        except OSError:  # Windows: git deja el repo temporal tomado un instante; es solo limpieza
            pass

    def sesion(self, sid, titulo, **kw):
        """Crea o actualiza una sesión falsa en el directorio de sesiones simulado."""
        d = {
            "sessionId": sid,
            "cliSessionId": "cli-" + sid,
            "title": titulo,
            "cwd": str(self.carpeta),
            "lastActivityAt": int(time.time() * 1000),
            **kw,
        }
        p = self.raiz / "a" / "b" / f"local_{sid}.json"
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d

    def reanudar(self, texto="Contenido", mtime=None):
        """Crea o actualiza REANUDAR.md en la carpeta con mtime específico opcional."""
        d = self.carpeta / ".claude" / "prompts"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "REANUDAR.md"
        f.write_text(texto, encoding="utf-8")
        if mtime is not None:
            os.utime(str(f), (mtime, mtime))
        return f

    def correr_cli(self, *args, env=None):
        """Ejecuta cierre-mudanza.py mediante subprocess (salida siempre en UTF-8)."""
        cmd = [sys.executable, str(AQUI / "cierre-mudanza.py"), *args]
        e = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")}
        e.update({"CLAUDE_SESIONES_DIR": str(self.raiz), "PYTHONIOENCODING": "utf-8", **(env or {})})
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(self.carpeta), env=e)
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    def test_ciclo_completo(self):
        """Ciclo completo: congelar → abierta → guardado → hijas → archivar verificando cada ✓/✗."""
        vieja = self.sesion("local_vieja", "Vieja principal")
        sucesora = self.sesion(
            "local_sucesora",
            "Sucesora principal",
            spawnedFrom={"sessionId": "local_vieja"},
            lineageDetached=True,
        )
        h1 = self.sesion(
            "local_h1",
            "Hija terminada",
            spawnedFrom={"sessionId": "local_vieja"},
            lastActivityAt=0,
        )
        h2 = self.sesion(
            "local_h2",
            "Hija esperando",
            spawnedFrom={"sessionId": "local_vieja"},
            prs=[{"state": "OPEN"}],
            lastActivityAt=0,
        )
        h3 = self.sesion(
            "local_h3",
            "Hija trabajando",
            spawnedFrom={"sessionId": "local_vieja"},
            lastActivityAt=int(time.time() * 1000),
            lineageDetached=False,
        )

        # 1. Congelar
        rc, out, _ = self.correr_cli("congelar", env={"CLAUDE_SESSION_ID": "cli-local_vieja"})
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("✓"))
        d = cierre_estado.leer(str(self.carpeta))
        self.assertIsNotNone(d)
        self.assertEqual(d["paso"], "congelado")
        self.assertEqual(d["vieja"], "local_vieja")

        # 2. Abierta
        rc, out, _ = self.correr_cli("abierta", "local_sucesora")
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("✓"))
        d = cierre_estado.leer(str(self.carpeta))
        self.assertEqual(d["paso"], "abierta")
        self.assertEqual(d["sucesora"], "local_sucesora")

        # 3. Guardado sin REANUDAR nuevo falla
        rc, out, _ = self.correr_cli("guardado")
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith("✗"))

        # Actualizar REANUDAR.md con fecha fresca
        self.reanudar("Nuevo contenido", mtime=d["desde"] + 5)
        rc, out, _ = self.correr_cli("guardado")
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("✓"))
        d = cierre_estado.leer(str(self.carpeta))
        self.assertEqual(d["paso"], "guardado")

        # 4. Hijas con pendientes falla y muestra viñetas
        rc, out, _ = self.correr_cli("hijas")
        self.assertEqual(rc, 1)
        self.assertIn("• ", out)
        self.assertIn("✗ ", out)

        # Resolver h1 y h2 archivándolas
        self.sesion("local_h1", "Hija terminada", isArchived=True)
        self.sesion("local_h2", "Hija esperando", isArchived=True)

        # h3 sigue trabajando pero colgada (sin lineageDetached) -> aún falla
        rc, out, _ = self.correr_cli("hijas")
        self.assertEqual(rc, 1)
        self.assertIn("colgada", out)

        # Independizar h3 (lineageDetached=True)
        self.sesion(
            "local_h3",
            "Hija trabajando",
            spawnedFrom={"sessionId": "local_vieja"},
            lastActivityAt=int(time.time() * 1000),
            lineageDetached=True,
        )
        rc, out, _ = self.correr_cli("hijas")
        self.assertEqual(rc, 0)
        self.assertTrue(out.splitlines()[-1].startswith("✓"))
        d = cierre_estado.leer(str(self.carpeta))
        self.assertEqual(d["paso"], "hijas")

        # 5. Archivar
        rc, out, _ = self.correr_cli("archivar")
        self.assertEqual(rc, 0)
        self.assertIn('✓ Ahora sí: archive_session("self") y terminá tu respuesta.', out)
        d = cierre_estado.leer(str(self.carpeta))
        self.assertEqual(d["paso"], "archivando")

    def test_congelar_sin_saber_la_sesion_pide_el_id_y_con_vieja_funciona(self):
        """Sin la variable de sesión no se adivina: pide --vieja <id>; con ese dato congela igual."""
        self.sesion("local_vieja", "Vieja")
        self.sesion("local_otra", "Otra")
        rc, out, _ = self.correr_cli("congelar")
        self.assertEqual(rc, 1)
        self.assertIn("--vieja", out)
        self.assertIsNone(cierre_estado.leer(str(self.carpeta)))
        rc, out, _ = self.correr_cli("congelar", "--vieja", "local_vieja")
        self.assertEqual(rc, 0)
        self.assertEqual(cierre_estado.leer(str(self.carpeta))["vieja"], "local_vieja")

    def test_estado_sin_datos_de_la_app_no_da_por_completa_la_mudanza(self):
        """Sin sesiones en disco (terminal, otra máquina) no se puede saber si la vieja se archivó: no se adivina."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.assertFalse(cierre_estado.completar(str(self.carpeta), []))
        self.assertEqual(cierre_estado.leer(str(self.carpeta))["paso"], "congelado")

    def test_abierta_sucesora_colgada(self):
        """Marcar abierta con sucesora colgada devuelve ✗ con motivo de detach."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.sesion("local_colgada", "Sucesora colgada", spawnedFrom={"sessionId": "local_vieja"}, lineageDetached=False)
        ses = hs.cargar()

        ok, motivo = cierre_estado.marcar_abierta(str(self.carpeta), "local_colgada", ses)
        self.assertFalse(ok)
        self.assertIn('detach_session("local_colgada")', motivo)
        self.assertIn("sigue colgada de la vieja", motivo)

    def test_hijas_ignora_las_ya_soltadas_y_sigue_frenando_las_vivas(self):
        """Una sesión soltada con detach_session ya no es hija (ni sus propias hijas); las colgadas siguen contando."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        ant = int(time.time() * 1000) - 3_600_000
        self.sesion("local_caja", "Caja permanente", spawnedFrom={"sessionId": "local_vieja"}, lineageDetached=True, lastActivityAt=ant)
        self.sesion("local_nieta", "Hija de la caja", spawnedFrom={"sessionId": "local_caja"}, lastActivityAt=ant)
        ses = hs.cargar()
        self.assertEqual(cierre_estado.hijas_pendientes(str(self.carpeta), ses), [])

        # soltada con PR abierto: tampoco cuenta (igual que sesiones_hijas.hijas_de); lo decide quien la soltó
        self.sesion("local_pr", "Soltada con PR", spawnedFrom={"sessionId": "local_vieja"}, lineageDetached=True, prs=[{"state": "OPEN"}], lastActivityAt=ant)
        self.sesion("local_viva", "Hija colgada", spawnedFrom={"sessionId": "local_vieja"}, lastActivityAt=ant)
        ids = [h["id"] for h in cierre_estado.hijas_pendientes(str(self.carpeta), hs.cargar())]
        self.assertEqual(ids, ["local_viva"])

    def test_guardado_sin_reanudar_nuevo(self):
        """Guardado sin REANUDAR fresco devuelve ✗."""
        d = cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.sesion("local_suc", "Sucesora", lineageDetached=True)
        cierre_estado.marcar_abierta(str(self.carpeta), "local_suc", hs.cargar())

        # Sin archivo
        ok, motivo = cierre_estado.marcar_guardado(str(self.carpeta))
        self.assertFalse(ok)
        self.assertIn("no existe", motivo)

        # Con mtime anterior a 'desde'
        self.reanudar("Viejo", mtime=d["desde"] - 10)
        ok, motivo = cierre_estado.marcar_guardado(str(self.carpeta))
        self.assertFalse(ok)
        self.assertIn("el REANUDAR.md no se actualizó desde que se congeló", motivo)

    def test_guardado_acepta_el_reanudar_de_la_raiz_o_de_prompts(self):
        """/cerrar deja el REANUDAR.md en la raíz de la carpeta; también vale .claude/prompts/."""
        d = cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.sesion("local_suc", "Sucesora", lineageDetached=True)
        cierre_estado.marcar_abierta(str(self.carpeta), "local_suc", hs.cargar())
        raiz = self.carpeta / "REANUDAR.md"
        raiz.write_text("de la raíz", encoding="utf-8")
        os.utime(str(raiz), (d["desde"] + 5, d["desde"] + 5))
        ok, motivo = cierre_estado.marcar_guardado(str(self.carpeta))
        self.assertTrue(ok, motivo)

    def test_saltar_paso_error(self):
        """Saltarse pasos en orden da error claro."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        # Intentar saltar directamente a guardado
        ok, motivo = cierre_estado.marcar_guardado(str(self.carpeta))
        self.assertFalse(ok)
        self.assertIn("abierta", motivo)

        # Intentar saltar directamente a hijas
        ok, motivo = cierre_estado.marcar_hijas(str(self.carpeta), hs.cargar())
        self.assertFalse(ok)
        self.assertIn("guardado", motivo)

        # Intentar saltar directamente a archivando
        ok, motivo = cierre_estado.marcar_archivando(str(self.carpeta))
        self.assertFalse(ok)
        self.assertIn("hijas", motivo)

        # Vía CLI
        rc, out, _ = self.correr_cli("guardado")
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith("✗"))

    def test_congelar_dos_veces_idempotente_y_otra_vieja_value_error(self):
        """Congelar con la misma vieja es idempotente; con otra lanza ValueError."""
        d1 = cierre_estado.congelar(str(self.carpeta), "local_v1")
        d2 = cierre_estado.congelar(str(self.carpeta), "local_v1")
        self.assertEqual(d1, d2)

        with self.assertRaises(ValueError) as ctx:
            cierre_estado.congelar(str(self.carpeta), "local_v2")
        self.assertIn("ya hay un cierre en curso de local_v1", str(ctx.exception))

    def test_estado_mas_24h_vigente_false(self):
        """Un estado de más de 24 horas no está vigente."""
        hace_25h = time.time() - 25 * 3600
        d = {
            "vieja": "local_v",
            "sucesora": None,
            "paso": "congelado",
            "desde": hace_25h,
            "carpeta": str(self.carpeta),
        }
        self.assertFalse(cierre_estado.vigente(d))

        # Estado en 'completo' tampoco está vigente
        d_completo = {
            "vieja": "local_v",
            "sucesora": "local_s",
            "paso": "completo",
            "desde": time.time(),
            "carpeta": str(self.carpeta),
        }
        self.assertFalse(cierre_estado.vigente(d_completo))

    def test_json_roto_leer_none(self):
        """JSON roto o campos faltantes hacen que leer devuelva None sin lanzar excepciones."""
        ruta_json = cierre_estado.ruta(str(self.carpeta))
        os.makedirs(os.path.dirname(ruta_json), exist_ok=True)

        with open(ruta_json, "w", encoding="utf-8") as f:
            f.write("{ json inválido")
        self.assertIsNone(cierre_estado.leer(str(self.carpeta)))

        # Campos faltantes
        with open(ruta_json, "w", encoding="utf-8") as f:
            f.write(json.dumps({"vieja": "v1"}))
        self.assertIsNone(cierre_estado.leer(str(self.carpeta)))

    def test_completar_cuando_vieja_archivada(self):
        """Completar devuelve True y pasa a 'completo' si la vieja figura archivada."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.sesion("local_vieja", "Vieja Viva", isArchived=False)
        ses = hs.cargar()

        # Con la vieja viva devuelve False
        self.assertFalse(cierre_estado.completar(str(self.carpeta), ses))

        # Con la vieja archivada devuelve True y actualiza a completo
        self.sesion("local_vieja", "Vieja Archivada", isArchived=True)
        ses = hs.cargar()
        self.assertTrue(cierre_estado.completar(str(self.carpeta), ses))
        d = cierre_estado.leer(str(self.carpeta))
        self.assertEqual(d["paso"], "completo")

    def test_hijas_pendientes_acciones_y_nietas(self):
        """hijas_pendientes recorre nietas y asigna la acción adecuada por estado."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        # Hija intermedia archivada pero con una nieta viva
        self.sesion("local_hija_intermedia", "Hija Intermedia", spawnedFrom={"sessionId": "local_vieja"}, isArchived=True)
        self.sesion(
            "local_nieta",
            "Nieta Viva",
            spawnedFrom={"sessionId": "local_hija_intermedia"},
            isArchived=False,
            lastActivityAt=0,
        )

        # Hija esperando con PR
        self.sesion(
            "local_esperando",
            "Hija Esperando",
            spawnedFrom={"sessionId": "local_vieja"},
            prs=[{"state": "OPEN"}],
            lastActivityAt=0,
        )

        # Hija trabajando
        self.sesion(
            "local_trabajando",
            "Hija Trabajando",
            spawnedFrom={"sessionId": "local_vieja"},
            lastActivityAt=int(time.time() * 1000),
        )

        pend = cierre_estado.hijas_pendientes(str(self.carpeta), hs.cargar())
        ids = {h["id"] for h in pend}
        self.assertIn("local_nieta", ids)
        self.assertIn("local_esperando", ids)
        self.assertIn("local_trabajando", ids)
        self.assertNotIn("local_hija_intermedia", ids)

        # Verificar textos de acción
        h_nieta = next(h for h in pend if h["id"] == "local_nieta")
        self.assertEqual(h_nieta["estado"], "terminada")
        self.assertIn('archive_session("local_nieta")', h_nieta["accion"])

        h_esp = next(h for h in pend if h["id"] == "local_esperando")
        self.assertEqual(h_esp["estado"], "esperando")
        self.assertIn("SendMessage a local_esperando", h_esp["accion"])
        self.assertIn("cartas.py", h_esp["accion"])
        self.assertIn("dejar", h_esp["accion"])
        self.assertIn("archive_session", h_esp["accion"])

        h_trab = next(h for h in pend if h["id"] == "local_trabajando")
        self.assertEqual(h_trab["estado"], "trabajando")
        self.assertIn('detach_session("local_trabajando")', h_trab["accion"])
        self.assertIn("cartas.py", h_trab["accion"])
        self.assertIn("dejar", h_trab["accion"])

    def test_retomar_y_estado_paso_exacto(self):
        """'retomar' y 'estado' imprimen el paso exacto si hay cierre vigente o 'Sin cierre en curso.'."""
        # Sin cierre
        rc, out, _ = self.correr_cli("retomar")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "Sin cierre en curso.")

        # Con cierre cortado en 'abierta'
        self.sesion("local_vieja", "Vieja")
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.sesion("local_suc", "Sucesora", lineageDetached=True)
        cierre_estado.marcar_abierta(str(self.carpeta), "local_suc", hs.cargar())

        rc, out, _ = self.correr_cli("retomar")
        self.assertEqual(rc, 0)
        self.assertIn("Paso actual: abierta", out)
        self.assertIn("REANUDAR.md", out)

        rc, out, _ = self.correr_cli("estado")
        self.assertEqual(rc, 0)
        self.assertIn("Paso actual: abierta", out)

    def test_cancelar_descongela_y_congelar_pisa_una_vieja_muerta(self):
        """cancelar deja la carpeta libre; y un cierre colgado de una vieja ya archivada no traba el siguiente."""
        self.sesion("local_a", "A", isArchived=True)
        self.sesion("local_c", "C")
        cierre_estado.congelar(str(self.carpeta), "local_a")
        self.assertTrue(cierre_estado.cancelar(str(self.carpeta)))
        self.assertFalse(cierre_estado.vigente(cierre_estado.leer(str(self.carpeta))))
        self.assertFalse(cierre_estado.cancelar(str(self.carpeta)))
        cierre_estado.congelar(str(self.carpeta), "local_a")  # queda colgado, la vieja ya murió
        d = cierre_estado.congelar(str(self.carpeta), "local_c", hs.cargar())
        self.assertEqual(d["vieja"], "local_c")
        with self.assertRaises(ValueError):  # sin ses no puede saber que murió
            cierre_estado.congelar(str(self.carpeta), "local_z")

    def test_congelar_no_deja_cartas(self):
        """Congelar no ensucia las cartas: son solo de quien escribe."""
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        self.assertEqual(cartas.pendientes(str(self.carpeta)), [])

    def test_congelar_de_la_sucesora_no_lo_traba_el_cierre_anterior_sin_completar(self):
        """Si la mudanza anterior nunca llegó a 'completo', la sucesora igual puede cerrar la próxima vez."""
        d = cierre_estado.congelar(str(self.carpeta), "local_vieja")
        d["sucesora"] = "local_nueva"
        d["paso"] = "archivando"
        cierre_estado.escribir(str(self.carpeta), d)
        d2 = cierre_estado.congelar(str(self.carpeta), "local_nueva")
        self.assertEqual(d2["vieja"], "local_nueva")
        self.assertEqual(d2["paso"], "congelado")
        with self.assertRaises(ValueError):
            cierre_estado.congelar(str(self.carpeta), "local_otra")

    def test_hija_terminada_con_trabajo_sin_subir_no_se_archiva(self):
        """Una hija quieta pero con cambios sin commitear en su carpeta propia frena el paso 'hijas'."""
        import subprocess as sp
        wt = self.t / "wt_hija"
        wt.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        sp.run(["git", "init", "-q", str(wt)], check=True, env=env)
        (wt / "a.txt").write_text("sin commitear")
        self.sesion("local_vieja", "Vieja")
        self.sesion("local_nueva", "Nueva", lineageDetached=True)
        self.sesion("local_hija", "Hija", spawnedFrom={"sessionId": "local_vieja"}, lastActivityAt=0,
                    worktreePath=str(wt))
        d = cierre_estado.congelar(str(self.carpeta), "local_vieja")
        d["sucesora"] = "local_nueva"
        d["paso"] = "guardado"
        cierre_estado.escribir(str(self.carpeta), d)
        pend = cierre_estado.hijas_pendientes(str(self.carpeta), hs.cargar())
        self.assertEqual(pend[0]["estado"], "terminada")
        self.assertTrue(pend[0]["bloqueos"])
        self.assertIn("SendMessage", pend[0]["accion"])
        ok, motivo = cierre_estado.marcar_hijas(str(self.carpeta), hs.cargar())
        self.assertFalse(ok)
        self.assertIn("sin resolver", motivo)


if __name__ == "__main__":
    unittest.main()
