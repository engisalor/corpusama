import unittest

from corpusama.source.call import Call

# TODO testing other methods requires writing up integration testing


class Test_Call(unittest.TestCase):
    def setUp(cls):
        cls.config_file = "test/config-example.yml"
        cls.job = Call(cls.config_file)

    def test_set_wait(self):
        self.job.wait_dict = {0: 1, 5: 49, 10: 99, 20: 499, 30: None}
        # test wait values for each k:v pair
        for k, v in self.job.config.get("wait_dict").items():
            # None value for highest wait level
            if not v:
                self.assertIsNone(v)
                v = 1000000
            # values and wait align
            self.job.stop_at = v
            self.job._set_wait()
            self.assertEqual(self.job.wait, int(k))
            # stop_at+1 changes wait
            if v != 1000000:
                self.job.stop_at = v + 1
                self.job._set_wait()
                self.assertNotEqual(self.job.wait, int(k))


if __name__ == "__main__":
    unittest.main()
