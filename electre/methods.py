"""Расчётная часть: приведение оценок, множество Парето, веса критериев и метод ЭЛЕКТРА."""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import Task

EPS = 1e-9


@dataclass
class Normalized:
    """Оценки, приведённые к безразмерному виду."""

    task: Task
    numeric: list[list[float]]        # числовые оценки до нормирования
    values: list[list[float]]         # безразмерные оценки: строка — критерий, столбец — альтернатива
    best: list[float]                 # величина, на которую делили
    comments: list[str]

    def column(self, index: int) -> list[float]:
        """Оценки одной альтернативы по всем критериям."""
        return [row[index] for row in self.values]


def normalize(task: Task) -> Normalized:
    """Шаг 1 метода ЭЛЕКТРА: переход к безразмерному виду.

    Для критериев, где лучше большее значение, оценки делятся на наибольшую.
    Для критериев, где лучше меньшее значение (например, затраты), сначала берётся
    обратная величина, поэтому лучшая площадка получает единицу.
    """
    numeric = task.numeric_values()
    values, best, comments = [], [], []
    for criterion, row in zip(task.criteria, numeric):
        if criterion.maximize:
            top = max(row)
            values.append([value / top for value in row])
            best.append(top)
            comments.append("оценки разделены на лучшую оценку " + f"{top:.2f}".replace(".", ","))
        else:
            low = min(row)
            values.append([low / value for value in row])
            best.append(low)
            comments.append("взято отношение наименьшего значения "
                            + f"{low:g}".replace(".", ",") + " к оценке площадки")
    return Normalized(task=task, numeric=numeric, values=values, best=best, comments=comments)


@dataclass
class ParetoResult:
    """Множество Парето и пояснения, почему альтернативы исключены."""

    kept: list[int]
    removed: list[int]
    reasons: dict[int, str] = field(default_factory=dict)
    dominance: list[list[bool]] = field(default_factory=list)


def pareto(normalized: Normalized) -> ParetoResult:
    """Отбор Парето-оптимальных альтернатив.

    Альтернатива исключается, если найдётся другая, которая не хуже неё по всем
    критериям и лучше хотя бы по одному.
    """
    task = normalized.task
    count = len(task.alternatives)
    values = normalized.values
    dominance = [[False] * count for _ in range(count)]
    removed, reasons = [], {}

    for i in range(count):
        for j in range(count):
            if i == j:
                continue
            not_worse = all(values[c][i] >= values[c][j] - EPS for c in range(len(values)))
            better = any(values[c][i] > values[c][j] + EPS for c in range(len(values)))
            dominance[i][j] = not_worse and better

    for j in range(count):
        winners = [i for i in range(count) if dominance[i][j]]
        if winners:
            removed.append(j)
            names = ", ".join(task.alternatives[i] for i in winners)
            reasons[j] = f"уступает по всем критериям: {names}"
    kept = [i for i in range(count) if i not in removed]
    return ParetoResult(kept=kept, removed=removed, reasons=reasons, dominance=dominance)


@dataclass
class Weights:
    """Веса критериев, полученные методом ранга."""

    scores: list[list[float]]      # баллы экспертов
    sums: list[float]              # суммарные баллы критериев
    total: float
    values: list[float]            # веса критериев


def rank_weights(scores: list[list[float]]) -> Weights:
    """Метод ранга: веса критериев по балльным оценкам нескольких экспертов.

    Баллы каждого критерия складываются по всем экспертам, затем сумма делится
    на общую сумму баллов. Чем важнее критерий, тем больше его вес.
    """
    count = len(scores[0])
    sums = [sum(row[index] for row in scores) for index in range(count)]
    total = sum(sums)
    values = [value / total for value in sums]
    return Weights(scores=scores, sums=sums, total=total, values=values)


