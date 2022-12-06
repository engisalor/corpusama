"""Stores the Corpus class, for executing operations on corpora."""
import logging
import pathlib

from corpusama.database.database import Database
from corpusama.util import io as _io

logger = logging.getLogger(__name__)


class Corpus:
    """A class to make and maintain a corpus of vertical files.

    Args:
        db: A database filename (``myCorpus.db``).
        text_column: The column with raw text content.
        drop_attr: Columns to drop from attributes.
        resources: A path to stanza resources.
        processors: Stanza processors to load.
        tagset: A path to the corpus tagset YAML file.

    Attributes:
        db_name: The Database filename.
        tagset (dict): The loaded tagset file.
        tagset_file: The tagset filename (the initial ``tagset`` arg).

    Methods:
        Refer to modules in See Also.

    Notes:
        - Preset for use with ReliefWeb data.
        - Combines methods from other modules that together constitute.
            all the steps needed for making and maintaining a corpus
            (after raw data has been downloaded from a source).

    See Also:
        ``archive``: Producing compressed archives of vertical files.
        ``attribute``: Generating document attributes.
        ``tagset``: Managing corpus tagsets.
        ``vertical``: Generating vertical content from raw documents."""

    from corpusama.corpus.archive import export_archive, make_archive
    from corpusama.corpus.attribute import export_attribute, make_attribute
    from corpusama.corpus.tagset import export_tagset
    from corpusama.corpus.vertical import make_vertical, outdated_vert

    def __init__(
        self,
        db: str,
        text_column: str = "body_html",
        drop_attr: list = ["body", "disaster__type"],
        resources: str = ".local-only/stanza_resources",
        processors: str = "tokenize,pos,lemma",
        tagset: str = "corpusama/corpus/tagset/ud_en_ewt.yml",
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
