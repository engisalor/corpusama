import os
import unittest

import requests

from rwapi.call import Call

log_file = "tests/.test_rwapi.log"
skip_manual = "Run test manually."

call = {
    "fields": {"exclude": ["body-html", "url_alias"]},
    "query": {"value": "earthquake"},
    "limit": 1,
    "offset": 0,
    "profile": "full",
    "slim": 1,
    "sort": ["date:asc"],
}


class Test_Call(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input_yml = "tests/call.yml"
        cls.input_json = "tests/call.json"
        cls.input_dict = call

    @classmethod
    def tearDownClass(cls):
        for x in [log_file]:
            if os.path.exists(x):
                os.remove(x)

    def setUp(cls):
        # make Call object
        cls.job = Call(cls.input_json, quota=2)
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
            job = Call(self.input_json, v)
            self.assertEqual(job.wait, k)
            # n_calls+1 changes wait
            if v != 1000000:
                job = Call(self.input_json, v + 1)
                self.assertNotEqual(job.wait, k)

    def test_get_parameters(self):
        # parameters are properly read from file
        job2 = Call(self.input_yml)
        for x in [self.job, job2]:
            self.assertDictEqual(x.parameters, self.input_dict)
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

    @unittest.skip(skip_manual)
    def test_run_request_error(self):
        self.job.parameters["slim"] = "slim"
        with self.assertRaises(requests.exceptions.HTTPError):
            self.job.run()


if __name__ == "__main__":
    unittest.main()