@dataclass
class ElectreResult:
    """Матрицы согласия и несогласия, пороги и «ядро» альтернатив."""

    indices: list[int]                       # какие альтернативы участвовали
    names: list[str]
    concordance: list[list[float]]
    discordance: list[list[float]]
    min_concordance: list[float]
    max_discordance: list[float]
    threshold_c: float
    threshold_d: float
    core: list[int]
    details: list[list[dict]] = field(default_factory=list)

    def core_names(self) -> list[str]:
        return [self.names[i] for i in self.core]


def electre(normalized: Normalized, weights: list[float], indices: list[int],
            threshold_c: float = 0.5, threshold_d: float = 0.5) -> ElectreResult:
    """Метод ЭЛЕКТРА I.

    Для каждой пары альтернатив проверяется предположение «j лучше k».
    Индекс согласия — сумма весов критериев, по которым j не хуже k.
    Индекс несогласия — наибольшее отставание j от k среди остальных критериев.
    В «ядро» попадают альтернативы, у которых наименьший индекс согласия
    не ниже порога, а наибольший индекс несогласия не выше порога.
    """
    values = normalized.values
    names = [normalized.task.alternatives[i] for i in indices]
    size = len(indices)
    concordance = [[0.0] * size for _ in range(size)]
    discordance = [[0.0] * size for _ in range(size)]
    details: list[list[dict]] = [[{} for _ in range(size)] for _ in range(size)]

    for a, j in enumerate(indices):
        for b, k in enumerate(indices):
            if a == b:
                continue
            agree, disagree = [], []
            gap = 0.0
            for c in range(len(values)):
                if values[c][j] >= values[c][k] - EPS:
                    agree.append(c)
                else:
                    disagree.append(c)
                    gap = max(gap, values[c][k] - values[c][j])
            concordance[a][b] = sum(weights[c] for c in agree)
            discordance[a][b] = gap
            details[a][b] = {"agree": agree, "disagree": disagree}

    min_concordance = [min(concordance[a][b] for b in range(size) if b != a) for a in range(size)]
    max_discordance = [max(discordance[a][b] for b in range(size) if b != a) for a in range(size)]
    core = [a for a in range(size)
            if min_concordance[a] >= threshold_c - EPS and max_discordance[a] <= threshold_d + EPS]

    return ElectreResult(
        indices=indices,
        names=names,
        concordance=concordance,
        discordance=discordance,
        min_concordance=min_concordance,
        max_discordance=max_discordance,
        threshold_c=threshold_c,
        threshold_d=threshold_d,
        core=core,
        details=details,
    )


def thresholds_for_count(result: ElectreResult, wanted: int) -> tuple[float, float] | None:
    """Подбор порогов, при которых в «ядро» попадает нужное число альтернатив.

    Перебираются значения порогов с мелким шагом; выбирается пара, при которой
    порог согласия наибольший, а порог несогласия наименьший — то есть самые строгие условия.
    """
    size = len(result.names)
    candidates = []
    steps = [i / 100 for i in range(0, 101)]
    for threshold_c in steps:
        for threshold_d in steps:
            core = [a for a in range(size)
                    if result.min_concordance[a] >= threshold_c - EPS
                    and result.max_discordance[a] <= threshold_d + EPS]
            if len(core) == wanted:
                candidates.append((threshold_c, -threshold_d, tuple(core)))
    if not candidates:
        return None
    best = max(candidates)
    return best[0], -best[1]


def ranking(normalized: Normalized, weights: list[float]) -> list[tuple[int, float]]:
    """Вспомогательная оценка: взвешенная сумма безразмерных оценок.

    Метод ЭЛЕКТРА не строит полного упорядочения, поэтому взвешенная сумма
    используется только как подсказка — чтобы видеть, насколько альтернативы близки.
    """
    values = normalized.values
    count = len(normalized.task.alternatives)
    result = [(index, sum(weights[c] * values[c][index] for c in range(len(values))))
              for index in range(count)]
    return sorted(result, key=lambda item: item[1], reverse=True)
