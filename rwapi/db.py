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
            country,
            date,
            disaster,
            disaster_type,
            feature,
            file,
            format,
            headline,
            id PRIMARY KEY,
            image,
            language,
            ocha_product,
            origin,
            primary_country,
            rwapi_date,
            rwapi_input,
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
            id PRIMARY KEY,
            qty,
            description,
            exclude,
            download,
            size_mb,
            words_pdf,
            lang_pdf,
            lang_score_pdf,
            orphan,
            url
            )"""
        )

        self.c.execute(
            """
            CREATE TABLE IF NOT EXISTS call_log (
            parameters PRIMARY KEY,
            rwapi_input,
            rwapi_date,
            count,
            total_count
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

    def orphaned_ids(self):
        """Detects ids in 'pdfs' that are missing in 'records'."""

        self.c.execute("""SELECT id FROM pdfs EXCEPT SELECT id FROM records;""")
        self.orphan_ids = self.c.fetchall()
        self.orphan_ids = [item[0] for item in self.orphan_ids if item]
        if len(self.orphan_ids):
            logger.warning(f"{len(self.orphan_ids)}")
        else:
            logger.debug(f"{len(self.orphan_ids)}")

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

        # logging
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        logger.setLevel(numeric_level)

        self.open_db()
        self.make_tables()
        self.get_columns()
        self.orphaned_ids()
