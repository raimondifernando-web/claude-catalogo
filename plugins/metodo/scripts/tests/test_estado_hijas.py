"""Pruebas del estado de una sesión hija (sesiones_hijas.estado, la definición única del cierre de sesiones).

Mide el estado de una sesión hija ('trabajando' | 'esperando' | 'terminada')
únicamente a partir de sus metadatos (dict `s` de local_*.json), sin red ni git.
Prioridad: archivada > trabajando > esperando > terminada.
"""
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent  # plugins/metodo/scripts
sys.path.insert(0, str(AQUI))
import sesiones_hijas as hs


class TestArchivadaConPR(unittest.TestCase):
    """archivada con PR → terminada (la prioridad de archivada está por encima de esperando)."""

    def test_archivada_con_pr_terminada(self):
        ahora = 1700000000
        s = {
            "sessionId": "h1",
            "isArchived": True,
            "prs": [{"prNumber": 1, "state": "OPEN"}],
            "lastActivityAt": int(ahora * 1000),
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "terminada")


class TestRecienteSinResumen(unittest.TestCase):
    """reciente sin resumen → trabajando."""

    def test_reciente_sin_resumen_trabajando(self):
        ahora = 1700000000
        s = {
            "sessionId": "h2",
            "isArchived": False,
            "lastActivityAt": int((ahora - 60) * 1000),  # hace 1 minuto
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "trabajando")


class TestRecienteConResumenListoSinPR(unittest.TestCase):
    """reciente con resumen listo y sin PR → terminada."""

    def test_reciente_con_resumen_listo_sin_pr_terminada(self):
        ahora = 1700000000
        s = {
            "sessionId": "h3",
            "isArchived": False,
            "lastActivityAt": int((ahora - 60) * 1000),
            "postTurnSummary": "Resumen del turno listo",
            "postTurnSummaryFor": "asistente-uuid-1",
            "lastAssistantUuid": "asistente-uuid-1",
            "prs": [],
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "terminada")


class TestRecienteConResumenListoYPR(unittest.TestCase):
    """reciente con resumen listo y PR abierto → esperando."""

    def test_reciente_con_resumen_listo_y_pr_abierto_esperando(self):
        ahora = 1700000000
        s = {
            "sessionId": "h4",
            "isArchived": False,
            "lastActivityAt": int((ahora - 60) * 1000),
            "postTurnSummary": "Resumen listo",
            "postTurnSummaryFor": "asistente-uuid-2",
            "lastAssistantUuid": "asistente-uuid-2",
            "prs": [{"prNumber": 10, "state": "OPEN"}],
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "esperando")


class TestViejaSinResumenConPROPEN(unittest.TestCase):
    """vieja sin resumen y con PR OPEN → esperando."""

    def test_vieja_sin_resumen_con_pr_open_esperando(self):
        ahora = 1700000000
        s = {
            "sessionId": "h5",
            "isArchived": False,
            "lastActivityAt": int((ahora - 2 * hs.ACTIVA_S) * 1000),  # vieja
            "prs": [{"prNumber": 12, "state": "OPEN"}],
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "esperando")


class TestViejaConPRMERGED(unittest.TestCase):
    """vieja con PR MERGED → terminada."""

    def test_vieja_con_pr_merged_terminada(self):
        ahora = 1700000000
        s = {
            "sessionId": "h6",
            "isArchived": False,
            "lastActivityAt": int((ahora - 2 * hs.ACTIVA_S) * 1000),  # vieja
            "prs": [{"prNumber": 12, "state": "MERGED"}],
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "terminada")


class TestViejaConSideSessionReportOwed(unittest.TestCase):
    """vieja con sideSessionReportOwed → esperando."""

    def test_vieja_con_side_session_report_owed_esperando(self):
        ahora = 1700000000
        s = {
            "sessionId": "h7",
            "isArchived": False,
            "lastActivityAt": int((ahora - 2 * hs.ACTIVA_S) * 1000),  # vieja
            "sideSessionReportOwed": True,
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "esperando")


class TestSinLastActivityAt(unittest.TestCase):
    """sin lastActivityAt → no revienta (se trata como vieja = 0)."""

    def test_sin_last_activity_at_no_revienta(self):
        ahora = 1700000000
        s_quieta = {
            "sessionId": "h8a",
            "isArchived": False,
        }
        self.assertEqual(hs.estado(s_quieta, ahora=ahora), "terminada")

        s_esperando = {
            "sessionId": "h8b",
            "isArchived": False,
            "sideSessionReportOwed": True,
        }
        self.assertEqual(hs.estado(s_esperando, ahora=ahora), "esperando")


class TestRecienteArchivada(unittest.TestCase):
    """reciente + archivada → terminada."""

    def test_reciente_archivada_terminada(self):
        ahora = 1700000000
        s = {
            "sessionId": "h9",
            "isArchived": True,
            "lastActivityAt": int(ahora * 1000),
        }
        self.assertEqual(hs.estado(s, ahora=ahora), "terminada")


if __name__ == "__main__":
    unittest.main()
