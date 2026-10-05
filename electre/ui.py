"""Окно приложения: исходные данные, приведение оценок, Парето, веса и метод ЭЛЕКТРА."""

from __future__ import annotations

import os
import sys

# PySide6 подключается раньше matplotlib, чтобы графики использовали именно его.
os.environ.setdefault("QT_API", "pyside6")
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from .data import WORD_VALUES, Task, variant_3
from .excel_report import save_workbook
from .methods import ElectreResult, electre, normalize, pareto, rank_weights, ranking, thresholds_for_count

ACCENT = "#1f6feb"
DARK = "#16233a"
LIGHT = "#f4f7fb"
GOOD = "#1a7f37"

STYLE = f"""
QMainWindow, QWidget#Root {{ background: {LIGHT}; }}
QLabel#Title {{ color: white; font-size: 19px; font-weight: 600; }}
QLabel#Subtitle {{ color: #c7d6ee; font-size: 12px; }}
QFrame#Header {{ background: {DARK}; border: none; }}
QGroupBox {{
    background: white; border: 1px solid #d7e0ee; border-radius: 10px;
    margin-top: 14px; padding: 10px 8px 8px 8px; font-weight: 600; color: #223;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
QPushButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 8px;
    padding: 9px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: #3b82f6; }}
QPushButton#Secondary {{ background: white; color: {ACCENT}; border: 1px solid {ACCENT}; }}
QPushButton#Secondary:hover {{ background: #eaf2ff; }}
QTableWidget {{
    background: white; border: 1px solid #d7e0ee; border-radius: 8px;
    gridline-color: #e6ecf5; selection-background-color: #dbeafe; selection-color: #16233a;
}}
QHeaderView::section {{
    background: #eef3fa; color: #223; border: none; border-right: 1px solid #dfe7f2;
    border-bottom: 1px solid #dfe7f2; padding: 7px; font-weight: 600;
}}
QTabWidget::pane {{ border: 1px solid #d7e0ee; border-radius: 10px; background: white; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: #4a5a72; padding: 9px 16px; margin-right: 4px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600;
}}
QTabBar::tab:selected {{ background: white; color: {ACCENT}; border: 1px solid #d7e0ee; border-bottom: 1px solid white; }}
QFrame#Card {{ background: white; border: 1px solid #d7e0ee; border-radius: 10px; }}
QLabel#CardValue {{ font-size: 20px; font-weight: 700; color: {DARK}; }}
QLabel#CardName {{ color: #5b6b83; font-size: 12px; }}
QLabel#CardHint {{ color: {GOOD}; font-size: 12px; font-weight: 600; }}
QTextBrowser {{ background: white; border: 1px solid #d7e0ee; border-radius: 8px; padding: 10px; }}
QStatusBar {{ background: white; color: #4a5a72; }}
QSlider::groove:horizontal {{ height: 6px; background: #dfe7f2; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QSlider::sub-page:horizontal {{ background: #9dc1fb; border-radius: 3px; }}
"""


def card(name: str, value: str = "—", hint: str = "") -> tuple[QFrame, QLabel, QLabel]:
    """Карточка с крупным значением."""
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    title = QLabel(name)
    title.setObjectName("CardName")
    value_label = QLabel(value)
    value_label.setObjectName("CardValue")
    value_label.setWordWrap(True)
    hint_label = QLabel(hint)
    hint_label.setObjectName("CardHint")
    hint_label.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(value_label)
    layout.addWidget(hint_label)
    return frame, value_label, hint_label


