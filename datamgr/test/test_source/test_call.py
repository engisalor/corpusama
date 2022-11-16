import pathlib
import unittest

from datamgr.source.call import Call

log_file = ".logs/.d823kd843hj2ks88.log"
input_yml = "datamgr/test/test_source/call.yml"
input_json = "datamgr/test/test_source/call.json"
wait_dict = {0: 1, 5: 49, 10: 99, 20: 499, 30: None}
input_dict = {
    "query": {"value": "earthquake"},
    "limit": 100,
    "offset": 0,
    "profile": "full",
    "sort": ["date:asc"],
}


class Test_Call(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        pathlib.Path(log_file).unlink(missing_ok=True)

    def setUp(cls):
        cls.job = Call()
        cls.job.log_file = log_file

    def tearDown(cls):
        with open(log_file, "w") as f:
            f.write("\n")

    def test_calls_made_is_0(self):
        self.job._calls_made()
        self.assertEqual(self.job.calls_made, 0)

    def test_calls_made_from_log(self):
        with open(log_file, "w") as f:
            f.write("\n".join([f"_calls_made - {self.job.source}"] * 5))
        self.job._calls_made()
        self.assertEqual(self.job.calls_made, 5)

    def test_enforce_quota(self):
        self.job.n_calls = 5
        # quota calculated
        with open(log_file, "w") as f:
            f.write("\n".join([f"_calls_made - {self.job.source}"] * 1))
        self.job.log_file = log_file
        self.job.quota = 10
        self.job._enforce_quota()
        self.assertEqual(self.job.calls_remaining, 9)
        # quota reached
        self.job.quota = 1
        with self.assertRaises(UserWarning):
            self.job._enforce_quota()

    def test_set_wait(self):
        self.job.wait_dict = wait_dict
        # test wait values for each k:v pair
        for k, v in self.job.wait_dict.items():
            # None value for highest wait level
            if not v:
                self.assertIsNone(v)
                v = 1000000
            # values and wait align
            self.job.n_calls = v
            self.job._set_wait()
            self.assertEqual(self.job.wait, k)
            # n_calls+1 changes wait
            if v != 1000000:
                self.job.n_calls = v + 1
                self.job._set_wait()
                self.assertNotEqual(self.job.wait, k)

    def test_get_parameters(self):
        # parameters are properly read from file
        for x in [input_yml, input_json]:
            self.job.input = x
            self.job._get_parameters()
            self.assertDictEqual(self.job.parameters, input_dict)
        # bad filepath
        with self.assertRaises(FileNotFoundError):
            self.job.input = "nonexistent/file.json"
            self.job._get_parameters()
        # bad file extension
        with self.assertRaises(ValueError):
            self.job.input = "nonexistent/file.xlsx"
            self.job._get_parameters()
        # bad input type
        with self.assertRaises(TypeError):
            self.job.input = [1, 2, 3]
            self.job._get_parameters()


if __name__ == "__main__":
    unittest.main()
