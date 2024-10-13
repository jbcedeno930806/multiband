# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 15:10:30 2022

@author: redno
"""
import os
import json
import jsonschema
from jsonschema import validate


class Reader:
    def get_schema_path(self):
        print(os.path.join(os.path.dirname(__file__), "bitRates.schema.json"))
        return os.path.join(os.path.dirname(__file__), "bitRates.schema.json")

    @staticmethod
    def validateJson(jsonData):
        try:
            localSchema = Reader.load_schema()
            validate(instance=jsonData, schema=localSchema)
        except jsonschema.exceptions.ValidationError:
            return False
        return True

    @staticmethod
    def load_schema():
        """Load the JSON schema at the given path as a Python object.

        Args:
            schema_path: A filename for a JSON schema.

        Returns:
            A Python object representation of the schema.

        """
        schema_path = os.path.join(os.path.dirname(__file__), "network.schema.json")
        try:
            with open(schema_path) as schema_file:
                schema = json.load(schema_file)
        except ValueError as e:
            raise "Invalid JSON in schema or included schema: %s\n%s" % (
                schema_file.name,
                str(e),
            )

        return schema
