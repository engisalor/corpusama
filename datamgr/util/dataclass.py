"""Library dataclasses."""
import json
import logging

from datamgr.util import util

logger = logging.getLogger(__name__)


class DocBundle:
    """A class for organizing text data during corpus preparation.

    Variables to supply:
    - doc, [str], documents to process
    - id, [int], ids for docs

    Generated variables:
    - date, str, creation date

    Reserved variables:
    - token, int, token count
    - xpos, [str], unique xpos values"""

    def check_len(self):
        if not len(self.doc) == len(self.id):
            m = f"Lengths for doc and id differ: {len(self.doc)} != {len(self.id)}"
            raise ValueError(m)

    def __repr__(self):
        return f"DocBundle: {str(self.__dict__)}"

    def __init__(self, doc: list, id: list, token=None, xpos=None):
        self.doc = doc
        self.id = id
        self.check_len()
        self.len = len(doc)
        self.token = token
        self.xpos = xpos
        self.date = util.now()


class CorpusAttribute:
    """A class for corpus attributes.

    Used to generate entries for corpus configuration files.
    See https://www.sketchengine.eu/documentation/

    - config_entry generates a config file attribute entry with parameters"""

    def __repr__(self):
        return self.config_entry

    def set_config_entry(self):
        self.config_entry = f"""\nATTRIBUTE "{self.value}" """
        if self.parameters:
            self.config_entry += "{"
            for k, v in self.parameters.items():
                self.config_entry += f"\n    {k} {json.dumps(str(v))}"
            self.config_entry += "\n    }"
        return self.config_entry

    def __init__(self, attribute, parameters: dict = None):
        self.value = attribute
        self.parameters = parameters
        self.set_config_entry()
