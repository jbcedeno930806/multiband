from abc import ABC, abstractmethod
import time
import csv
import json
import os
from typing import Dict, Any, Optional, Tuple, Union

from ..event import Event, EventType
from ..network import Network, Connection


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
        should_save: bool = True,
        info_keywords: Tuple[str] = [],
        override_existing: bool = True,
    ):
        super().__init__()
        self.blockedEvents = 0
        self.filename = filename
        self.header = header
        self.should_save = should_save
        self.info_keywords = info_keywords
        self.override_existing = override_existing
        self.results_writer = None

    def on_init(self):
        if self.should_save:
            self.results_writer = ResultWriter(
                self.filename,
                self.header,
                self.info_keywords,
                self.override_existing,
            )

    def on_update(self, args: Dict[str, Any]):
        data = self._on_update(args)
        self.results_writer and self.results_writer.write_row(data)

    def on_run_end(self, args: Dict[str, Any]):
        self._on_run_end(args)
        self.results_writer and self.results_writer.close()

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
        should_save: bool = False,
        info_keywords: Tuple[str] = [],
        override_existing: bool = True,
        with_protection=False,
    ):
        self.metrics = {self.STEPS: 0, self.BLOCKED_EVENTS: 0}
        self.with_protection = with_protection
        super().__init__(
            filename,
            header,
            should_save=should_save,
            info_keywords=list(self.metrics.keys()) + info_keywords,
            override_existing=override_existing,
        )

    def _on_update(self, args):
        self.metrics["steps"] = args["steps"]
        event: Event = args["event"]
        # if self.with_protection:
        #     if event.getType() == EventType.Departure:
        #         con: Connection = args["connection"]
        #         if not con.protected:
        #             self.metrics["blockedEvents"] += 1
        #     else:
        #         self.metrics["blockedEvents"] += 2
        # else:
        if event.getType() != EventType.Departure:
            self.metrics["blockedEvents"] += 1

        # return self.metrics

    def _on_run_end(self, args):
        bp = round(self.metrics["blockedEvents"] / self.metrics["steps"], 7)
        print(
            "Total blocked events: {} for a BP={}".format(
                self.metrics["blockedEvents"], bp
            )
        )


class NetworkEvaluator(EventEvaluator):
    metrics = None

    def __init__(
        self,
        name,
        should_save: bool = True,
        bands=["C", "S", "L", "E"],
        filename="net.evaluations",
        header=None,
        info_keywords=[],
        override_existing=True,
    ):
        self.metrics = {
            "steps": 0,
            "blockedEvents": 0,
            "attendedByRouteIndex": {},
            "totalAttendedByBand": {},
            "totalAttended": 0,
            "attendedByModulation": {},
            "blockedBitRateByBitRate": {},
            "totalBitRate": 0,
            "bitRateByBand": {},
        }
        super().__init__(
            name + filename,
            header,
            should_save=should_save,
            info_keywords=list(self.metrics.keys()) + info_keywords,
            override_existing=override_existing,
        )
        self.bands = bands

        for band in self.bands:
            self.metrics["totalAttendedByBand"][band] = 0
            self.metrics["blockedBitRateByBitRate"] = {}
            self.metrics["bitRateByBand"][band] = 0

    def _on_run_end(self, args):
        block = self.metrics["blockedEvents"]
        steps = self.metrics["steps"]
        self.results_writer.write_row(self.metrics)
        print(f"Blocking probability: {round(block/steps, 6)}")

    def _on_update(self, args):
        event: Event = args["event"]
        self.metrics["steps"] = args["steps"]
        network: Network = args.get("network", None)
        con: Connection = args["connection"]

        # connect = args["connection"]
        # conID = connect.eventID
        if event.getType() != EventType.Departure:
            self.metrics["blockedEvents"] += 1
            if con.bitRate.getBitRate() not in self.metrics["blockedBitRateByBitRate"]:
                self.metrics["blockedBitRateByBitRate"][con.bitRate.getBitRate()] = 0
            self.metrics["blockedBitRateByBitRate"][
                con.bitRate.getBitRate()
            ] += con.bitRate.getBitRate()
        if network is not None:
            if event.getType() == EventType.Departure:
                # if conID != con.eventID:
                #     print("ERRRRROOOOORRRR")
                # the event was allocated, get connection associated:
                self.metrics["totalAttended"] += 1
                self.metrics["totalBitRate"] += con.bitRate.getBitRate()
                band = con.getBand(con.linksID[0])
                self.metrics["totalAttendedByBand"][band] += 1
                self.metrics["bitRateByBand"][band] += con.bitRate.getBitRate()
                modulation = con.getModulationName(con.linksID[0])
                if modulation not in self.metrics["attendedByModulation"]:
                    self.metrics["attendedByModulation"][modulation] = 1
                else:
                    self.metrics["attendedByModulation"][modulation] += 1

                if con.routeIndex is not None:
                    if con.routeIndex not in self.metrics["attendedByRouteIndex"]:
                        self.metrics["attendedByRouteIndex"][con.routeIndex] = 1
                    else:
                        self.metrics["attendedByRouteIndex"][con.routeIndex] += 1
