"""A module with the Call base class, for implementing new API data sources."""
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
    """A base class with common methods for managing API calls.

    Args:
        config_file: A filename for a JSON configuration file (``.config.json``).
        source: The name of the API resource being used (supplied by
            child classes, e.g., ``ReliefWeb``).

    Attributes:
        call_n: The current call number.
        calls_made: Number of calls made in a job so far.
        calls_remaining: Number of calls before the quota is reached.
        hash: A hash of sorted input parameters.
        input: The parameters file to use or a dictionary.
        limit: Maximum calls for a job as set by the user.
        now: The current timestamp.
        parameters: A dictionary of call parameters.
        quota: The maximum calls allowed in a time period.
        response: An API call response.
        response_json: JSON call response data.
        wait: Seconds to wait in between calls.
        wait_dict: A dictionary with wait parameters.

    Notes:
        This class is never instantiated: implement it with a child class.

        Internal methods manage these aspects of API calls:
        - Loading API parameters from file/object.
        - Loading a configuration file.
        - Making basic API requests.
        - Checking for valid GET/POST responses.
        - Tracking the number of calls made in a job.
        - Enforcing quota limits, if supplied in the child class.
        - Managing wait periods between calls.
        - Making hashes of call parameters.

    See Also:
        - Existing call parameter files in ``/corpusama/source/params``.
        - ``_set_wait`` on how wait dictionaries work.
        - ``_load_config`` on implementing configuration values.
        - ``source.reliefweb.ReliefWeb`` for an example inheriting class."""

    def _check_response(self) -> None:
        """Checks a call response and loads JSON data if valid."""

        self.response.raise_for_status()
        response_json = self.response.json()
        if "error" in response_json:
            raise ValueError(response_json)
        self.response_json = response_json
        logger.debug(f"{self.response.status_code}")

    def _calls_made(self) -> None:
        """Calculates the number of calls already made in the log file."""

        message = f"_calls_made - {self.source}"
        self.calls_made = util.count_log_lines(message, log_file)
        logger.debug(f"{self.source} - {self.calls_made}")

    def _enforce_quota(self) -> None:
        """Enforces API usage quota.

        Notes:
            ``quota`` must be set in the inherited class."""

        self._calls_made()
        self.calls_remaining = self.quota - self.calls_made
        if self.calls_made >= self.quota:
            logger.debug(f"reached {self.calls_made}")
            raise SystemExit()

    def _set_wait(self, manual=None) -> None:
        """Sets a wait time between API calls.

        Args:
            manual (int): a wait time, in seconds, to override ``wait_dict``.

        Example:
            ``wait_dict = {0: 1, 5: 49, 10: 99, 20: 499, 30: None}``

            Where keys are the number of seconds to wait and
            values are the maximum number of calls allowed
            before increasing the wait time: e.g., 49 calls has
            a wait of 5 seconds and for 50 calls it's 10 seconds.
            ``None`` is used for the largest possible wait time."""

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

    def _get_parameters(self) -> None:
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

    def _hash(self) -> None:
        """Makes a hash of a sorted dictionary of parameters."""

        params = json.dumps(self.parameters, sort_keys=True)
        self.hash = hashlib.blake2b(params.encode()).hexdigest()[:16]

    def _wait(self) -> None:
        """Executes wait periods between calls."""

        if self.call_n < (self.limit - 1):
            logger.debug(f"{self.wait}")
            time.sleep(self.wait)

    def _request(self) -> None:
        """Executes an API call."""

        self.now = util.now()
        self.response = requests.post(self.url, json.dumps(self.parameters))
        self._check_response()

    def load_config(self, config_file: str) -> None:
        """Loads a config file for passing variables to API related methods.

        Args:
            config_file: a JSON filename (``.config.json``) pointing to a
                file stored in cwd.

        Notes:
            Using data stored in a config file requires altering existing methods."""

        with open(config_file, "r") as f:
            self.config = json.load(f)
        logger.debug(f"{config_file}")

    def __init__(self, config_file=".config.json", source=None):
        self.log_file = log_file
        self.source = source
        self.call_n = 0
        self.load_config(config_file)
