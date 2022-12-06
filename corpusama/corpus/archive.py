"""A module for managing archived corpus content."""
import logging
import lzma

import pandas as pd

from corpusama.corpus import attribute
from corpusama.util import convert, decorator, util

logger = logging.getLogger(__name__)


def make_archive(self, mode: str, note=None, size=10, runs=0) -> None:
    """Makes an xz version of vertical documents in the ``_archive`` table.

    Args:
        self: A ``Corpus`` object.
        mode: What to archive (``full`` or ``add``).
        note: Comments about the archive.
        size: Number of documents to process at a time.
        runs: Maximum number of batches to run (for testing).

    Notes:
        - ``full`` creates a single archive with all available content.
        - ``add`` creates an archive of new content only.

        A version number is set based on the mode and existing content.
        Full archives are given a new version number: ``1.0``, ``2.0``, etc.
        Partial archives keep the major version number and increment
        the minor version number: adding to ``1.0`` will make archive ``1.1``.
        A whole corpus is the set of archives with the same version
        number: Corpus Version 1 is made up of ``1.0``, ``1.1``, etc.

    See Also:
        ``util.util.increment_version``"""

    # variables
    self.size = size
    self.archive_runs = runs
    self.archive_run = 0
    self.lzc = lzma.LZMACompressor()
    self.archive = []
    self.archive_ids = []
    # manage versions
    res = self.db.c.execute(
        "SELECT version FROM _archive WHERE ROWID = (SELECT MAX(ROWID) FROM _archive)"
    )
    old_version = res.fetchone()
    if old_version:
        version = util.increment_version(old_version[0], mode)
    else:
        version = "1.0"
    # make compressed archive content
    _, t = _batch(self, mode)
    self.archive.append(self.lzc.flush())
    # insert archive
    if not self.archive_ids:
        logger.debug("no documents to compress")
    else:
        df = pd.DataFrame()
        df["id"] = [self.archive_ids]
        df["version"] = version
        df["note"] = note
        df["archive_date"] = util.now()
        df["archive"] = b"".join(self.archive)
        self.db.insert(df, "_archive")
        logger.debug(f"v{version} - {t:,}s - {len(self.archive_ids)} docs")


@decorator.timer
@decorator.while_loop
def _batch(self, mode: str) -> None:
    """Combines vertical documents with their tags, then archives."""

    # get vertical data
    query = """SELECT * FROM _vert
    LEFT JOIN _raw
    ON _vert.id = _raw.id
    LIMIT ?,?;"""
    batch, offset = self.db.fetch_batch(self.archive_run, self.size, query)
    if not batch:
        return False
    if mode == "add":
        # skip existing
        res = self.db.c.execute("SELECT id FROM _archive")
        exists = [convert.str_to_obj(x[0]) for x in res.fetchall()]
        exists = set([x for y in exists for x in y])
        batch = [x for x in batch if x[0] not in exists]
        if not batch:
            self.archive_run += 1
            return True
    # make joined df
    cols = self.db.tables["_vert"] + self.db.tables["_raw"]
    df = util.join_results(batch, cols)
    drops = [x for x in self.drop_attr if x in df.columns]
    df.drop(drops, axis=1)
    # append compressed content
    df["vert"] = df.apply(lambda row: attribute.join_vert(row), axis=1)
    df["archive"] = df["vert"].apply(lambda x: self.lzc.compress(bytes(x, "utf-8")))
    self.archive.extend(df["archive"].tolist())
    self.archive_ids.extend(df["id"].tolist())
    # continue loop
    self.archive_run += 1
    repeat = util.limit_runs(self.archive_run, self.archive_runs)
    if not repeat:
        return False
    return repeat


def export_archive(self, version=None, date=None) -> None:
    """Exports archives matching a version or date.

    Args:
        self: A ``Corpus`` object.
        version (str): The major.minor version to export.
        date (str): The date of the archive to export.

    Notes:
        Use one argument only, ``version`` or ``date``.

        Generates an .xz archive at the path:
        ``data/<db_name>_<version>.vert.xz``."""

    # make query
    if version:
        res = self.db.c.execute("SELECT * FROM _archive WHERE version=?", (version,))
    elif date:
        _ = pd.Timestamp.fromisoformat(date)
        res = self.db.c.execute("SELECT * FROM _archive WHERE corpus_date=?", (date,))
    else:
        raise ValueError("Supply a date or version to export archives.")
    while True:
        batch = res.fetchone()
        if not batch:
            break
        file = f"data/{self.db_name.stem}_{batch[1]}.vert.xz"
        with open(file, "wb") as f:
            f.write(batch[4])
            logger.debug(f"{file}")
