import json

import yaml


def load_json(file):
    """Loads a JSON file."""

    with open(file, "r") as f:
        return json.load(f)


def load_yaml(file):
    """Loads a YAML file."""

    with open(file, "r") as stream:
        return yaml.safe_load(stream)
