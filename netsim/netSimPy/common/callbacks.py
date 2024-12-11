from typing import Dict, Any
from ..network import Network
from ..event import Event, EventType


class EventCallback:
    def __init__(self):
        self.blockedEvents = 0

    def on_run_end(self, args: Dict[str, Any]):
        steps: int = args["steps"]
        bp = round(self.blockedEvents / steps, 7)
        print(f"Simulation finished with blocking probability:{bp}")

    def on_update(self, args: Dict[str, Any]):
        event: Event = args["event"]
        if event.getType() != EventType.Departure:
            self.blockedEvents += 1


class NetworkCallback:
    def __init__(self, bands: list[str]):
        self.blockedEvents = 0
        self.bands = bands
        self.attendedByRouteIndex = {}
        self.totalAttendedByBand = {}
        self.totalAttended = 0
        self.fragmentationByBand: dict[str, list] = {}
        for band in self.bands:
            self.totalAttendedByBand[band] = 0
            self.fragmentationByBand[band] = []

    def on_update(self, args: Dict[str, Any]):
        event: Event = args["event"]
        network: Network = args.get("network", None)
        if event.getType() != EventType.Departure:
            self.blockedEvents += 1

        if network is not None:
            if event.getType() == EventType.Departure:
                # the event was allocated, get connection associated:
                con = network.getConnection(event.id)
                self.totalAttended += 1
                self.totalAttendedByBand[con.getBand(con.linksID[0])] += 1
                if con.routeIndex is not None:
                    if con.routeIndex not in self.attendedByRouteIndex:
                        self.attendedByRouteIndex[con.routeIndex] = 1
                    else:
                        self.attendedByRouteIndex[con.routeIndex] += 1
            for band in self.bands:
                self.fragmentationByBand[band].append(network.getBandFragmentation(band))

    def on_run_end(self, args: Dict[str, Any]):
        steps: int = args["steps"]
        bp = round(self.blockedEvents / steps, 7)
        print("self.totalAttended", self.totalAttended)
        print("self.totalAttendedByBand", self.totalAttendedByBand)
        print("self.attendedByRouteIndex", self.attendedByRouteIndex)
        print("self.fragmentationByBand", self.fragmentationByBand)
        print(f"Simulation finished with Blocking probability:{bp}")
