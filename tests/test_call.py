import yaml
import unittest
import requests
from rwapi import Call
import os

log_file = "tests/.test_rwapi.log"
skip_manual = "Run test manually."


class Test_Call(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input = "rwapi/calls/example.yml"

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(log_file):
            os.remove(log_file)

    def setUp(cls):
        # make Call object
        cls.job = Call(cls.input, quota=1)
        cls.job.log_file = log_file

    def tearDown(cls):
        # clear log_file
        with open(log_file, "w") as f:
            f.write("\n")

    def test_set_wait(self):
        # test wait values for each k:v pair
        for k, v in self.job.wait_dict.items():
            # None value for highest wait level
            if not v:
                self.assertIsNone(v)
                v = 1000000
            # values and wait align
            job = Call(self.input, v)
            self.assertEqual(job.wait, k)
            # n_calls+1 changes wait
            if v != 1000000:
                job = Call(self.input, v + 1)
                self.assertNotEqual(job.wait, k)

    def test_get_parameters(self):
        # get example parameters
        with open(self.input, "r") as stream:
            self.example_parameters = yaml.safe_load(stream)
        # parameters are properly read from file
        job2 = Call("rwapi/calls/example.json")
        for x in [self.job, job2]:
            self.assertDictEqual(x.parameters, self.example_parameters)
        # bad filepath
        with self.assertRaises(FileNotFoundError):
            Call("nonexistent/file.json")
        # bad file extension
        with self.assertRaises(ValueError):
            Call(log_file)
        # bad input type
        with self.assertRaises(TypeError):
            Call([1, 2, 3])

    def test_run_enforce_quota(self):
        with open(log_file, "w") as f:
            f.write("\n".join(["_request"] * self.job.quota))
        with self.assertRaises(UserWarning):
            self.job.run()

    @unittest.skip(skip_manual)
    def test_run_request_successful(self):
        self.job.n_calls = 2
        self.job.run()
        # offset gets incremented
        self.assertEqual(self.job.parameters["offset"], self.job.response_json["count"])
        # store response data
        self.assertIsInstance(self.job.response, requests.Response)
        self.assertIsInstance(self.job.response_json, dict)

    @unittest.skip(skip_manual)
    def test_run_request_error(self):
        self.job.parameters["slim"] = "slim"
        with self.assertRaises(requests.exceptions.HTTPError):
            self.job.run()


if __name__ == "__main__":
    unittest.main()
