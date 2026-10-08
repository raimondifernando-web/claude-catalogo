"""Tests del vigía de la documentación oficial (plugin metodo).
Solo biblioteca estándar, SIN red (fuentes simuladas). Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_docs_vigia.py' -v
"""
import unittest
from datetime import date

from test_radar import Base, FU, R, radar_de_prueba


def fuentes_de(**k):
    d = {"modelsdev": {}, "openrouter": {}, "litellm": {}, "arena": {}, "paginas": {}, "guias": {}}
    d.update(k)
    return d


def radar_con_docs(**extra):
    r = radar_de_prueba()
    fa = r.setdefault("fuentes_auto", {})
    fa["docs"] = {
        "indice": {
            "url": "https://code.claude.com/docs/llms.txt",
            "conocidas": ["pagina-%d" % i for i in range(50)],
            "nuevas": ["pagina-0 2026-10-01"],
        },
        "paginas": {
            "mods": {
                "titulo": "Mods",
                "url": "https://code.claude.com/docs/en/plugins/mods/overview.md",
                "hash": "1111222233334444",
                "cambio": "2026-10-01",
            }
        },
        "changelogs": {
            "claude_code": {
                "proveedor": "Anthropic",
                "titulo": "Claude Code",
                "url": "https://github.com/anthropics/claude-code/releases.atom",
                "tipo": "atom_estable",
                "version": "2.1.295",
                "paso": 25,
                "cambio": "2026-10-01",
            },
            "codex": {
                "proveedor": "OpenAI",
                "titulo": "Codex",
                "url": "https://github.com/openai/codex/releases.atom",
                "tipo": "atom_estable",
                "version": "0.63.0",
                "corte": 2,
                "cambio": "2026-10-01",
            },
        },
    }
    r.update(extra)
    return r


