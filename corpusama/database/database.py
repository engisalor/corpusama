"""Stores the Database class and methods for managing SQL content."""
import logging
import pathlib
import re
import sqlite3 as sql

import pandas as pd

from corpusama._version import __version__
from corpusama.util import convert

logger = logging.getLogger(__name__)


class Database:
    """A class for managing an SQL database with corpusama content.

    Args:
        db: A database filename, e.g., ``mycorpus.db``.
        dir: The destination directory name, defaults to ``data``.

    Methods:
        open_db: Opens a database.
        close_db: Closes a database.
        get_schema: Loads .sql files in cwd.
        get_tables: Makes a dict of database tables and columns.
        insert: Inserts data into a table.
        update_column: Updates column data.
        fetch_batch: Returns a slice of table rows.
        set_about: Makes a table with database metadata.

    Attributes:
        c (Cursor): A database cursor.
        conn (Connection): A database connection.
        path (Path): The database filepath.
        schema (dict): A dictionary of loaded .sql strings.
        tables (list): A list of tables and their columns.

    Notes:
        Database objects are used by other modules to manage content.
        E.g., a ``Corpus`` object instantiates a ``Database`` as a ``db``
        attribute. It is not necessary to instantiate a ``Database`` by
        itself unless specific operations will be executed without
        making use of other modules.

        Instantiating a ``Database`` runs methods to quickly get started:
        - ``open_db``
        - ``get_schema``
        - ``get_tables``
        - ``set_about``"""

    def open_db(self) -> None:
        """Opens an SQL database connection."""

        self.conn = sql.connect(self.path)
        self.c = self.conn.cursor()
        logger.debug(f"{self.path}")

    def close_db(self) -> None:
        """Closes an SQL database connection."""

        self.c.execute("pragma optimize")
        self.c.close()
        self.conn.close()
        logger.debug(f"{self.path}")

    def get_schema(self) -> None:
        """Loads any .sql files in cwd into a dictionary at ``Database.schema``.

        Note:
            Schema are used to generate tables for a corpus
            and other .sql files can be added to save common tasks."""

        self.schema = pathlib.Path("").glob("**/*.sql")
        self.schema = {x.stem: {"path": x} for x in self.schema}
        for v in self.schema.values():
            with open(v["path"], "r") as f:
                v["query"] = f.read()
        logger.debug(f"{len(self.schema)}")

    def get_tables(self) -> None:
        """Makes a dict of database tables and their columns at ``Corpus.tables``."""

        self.tables = {}
        res = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        # get tables if db not empty
        if [x[0] for x in res.fetchall()]:
            queries = [
                "SELECT * FROM _about",
                "SELECT * FROM _log",
                "SELECT * FROM _pdf",
                "SELECT * FROM _raw",
                "SELECT * FROM _vert",
                "SELECT * FROM _archive",
            ]
            for q in queries:
                # add table
                key = re.search(r"\w+$", q).group()
                try:
                    self.tables[key] = [x[0] for x in self.c.execute(q).description]
                except sql.OperationalError:
                    logger.debug(f"{key} does not exist")

        logger.debug(f"{self.tables}")

    def insert(self, df: pd.DataFrame, table: str) -> None:
        """Inserts/replaces a DataFrame into a table.

        Note:
            Uses a standardized insert command that converts
            nan-like values to ``None``.

        See Also:
            - ``util.convert.to_json_or_str``
            - ``util.convert.nan_to_none``"""

        # standardize datatypes
        df = df.applymap(convert.to_json_or_str)
        df = df.apply(convert.nan_to_none)
        # insert into SQL
        records = df[self.tables[table]].to_records(index=False)
        n_columns = len(self.tables[table])
        values = ",".join(list("?" * n_columns))
        self.c.executemany(
            f"INSERT OR REPLACE INTO {table} VALUES ({values})",
            records,
        )
        self.conn.commit()
        logger.debug(f"{len(df)} row(s) into {table}")

    def update_column(
        self, table: str, column: str, series: pd.Series, rowids: list
    ) -> None:
        """Updates the values for a table column according to rowid.

        Args:
            table: The table.
            column: The column.
            series: The new data .
            rowids: The column's rowids.

        See Also:
            - ``util.convert.to_json_or_str``
            - ``util.convert.nan_to_none``"""

        series = series.apply(convert.to_json_or_str)
        series = convert.nan_to_none(series)
        self.c.executemany(
            f"UPDATE {table} SET {column} = ? WHERE rowid = ?", zip(series, rowids)
        )
        self.conn.commit()
        logger.debug(f"{len(series)} values into {table}.{column}")

    def fetch_batch(self, run: int, size: int, query: str) -> tuple:
        """Fetches SQL batches using a limit and offset.

        Args:
            run: The current run in a while loop.
            size: The maximum number of rows to select.
            query: The SQL query to repeat in loop.

        Returns:
            A tuple of fetched content and the current offset,
            where ``offset = run * size``."""

        offset = run * size
        batch = self.c.execute(query, (offset, size)).fetchall()
        return batch, offset

    def _add_missing_columns(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        """Returns a DataFrame with database table columns added when missing.

        Args:
            df: A DataFrame to be inserted.
            table: The destination table."""

        for x in [x for x in self.tables[table] if x not in df.columns]:
            df[x] = None
        return df

    def set_about(self) -> None:
        """Records metadata about a database in its own table.

        Note:
            Includes the current library version and can be used to store
            other metadata in ``_about.key`` and ``_about.value`` columns."""

        query = """CREATE TABLE IF NOT EXISTS _about
            ('key' TEXT PRIMARY KEY, 'value' TEXT)"""
        self.c.execute(query)
        values = ("version", __version__)
        self.c.execute("INSERT OR REPLACE INTO _about VALUES (?,?)", values)
        self.conn.commit()

    def __repr__(self):
        return ""

    def __init__(
        self,
        db: str,
        dir: str = "data",
    ):
        self.path = pathlib.Path(dir) / pathlib.Path(db)
        self.path.parent.mkdir(exist_ok=True)
        self.open_db()
        self.get_schema()
        self.get_tables()
        self.set_about()
