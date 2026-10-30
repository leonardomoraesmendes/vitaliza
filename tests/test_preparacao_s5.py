"""Verificações independentes das regras que podem distorcer o diagnóstico."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from preparar_diagnostico_s5 import (
    active_at, build_intervals, clean_activities, historical_panel,
    intended_days, money_cents, timestamps,
)


class PreparacaoS5Tests(unittest.TestCase):
    def test_utc_crosses_month_in_brasilia(self):
        ts = timestamps(pd.Series(["2026-10-01T02:59:59Z", "2026-10-01T03:00:00Z", "2026-09-30 23:59:59"]))
        self.assertEqual(ts.dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
                         ["2026-09-30 23:59:59", "2026-10-01 00:00:00", "2026-09-30 23:59:59"])

    def test_money_formats_and_missing(self):
        out = money_cents(pd.Series(["R$ 34,90", "34.90", "239.9", None]))
        self.assertEqual(out.iloc[:3].tolist(), [3490, 3490, 23990])
        self.assertTrue(pd.isna(out.iloc[3]))

    def test_days_only_explicit_values(self):
        out = intended_days(pd.Series(["3x", "4 vezes", "todos", "99", None, "3 ou 4"]))
        self.assertEqual(out.iloc[:3].tolist(), [3, 4, 7])
        self.assertTrue(out.iloc[3:].isna().all())

    def test_active_interval_includes_start_excludes_end(self):
        intervals = pd.DataFrame({"user_id": ["a", "b"], "inicio_ts": pd.to_datetime(["2026-01-01", "2026-02-01"]),
                                  "fim_ts": pd.to_datetime(["2026-02-01", None])})
        self.assertEqual(active_at(intervals, pd.Timestamp("2026-02-01")).user_id.tolist(), ["b"])

    def test_pre_log_seed_but_later_start_must_come_from_event(self):
        subs = pd.DataFrame({"user_id": ["old", "new"], "inicio": ["2020-01-01", "2025-01-01"],
                             "plano_atual": ["anual", "mensal"], "canal_cobranca": ["app_store", "web_pix"]})
        events = pd.DataFrame({"user_id": ["old", "old", "new"],
            "ts": pd.to_datetime(["2025-02-01", "2025-03-01", "2025-01-02"]),
            "evento": ["renovacao_automatica_desligada", "assinatura_expirada", "assinatura_iniciada"],
            "plano": ["anual", "anual", "mensal"], "canal_cobranca": ["app_store", "app_store", "web_pix"]})
        intervals = build_intervals(subs, events)
        self.assertIn("old", set(active_at(intervals, pd.Timestamp("2025-02-15")).user_id))
        self.assertNotIn("new", set(active_at(intervals, pd.Timestamp("2025-01-01")).user_id))
        self.assertEqual(intervals.set_index("user_id").loc["new", "inicio_ts"], pd.Timestamp("2025-01-02"))

    def test_unmatched_expiration_fails(self):
        subs = pd.DataFrame(columns=["user_id", "inicio", "plano_atual", "canal_cobranca"])
        events = pd.DataFrame({"user_id": ["x"], "ts": pd.to_datetime(["2026-01-01"]),
                              "evento": ["assinatura_expirada"], "plano": ["mensal"], "canal_cobranca": ["web_pix"]})
        with self.assertRaises(AssertionError):
            build_intervals(subs, events)

    def example_panel(self):
        intervals = pd.DataFrame({"user_id": ["old", "short"],
            "inicio_ts": pd.to_datetime(["2024-01-01", "2025-02-05"]),
            "fim_ts": pd.to_datetime([None, "2025-02-20"]),
            "plano": ["mensal", "mensal"], "canal_cobranca": ["web_pix", "web_pix"]})
        usage = pd.DataFrame(columns=["user_id", "mes", "atividades", "minutos", "sessoes_app"])
        return historical_panel(intervals, usage)

    def test_same_month_start_and_end_not_in_churn_denominator(self):
        panel = self.example_panel()
        self.assertNotIn("short", set(panel.user_id))
        self.assertFalse(panel.saiu_mes.any())

    def test_missing_usage_only_zero_inside_coverage(self):
        panel = self.example_panel().set_index("mes")
        self.assertTrue(pd.isna(panel.loc["2025-01", "atividades_mes_anterior"]))
        self.assertEqual(panel.loc["2025-02", "atividades_mes_anterior"], 0)

    def test_2025_missing_app_sessions_not_fabricated(self):
        panel = self.example_panel().set_index("mes")
        self.assertTrue(pd.isna(panel.loc["2025-02", "sessoes_mes_anterior"]))
        self.assertEqual(panel.loc["2026-02", "sessoes_mes_anterior"], 0)

    def test_garmin_copy_is_removed_after_timezone_conversion(self):
        a = pd.DataFrame({"atividade_id": ["app1", "watch1", "zero", "future"], "user_id": ["u"]*4,
            "inicio": ["2026-09-01 09:00:00", "2026-09-01 12:00:00", "2026-09-02 09:00:00", "2026-10-01 09:00:00"],
            "origem": ["app", "garmin", "app", "app"], "tipo": ["corrida"]*4,
            "duracao_min": [30, 30, 0, 30], "ritmo_min_km": [5, 5, 5, 5], "distancia_km": [6, 6, 300, 6]})
        clean, stats = clean_activities(a)
        self.assertEqual(set(clean.atividade_id), {"watch1", "zero"})
        self.assertEqual(stats["copias_app_removidas"], 1)
        self.assertTrue(clean.set_index("atividade_id").loc["zero", "duracao_invalida"])
        self.assertTrue(clean.set_index("atividade_id").loc["zero", "distancia_invalida"])


if __name__ == "__main__":
    unittest.main()
