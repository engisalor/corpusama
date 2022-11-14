import logging
import pathlib
import re
import sqlite3 as sql

import pandas as pd

from datamgr.util import convert

logger = logging.getLogger(__name__)


class Database:
    """A class to connect to a database and execute queries."""

    def open_db(self):
        """Opens SQL database connection."""

        self.conn = sql.connect(self.path)
        self.c = self.conn.cursor()
        logger.debug(f"{self.path}")

    def close_db(self):
        """Closes SQL database connection."""

        self.c.execute("pragma optimize")
        self.c.close()
        self.conn.close()
        logger.debug(f"{self.path}")

    def get_queries(self):
        """Finds and loads any .sql files in ./** to a dict at self.queries."""

        self.queries = pathlib.Path("").glob("**/*.sql")
        self.queries = {x.stem: {"path": x} for x in self.queries}
        for v in self.queries.values():
            with open(v["path"], "r") as f:
                v["query"] = f.read()
        logger.debug(f"{len(self.queries)}")

    def get_tables(self):
        """Makes a dict of {table:[columns]} at self.tables.

        Uses rw_select.sql statements to supply valid tables."""

        self.tables = {}
        res = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        # get tables if db not empty
        if [x[0] for x in res.fetchall()]:
            # prepare queries
            queries = self.queries["rw_select"]["query"].split(";")
            queries = [x.strip() for x in queries if x.strip()]
            for q in queries:
                # add table
                check_query(r"^SELECT \* FROM \w+$", q)
                key = re.search(r"\w+$", q).group()
                self.tables[key] = [x[0] for x in self.c.execute(q).description]
        logger.debug(f"{self.tables}")

    def get_df(self, table):
        """Loads one or more tables with pd.read_sql at self.df {table:DataFrame}.

        Converts strings to objects when possible."""

        self.df = {}
        if isinstance(table, str):
            tables = [table]
        if [x for x in tables if x not in self.tables.keys()]:
            raise ValueError(f"Tables must be in {self.tables.keys()}")
        queries = self.queries["rw_select"]["query"].split(";")
        queries = [x.strip() for x in queries if x.strip()]
        for q in queries:
            check_query(r"^SELECT \* FROM \w+$", q)
            key = re.search(r"\w+$", q).group()
            if key in tables:
                self.df[key] = pd.read_sql(q, self.conn)
                self.df[key] = self.df[key].applymap(convert.str_to_obj)
        logger.debug(f"{tables}")

    def insert(self, df, table):
        """Inserts/replaces a df into a table with a standardized insert command.

        Converts nan-like values to None, then converts all values to str."""

        # standardize datatypes
        df = df.astype(str)
        df = convert.nan_to_none(df)
        # insert into SQL
        records = df[self.tables[table]].to_records(index=False)
        n_columns = len(self.tables[table])
        values = ",".join(list("?" * n_columns))
        self.c.executemany(
            f"INSERT OR REPLACE INTO {table} VALUES ({values})",
            records,
        )
        self.conn.commit()
        logger.debug(f"{len(df)} rows into {table}")

    def __repr__(self):
        return ""

    def __init__(
        self,
        db,
        dir="data",
    ):
        # variables
        self.path = pathlib.Path(dir) / pathlib.Path(db)
        self.df = {}
        # execute
        self.path.parent.mkdir(exist_ok=True)
        self.open_db()
        self.get_queries()
        self.get_tables()


def check_query(pattern, query):
    """Checks that a query matches a regex pattern/raises an error."""

    if not re.match(pattern, query):
        raise ValueError(f"Prohibited pattern {query}\n(must be {pattern}")
