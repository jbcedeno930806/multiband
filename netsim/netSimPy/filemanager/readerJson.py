# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 15:10:30 2022

@author: redno
"""
import os
import json
import jsonschema
from jsonschema import validate
from ..node import Node
from ..link import Link
from typing import Dict, Tuple


class Reader:
    def get_schema_path(self):
        print(os.path.join(os.path.dirname(__file__), "bitRates.schema.json"))
        return os.path.join(os.path.dirname(__file__), "bitRates.schema.json")

    def load_schema(self):
        """Load the JSON schema at the given path as a Python object.

        Args:
            schema_path: A filename for a JSON schema.

        Returns:
            A Python object representation of the schema.

        """
        schema_path = os.path.join(os.path.dirname(__file__), "bitRates.schema.json")
        try:
            with open(schema_path) as schema_file:
                schema = json.load(schema_file)
        except ValueError as e:
            raise "Invalid JSON in schema or included schema: %s\n%s" % (
                schema_file.name,
                str(e),
            )

        return schema

    def validateJson(self, jsonData):
        try:
            localSchema = self.load_schema()
            validate(instance=jsonData, schema=localSchema)
        except jsonschema.exceptions.ValidationError as err:
            return False
        return True

    def readNetwork(self, file)->Tuple[Dict[str, Node], Dict[str, Link]]:
        nodes = {}
        links = {}
        with open(file) as json_file:
            info = json.load(json_file)
            if self.validateJson(info):
                pass
            else:
                for readNode in info["nodes"]:
                    nodeID = readNode["id"]
                    nodes[nodeID] = Node(nodeID)
                for readLink in info["links"]:
                    src = readLink["src"]
                    dst = readLink["dst"]
                    link = Link(
                        f"{src}-{dst}", readLink["length"], slots=readLink["slots"]
                    )
                    link.src = src
                    link.dst = dst
                    links[link.id] = link
        return nodes, links
