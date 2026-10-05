"""Проверки расчёта: приведение оценок, множество Парето, веса критериев и метод ЭЛЕКТРА.

Запуск из папки проекта: python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from electre.data import WORD_VALUES, variant_3
from electre.methods import electre, normalize, pareto, rank_weights, ranking, thresholds_for_count


class TestNormalization(unittest.TestCase):
    """Приведение оценок к безразмерному виду."""

    def setUp(self) -> None:
        self.task = variant_3()
        self.normalized = normalize(self.task)

    def test_words_converted_by_scale(self):
        """Словесные оценки заменяются числами шкалы Харрингтона."""
        numeric = self.normalized.numeric
        self.assertEqual(numeric[0][0], WORD_VALUES["средняя"])
        self.assertEqual(numeric[1][4], WORD_VALUES["очень хорошее"])
        self.assertEqual(numeric[2][5], 2.0)

    def test_best_gets_one(self):
        """По каждому критерию лучшая площадка получает единицу."""
        for row in self.normalized.values:
            self.assertAlmostEqual(max(row), 1.0, places=9)

    def test_values_between_zero_and_one(self):
        """Все безразмерные оценки лежат в диапазоне от 0 до 1."""
        for row in self.normalized.values:
            self.assertTrue(all(0.0 < value <= 1.0 for value in row))

    def test_costs_inverted(self):
        """Для затрат меньшее значение даёт большую безразмерную оценку."""
        costs = self.normalized.numeric[2]
        scaled = self.normalized.values[2]
        cheapest = costs.index(min(costs))
        priciest = costs.index(max(costs))
        self.assertAlmostEqual(scaled[cheapest], 1.0, places=9)
        self.assertLess(scaled[priciest], scaled[cheapest])

    def test_known_values(self):
        """Числа совпадают с ручным расчётом по условию варианта 3."""
        self.assertAlmostEqual(self.normalized.values[0][3], 1.0, places=3)        # Пл4, дорожная сеть
        self.assertAlmostEqual(self.normalized.values[1][2], 0.311, places=3)      # Пл3, энергоснабжение
        self.assertAlmostEqual(self.normalized.values[2][0], 0.571, places=3)      # Пл1, затраты


class TestPareto(unittest.TestCase):
    """Отбор Парето-оптимальных площадок."""

    def setUp(self) -> None:
        self.task = variant_3()
        self.normalized = normalize(self.task)
        self.result = pareto(self.normalized)

    def test_first_site_removed(self):
        """Пл1 уступает Пл5 по всем критериям и исключается."""
        self.assertIn(0, self.result.removed)
        self.assertNotIn(0, self.result.kept)
        self.assertIn("Пл5", self.result.reasons[0])

    def test_five_sites_left(self):
        """Во множестве Парето остаётся пять площадок."""
        self.assertEqual(len(self.result.kept), 5)

    def test_kept_sites_not_dominated(self):
        """Ни одна оставшаяся площадка не уступает другой по всем критериям."""
        for j in self.result.kept:
            self.assertFalse(any(self.result.dominance[i][j] for i in range(len(self.task.alternatives))))


class TestWeights(unittest.TestCase):
    """Метод ранга."""

    def test_weights_sum_to_one(self):
        """Сумма весов критериев равна единице."""
        weights = rank_weights(variant_3().expert_scores)
        self.assertAlmostEqual(sum(weights.values), 1.0, places=9)

    def test_costs_are_most_important(self):
        """По оценкам экспертов самый весомый критерий — затраты на подготовку."""
        task = variant_3()
        weights = rank_weights(task.expert_scores)
        heaviest = weights.values.index(max(weights.values))
        self.assertEqual(task.criteria[heaviest].name, "Затраты на подготовку")

    def test_known_weights(self):
        """Веса совпадают с ручным расчётом: 8/23, 6/23 и 9/23."""
        weights = rank_weights(variant_3().expert_scores)
        self.assertAlmostEqual(weights.values[0], 8 / 23, places=6)
        self.assertAlmostEqual(weights.values[1], 6 / 23, places=6)
        self.assertAlmostEqual(weights.values[2], 9 / 23, places=6)


class TestElectre(unittest.TestCase):
    """Индексы согласия и несогласия, ядро альтернатив."""

    def setUp(self) -> None:
        self.task = variant_3()
        self.normalized = normalize(self.task)
        self.pareto = pareto(self.normalized)
        self.weights = rank_weights(self.task.expert_scores)
        self.result = electre(self.normalized, self.weights.values, self.pareto.kept)

    def test_matrix_size(self):
        """Матрицы строятся только по площадкам из множества Парето."""
        self.assertEqual(len(self.result.names), len(self.pareto.kept))
        self.assertEqual(len(self.result.concordance), len(self.pareto.kept))

    def test_indices_in_range(self):
        """Индексы согласия и несогласия лежат в диапазоне от 0 до 1."""
        for a in range(len(self.result.names)):
            for b in range(len(self.result.names)):
                if a == b:
                    continue
                self.assertGreaterEqual(self.result.concordance[a][b], 0.0)
                self.assertLessEqual(self.result.concordance[a][b], 1.0)
                self.assertGreaterEqual(self.result.discordance[a][b], 0.0)
                self.assertLessEqual(self.result.discordance[a][b], 1.0)

    def test_concordance_matches_manual_sum(self):
        """Индекс согласия равен сумме весов критериев, по которым строка не хуже столбца."""
        values = self.normalized.values
        for a, j in enumerate(self.result.indices):
            for b, k in enumerate(self.result.indices):
                if a == b:
                    continue
                manual = sum(self.weights.values[c] for c in range(len(values))
                             if values[c][j] >= values[c][k] - 1e-9)
                self.assertAlmostEqual(self.result.concordance[a][b], manual, places=9)

    def test_discordance_matches_manual_gap(self):
        """Индекс несогласия равен наибольшему отставанию строки от столбца."""
        values = self.normalized.values
        for a, j in enumerate(self.result.indices):
            for b, k in enumerate(self.result.indices):
                if a == b:
                    continue
                gaps = [values[c][k] - values[c][j] for c in range(len(values))
                        if values[c][k] > values[c][j]]
                self.assertAlmostEqual(self.result.discordance[a][b], max(gaps, default=0.0), places=9)

    def test_core_for_variant_3(self):
        """При обычных порогах 0,5 и 0,5 в ядре остаётся одна площадка — Пл5."""
        self.assertEqual(self.result.core_names(), ["Пл5"])

    def test_loose_thresholds_keep_everyone(self):
        """Если пороги ослабить до предела, в ядро попадают все площадки."""
        loose = electre(self.normalized, self.weights.values, self.pareto.kept, 0.0, 1.0)
        self.assertEqual(len(loose.core), len(self.pareto.kept))

    def test_strict_thresholds_empty_core(self):
        """Слишком строгие пороги оставляют ядро пустым."""
        strict = electre(self.normalized, self.weights.values, self.pareto.kept, 0.95, 0.05)
        self.assertEqual(strict.core, [])

    def test_threshold_search(self):
        """Подбор порогов даёт ядро нужного размера."""
        for wanted in (1, 2, 3):
            found = thresholds_for_count(self.result, wanted)
            self.assertIsNotNone(found, f"пороги для {wanted} площадок не найдены")
            checked = electre(self.normalized, self.weights.values, self.pareto.kept, *found)
            self.assertEqual(len(checked.core), wanted)

    def test_ranking_matches_weighted_sum(self):
        """Вспомогательный порядок считается как взвешенная сумма оценок."""
        order = ranking(self.normalized, self.weights.values)
        values = self.normalized.values
        for index, value in order:
            manual = sum(self.weights.values[c] * values[c][index] for c in range(len(values)))
            self.assertAlmostEqual(value, manual, places=9)
        self.assertEqual(order[0][0], 4)  # первой идёт Пл5


if __name__ == "__main__":
    unittest.main()
