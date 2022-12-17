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
    logger.debug(f"{cores} max")
    return cores


def limit_cores(cores: int, ls: list) -> int:
    """Limits ``cores`` to always be equal or lesser than the length of ``ls``.

    Args:
        cores: Number of cores to use for multiprocessing.
        ls: A list of values to process in parallel.

    Notes:
        Prevents ``parallel.run`` from trying to use more cores than necessary."""

    if cores > len(ls):
        cores = len(ls)
    return cores


def run(iterable: iter, func: Callable, cores: int) -> iter:
    """Splits an iterable into 1 chunk per core and runs a function in parallel.

    Args:
        iterable: E.g., a ``list`` or ``DataFrame``.
        func: Function to execute (returns modified iterable).
        cores: Number of cores to use."""

    _split = np.array_split(iterable, cores)
    pool = Pool(cores)
    if isinstance(iterable, pd.DataFrame):
        iterable = pd.concat(pool.map(func, _split))
    elif isinstance(iterable, list):
        iterable = np.concatenate(pool.map(func, _split))
        iterable = list(iterable)
    else:
        raise TypeError(f"Type {type(iterable)} not implemented for ``parallel.run``")
    pool.close()
    pool.join()
    return iterable
