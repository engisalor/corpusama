import hashlib
import json
import logging
import pathlib
import time

import pandas as pd
import requests
import yaml

from datamgr import log_file

logger = logging.getLogger(__name__)


class Call:
    """A base class with common methods for managing API calls."""

    def _check_response(self):
        """Checks a call response and loads JSON data if valid."""

        self.response.raise_for_status()
        response_json = self.response.json()
        if "error" in response_json:
            raise ValueError(response_json)
        self.response_json = response_json
        logger.debug(f"{self.response.status_code}")

    def _calls_made(self):
        """Calculates the number of calls already made in log_file."""

        self.calls_made = 0
        if pathlib.Path(self.log_file).exists():
            with open(pathlib.Path(self.log_file), "r") as f:
                daily_log = f.readlines()
            for x in daily_log:
                if f"_calls_made - {self.source}" in x:
                    self.calls_made += 1
        logger.debug(f"{self.source} - {self.calls_made}")

    def _enforce_quota(self):
        """Enforces API usage quota."""

        self._calls_made()
        self.calls_remaining = self.quota - self.calls_made
        if self.calls_made >= self.quota:
            raise UserWarning(f"Daily API quota reached {self.calls_made}")

    def _set_wait(self):
        """Sets a wait time between API calls given n_calls and wait_dict.

        Example wait_dict: `{0: 1, 5: 49, 10: 99, 20: 499, 30: None}`
        Where: keys = seconds to wait and values = the maximum number of
        calls allowed before increasing the wait time.
        A `None` value indicates the largest possible wait time."""

        waits = []
        for k, v in self.wait_dict.items():
            if v:
                if self.n_calls <= v:
                    waits.append(k)
        if not waits:
            waits.append(max([k for k in self.wait_dict.keys()]))

        logger.debug(f"{min(waits)} second(s)")
        self.wait = min(waits)

    def _parse_input_file(self):
        """Loads API call parameters from a JSON or YAML file."""

        self.input = pathlib.Path(self.input)
        if self.input.suffix in [".yml", ".yaml"]:
            with open(self.input, "r") as stream:
                self.parameters = yaml.safe_load(stream)
        elif self.input.suffix == ".json":
            with open(self.input, "r") as f:
                self.parameters = json.load(f)
        else:
            raise ValueError("Bad file format (must be <filepath>.<json|yml|yaml>).")

    def _parse_input_dict(self):
        """Loads API call parameters from a dict."""

        self.parameters = self.input
        self.input = "dict"

    def _get_parameters(self):
        """Loads parameters from an input file or dict."""

        if isinstance(self.input, str):
            self._parse_input_file()
        elif isinstance(self.input, dict):
            self._parse_input_dict
        else:
            raise TypeError("Input must be a dict of parameters or filepath.")

    def _hash(self):
        params = json.dumps(self.parameters, sort_keys=True)
        self.hash = hashlib.blake2b(params.encode()).hexdigest()[:16]

    def _wait(self):
        """Waits between calls."""

        if self.call_n < (self.n_calls - 1):
            logger.debug(f"{self.wait}")
            time.sleep(self.wait)

    def _request(self):
        """Executes an API call."""

        self.now = pd.Timestamp.now().round("S").isoformat()
        self.response = requests.post(self.url, json.dumps(self.parameters))
        self._check_response()

    def load_config(self, config_file):
        """Loads a config file for passing variables to API related methods."""

        with open(config_file, "r") as f:
            self.config = json.load(f)
        logger.debug(f"{config_file}")

    def __init__(self, config_file=".config.json", source=None):
        self.log_file = log_file
        self.source = source
        self.load_config(config_file)
