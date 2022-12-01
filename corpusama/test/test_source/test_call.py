import unittest

from corpusama.source.call import Call

wait_dict = {0: 1, 5: 49, 10: 99, 20: 499, 30: None}
input_yml = "corpusama/test/test_source/call.yml"
input_json = "corpusama/test/test_source/call.json"
input_dict = {
    "filter": {
        "conditions": [
            {"field": "language", "value": "English"},
            {
                "field": "date",
                "value": {
                    "from": "2000-01-01T00:00:00+00:00",
                    "to": "2005-09-01T00:00:00+00:00",
                },
            },
        ],
        "operator": "AND",
    },
    "limit": 100,
    "offset": 0,
    "profile": "full",
    "query": {"value": "earthquake"},
    "sort": ["date.changed:asc"],
}


class Test_Call(unittest.TestCase):
    def setUp(cls):
        cls.job = Call()

    # TODO testing quota enforcement requires altering the method
    # to allow for manually setting variables or supplying a test log file
    # def test_enforce_quota(self):
    #     self.job.quota = 1000
    #     self.job.calls_made = 1000
    #     with self.assertRaises(SystemExit):
    #         self.job._enforce_quota()

    def test_set_wait(self):
        self.job.wait_dict = wait_dict
        # test wait values for each k:v pair
        for k, v in self.job.wait_dict.items():
            # None value for highest wait level
            if not v:
                self.assertIsNone(v)
                v = 1000000
            # values and wait align
            self.job.limit = v
            self.job._set_wait()
            self.assertEqual(self.job.wait, k)
            # limit+1 changes wait
            if v != 1000000:
                self.job.limit = v + 1
                self.job._set_wait()
                self.assertNotEqual(self.job.wait, k)

    def test_get_parameters(self):
        # load parameters
        for x in [input_dict, input_yml, input_json]:
            self.job.input = x
            self.job._get_parameters()
            self.assertDictEqual(self.job.parameters, input_dict)
        # bad inputs
        with self.assertRaises(ValueError):
            self.job.input = "file.xlsx"
            self.job._get_parameters()
        with self.assertRaises(TypeError):
            self.job.input = [1, 2, 3]
            self.job._get_parameters()
        with self.assertRaises(FileNotFoundError):
            self.job.input = "file.yml"
            self.job._get_parameters()


if __name__ == "__main__":
    unittest.main()
