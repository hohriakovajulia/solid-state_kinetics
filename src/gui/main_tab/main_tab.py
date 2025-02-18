from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from src.core.basic_signals import BasicSignals
from src.core.logger_config import logger
from src.core.logger_console import LoggerConsole as console
from src.gui.console_widget import ConsoleWidget
from src.gui.main_tab.plot_canvas.plot_canvas import PlotCanvas
from src.gui.main_tab.sidebar import SideBar
from src.gui.main_tab.sub_sidebar.sub_side_hub import SubSideHub

MIN_WIDTH_SIDEBAR = 220
MIN_WIDTH_SUBSIDEBAR = 220
MIN_WIDTH_CONSOLE = 150
MIN_WIDTH_PLOTCANVAS = 500
SPLITTER_WIDTH = 100
MIN_HEIGHT_MAINTAB = 700
COMPONENTS_MIN_WIDTH = (
    MIN_WIDTH_SIDEBAR + MIN_WIDTH_SUBSIDEBAR + MIN_WIDTH_CONSOLE + MIN_WIDTH_PLOTCANVAS + SPLITTER_WIDTH
)


class MainTab(QWidget, BasicSignals):
    active_file_modify_signal = pyqtSignal(dict)
    calculations_data_modify_signal = pyqtSignal(dict)
    processing_signal = pyqtSignal(bool)
    request_signal = pyqtSignal(dict)
    response_signal = pyqtSignal(dict)
    calculations_data_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        BasicSignals.__init__(self, actor_name="main_tab")

        self.layout = QVBoxLayout(self)
        self.setMinimumHeight(MIN_HEIGHT_MAINTAB)
        self.setMinimumWidth(COMPONENTS_MIN_WIDTH + SPLITTER_WIDTH)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.layout.addWidget(self.splitter)

        self.sidebar = SideBar(self)
        self.sidebar.setMinimumWidth(MIN_WIDTH_SIDEBAR)
        self.splitter.addWidget(self.sidebar)

        self.sub_sidebar = SubSideHub(self)
        self.sub_sidebar.setMinimumWidth(MIN_WIDTH_SUBSIDEBAR)
        self.sub_sidebar.hide()
        self.splitter.addWidget(self.sub_sidebar)

        self.plot_canvas = PlotCanvas(self)
        self.plot_canvas.setMinimumWidth(MIN_WIDTH_PLOTCANVAS)
        self.splitter.addWidget(self.plot_canvas)

        self.console_widget = ConsoleWidget(self)
        self.console_widget.setMinimumWidth(MIN_WIDTH_CONSOLE)
        self.splitter.addWidget(self.console_widget)

        self.sidebar.sub_side_bar_needed.connect(self.toggle_sub_sidebar)
        self.sidebar.console_show_signal.connect(self.toggle_console_visibility)
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.cancel_changes_clicked.connect(self.to_active_file)
        self.sub_sidebar.experiment_sub_bar.action_buttons_block.derivative_clicked.connect(self.to_active_file)
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_added.connect(
            self.to_calculations_data_operations
        )
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_removed.connect(
            self.to_calculations_data_operations
        )
        self.sub_sidebar.deconvolution_sub_bar.reactions_table.reaction_chosed.connect(
            self.to_calculations_data_operations
        )
        self.sub_sidebar.deconvolution_sub_bar.update_value.connect(self.to_calculations_data_operations)
        self.sidebar.active_file_selected.connect(self.sub_sidebar.deconvolution_sub_bar.reactions_table.switch_file)
        self.plot_canvas.update_value.connect(self.update_anchors_slot)
        self.sub_sidebar.deconvolution_sub_bar.calc_buttons.calculation_started.connect(
            self.to_calculations_data_operations
        )
        self.sub_sidebar.ea_sub_bar.create_series_signal.connect(self.to_calculations_data)
        self.calculations_data_signal.connect(self.sub_sidebar.ea_sub_bar.open_merge_dialog)

    def initialize_sizes(self):
        total_width = self.width()

        sidebar_ratio = MIN_WIDTH_SIDEBAR / COMPONENTS_MIN_WIDTH
        subsidebar_ratio = MIN_WIDTH_SUBSIDEBAR / COMPONENTS_MIN_WIDTH
        console_ratio = MIN_WIDTH_CONSOLE / COMPONENTS_MIN_WIDTH

        sidebar_width = int(total_width * sidebar_ratio)
        console_width = int(total_width * console_ratio) if self.console_widget.isVisible() else 0
        sub_sidebar_width = int(total_width * subsidebar_ratio) if self.sub_sidebar.isVisible() else 0
        canvas_width = total_width - (sidebar_width + sub_sidebar_width + console_width)
        self.splitter.setSizes([sidebar_width, sub_sidebar_width, canvas_width, console_width])

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_sizes()

    def toggle_sub_sidebar(self, content_type):
        if content_type:
            if content_type in self.sidebar.get_experiment_files_names():
                self.sub_sidebar.update_content("Эксперимент")
            else:
                self.sub_sidebar.update_content(content_type)
            self.sub_sidebar.setVisible(True)
        else:
            self.sub_sidebar.setVisible(False)
        self.initialize_sizes()

    def toggle_console_visibility(self, visible):
        self.console_widget.setVisible(visible)
        self.initialize_sizes()

    def to_active_file(self, params: dict):
        params["file_name"] = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else "no_file"
        logger.debug(f"Активный файл: {params['file_name']} запрашивает операцию: {params["operation"]}")
        self.active_file_modify_signal.emit(params)

    def to_calculations_data(self, params: dict):
        logger.debug(f"{params=}")
        operation = params.pop("operation", None)
        target = params.pop("target", "calculations_data")
        response_data = self.handle_request_cycle(target, operation, **params)
        response = {"data": response_data}
        if operation == "get_full_data":
            self.calculations_data_signal.emit(response)

    def to_calculations_data_operations(self, params: dict):
        active_file_name = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else "no_file"
        params["path_keys"].insert(0, active_file_name)
        operation = params.pop("operation", None)
        response_data = self.handle_request_cycle("calculations_data_operations", operation, **params)
        logger.debug(f"respose to_calculations_data_operations: {response_data}")

    @pyqtSlot(list)
    def update_anchors_slot(self, params_list: list):
        self.processing_signal.emit(True)
        for i, params in enumerate(params_list):
            params["path_keys"].insert(
                0,
                self.sub_sidebar.deconvolution_sub_bar.reactions_table.active_reaction,
            )
            params["is_chain"] = True
            if i == len(params_list) - 1:
                self.processing_signal.emit(False)
            self.to_calculations_data_operations(params)
        params["operation"] = "highlight_reaction"
        self.to_calculations_data_operations(params)

    @pyqtSlot(dict)
    def response_slot(self, params: dict):
        super().response_slot(params)

        if params["target"] != "main_tab":
            return

        request_id = params.get("request_id")

        if request_id in self.pending_requests:
            if params["operation"] == "add_reaction" and params["data"] is False:
                console.log(
                    "Перед добвлением реакции необходимо привести данные к da/dT. Данные экспериментов ->\
                     выберите эксперимент -> Привести к da/dT"
                )
                self.sub_sidebar.deconvolution_sub_bar.reactions_table.on_fail_add_reaction()
                logger.debug("Добавление реакции в таблицу не удалось. Ответ: False")

    @pyqtSlot(dict)
    def request_slot(self, params: dict):
        if params["target"] != "main_tab":
            return

        logger.debug(f"В request_slot пришли данные {params}")
        operation = params.pop("operation", None)
        if not operation:
            logger.error(f"Операция {operation} не найдена: {params}")
            return

        elif operation == "get_file_name":
            params["data"] = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else None
        elif operation == "plot_df":
            df = params.get("df")
            _ = self.plot_canvas.plot_file_data_from_dataframe(df)
            params["data"] = True
        elif operation == "update_reaction_table":
            reactions_data = params.get("reactions_data", {})
            active_file_name = self.sidebar.active_file_item.text() if self.sidebar.active_file_item else None
            if not active_file_name:
                logger.error("Нет активного файла для обновления UI.")
                return

            reaction_table = self.sub_sidebar.deconvolution_sub_bar.reactions_table
            reaction_table.switch_file(active_file_name)
            table = reaction_table.reactions_tables[active_file_name]
            table.setRowCount(0)
            reaction_table.reactions_counters[active_file_name] = 0

            for reaction_name, reaction_info in reactions_data.items():
                function_name = reaction_info.get("function", "gauss")
                reaction_table.add_reaction(reaction_name=reaction_name, function_name=function_name, emit_signal=False)
            logger.debug("UI успешно обновлен с загруженными реакциями.")
        else:
            logger.error(f"Операция не найдена: {params}")

        params["target"], params["actor"] = params["actor"], params["target"]
        self.response_signal.emit(params)