class TestDocsVigia(Base):
    def test_linea_base_sin_motivos_de_nuevas(self):
        radar = radar_con_docs()
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = []
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = []
        slugs_50 = ["pagina-%d" % i for i in range(50)]
        fuentes = fuentes_de(docs={"indice": slugs_50})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertEqual(motivos[0], "Línea base del índice de la doc oficial de Claude Code: 50 páginas.")
        self.assertFalse(any("Páginas nuevas" in m for m in motivos))
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["indice"]["conocidas"], sorted(slugs_50))
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["indice"]["nuevas"], [])

    def test_pagina_nueva_en_el_indice_motivo_y_entrada_en_nuevas_con_fecha(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(50)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = []
        nuevos_slugs = ["plugins/mods/overview", "sub-agents"]
        fuentes = fuentes_de(docs={"indice": slugs_base + nuevos_slugs})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertIn("Páginas nuevas en la doc oficial de Claude Code: plugins/mods/overview, sub-agents. Revisar si hay una función que sumar a plugins/metodo/radar/FUNCIONES.md.", motivos[0])
        self.assertIn("plugins/mods/overview 2026-10-08", nuevo["fuentes_auto"]["docs"]["indice"]["nuevas"])
        self.assertIn("sub-agents 2026-10-08", nuevo["fuentes_auto"]["docs"]["indice"]["nuevas"])
        self.assertIn("plugins/mods/overview", nuevo["fuentes_auto"]["docs"]["indice"]["conocidas"])
        self.assertIn("sub-agents", nuevo["fuentes_auto"]["docs"]["indice"]["conocidas"])

    def test_slugs_que_desaparecen_no_avisan(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(52)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        # Desaparecen pagina-0 y pagina-1, pero quedan 50 slugs
        fuentes = fuentes_de(docs={"indice": slugs_base[2:]})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)
        self.assertIn("pagina-0", radar["fuentes_auto"]["docs"]["indice"]["conocidas"])
        self.assertIn("pagina-1", radar["fuentes_auto"]["docs"]["indice"]["conocidas"])

    def test_slugs_raros_se_ignoran(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(50)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        raros = ["slug con espacios", "slug\nraro", "x" * 121, "slug*invalido", ""]
        fuentes = fuentes_de(docs={"indice": slugs_base + raros})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)
        for r in raros:
            self.assertNotIn(r, radar["fuentes_auto"]["docs"]["indice"]["conocidas"])

    def test_whats_new_y_changelog_no_cuentan(self):
        lineas = ["# llms.txt falso"]
        for i in range(50):
            lineas.append("- [P%d](https://code.claude.com/docs/en/pagina-%d.md)" % (i, i))
        lineas.append("- [Changelog](https://code.claude.com/docs/en/changelog.md)")
        lineas.append("- [Whats New Sep](https://code.claude.com/docs/en/whats-new/sep-2026.md)")
        lineas.append("- [Whats New Oct](https://code.claude.com/docs/en/whats-new/october-2026.md)")
        texto = "\n".join(lineas)
        slugs = FU.slugs_de_indice(texto)
        self.assertIsNotNone(slugs)
        self.assertEqual(len(slugs), 50)
        self.assertNotIn("changelog", slugs)
        self.assertNotIn("whats-new/sep-2026", slugs)
        self.assertNotIn("whats-new/october-2026", slugs)

    def test_indice_con_menos_de_50_slugs_devuelve_none(self):
        lineas = ["- [P%d](https://code.claude.com/docs/en/p-%d.md)" % (i, i) for i in range(49)]
        texto_49 = "\n".join(lineas)
        self.assertIsNone(FU.slugs_de_indice(texto_49))
        self.assertIsNone(FU.slugs_de_indice(""))
        self.assertIsNone(FU.slugs_de_indice(None))

    def test_poda_de_nuevas_viejas(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(50)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = [
            "pagina-vieja 2026-07-01",      # 99 días antes de 2026-10-08: se poda
            "pagina-reciente 2026-09-20",   # 18 días antes: se conserva
            "pagina-limite 2026-08-09",     # 60 días antes: se conserva
        ]
        # Con una página nueva para que haya motivo y se devuelva nuevo
        fuentes = fuentes_de(docs={"indice": slugs_base + ["pagina-nueva"]})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertTrue(motivos)
        nuevas = nuevo["fuentes_auto"]["docs"]["indice"]["nuevas"]
        self.assertNotIn("pagina-vieja 2026-07-01", nuevas)
        self.assertIn("pagina-reciente 2026-09-20", nuevas)
        self.assertIn("pagina-limite 2026-08-09", nuevas)
        self.assertIn("pagina-nueva 2026-10-08", nuevas)

    def test_poda_sola_sin_otros_cambios_no_abre_pr(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(50)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = ["pagina-vieja 2026-07-01"]
        fuentes = fuentes_de(docs={"indice": slugs_base})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)

    def test_cambio_de_hash_de_una_pagina_motivo_y_cambio(self):
        radar = radar_con_docs()
        fuentes = fuentes_de(docs={"paginas": {"mods": "9999888877776666"}})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertIn("Cambió la página oficial «Mods» (https://code.claude.com/docs/en/plugins/mods/overview.md): rehacer su fila de plugins/metodo/radar/FUNCIONES.md.", motivos[0])
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["paginas"]["mods"]["hash"], "9999888877776666")
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["paginas"]["mods"]["cambio"], "2026-10-08")

    def test_pagina_oficial_linea_base(self):
        radar = radar_con_docs()
        radar["fuentes_auto"]["docs"]["paginas"]["mods"]["hash"] = None
        radar["fuentes_auto"]["docs"]["paginas"]["mods"].pop("cambio", None)
        fuentes = fuentes_de(docs={"paginas": {"mods": "1111222233334444"}})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertIn("Línea base de la página oficial «Mods»: desde acá se avisa si cambia.", motivos[0])
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["paginas"]["mods"]["hash"], "1111222233334444")
        self.assertNotIn("cambio", nuevo["fuentes_auto"]["docs"]["paginas"]["mods"])

    def test_changelog_parche_no_abre_pr_minor_nuevo_si(self):
        radar = radar_con_docs()
        # Parche de Codex (0.63.0 -> 0.63.1 con corte=2): la clave sigue siendo (0, 63)
        fuentes_parche = fuentes_de(docs={"changelogs": {"codex": "0.63.1"}})
        nuevo, motivos = FU.analizar(radar, fuentes_parche, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)
        self.assertEqual(radar["fuentes_auto"]["docs"]["changelogs"]["codex"]["version"], "0.63.0")

        # Minor nuevo de Codex (0.63.0 -> 0.64.0): la clave cambia de (0, 63) a (0, 64)
        fuentes_minor = fuentes_de(docs={"changelogs": {"codex": "0.64.0"}})
        nuevo2, motivos2 = FU.analizar(radar, fuentes_minor, date(2026, 10, 8))
        self.assertEqual(len(motivos2), 1)
        self.assertIn("Nueva versión de «Codex»: antes 0.63.0, ahora 0.64.0: leer qué funciones trae y actualizar plugins/metodo/radar/FUNCIONES.md.", motivos2[0])
        self.assertEqual(nuevo2["fuentes_auto"]["docs"]["changelogs"]["codex"]["version"], "0.64.0")
        self.assertEqual(nuevo2["fuentes_auto"]["docs"]["changelogs"]["codex"]["cambio"], "2026-10-08")

    def test_changelog_retroceso_no_avisa(self):
        radar = radar_con_docs()
        radar["fuentes_auto"]["docs"]["changelogs"]["codex"]["version"] = "0.64.0"
        nuevo, motivos = FU.analizar(radar, fuentes_de(docs={"changelogs": {"codex": "0.63.2"}}), date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)

    def test_changelog_paso_25(self):
        radar = radar_con_docs()
        # Claude Code con version=2.1.295 y paso=25 (clave = (2, 1, 11))
        # 2.1.299: 299 // 25 = 11 -> misma clave, no abre PR
        fuentes_299 = fuentes_de(docs={"changelogs": {"claude_code": "2.1.299"}})
        nuevo, motivos = FU.analizar(radar, fuentes_299, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)

        # 2.1.300: 300 // 25 = 12 -> clave cambia a (2, 1, 12), sí abre PR
        fuentes_300 = fuentes_de(docs={"changelogs": {"claude_code": "2.1.300"}})
        nuevo2, motivos2 = FU.analizar(radar, fuentes_300, date(2026, 10, 8))
        self.assertEqual(len(motivos2), 1)
        self.assertIn("Nueva versión de «Claude Code»: antes 2.1.295, ahora 2.1.300: leer qué funciones trae y actualizar plugins/metodo/radar/FUNCIONES.md.", motivos2[0])
        self.assertEqual(nuevo2["fuentes_auto"]["docs"]["changelogs"]["claude_code"]["version"], "2.1.300")
        self.assertEqual(nuevo2["fuentes_auto"]["docs"]["changelogs"]["claude_code"]["cambio"], "2026-10-08")

    def test_version_de_changelog_atom_y_gemini(self):
        atom_falso = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>rust-v0.163.0-alpha.1</title>
  </entry>
  <entry>
    <title>0.162.0</title>
  </entry>
