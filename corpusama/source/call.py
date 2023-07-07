"""A module for managing the Call class, a base class for API call management."""
import hashlib
import json
import logging
import pathlib
import time

import requests

from corpusama import log_file
from corpusama.util import io as _io
from corpusama.util import util


class Call:
    """A base class with common methods for managing API calls."""

    def _check_response(self) -> None:
        """Checks a call response and loads JSON data if valid."""
        self.response.raise_for_status()
        response_json = self.response.json()
        if "error" in response_json:
            raise ValueError(response_json)
        self.response_json = response_json
        logging.debug(f"{self.response.status_code}")

    def _calls_made(self) -> None:
        """Calculates the number of calls already made in the log file."""
        source = self.config.get("source")
        message = f"_calls_made - {source}"
        self.calls_made = util.count_log_lines(message, log_file)
        logging.debug(f"{source} - {self.calls_made}")

    def _enforce_quota(self) -> None:
        """Enforces API usage quota."""
        self._calls_made()
        quota = self.config.get("quota")
        self.calls_remaining = quota - self.calls_made
        if self.calls_made >= quota:
            logging.debug(f"reached {self.calls_made}")
            raise SystemExit()

    def _set_wait(self, manual=None) -> None:
        """Sets a wait time between API calls."""
        waits = []
        wait_dict = self.config.get("wait_dict")
        for k, v in wait_dict.items():
            if v:
                if self.stop_at <= v:
                    waits.append(int(k))
        if not waits:
            waits.append(max([int(k) for k in wait_dict.keys()]))

        self.wait = min(waits)
        if manual:
            self.wait = manual
        logging.debug(f"{self.wait}")

    def _hash(self) -> None:
        """Makes a hash of a sorted dictionary of parameters."""
        params = json.dumps(self.config.get("parameters"), sort_keys=True)
        self.hash = hashlib.blake2b(params.encode()).hexdigest()[:16]

    def _wait(self) -> None:
        """Executes wait periods between calls."""
        if self.call_n < (self.stop_at - 1):
            logging.debug(f"{self.wait}")
            time.sleep(self.wait)

    def _request(self) -> None:
        """Executes an API call."""
        self.now = util.now()
        params = self.config.get("parameters")
        self.response = requests.post(
            self.config["url"], json.dumps(params), timeout=(6.05, 57)
        )
        self._check_response()

    def __init__(self, config=None):
        self.call_n = 0
        self.config_file = config
        secrets = pathlib.Path(config).with_suffix(".secret.yml")
        self.config = _io.load_yaml(config) | _io.load_yaml(secrets)
