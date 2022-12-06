"""Functions for reading and writing files."""
import json

import yaml


def load_json(file):
    """Loads a JSON file from a given filepath."""

    with open(file, "r") as f:
        return json.load(f)


def load_yaml(file):
    """Loads a YAML file from a given filepath."""

    with open(file, "r") as stream:
        return yaml.safe_load(stream)
