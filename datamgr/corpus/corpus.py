"""Primary module for creating and maintaining corpora."""
import logging
import pathlib

from datamgr.database.database import Database
from datamgr.util import io as _io

logger = logging.getLogger(__name__)


class Corpus:
    """A class to make and maintain a corpus of vertical files.

    - db, a database
    - text_column, str, the column in raw with text content
    - drop_attr, [str], columns to drop from attributes (includes text_column)
    - resources, str, path to stanza resources
    - processors, str, stanza resources to load
    - tagset, str, path to corpus tagset YAML file"""

    from datamgr.corpus.archive import export_archive, make_archive
    from datamgr.corpus.attribute import export_attribute, make_attribute
    from datamgr.corpus.tagset import export_tagset
    from datamgr.corpus.vertical import make_vertical

    def __init__(
        self,
        db,
        text_column="body_html",
        drop_attr=["body", "disaster__type"],
        resources=".local-only/stanza_resources",
        processors="tokenize,pos,lemma",
        tagset="datamgr/corpus/tagset/ud_en_ewt.yml",
    ):
        # variables
        self.text_column = text_column
        self.resources = resources
        self.processors = processors
        self.drop_attr = drop_attr + [text_column]
        self.db_name = pathlib.Path(db)
        self.db = Database(db)
        self.tagset_file = tagset
        self.tagset = _io.load_yaml(tagset)
