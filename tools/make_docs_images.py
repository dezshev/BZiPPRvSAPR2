"""Рисунки для README: порядок решения задачи, шкала Харрингтона, сравнение площадок.

Запуск: python tools/make_docs_images.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from electre.data import HARRINGTON, WORD_VALUES, variant_3
from electre.methods import normalize, pareto, rank_weights

OUT = os.path.join(ROOT, "docs", "img")
ACCENT = "#1f6feb"
DARK = "#16233a"
GREEN = "#1a7f37"
ORANGE = "#b54708"


def steps_scheme() -> None:
    """Порядок решения задачи: четыре шага и что получается на каждом."""
    figure, axes = plt.subplots(figsize=(13.4, 3.6))
    steps = [
        ("1. Приведение оценок", "словесные оценки → числа\nвсе критерии к виду «больше — лучше»", ACCENT),
        ("2. Множество Парето", "отсев заведомо худших площадок\n(осталось 5 из 6)", GREEN),
        ("3. Веса критериев", "метод ранга: баллы двух экспертов\n→ вес каждого критерия", ORANGE),
        ("4. Метод ЭЛЕКТРА", "индексы согласия и несогласия\n→ ядро альтернатив", DARK),
    ]
    width, gap = 3.0, 0.55
    for index, (title, text, color) in enumerate(steps):
        x = index * (width + gap)
        axes.add_patch(FancyBboxPatch((x, 0.35), width, 1.5,
                                      boxstyle="round,pad=0.04,rounding_size=0.12",
                                      linewidth=1.8, edgecolor=color, facecolor="white"))
        axes.text(x + width / 2, 1.5, title, ha="center", va="center", fontsize=11,
                  color=color, fontweight="bold")
        axes.text(x + width / 2, 0.95, text, ha="center", va="center", fontsize=9.5, color="#31415c")
        if index < len(steps) - 1:
            axes.add_patch(FancyArrowPatch((x + width, 1.1), (x + width + gap, 1.1),
                                           arrowstyle="-|>", mutation_scale=14,
                                           color="#6b7c93", linewidth=1.4))
    axes.text((4 * width + 3 * gap) / 2, 2.15, "Порядок решения задачи выбора площадки",
              ha="center", fontsize=13, color=DARK, fontweight="bold")
    axes.set_xlim(-0.4, 4 * width + 3 * gap + 0.4)
    axes.set_ylim(0, 2.5)
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "steps.png"), dpi=150, facecolor="white")
    plt.close(figure)


def harrington_scale() -> None:
    """Шкала Харрингтона и место оценок из условия задачи."""
    figure, axes = plt.subplots(figsize=(12, 4.0))
    colors = ["#b3261e", "#e8833a", "#f2c200", "#7cb342", "#1a7f37"]
    for (name, (low, high, middle)), color in zip(HARRINGTON.items(), colors):
        axes.barh(0, high - low, left=low, height=0.5, color=color, alpha=0.75, edgecolor="white")
        axes.text((low + high) / 2, 0, name, ha="center", va="center", fontsize=9.5, color="white",
                  fontweight="bold")
        axes.text((low + high) / 2, -0.38, f"{low:.2f} – {high:.2f}".replace(".", ","),
                  ha="center", fontsize=8.5, color="#4a5a72")

    for word, value in sorted(WORD_VALUES.items(), key=lambda item: item[1]):
        axes.plot(value, 0.26, marker="o", color=DARK, markersize=4)
    labels = {}
    for word, value in sorted(WORD_VALUES.items(), key=lambda item: item[1]):
        labels.setdefault(value, []).append(word)
    # подписи ставятся в два яруса, иначе близкие оценки 0,70 и 0,75 наезжают друг на друга
    for level, (value, words) in enumerate(sorted(labels.items())):
        height = 0.56 if level % 2 == 0 else 0.86
        text = "\n".join(word.replace(", чем у Пл3", "\nчем у Пл3") for word in words)
        axes.plot([value, value], [0.26, height], color=DARK, linewidth=1.0)
        axes.text(value, height + 0.02, text + f"\n{value:.2f}".replace(".", ","),
                  ha="center", va="bottom", fontsize=8.5, color=DARK)

    axes.set_xlim(-0.02, 1.02)
    axes.set_ylim(-0.6, 1.7)
    axes.set_yticks([])
    axes.set_xticks([0, 0.2, 0.36, 0.63, 0.8, 1.0])
    axes.set_xlabel("числовая оценка")
    axes.set_title("Шкала Харрингтона и словесные оценки из условия варианта 3", fontsize=12,
                   color=DARK, fontweight="bold")
    for spine in ("top", "right", "left"):
        axes.spines[spine].set_visible(False)
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "harrington.png"), dpi=150, facecolor="white")
    plt.close(figure)


def alternatives_chart() -> None:
    """Сравнение площадок по безразмерным оценкам с учётом весов критериев."""
    task = variant_3()
    normalized = normalize(task)
    weights = rank_weights(task.expert_scores)
    pareto_result = pareto(normalized)

    names = task.alternatives
    positions = np.arange(len(names))
    figure, axes = plt.subplots(figsize=(10, 4.8))
    colors = ["#1f6feb", "#f2a900", "#1a7f37"]
    width = 0.26
    for index, criterion in enumerate(task.criteria):
        axes.bar(positions + (index - 1) * width, normalized.values[index], width,
                 label=f"{criterion.name} (вес {weights.values[index]:.2f})".replace(".", ","),
                 color=colors[index])
    for index, name in enumerate(names):
        if index not in pareto_result.kept:
            axes.text(index, 1.06, "исключена\nпо Парето", ha="center", fontsize=8.5, color="#b3261e")
    axes.set_xticks(positions)
    axes.set_xticklabels(names)
    axes.set_ylim(0, 1.2)
    axes.set_ylabel("безразмерная оценка")
    axes.set_title("Площадки по трём критериям (вариант 3)", fontsize=12, color=DARK, fontweight="bold")
    axes.legend(loc="lower right", fontsize=9)
    axes.grid(axis="y", alpha=0.3)
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "alternatives.png"), dpi=150, facecolor="white")
    plt.close(figure)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    steps_scheme()
    harrington_scale()
    alternatives_chart()
    print("рисунки сохранены в", OUT)


if __name__ == "__main__":
    main()
