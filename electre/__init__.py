"""Лабораторная работа № 2: принятие решений при многих критериях (метод ЭЛЕКТРА)."""

from .data import Task, variant_3
from .methods import electre, normalize, pareto, rank_weights, ranking, thresholds_for_count

__all__ = [
    "Task",
    "variant_3",
    "normalize",
    "pareto",
    "rank_weights",
    "electre",
    "ranking",
    "thresholds_for_count",
]
