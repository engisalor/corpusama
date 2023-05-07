import unittest

import stanza

from corpusama.util import langid


class Test_LangID(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = stanza.Pipeline(
            lang="multilingual",
            processors="langid",
            download_method=None,
        )
        cls.file = "test/test_util/text-file.txt"
        cls.empty_file = "test/test_util/empty-file.txt"
        cls.clean_kwargs = dict(
            min_len=3,
            drops=langid.drop_all,
        )

    @classmethod
    def tearDownClass(cls):
        pass

    def test_clean_lines(self):
        lines = ["a", "  \n\n # 34 abcde  � "]
        ref = ["abcde"]
        self.assertEqual(langid.clean_lines(lines, 3, langid.drop_all), ref)

    def test_sample_lines(self):
        lines = ["a", "b", "c", "  \n\n # 34 abcde  � ", "fghij"]
        ref = sorted(["abcde", "fghij"])
        sam = sorted(langid.sample_lines(lines, 4, 10, self.clean_kwargs))
        self.assertEqual(sam, ref)

    def test_stanza_full(self):
        dt = langid.stanza_full(self.file, langid.sample_kwargs, self.nlp)
        self.assertTrue("en" in dt["langs"].keys())

    def test_stanza_full_empty(self):
        dt = langid.stanza_full(self.empty_file, langid.sample_kwargs, self.nlp)
        self.assertEqual(dt["langs"], {})

    def test_fasttext_full(self):
        dt = langid.fasttext_full(
            self.file, langid.sample_kwargs, langid.fasttext_source
        )
        self.assertTrue("en" in dt["langs"].keys())

    def test_fasttext_empty_full(self):
        dt = langid.fasttext_full(
            self.empty_file, langid.sample_kwargs, langid.fasttext_source
        )
        self.assertEqual(dt["langs"], {})

    def test_identify(self):
        df = langid.identify(
            self.file,
            langid.sample_kwargs,
            self.nlp,
            fasttext_source=langid.fasttext_source,
        )
        self.assertEqual(df["top"][0], "en")

    def test_identify_empty(self):
        df = langid.identify(
            self.empty_file,
            langid.sample_kwargs,
            self.nlp,
            fasttext_source=None,
        )
        self.assertEqual(df["langs"][0], {})


if __name__ == "__main__":
    unittest.main()
