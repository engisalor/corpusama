import unittest
from dataclasses import dataclass

import stanza

from datamgr.corpus import stanza as _stanza
from datamgr.util.dataclass import DocBundle


@dataclass
class Word:
    text: str = "is"
    lemma: str = "be"
    xpos: str = "VBZ"


resources = ".local-only/stanza_resources"
processors = "tokenize,pos,lemma"
text = """This is an example sentence with the number 5 and symbol &.
Another sentence could include a URL, like www.google.com."""


class Test_Stanza_Load(unittest.TestCase):
    def test_load_nlp(self):
        nlp = _stanza.load_nlp(resources, processors)
        self.assertEqual(type(nlp), stanza.Pipeline)


class Test_Stanza_Usage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = _stanza.load_nlp(resources, processors)
        cls.doc = cls.nlp.process(text)

    def test_get_xpos(self):
        xpos = _stanza.get_xpos([self.doc])
        test_xpos = [",", ".", "NN", "VB"]
        for x in test_xpos:
            self.assertIn(x, xpos)

    def test_fix_lemma_number(self):
        word_5 = self.doc.sentences[0].words[8]
        self.assertEqual(_stanza.fix_lemma(word_5), "[number]")

    def test_fix_lemma_do_nothing(self):
        word_This = self.doc.sentences[0].words[0]
        self.assertEqual(_stanza.fix_lemma(word_This), "this")

    def test_fix_lemma_no_lemma(self):
        word = Word(lemma=None)
        self.assertEqual(_stanza.fix_lemma(word), "is")

    def test_run(self):
        bundle = _stanza.run([text], [1], self.nlp)
        self.assertIsInstance(bundle, DocBundle)
