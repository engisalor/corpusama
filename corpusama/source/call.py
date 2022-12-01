import hashlib
import json
import logging
import pathlib
import time

import requests

from corpusama import log_file
from corpusama.util import io as _io
from corpusama.util import util

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

        message = f"_calls_made - {self.source}"
        self.calls_made = util.count_log_lines(message, log_file)
        logger.debug(f"{self.source} - {self.calls_made}")

    def _enforce_quota(self):
        """Enforces API usage quota.

        self.quota must be set in inherited class."""

        self._calls_made()
        self.calls_remaining = self.quota - self.calls_made
        if self.calls_made >= self.quota:
            logger.debug(f"reached {self.calls_made}")
            raise SystemExit()

    def _set_wait(self, manual=None):
        """Sets a wait time between API calls.

        Example wait_dict: `{0: 1, 5: 49, 10: 99, 20: 499, 30: None}`
        Where: keys = seconds to wait and values = the maximum number of
        calls allowed before increasing the wait time.
        A `None` value indicates the largest possible wait time.
        Manual, int, overrides the wait dict"""

        waits = []
        for k, v in self.wait_dict.items():
            if v:
                if self.limit <= v:
                    waits.append(k)
        if not waits:
            waits.append(max([k for k in self.wait_dict.keys()]))

        self.wait = min(waits)
        if manual:
            self.wait = manual
        logger.debug(f"{self.wait}")

    def _get_parameters(self):
        """Loads API call parameters from a dict."""

        if isinstance(self.input, dict):
            self.parameters = self.input
            self.input = "dict"
        elif isinstance(self.input, str):
            self.input = pathlib.Path(self.input)
            if self.input.suffix in [".yml", ".yaml"]:
                self.parameters = _io.load_yaml(self.input)
            elif self.input.suffix == ".json":
                self.input = pathlib.Path(self.input)
                self.parameters = _io.load_json(self.input)
            else:
                raise ValueError("Input files must be JSON or YAML.")
        else:
            raise TypeError("Input must be dict or filename (JSON or YAML).")

    def _hash(self):
        params = json.dumps(self.parameters, sort_keys=True)
        self.hash = hashlib.blake2b(params.encode()).hexdigest()[:16]

    def _wait(self):
        """Waits between calls."""

        if self.call_n < (self.limit - 1):
            logger.debug(f"{self.wait}")
            time.sleep(self.wait)

    def _request(self):
        """Executes an API call."""

        self.now = util.now()
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
        self.call_n = 0
        self.load_config(config_file)