def table(headers: list[str], rows: int = 0, editable: bool = False) -> QTableWidget:
    widget = QTableWidget(rows, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().setVisible(False)
    widget.setAlternatingRowColors(True)
    if not editable:
        widget.setEditTriggers(QTableWidget.NoEditTriggers)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return widget


def number(value: float, digits: int = 3) -> str:
    """Число с запятой в качестве десятичного разделителя — как принято в русском тексте."""
    return f"{value:.{digits}f}".replace(".", ",")


def item(text: str, bold: bool = False, color: str | None = None) -> QTableWidgetItem:
    cell = QTableWidgetItem(text)
    cell.setTextAlignment(Qt.AlignCenter)
    if bold:
        font = cell.font()
        font.setBold(True)
        cell.setFont(font)
    if color:
        cell.setBackground(QColor(color))
    return cell


class MainWindow(QMainWindow):
    """Главное окно лабораторной работы."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Методы принятия решений при многих критериях — метод ЭЛЕКТРА (вариант 3)")
        self.resize(1360, 880)
        self.task: Task = variant_3()
        self.result: ElectreResult | None = None
        self._build()
        self.recalculate()

    # ---------- интерфейс ----------

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_layout.setSpacing(2)
        title = QLabel("Лабораторная работа № 2. Принятие решений при многих критериях")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Задача варианта 3: выбрать площадку для строительства предприятия. "
            "Последовательно применяются отбор Парето, метод ранга и метод ЭЛЕКТРА."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        outer.addWidget(header)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 12, 16, 10)
        layout.setSpacing(12)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_pareto, self.card_pareto_value, self.card_pareto_hint = card("Множество Парето")
        self.card_weight, self.card_weight_value, self.card_weight_hint = card("Самый важный критерий")
        self.card_core, self.card_core_value, self.card_core_hint = card("Ядро альтернатив")
        self.card_choice, self.card_choice_value, self.card_choice_hint = card("Рекомендуемый выбор")
        for widget in (self.card_pareto, self.card_weight, self.card_core, self.card_choice):
            cards.addWidget(widget)
        layout.addLayout(cards)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_source(), "Исходные данные")
        self.tabs.addTab(self._tab_normalized(), "Приведение оценок")
        self.tabs.addTab(self._tab_pareto(), "Множество Парето")
        self.tabs.addTab(self._tab_weights(), "Веса критериев")
        self.tabs.addTab(self._tab_electre(), "Метод ЭЛЕКТРА")
        self.tabs.addTab(self._tab_help(), "Как считается")
        layout.addWidget(self.tabs, 1)
        outer.addWidget(body, 1)
        self.statusBar().showMessage("Готово")

    def _tab_source(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        box = QGroupBox("Характеристики площадок (значения можно менять)")
        box_layout = QVBoxLayout(box)
        self.source_table = table(["Критерий"] + self.task.alternatives, len(self.task.criteria), editable=True)
        self.source_widgets: list[list] = []
        for row, criterion in enumerate(self.task.criteria):
            name = criterion.name + (f", {criterion.unit}" if criterion.unit else "")
            self.source_table.setItem(row, 0, item(name, bold=True))
            widgets_row = []
            for column, value in enumerate(self.task.values[row], start=1):
                if criterion.kind == "качественный":
                    editor = QComboBox()
                    editor.addItems(sorted(WORD_VALUES, key=lambda word: WORD_VALUES[word]))
                    editor.setCurrentText(str(value))
                    editor.currentTextChanged.connect(self.recalculate)
                else:
                    editor = QDoubleSpinBox(maximum=1_000_000.0, decimals=2, singleStep=0.5)
                    editor.setValue(float(value))
                    editor.valueChanged.connect(self.recalculate)
                editor.setStyleSheet("padding: 4px;")
                self.source_table.setCellWidget(row, column, editor)
                widgets_row.append(editor)
            self.source_widgets.append(widgets_row)
        self.source_table.setFixedHeight(150)
        box_layout.addWidget(self.source_table)
        layout.addWidget(box)

        expert_box = QGroupBox("Баллы экспертов (пятибалльная шкала, чем важнее критерий — тем выше балл)")
        expert_layout = QVBoxLayout(expert_box)
        self.expert_table = table(["Эксперт"] + [c.name for c in self.task.criteria],
                                  len(self.task.expert_scores), editable=True)
        self.expert_widgets: list[list[QSpinBox]] = []
        for row, scores in enumerate(self.task.expert_scores):
            self.expert_table.setItem(row, 0, item(f"Эксперт {row + 1}", bold=True))
            widgets_row = []
            for column, score in enumerate(scores, start=1):
                editor = QSpinBox(minimum=1, maximum=10)
                editor.setValue(int(score))
                editor.valueChanged.connect(self.recalculate)
                editor.setStyleSheet("padding: 4px;")
                self.expert_table.setCellWidget(row, column, editor)
                widgets_row.append(editor)
            self.expert_widgets.append(widgets_row)
        self.expert_table.setFixedHeight(110)
        expert_layout.addWidget(self.expert_table)
        notes = QLabel("\n".join(self.task.expert_notes))
        notes.setWordWrap(True)
        notes.setStyleSheet("color: #4a5a72;")
        expert_layout.addWidget(notes)
        layout.addWidget(expert_box)

        buttons = QHBoxLayout()
        reset = QPushButton("Вернуть данные варианта 3")
        reset.setObjectName("Secondary")
        reset.clicked.connect(self.reset_task)
        excel = QPushButton("Отчёт в Excel")
        excel.clicked.connect(self.save_excel)
        buttons.addWidget(reset)
        buttons.addWidget(excel)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)
        return widget

    def _tab_normalized(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        self.normalized_table = table(["Критерий", "Что делаем"] + self.task.alternatives)
        for column in (0, 1):
            self.normalized_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        layout.addWidget(self.normalized_table)
        self.normalized_note = QLabel()
        self.normalized_note.setWordWrap(True)
        self.normalized_note.setStyleSheet("color: #4a5a72;")
        layout.addWidget(self.normalized_note)
        return widget

    def _tab_pareto(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        left = QVBoxLayout()
        self.pareto_table = table([""] + self.task.alternatives, len(self.task.alternatives))
        left.addWidget(QLabel("Кто кого превосходит по всем критериям («+» — строка лучше столбца)"))
        left.addWidget(self.pareto_table)
        self.pareto_note = QLabel()
        self.pareto_note.setWordWrap(True)
        left.addWidget(self.pareto_note)
        layout.addLayout(left, 1)
        self.pareto_figure = Figure(figsize=(5.4, 4.2), dpi=100)
        self.pareto_canvas = FigureCanvas(self.pareto_figure)
        layout.addWidget(self.pareto_canvas, 1)
        return widget

    def _tab_weights(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        left = QVBoxLayout()
        self.weights_table = table(["Критерий", "Эксперт 1", "Эксперт 2", "Сумма баллов", "Вес"],
                                   len(self.task.criteria))
        self.weights_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        left.addWidget(QLabel("Метод ранга: вес критерия — доля его баллов в общей сумме"))
        left.addWidget(self.weights_table)
        layout.addLayout(left, 1)
        self.weights_figure = Figure(figsize=(5.0, 4.0), dpi=100)
        self.weights_canvas = FigureCanvas(self.weights_figure)
        layout.addWidget(self.weights_canvas, 1)
        return widget

    def _tab_electre(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        tables = QHBoxLayout()
        tables.setSpacing(12)
        left = QVBoxLayout()
        left.addWidget(QLabel("Индексы согласия: сумма весов критериев, по которым строка не хуже столбца"))
        self.concordance_table = table([""])
        left.addWidget(self.concordance_table)
        right = QVBoxLayout()
        right.addWidget(QLabel("Индексы несогласия: наибольшее отставание строки от столбца"))
        self.discordance_table = table([""])
        right.addWidget(self.discordance_table)
        tables.addLayout(left, 1)
        tables.addLayout(right, 1)
        layout.addLayout(tables, 3)

        controls = QGroupBox("Пороговые значения")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setSpacing(14)
        self.slider_c = QSlider(Qt.Horizontal)
        self.slider_c.setRange(0, 100)
        self.slider_c.setValue(50)
        self.slider_c.valueChanged.connect(self.update_core)
        self.slider_d = QSlider(Qt.Horizontal)
        self.slider_d.setRange(0, 100)
        self.slider_d.setValue(50)
        self.slider_d.valueChanged.connect(self.update_core)
        self.label_c = QLabel("c* = 0,50")
        self.label_d = QLabel("d* = 0,50")
        for label in (self.label_c, self.label_d):
            label.setStyleSheet("font-weight: 600; color: #16233a;")
        controls_layout.addWidget(QLabel("Порог согласия"))
        controls_layout.addWidget(self.slider_c, 1)
        controls_layout.addWidget(self.label_c)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("Порог несогласия"))
        controls_layout.addWidget(self.slider_d, 1)
        controls_layout.addWidget(self.label_d)
        button_one = QPushButton("Подобрать для одной")
        button_one.setObjectName("Secondary")
        button_one.clicked.connect(lambda: self.pick_thresholds(1))
        button_two = QPushButton("Подобрать для двух")
        button_two.setObjectName("Secondary")
        button_two.clicked.connect(lambda: self.pick_thresholds(2))
        controls_layout.addWidget(button_one)
        controls_layout.addWidget(button_two)
        layout.addWidget(controls)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self.core_table = table(["Площадка", "Наименьший\nиндекс согласия", "Наибольший\nиндекс несогласия", "Вывод"])
        self.core_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        bottom.addWidget(self.core_table, 1)
        self.electre_figure = Figure(figsize=(5.2, 3.4), dpi=100)
        self.electre_canvas = FigureCanvas(self.electre_figure)
        bottom.addWidget(self.electre_canvas, 1)
        layout.addLayout(bottom, 3)

        self.conclusion = QLabel()
        self.conclusion.setWordWrap(True)
        self.conclusion.setStyleSheet("font-size: 13px; color: #16233a; padding: 4px;")
        layout.addWidget(self.conclusion)
        return widget

    def _tab_help(self) -> QWidget:
        view = QTextBrowser()
        view.setHtml(HELP_HTML)
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(view)
        return holder

    # ---------- расчёт ----------

    def collect_task(self) -> Task:
        """Сбор данных из полей окна."""
        task = variant_3()
        values = []
        for row, criterion in enumerate(self.task.criteria):
            row_values = []
            for editor in self.source_widgets[row]:
                if criterion.kind == "качественный":
                    row_values.append(editor.currentText())
                else:
                    row_values.append(float(editor.value()))
            values.append(row_values)
        task.values = values
        task.expert_scores = [[editor.value() for editor in row] for row in self.expert_widgets]
        return task

    def reset_task(self) -> None:
        """Возврат к исходным данным варианта 3."""
        original = variant_3()
        for row, criterion in enumerate(original.criteria):
            for column, value in enumerate(original.values[row]):
                editor = self.source_widgets[row][column]
                if criterion.kind == "качественный":
                    editor.setCurrentText(str(value))
                else:
                    editor.setValue(float(value))
        for row, scores in enumerate(original.expert_scores):
            for column, score in enumerate(scores):
                self.expert_widgets[row][column].setValue(int(score))
        self.slider_c.setValue(50)
        self.slider_d.setValue(50)
        self.recalculate()

    def recalculate(self) -> None:
        """Полный пересчёт: приведение оценок, Парето, веса, метод ЭЛЕКТРА."""
        self.task = self.collect_task()
        self.normalized = normalize(self.task)
        self.pareto_result = pareto(self.normalized)
        self.weights = rank_weights(self.task.expert_scores)
        self.result = electre(
            self.normalized, self.weights.values, self.pareto_result.kept,
            self.slider_c.value() / 100, self.slider_d.value() / 100,
        )
        self._fill_normalized()
        self._fill_pareto()
        self._fill_weights()
        self._fill_electre()
        self.update_core()

    def _fill_normalized(self) -> None:
        widget = self.normalized_table
        widget.setRowCount(2 * len(self.task.criteria))
        for index, criterion in enumerate(self.task.criteria):
            numeric_row = index * 2
            widget.setItem(numeric_row, 0, item(criterion.name, bold=True))
            widget.setItem(numeric_row, 1, item("оценка в числах"))
            for column, value in enumerate(self.normalized.numeric[index], start=2):
                widget.setItem(numeric_row, column, item(f"{value:g}".replace(".", ",")))
            scaled_row = numeric_row + 1
            widget.setItem(scaled_row, 0, item(""))
            widget.setItem(scaled_row, 1, item(self.normalized.comments[index]))
            best = max(self.normalized.values[index])
            for column, value in enumerate(self.normalized.values[index], start=2):
                cell = item(number(value), bold=abs(value - best) < 1e-9,
                            color="#e6f4ea" if abs(value - best) < 1e-9 else None)
                widget.setItem(scaled_row, column, cell)
        self.normalized_note.setText(
            "Словесные оценки переведены в числа по шкале Харрингтона: «плохо» — 0,28, "
            "«удовлетворительно» — 0,50, «хорошо» — 0,70, «отлично» — 0,90. Площадке Пл4 назначено 0,75: "
            "по условию её дорожная сеть немного лучше, чем у Пл3, а оценка остаётся в диапазоне «хорошо». "
            "Затраты приведены обратной величиной, поэтому наименьшие затраты получают единицу."
        )

    def _fill_pareto(self) -> None:
        names = self.task.alternatives
        widget = self.pareto_table
        widget.setColumnCount(len(names) + 1)
        widget.setHorizontalHeaderLabels([""] + names)
        widget.setRowCount(len(names))
        for i, name in enumerate(names):
            widget.setItem(i, 0, item(name, bold=True))
            for j in range(len(names)):
                if i == j:
                    widget.setItem(i, j + 1, item("—"))
                else:
                    wins = self.pareto_result.dominance[i][j]
                    widget.setItem(i, j + 1, item("+" if wins else "", color="#e6f4ea" if wins else None))
        kept = ", ".join(names[i] for i in self.pareto_result.kept)
        removed = "; ".join(f"{names[i]} — {self.pareto_result.reasons[i]}" for i in self.pareto_result.removed)
        self.pareto_note.setText(
            f"<b>Во множество Парето вошли:</b> {kept}.<br>"
            + (f"<b>Исключены:</b> {removed}." if removed else "Ни одна площадка не исключена.")
        )

        self.pareto_figure.clear()
        axes = self.pareto_figure.add_subplot(111)
        x = [self.normalized.values[0][i] for i in range(len(names))]
        y = [self.normalized.values[1][i] for i in range(len(names))]
        sizes = [300 * self.normalized.values[2][i] for i in range(len(names))]
        colors = [GOOD if i in self.pareto_result.kept else "#b3261e" for i in range(len(names))]
        axes.scatter(x, y, s=sizes, c=colors, alpha=0.65, edgecolors="white")
        for i, name in enumerate(names):
            axes.annotate(name, (x[i], y[i]), textcoords="offset points", xytext=(8, 6), fontsize=9)
        axes.set_xlabel("Дорожная сеть (безразмерная оценка)")
        axes.set_ylabel("Энергоснабжение (безразмерная оценка)")
        axes.set_title("Площадки: зелёные — Парето, красные — исключены\n(размер точки — выгода по затратам)", fontsize=10)
        axes.margins(0.14)
        axes.grid(alpha=0.3)
        self.pareto_figure.tight_layout()
        self.pareto_canvas.draw_idle()

    def _fill_weights(self) -> None:
        widget = self.weights_table
        widget.setRowCount(len(self.task.criteria))
        best = max(self.weights.values)
        for row, criterion in enumerate(self.task.criteria):
            widget.setItem(row, 0, item(criterion.name, bold=True))
            for column, scores in enumerate(self.weights.scores, start=1):
                widget.setItem(row, column, item(f"{scores[row]:g}"))
            widget.setItem(row, 3, item(f"{self.weights.sums[row]:g}"))
            value = self.weights.values[row]
            widget.setItem(row, 4, item(number(value), bold=abs(value - best) < 1e-9,
                                        color="#e6f4ea" if abs(value - best) < 1e-9 else None))

        self.weights_figure.clear()
        axes = self.weights_figure.add_subplot(111)
        labels = [criterion.name for criterion in self.task.criteria]
        axes.pie(self.weights.values, labels=labels, autopct="%1.1f%%",
                 colors=["#1f6feb", "#f2a900", "#1a7f37"], startangle=90,
                 wedgeprops={"edgecolor": "white", "linewidth": 2})
        axes.set_title("Доли важности критериев", fontsize=11)
        self.weights_figure.tight_layout()
        self.weights_canvas.draw_idle()

    def _fill_electre(self) -> None:
        result = self.result
        for widget, matrix in ((self.concordance_table, result.concordance),
                               (self.discordance_table, result.discordance)):
            widget.setColumnCount(len(result.names) + 1)
            widget.setHorizontalHeaderLabels([""] + result.names)
            widget.setRowCount(len(result.names))
            for a, name in enumerate(result.names):
                widget.setItem(a, 0, item(name, bold=True))
                for b in range(len(result.names)):
                    if a == b:
                        widget.setItem(a, b + 1, item("—"))
                    else:
                        widget.setItem(a, b + 1, item(number(matrix[a][b])))

    def update_core(self) -> None:
        """Пересчёт «ядра» при изменении порогов."""
        if not self.result:
            return
        threshold_c = self.slider_c.value() / 100
        threshold_d = self.slider_d.value() / 100
        self.label_c.setText(f"c* = {threshold_c:.2f}".replace(".", ","))
        self.label_d.setText(f"d* = {threshold_d:.2f}".replace(".", ","))
        self.result = electre(self.normalized, self.weights.values, self.pareto_result.kept,
                              threshold_c, threshold_d)
        result = self.result

        widget = self.core_table
        widget.setRowCount(len(result.names))
        for a, name in enumerate(result.names):
            inside = a in result.core
            widget.setItem(a, 0, item(name, bold=True))
            widget.setItem(a, 1, item(number(result.min_concordance[a])))
            widget.setItem(a, 2, item(number(result.max_discordance[a])))
            widget.setItem(a, 3, item("входит в ядро" if inside else "не проходит по порогам",
                                      bold=inside, color="#fff4cc" if inside else None))

        self.electre_figure.clear()
        axes = self.electre_figure.add_subplot(111)
        for a, name in enumerate(result.names):
            inside = a in result.core
            axes.scatter(result.min_concordance[a], result.max_discordance[a], s=150,
                         color=GOOD if inside else "#9fb3cd", zorder=4)
            axes.annotate(name, (result.min_concordance[a], result.max_discordance[a]),
                          textcoords="offset points", xytext=(8, 6), fontsize=9)
        axes.axvline(threshold_c, color=ACCENT, linestyle="--", linewidth=1.4)
        axes.axhline(threshold_d, color="#b3261e", linestyle="--", linewidth=1.4)
        axes.set_xlabel("наименьший индекс согласия", fontsize=9)
        axes.set_ylabel("наибольший индекс несогласия", fontsize=9)
        axes.set_title("В ядро попадают точки правее и ниже линий", fontsize=10)
        axes.tick_params(labelsize=8)
        axes.set_xlim(0, 1)
        axes.set_ylim(0, 1)
        axes.grid(alpha=0.3)
        self.electre_figure.tight_layout(pad=1.4)
        self.electre_canvas.draw_idle()

        self._fill_cards()

    def _fill_cards(self) -> None:
        result = self.result
        names = self.task.alternatives
        kept = ", ".join(names[i] for i in self.pareto_result.kept)
        self.card_pareto_value.setText(f"{len(self.pareto_result.kept)} из {len(names)}")
        self.card_pareto_hint.setText(kept)

        best_index = max(range(len(self.weights.values)), key=lambda i: self.weights.values[i])
        self.card_weight_value.setText(self.task.criteria[best_index].name)
        self.card_weight_hint.setText(f"вес {number(self.weights.values[best_index])}")

        core = result.core_names()
        self.card_core_value.setText(", ".join(core) if core else "пусто")
        self.card_core_hint.setText(
            f"пороги c* = {result.threshold_c:.2f}, d* = {result.threshold_d:.2f}".replace(".", ","))

        order = ranking(self.normalized, self.weights.values)
        if len(core) == 1:
            choice = core[0]
            hint = "лучшая по методу ЭЛЕКТРА"
        elif core:
            choice = ", ".join(core)
            hint = "в ядре несколько площадок — ужесточите пороги"
        else:
            choice = names[order[0][0]]
            hint = "ядро пусто: показана лучшая по взвешенной сумме"
        self.card_choice_value.setText(choice)
        self.card_choice_hint.setText(hint)

        lines = [
            f"<b>Ядро при порогах c* = {result.threshold_c:.2f} и d* = {result.threshold_d:.2f}:</b> "
            f"{', '.join(core) if core else 'пусто'}.".replace(".", ",", 2),
            "Порядок по взвешенной сумме оценок (подсказка, а не результат метода): "
            + ", ".join(f"{names[i]} — {number(value)}" for i, value in order[:4]) + ".",
        ]
        if len(core) == 1:
            lines.append(f"Для строительства предприятия следует выбрать площадку <b>{core[0]}</b>.")
        elif len(core) > 1:
            lines.append("В ядро попало несколько площадок: чтобы оставить одну, поднимите порог согласия "
                         "или опустите порог несогласия.")
        else:
            lines.append("Ядро пусто: пороги слишком строгие, их нужно ослабить.")
        self.conclusion.setText("<br>".join(lines))
        self.statusBar().showMessage(
            f"Парето: {len(self.pareto_result.kept)} площадок; ядро: {', '.join(core) if core else 'пусто'}"
        )

    def pick_thresholds(self, wanted: int) -> None:
        """Подбор порогов, при которых в ядре остаётся нужное число площадок."""
        found = thresholds_for_count(self.result, wanted)
        if not found:
            QMessageBox.information(self, "Подбор порогов",
                                    f"Порогов, при которых в ядре останется площадок: {wanted}, не нашлось.")
            return
        threshold_c, threshold_d = found
        self.slider_c.blockSignals(True)
        self.slider_d.blockSignals(True)
        self.slider_c.setValue(int(round(threshold_c * 100)))
        self.slider_d.setValue(int(round(threshold_d * 100)))
        self.slider_c.blockSignals(False)
        self.slider_d.blockSignals(False)
        self.update_core()

    def save_excel(self) -> None:
        """Сохранение книги Excel с проверкой расчёта."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "Проверка_ЛР2_ЭЛЕКТРА.xlsx", "Книга Excel (*.xlsx)")
        if not path:
            return
        try:
            save_workbook(self.task, self.normalized, self.pareto_result, self.weights, self.result, path)
        except PermissionError:
            QMessageBox.warning(self, "Файл занят", "Закройте файл в Excel и повторите сохранение.")
            return
        self.statusBar().showMessage(f"Отчёт сохранён: {path}")
        if QMessageBox.question(self, "Отчёт готов", "Открыть файл в Excel?") == QMessageBox.Yes:
            os.startfile(path) if sys.platform.startswith("win") else None


HELP_HTML = """
<h3>Порядок решения задачи</h3>
<ol>
<li><b>Приведение оценок.</b> Словесные оценки переводятся в числа по шкале Харрингтона,
затем все критерии приводятся к безразмерному виду: лучшая оценка получает единицу.
Для затрат, где лучше меньшее значение, берётся обратная величина.</li>
<li><b>Множество Парето.</b> Площадка исключается, если есть другая, которая не хуже неё
по всем критериям и лучше хотя бы по одному. Так отсеиваются заведомо неподходящие варианты.</li>
<li><b>Веса критериев (метод ранга).</b> Каждый эксперт выставляет критериям баллы.
Баллы складываются, сумма по критерию делится на общую сумму — это и есть вес.</li>
<li><b>Метод ЭЛЕКТРА.</b> Для каждой пары площадок проверяется предположение «первая лучше второй»
и считаются два числа: индекс согласия и индекс несогласия.</li>
</ol>

<h3>Индексы согласия и несогласия</h3>
<p><b>Индекс согласия</b> — сумма весов критериев, по которым первая площадка не хуже второй.
Чем он больше, тем сильнее подтверждается предположение о превосходстве.</p>
<p><b>Индекс несогласия</b> — наибольшее отставание первой площадки от второй среди остальных
критериев. Чем он больше, тем сильнее возражение против предположения.</p>

<h3>Ядро альтернатив</h3>
<p>Для каждой площадки берутся наименьший индекс согласия и наибольший индекс несогласия.
В ядро попадают площадки, у которых наименьший индекс согласия не ниже порога c*,
а наибольший индекс несогласия не выше порога d*. Обычно берут c* = d* = 0,5.</p>
<p>Пороги меняются ползунками. Чем выше порог согласия и ниже порог несогласия, тем строже отбор
и тем меньше площадок остаётся в ядре. Кнопки «Подобрать» сами находят пороги для одной или двух площадок.</p>
"""


def run_application() -> int:
    """Запуск приложения."""
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    application.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    return application.exec()
