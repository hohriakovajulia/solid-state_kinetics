import pandas as pd
from core.basic_signals import BasicSignals
from core.logger_config import logger
from PyQt6.QtCore import pyqtSlot


class ActiveFileOperations(BasicSignals):
    def __init__(self):
        super().__init__("active_file_operations")

    @pyqtSlot(dict)
    def request_slot(self, params: dict):
        logger.debug(f"В request_slot пришли данные {params}")
        operation = params.pop("operation", None)

        if operation == "differential":
            params["function"] = self.diff_function

        response_data = self.handle_request_cycle("file_data", operation, **params)

        logger.debug(f"В операция {operation} завершилась статусом {response_data}")

    def diff_function(self, data: pd.DataFrame):
        return data.diff() * -1
