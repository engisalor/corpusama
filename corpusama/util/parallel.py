import logging
from multiprocessing import Pool, cpu_count
from typing import Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def set_cores(cores: int = 0, divisor: int = 2) -> int:
    """Returns the number of cores made available for multiprocessing.

    Args:
        cores: Number of cores to use.
            (``0`` defaults to ``int(cpu_count/divisor)``).
        divisor: How much to throttle the default number of cores.
            (Active only when ``cores=0``. E.g., if ``divisor=2``,
            4 cores will be used on a device with 8 cores total).

    Notes:
        - Run ``set_cores`` before other parallelized functions
            and supply its output to any such function.
        - If ``multiprocessing.cpu_count`` raises ``NotImplementedError``
            on a device, default cores will fall back to 1."""

    if cores == 0:
        try:
            cores = int(cpu_count() / divisor)
        except NotImplementedError:
            cores = 1
    else:
        cores = cores
    logger.debug(f"{cores}")
    return cores


def dataframe(
    df: pd.DataFrame, func: Callable[[pd.DataFrame], pd.DataFrame], cores: int
) -> pd.DataFrame:
    """Splits a DataFrame into 1 chunk per core and runs a function in parallel.

    Args:
        df: Input DataFrame (returns modified df).
        func: Function to execute.
        cores: Number of cores to use."""

    df_split = np.array_split(df, cores)
    pool = Pool(cores)
    df = pd.concat(pool.map(func, df_split))
    pool.close()
    pool.join()
    return df
