import logging
import sqlite3 as sql

import pandas as pd

import rwapi

logger = logging.getLogger(__name__)
log_file = ".rwapi.log"


class Database:
    """A class to manage common SQL operations."""

    def open_db(self):
        """Opens SQL database connection."""

        self.conn = sql.connect(self.db_name)
        self.c = self.conn.cursor()
        logger.debug(f"{self.db_name}")

    def close_db(self):
        """Closes SQL database connection."""

        self.c.execute("pragma optimize")
        self.c.close()
        self.conn.close()
        logger.debug(f"{self.db_name}")

    def get_columns(self):
        """Gets lists of columns from db tables."""

        self.columns = {}
        self.c.execute("SELECT * FROM records")
        self.columns["records"] = [x[0] for x in self.c.description]
        self.c.execute("SELECT * FROM pdfs")
        self.columns["pdfs"] = [x[0] for x in self.c.description]
        self.c.execute("SELECT * FROM call_log")
        self.columns["call_log"] = [x[0] for x in self.c.description]
        logger.debug(f"{self.columns}")

    def make_tables(self):
        self.c.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
            params_hash NOT NULL,
            id PRIMARY KEY,
            country,
            date,
            disaster,
            disaster_type,
            feature,
            file,
            format,
            headline,
            image,
            language,
            ocha_product,
            origin,
            primary_country,
            source,
            status,
            theme,
            title,
            url,
            vulnerable_group,
            body
            ) WITHOUT ROWID"""
        )

        self.c.execute(
            """
            CREATE TABLE IF NOT EXISTS pdfs (
            id NOT NULL,
            file_id NOT NULL UNIQUE,
            description,
            filename NOT NULL,
            filesize NOT NULL,
            url NOT NULL UNIQUE,
            mimetype NOT NULL,
            FOREIGN KEY(id) REFERENCES records(id)
            )"""
        )

        self.c.execute(
            """
            CREATE TABLE IF NOT EXISTS call_log (
            params_hash PRIMARY KEY,
            parameters NOT NULL UNIQUE,
            rwapi_input NOT NULL,
            rwapi_date NOT NULL,
            count,
            total_count,
            FOREIGN KEY(params_hash) REFERENCES records(params_hash)
            )"""
        )

        logger.debug(f"tables generated, if missing")

    def make_dfs(self, tables=["records", "pdfs", "call_log"]):
        """Adds a dict of dfs to instance.

        'tables' specifies which dfs are created (must be from existing options).
        Caution: may use excessive memory."""

        self.dfs = {}
        if isinstance(tables, str):
            tables = [tables]
        if [x for x in tables if x not in ["records", "pdfs", "call_log"]]:
            raise ValueError(f"Accepted tables are {tables}")
        if "records" in tables:
            self.dfs["records"] = pd.read_sql("SELECT * FROM records", self.conn)
        if "pdfs" in tables:
            self.dfs["pdfs"] = pd.read_sql("SELECT * FROM pdfs", self.conn)
        if "call_log" in tables:
            self.dfs["call_log"] = pd.read_sql("SELECT * FROM call_log", self.conn)
        for k, v in self.dfs.items():
            self.dfs[k] = v.applymap(rwapi.convert.str_to_obj)

        logger.debug(f"generated {tables} dataframes")

    def _insert(self, df, table):
        # standardize datatypes
        df = df.astype(str)
        df = rwapi.convert.nan_to_none(df)
        # insert into SQL
        records = df[self.columns[table]].to_records(index=False)
        n_columns = len(self.columns[table])
        self.c.executemany(
            f"INSERT INTO {table} VALUES ({','.join(list('?' * n_columns))})", records
        )
        self.conn.commit()
        logger.debug(f"{len(df)} rows into {table}")

    def insert_pdfs(self):
        """Updates 'pdfs' table."""

        # get records with files
        self.make_dfs("records")
        df = self.dfs["records"]
        pdfs = df.loc[df["file"].notna()].copy()
        # make 1 row per file
        pdfs_flat = pd.json_normalize(pdfs["file"].explode())
        pdfs_flat.rename(columns={"id": "file_id"}, inplace=True)
        # add columns
        ids_temp = [
            [pdfs.iloc[x]["id"]] * len(pdfs.iloc[x]["file"]) for x in range(len(pdfs))
        ]
        pdfs_flat["id"] = [x for y in ids_temp for x in y]
        self._insert(pdfs_flat, "pdfs")

    def __repr__(self):
        return ""

    def __init__(
        self,
        db="data/reliefweb.db",
        log_level="info",
    ):
        # variables
        self.db_name = db
        self.log_level = log_level
        self.log_file = log_file
        self.orphans = {}

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logger.setLevel(numeric_level)

        self.open_db()
        self.make_tables()
        self.get_columns()
