import logging
import unittest

import pandas as pd

from corpusama.corpus import stanza as _stanza
from corpusama.corpus import vertical
from corpusama.util.io import load_yaml

logger = logging.getLogger(__name__)
resources = ".local-only/stanza_resources"
processors = "tokenize,pos,lemma"
text = """This is an example sentence with the number 5 and symbol &.
# Another sentence could include a URL, like www.google.com."""


class Test_Vertical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = _stanza.load_nlp(resources, processors)
        cls.bundle = _stanza.run([text], [1], cls.nlp)
        cls.tagset = load_yaml("corpusama/corpus/tagset/ud_en_ewt.yml")

    def test_run_vertical(self):
        vert = vertical.stanza_to_vert(self.bundle, self.tagset)
        vert_head = "<s>\nThis\tDT\tthis-x"
        vert_tail = "www.google.com.\t.\twww.google.com.-x\n</s>\n"
        # doc first line
        self.assertEqual(vert.doc[0][:18], vert_head)
        # doc last line
        self.assertEqual(vert.doc[0][-41:], vert_tail)
        # other attributes
        self.assertTrue(vert.id, [1])
        self.assertTrue(vert.len, 1)
        self.assertTrue(vert.token, 22)
        self.assertTrue(type(pd.Timestamp(vert.date)), pd.Timestamp)
        self.assertIn("NN", vert.xpos)


class Test_Vertical_Functions(unittest.TestCase):
    def test_drop_empty_vert(self):
        df = pd.DataFrame({"vert": ["a", ""], "id": [0, 1]})
        df = vertical.drop_empty_vert(df)
        self.assertEqual(len(df), 1)
