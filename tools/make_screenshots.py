"""Снимки окна приложения для README.

Скрипт открывает окно, проходит по вкладкам и сохраняет их в docs/img/app_*.png.
Запуск: python tools/make_screenshots.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from electre.ui import STYLE, MainWindow  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")
TABS = ["app_source", "app_normalized", "app_pareto", "app_weights", "app_electre", "app_help"]


def wait(application: QApplication, seconds: float) -> None:
    """Пауза с обработкой событий окна."""
    end = time.time() + seconds
    while time.time() < end:
        application.processEvents()
        time.sleep(0.02)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    wait(application, 1.2)

    for index, name in enumerate(TABS):
        window.tabs.setCurrentIndex(index)
        wait(application, 0.8)
        window.grab().save(os.path.join(OUT, f"{name}.png"))
        print("сохранено", f"{name}.png")

    # отдельный снимок вкладки «ЭЛЕКТРА» с порогами для двух площадок
    window.tabs.setCurrentIndex(4)
    window.pick_thresholds(2)
    wait(application, 0.8)
    window.grab().save(os.path.join(OUT, "app_electre_two.png"))
    print("сохранено app_electre_two.png")

    window.pick_thresholds(1)
    wait(application, 0.5)
    window.pareto_figure.savefig(os.path.join(OUT, "pareto_plot.png"), dpi=150, facecolor="white")
    window.weights_figure.savefig(os.path.join(OUT, "weights_plot.png"), dpi=150, facecolor="white")
    window.electre_figure.savefig(os.path.join(OUT, "electre_plot.png"), dpi=150, facecolor="white")
    print("сохранены графики")
    window.close()


if __name__ == "__main__":
    main()
