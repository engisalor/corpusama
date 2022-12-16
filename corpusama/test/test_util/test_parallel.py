import unittest
from multiprocessing import cpu_count

import numpy as np
import pandas as pd

from corpusama.util import parallel


def df_func(df):
    """A test function for ``test_run_dataframe``."""

    df["A"] = df["A"] / df["B"] * df["C"]
    df["B"] = df["B"] / df["A"] * df["C"]
    df["C"] = df["C"] / df["A"] * df["B"]
    return df


def ls_func(ls):
    """A test function for ``test_run_ls``."""

    return [x / 13 for x in ls]


class Test_Parallel(unittest.TestCase):
    def test_set_cores(self):
        self.assertEqual(parallel.set_cores(2), 2)
        divisor = 2
        _cores = int(cpu_count() / divisor)
        self.assertEqual(parallel.set_cores(divisor=divisor), _cores)

    def test_run_dataframe(self):
        """Ensures result is identical whether function is/isn't run in parallel."""

        df = pd.DataFrame(
            np.random.randint(100000, 1000000, size=(100, 3)), columns=list("ABC")
        )
        cores = int(cpu_count() / 2)
        df1 = df_func(df.copy())
        df2 = parallel.run(df.copy(), df_func, cores)
        self.assertTrue(df1.equals(df2))

    def test_run_list(self):
        """Ensures result is identical whether function is/isn't run in parallel."""

        ls = np.random.randint(100000, 1000000, size=(100))
        ls = list(ls)
        cores = int(cpu_count() / 2)
        ls1 = ls_func(list(ls))
        ls2 = parallel.run(ls.copy(), ls_func, cores)
        self.assertListEqual(ls1, ls2)
