from abc import ABC, abstractmethod
import time
import csv
import json
import os
from typing import Dict, Any, Optional, Tuple, Union

from ..event import Event, EventType


class ResultWriter:
    EXT = "csv"

    def __init__(
        self,
        filename: Optional[str] = None,
        header: Optional[Dict[str, Union[float, str]]] = None,
        info_keywords: Tuple[str] = [],
        override_existing: bool = True,
    ):
        if header is None:
            header = {}
        if not filename.endswith(self.EXT):
            if os.path.isdir(filename):
                filename = os.path.join(filename, self.EXT)
            else:
                filename = filename + "." + self.EXT
        filename = os.path.realpath(filename)
        # Create (if any) missing filename directories
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        # Append mode when not overriding existing file
        mode = "w" if override_existing else "a"
        # Prevent newline issue on Windows, see GH issue #692
        self.file_handler = open(filename, f"{mode}t", newline="\n")
        self.logger = csv.DictWriter(self.file_handler, fieldnames=info_keywords)
        if override_existing:
            self.file_handler.write(f"#{json.dumps(header)}\n")
            self.logger.writeheader()

        self.file_handler.flush()

    def write_row(self, info: Dict[str, float]) -> None:
        """
        Write row of logger data to csv log file.

        :param info: the information to log
        """
        if self.logger and info is not None:
            self.logger.writerow(info)
            self.file_handler.flush()

    def close(self) -> None:
        """
        Close the file handler
        """
        if self.file_handler:
            self.file_handler.close()


class EventEvaluator(ABC):

    def __init__(
        self,
        filename: Optional[str] = None,
        header: Optional[Dict[str, Union[float, str]]] = None,
        info_keywords: Tuple[str] = [],
        override_existing: bool = True,
    ):
        super().__init__()
        self.blockedEvents = 0
        self.filename = filename
        self.header = header
        self.info_keywords = info_keywords
        self.override_existing = override_existing
        self.results_writer = None

    def on_init(self):
        self.results_writer = ResultWriter(
            self.filename,
            self.header,
            self.info_keywords,
            self.override_existing,
        )

    def on_update(self, args: Dict[str, Any]):
        self.results_writer.write_row(self._on_update(args))

    def on_run_end(self, args: Dict[str, Any]):
        self._on_run_end(args)
        self.results_writer.close()

    @abstractmethod
    def _on_update(self, args: Dict[str, Any]) -> Union[Dict[str, Any], None]:
        """If Dict[str, Any] its returned, the info will be wrote on the *.csv file

        Args:
            args (Dict[str, Any]): _description_

        Returns:
            Union[Dict[str, Any], None]: _description
        """
        return {}

    def _on_run_end(self, args: Dict[str, Any]):
        print("Procces finished.")


class SimpleEvaluator(EventEvaluator):
    STEPS = "steps"
    BLOCKED_EVENTS = "blockedEvents"
    metrics = None

    def __init__(
        self,
        filename: Optional[str] = "evaluations",
        header: Optional[Dict[str, Union[float, str]]] = {"timestamp": time.time()},
        info_keywords: Tuple[str] = [],
        override_existing: bool = True,
    ):
        self.metrics = {self.STEPS: 0, self.BLOCKED_EVENTS: 0}
        super().__init__(
            filename,
            header,
            info_keywords=list(self.metrics.keys()) + info_keywords,
            override_existing=override_existing,
        )

    def _on_update(self, args):
        event: Event = args["event"]
        if event.getType() != EventType.Departure:
            self.metrics["blockedEvents"] += 1
        self.metrics["steps"] = args["steps"]
        return self.metrics

    def _on_run_end(self, args):
        print("Total blocked events: {}".format(self.metrics["blockedEvents"]))