</feed>"""
        self.assertEqual(FU.version_de_changelog("atom_estable", atom_falso), "0.162.0")

        gemini_falso = "# Latest stable release: v0.63.0\nRelease notes here."
        self.assertEqual(FU.version_de_changelog("gemini_latest", gemini_falso), "0.63.0")

        self.assertIsNone(FU.version_de_changelog("atom_estable", "<feed><title>nightly-build</title></feed>"))
        self.assertIsNone(FU.version_de_changelog("gemini_latest", "Version 1.0.0"))
        self.assertIsNone(FU.version_de_changelog(None, gemini_falso))
        self.assertIsNone(FU.version_de_changelog("desconocido", gemini_falso))

    def test_fuente_caida_none_no_toca_nada(self):
        radar = radar_con_docs()
        fuentes = fuentes_de(docs={"indice": None, "paginas": {"mods": None}, "changelogs": {"codex": None, "claude_code": None}})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)

    def test_analizar_sin_seccion_docs_sigue_funcionando(self):
        radar_sin_docs = radar_de_prueba()
        self.assertNotIn("docs", radar_sin_docs.get("fuentes_auto", {}))
        fuentes_sin_docs = fuentes_de()
        nuevo, motivos = FU.analizar(radar_sin_docs, fuentes_sin_docs, date(2026, 10, 8))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar_sin_docs)
        self.assertNotIn("docs", nuevo.get("fuentes_auto", {}))

    def test_yaml_con_docs_sobrevive_a_volcado_y_carga(self):
        radar = radar_con_docs()
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = [
            "plugins/mods/overview 2026-10-08",
            "sub-agents 2026-10-07",
        ]
        volcado = R.yaml_volcar(radar)
        cargado = R.yaml_cargar(volcado)
        self.assertEqual(cargado["fuentes_auto"]["docs"], radar["fuentes_auto"]["docs"])

    def test_mas_de_8_paginas_nuevas_muestra_y_n_mas(self):
        radar = radar_con_docs()
        slugs_base = ["pagina-%d" % i for i in range(50)]
        radar["fuentes_auto"]["docs"]["indice"]["conocidas"] = list(slugs_base)
        radar["fuentes_auto"]["docs"]["indice"]["nuevas"] = []
        nuevos_10 = ["nueva-%02d" % i for i in range(10)]
        fuentes = fuentes_de(docs={"indice": slugs_base + nuevos_10})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertIn("y 2 más", motivos[0])
        for n in nuevos_10[:8]:
            self.assertIn(n, motivos[0])
        self.assertNotIn("nueva-08", motivos[0])
        self.assertNotIn("nueva-09", motivos[0])

    def test_changelog_linea_base(self):
        radar = radar_con_docs()
        radar["fuentes_auto"]["docs"]["changelogs"]["claude_code"]["version"] = None
        fuentes = fuentes_de(docs={"changelogs": {"claude_code": "2.1.295"}})
        nuevo, motivos = FU.analizar(radar, fuentes, date(2026, 10, 8))
        self.assertEqual(len(motivos), 1)
        self.assertIn("Línea base del registro de cambios de «Claude Code»: v2.1.295.", motivos[0])
        self.assertEqual(nuevo["fuentes_auto"]["docs"]["changelogs"]["claude_code"]["version"], "2.1.295")

    def test_juntar_con_docs_modo_diario_y_semanal(self):
        radar = radar_con_docs()
        avisos = []
        slugs_llms = "\n".join("- [P%d](https://code.claude.com/docs/en/p-%d.md)" % (i, i) for i in range(50))
        html_pagina = "contenido " * 50
        atom_xml = "<feed xmlns=\"http://www.w3.org/2005/Atom\"><entry><title>2.1.295</title></entry></feed>"

        def traer_simulado(url, como="json"):
            if "llms.txt" in url:
                return slugs_llms
            if "overview.md" in url:
                return html_pagina
            if "releases.atom" in url:
                return atom_xml
            raise OSError("no encontrada: " + url)

        # Modo diario: debe levantar docs
        fuentes_diario = FU.juntar(radar, "diario", traer_fn=traer_simulado, avisar=avisos.append)
        self.assertIn("docs", fuentes_diario)
        self.assertEqual(len(fuentes_diario["docs"]["indice"]), 50)
        self.assertIn("mods", fuentes_diario["docs"]["paginas"])
        self.assertIsNotNone(fuentes_diario["docs"]["paginas"]["mods"])
        self.assertEqual(fuentes_diario["docs"]["changelogs"].get("claude_code"), "2.1.295")

        # Modo semanal: NO debe levantar docs
        fuentes_semanal = FU.juntar(radar, "semanal", traer_fn=traer_simulado, avisar=avisos.append)
        self.assertNotIn("docs", fuentes_semanal)

        # Fallo en una fuente: avisa y sigue
        avisos_fallo = []
        def traer_con_fallo(url, como="json"):
            if "llms.txt" in url:
                raise OSError("error de red")
            return traer_simulado(url, como)

        fuentes_con_fallo = FU.juntar(radar, "diario", traer_fn=traer_con_fallo, avisar=avisos_fallo.append)
        self.assertIn("docs", fuentes_con_fallo)
        self.assertIsNone(fuentes_con_fallo["docs"]["indice"])
        self.assertTrue(any("índice de docs" in a for a in avisos_fallo))
        self.assertIn("mods", fuentes_con_fallo["docs"]["paginas"])

    def test_clave_version(self):
        self.assertEqual(FU.clave_version("2.1.295", None, 25), (2, 1, 11))
        self.assertEqual(FU.clave_version("2.1.299", None, 25), (2, 1, 11))
        self.assertEqual(FU.clave_version("2.1.300", None, 25), (2, 1, 12))
        self.assertEqual(FU.clave_version("0.63.0", 2, None), (0, 63))
        self.assertEqual(FU.clave_version("0.63.1", 2, None), (0, 63))
        self.assertEqual(FU.clave_version("0.64.0", 2, None), (0, 64))
        self.assertEqual(FU.clave_version(None), ())
        self.assertEqual(FU.clave_version(""), ())


if __name__ == "__main__":
    unittest.main()
