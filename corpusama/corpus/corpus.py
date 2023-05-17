"""Stores the Corpus class, for executing operations on corpora."""
from corpusama.database.database import Database
from corpusama.util import io as _io


class Corpus:
    """A class to make and maintain a corpus of vertical files.

    Args:
        config: YAML configuration file.

    Methods:
        Refer to modules in See Also.

    Notes:
        - Preset for use with ReliefWeb data.
        - Combines methods from other modules that together constitute.
            all the steps needed for making and maintaining a corpus
            (after raw data has been downloaded from a source).

    See Also:
        `archive`: Producing compressed archives of vertical files.
        `attribute`: Generating document attributes.
        `tagset`: Managing corpus tagsets.
        `vertical`: Generating vertical content from raw documents."""

    from corpusama.corpus.archive import export_archive, make_archive
    from corpusama.corpus.attribute import (
        export_attribute,
        make_attribute,
        unique_attribute,
    )
    from corpusama.corpus.langid import make_langid
    from corpusama.corpus.tagset import export_tagset
    from corpusama.corpus.vertical import make_vertical, outdated_vert

    def __init__(
        self,
        config: str,
    ):
        self.config = _io.load_yaml(config)
        self.changed = []
        self.db = Database(config)
        if self.config.get("source") == "reliefweb":
            from corpusama.source.reliefweb import ReliefWeb

            self.rw = ReliefWeb(config, self.db)
