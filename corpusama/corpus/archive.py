"""A module for managing archived corpus content."""
import logging
import lzma
import pathlib

import pandas as pd

from corpusama.corpus import attribute
from corpusama.database.database import Database
from corpusama.util import decorator, parallel, util

logger = logging.getLogger(__name__)


def make_archive(self, years: list = [], cores: int = 0, size: int = 1000) -> None:
    """Adds XZ archives of vertical documents to the ``_archive`` table, by year.

    Args:
        self: A ``Corpus`` object.
        years: Year(s) to archive (defaults to all).
        cores: Max number of cores to use in parallel.
            (each core processes 1 year at a time).
        size: Number of texts to process at a time while making an archive.

    Warning:
        If ``cores`` and/or ``size`` are too large, uses excessive
        memory for large corpora or corpora with very large texts."""

    def limit_cores(cores: int, years: list) -> int:
        if cores > len(years):
            cores = len(years)
        return cores

    # set variables
    cores = parallel.set_cores(cores)
    years = get_years(self, years)
    if not years:
        raise ValueError("No valid years to archive.")
    cores = limit_cores(cores, years)
    # create and insert archives in parallel in batches
    archive = Archive(size, self.db_name)
    for i in range(0, len(years), cores):
        _years = years[i : i + cores]
        _cores = limit_cores(cores, _years)
        logger.debug(f"processing {_cores}: {_years}")
        archives = parallel.run(_years, archive.make, _cores)
        for x in range(len(_years)):
            _insert_archive(self, _years[x], archives[x])


class Archive:
    """A class to supply additional variables when making an archive.

    Methods:
        make: The method to execute for making an archive."""

    def __init__(self, size: int, db_name: str):
        self.size = size
        self.db_name = db_name

    def make(self, years: list) -> list:
        """Returns a list of compressed archives with all texts for each year."""

        corpus = Database(self.db_name)
        corpus.size = self.size
        archives = []
        for year in years:
            corpus.archive = []
            corpus.archive_run = 0
            _batch(corpus, year)
            docs = len(corpus.archive)
            archive, t = _compress_archive(corpus.archive)
            archives.append(archive)
            logger.debug(f"{t:,}s - {year} - {docs:,} docs")
        return archives


@decorator.timer
def _compress_archive(archive: list) -> bytes:
    """Compresses a list of texts into a bytes object with ``lzma``."""

    archive = "\n".join(archive).lstrip()
    return lzma.compress(bytes(archive, "utf-8"))


def _insert_archive(self, year: int, archive: str) -> None:
    """Inserts a compressed archive of vertical texts into the ``_archive`` table.

    Args:
        self: A Corpus object.
        year: The year to compress.
        archive: A bytes object of compressed vertical texts.

    Notes:
        (For developers): When using multiprocessing, XZ archives are silently
        converted to ``np.bytes_``: convert back to ``bytes`` before insertion."""

    # get document count
    query = """
    SELECT count(_vert.id) FROM _vert
        LEFT JOIN _raw
        ON _vert.id = _raw.id
        WHERE json_extract(_raw.date,'$.original')
            LIKE ?"""
    res = self.db.c.execute(query, ("".join([str(year), "%"]),))
    batch = res.fetchall()
    if not batch:
        batch = [[None]]
    # insert archive row
    df = pd.DataFrame()
    df["year"] = [year]
    df["doc_count"] = [batch[0][0]]
    df["archive_date"] = [util.now()]
    df["archive"] = [bytes(archive)]
    self.db.insert(df, "_archive")


@decorator.while_loop
def _batch(self, year: int) -> None:
    """Creates ``Corpus.archive`` content for a year in batches.

    Args:
        self: A ``Corpus`` object.
        year: Year to be archived."""

    # get vertical data
    query = """
    SELECT * FROM _vert
        LEFT JOIN _raw
        ON _vert.id = _raw.id
        WHERE json_extract(_raw.date,'$.original')
            LIKE ?
        LIMIT ?,?"""
    offset = self.archive_run * self.size
    batch = self.c.execute(
        query, ("".join([str(year), "%"]), offset, self.size)
    ).fetchall()
    if not batch:
        return False
    # make joined df
    cols = self.tables["_vert"] + self.tables["_raw"]
    df = util.join_results(batch, cols)
    df["vert"] = df.apply(lambda row: attribute.join_vert(row), axis=1)
    # add vertical content archives
    self.archive.extend(df["vert"].tolist())
    # continue loop
    self.archive_run += 1
    return True


def export_archive(self, years: list = []) -> None:
    """Exports compressed vertical archives to ``data/<db_name>/<year>.vert.xz``.

    Args:
        self: A ``Corpus`` object.
        years: List of years to export (defaults to all)."""

    years = get_years(self, years)
    dir = pathlib.Path(f"data/{self.db_name.stem}")
    dir.mkdir(exist_ok=True)
    for year in years:
        res = self.db.c.execute("SELECT * FROM _archive WHERE year=?", (year,))
        batch = res.fetchone()
        if batch:
            file = dir / pathlib.Path(f"{batch[0]}.vert.xz")
            with open(file, "wb") as f:
                f.write(batch[3])
                logger.debug(f"{file}")
        else:
            logger.debug(f"{year} - no such archive")


def get_years(self, years: list = []):
    """Returns an ordered set of years from ``_raw.date.original`` values.

    Args:
        self: A Corpus object.
        years: Years to include (defaults to all;
            ignores non-existing values; refers to the ``date.original`` field)."""

    res = self.db.c.execute("SELECT json_extract(_raw.date,'$.original') FROM _raw")
    years_exist = set([x[0][:4] for x in res.fetchall()])
    years_exist = sorted(years_exist)

    if years:
        if isinstance(years, int):
            years = [years]
        years = [x for x in years if str(x) in years_exist]
        return years
    else:
        return years_exist
