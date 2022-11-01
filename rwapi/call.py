import hashlib
import json
import logging
import pathlib
import time

import pandas as pd
import requests
import yaml

logger = logging.getLogger(__name__)
log_file = ".rwapi.log"


class Call:
    """Manages API calls made to ReliefWeb.

    Usage:
    ```python
    job = rwapi.Call(<input>, <appname>) # set up a job
    job.run()                            # run API calls
    job.data                             # access results
    ```

    Options
    - input = JSON/YML filepath or dict with parameters
    - n_calls = number of calls to make (pages to collect)
    - appname = unique identifier for using RW API
    - url = base url for making POST calls
    - quota = daily usage limit (see RW API documentation)
    - wait_dict = dict of wait times for ranges of n_calls
    (default {0: 1, 5: 49, 10: 99, 20: 499, 30: None})"""

    def _check_response(self):
        """Checks a call response and loads JSON data if valid."""

        self.response.raise_for_status()
        response_json = self.response.json()
        if "error" in response_json:
            raise ValueError(response_json)
        self.response_json = response_json

    def _request(self):
        """Executes a ReliefWeb API call."""

        self.now = pd.Timestamp.now().round("S").isoformat()
        self.response = requests.post(self.url, json.dumps(self.parameters))
        self._check_response()
        self._get_field_names()
        summary = {k: v for k, v in self.response_json.items() if k != "data"}
        logger.info(f'offset {self.parameters["offset"]} - summary {summary}')

    def _quota_calls_made(self):
        """Calculates the number of calls already made in log_file."""

        self.calls_made = 0
        if pathlib.Path(self.log_file).exists():
            with open(pathlib.Path(self.log_file), "r") as f:
                daily_log = f.readlines()
            for x in daily_log:
                if "_request" in x:
                    self.calls_made += 1

        self.calls_remaining = self.quota - self.calls_made
        logger.debug(f"{self.calls_made}")

    def _quota_enforce(self):
        """Enforce API usage quota."""

        self._quota_calls_made()
        if self.calls_made >= self.quota:
            raise UserWarning(f"Daily API quota reached {self.calls_made}")
        elif self.n_calls > self.calls_remaining:
            logger.warning(
                f"daily quota will be reached: {self.calls_remaining} calls remaining"
            )
            self.n_calls = self.quota - self.calls_made

    def _set_wait(self):
        """Sets a wait time between API calls given n_calls and wait_dict.

        Example wait_dict: `{0: 1, 5: 49, 10: 99, 20: 499, 30: None}`
        Where: keys = seconds to wait and values = the maximum number of calls allowed before increasing the wait time.
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
        """Load API call parameters from a JSON or YAML file."""

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
        """Load API call parameters from a dict."""

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

    def _increment_parameters(self):
        """Adjusts offset when making multiple calls and halts job if no more results."""

        if self.call_n > 0:
            self.parameters["offset"] += self.response_json["count"]
            if self.response_json["count"] == 0:
                raise UserWarning("Call aborted: no more results.")

    def _hash(self):
        params = json.dumps(self.parameters, sort_keys=True)
        self.hash = hashlib.blake2b(params.encode()).hexdigest()[:16]

    def _wait(self):
        """Wait between calls."""

        if self.call_n < (self.n_calls - 1):
            logger.debug(f"waiting {self.wait} seconds")
            time.sleep(self.wait)

    def run(self):
        """Manages making one or more API calls and stores response_json in dict self.data."""

        for call_n in range(self.n_calls):
            self.call_n = call_n
            self._quota_enforce()
            self._increment_parameters()
            self._request()
            self._hash()
            self.data[call_n] = self.response_json
            self._wait()

    def _load_config(self):
        """Use a config file to load an appname from a JSON file.

        File contents:
        {"appname": "<my_appname>"}"""

        if not self.appname:
            with open(self.config_file, "r") as f:
                self.appname = json.load(f)["appname"]

        self.url = "".join([self.url, self.appname])
        logger.debug(f"{self.config_file}")

    def _get_field_names(self):
        """Makes a set of field names from response data."""

        self.field_names = set()
        for x in self.response_json["data"]:
            self.field_names.update(list(x["fields"].keys()))

        logger.debug(f"{len(self.field_names)} {sorted(self.field_names)}")

    def __repr__(self):
        return ""

    def __init__(
        self,
        input,
        n_calls=1,
        appname=None,
        url="https://api.reliefweb.int/v1/reports?appname=",
        quota=1000,
        wait_dict={0: 1, 5: 49, 10: 99, 20: 499, 30: None},
        log_level="warning",
    ):
        # variables
        self.input = input
        self.appname = appname
        self.n_calls = n_calls
        self.url = url
        self.quota = quota
        self.wait_dict = wait_dict
        self.data = {}
        self.log_file = log_file
        self.config_file = ".rwapi_config.json"

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        logger.setLevel(numeric_level)

        # prepare job
        self._load_config()
        self._set_wait()
        self._get_parameters()
