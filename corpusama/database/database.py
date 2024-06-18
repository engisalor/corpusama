"""Stores the Database class and methods for managing SQL content."""
import logging
import pathlib
import re
import sqlite3 as sql

import pandas as pd

from corpusama.util import convert
from corpusama.util import io as _io


class Database:
    """A class for managing an SQL database with corpusama content.

    Args:
        config: YAML configuration file.
    """

    def open_db(self) -> None:
        """Opens an SQL database connection."""
        self.conn = sql.connect(self.path)
        self.c = self.conn.cursor()
        logging.debug(f"{self.path}")

    def close_db(self) -> None:
        """Closes an SQL database connection."""
        self.c.execute("pragma optimize")
        self.c.close()
        self.conn.close()
        logging.debug(f"{self.path}")

    def get_tables(self) -> None:
        """Makes a dict of database tables from `config.schema`."""

        def _name(table: str):
            return re.findall(r"CREATE TABLE.*(_\w+).*", table)[0]

        def _columns(table: str):
            return [x.strip("\n '") for x in re.findall(r"\n'\w+'", table) if x]

        with open(self.config.get("schema")) as f:
            schema = f.read()
        tables = [x for x in schema.split(";") if x.strip()]
        self.tables = {_name(t): _columns(t) for t in tables}

    def insert(self, df: pd.DataFrame, table: str) -> None:
        """Inserts/replaces a DataFrame into a table."""
        # standardize datatypes
        df = df.map(convert.to_json_or_str)
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
        logging.debug(f"{len(df)} row(s) into {table}")

    def update_column(
        self, table: str, column: str, series: pd.Series, rowids: list
    ) -> None:
        """Updates the values for a table column according to rowid.

        Args:
            table: The table.
            column: The column.
            series: The new data .
            rowids: The column's rowids.
        """
        if table not in self.tables.keys():
            raise ValueError(f"table {table} not in {self.tables.key()}")
        if column not in self.tables.get(table):
            raise ValueError(f"column {column} not in {self.tables.get(table)}")
        series = series.apply(convert.to_json_or_str)
        series = convert.nan_to_none(series)
        q = f"UPDATE {table} SET {column} = ? WHERE rowid = ?"  # nosec
        self.c.executemany(q, zip(series, rowids))
        self.conn.commit()
        logging.debug(f"{len(series)} values into {table}.{column}")

    def _add_missing_columns(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        """Returns a DataFrame with database table columns added when missing.

        Args:
            df: A DataFrame to be inserted.
            table: The destination table.
        """
        for x in [x for x in self.tables[table] if x not in df.columns]:
            df[x] = None
        return df

    def __init__(
        self,
        config: str,
    ):
        secrets = pathlib.Path(config).with_suffix(".secret.yml")
        self.config = _io.load_yaml(config) | _io.load_yaml(secrets)
        self.path = pathlib.Path(self.config.get("db_name"))
        self.path.parent.mkdir(exist_ok=True)
        self.open_db()
        self.c.executescript(_io.load_yaml(self.config.get("schema")))
        self.get_tables()
