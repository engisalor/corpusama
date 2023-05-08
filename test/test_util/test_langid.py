import pathlib
import unittest

import fasttext
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
        cls.model = fasttext.load_model("./fastText/lid.176.bin")
        cls.file = "test/test_util/text-file.txt"
        cls.files = [cls.file, "test/test_util/text-file-2.txt"]
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
        dt = langid.fasttext_full(self.file, langid.sample_kwargs, self.model)
        self.assertTrue("en" in dt["langs"].keys())

    def test_fasttext_empty_full(self):
        dt = langid.fasttext_full(self.empty_file, langid.sample_kwargs, self.model)
        self.assertEqual(dt["langs"], {})

    def test_identify(self):
        df = langid.identify(self.file, langid.sample_kwargs, self.nlp, self.model)
        self.assertEqual(df["top"][0], "en")

    def test_identify_empty_no_fa(self):
        df = langid.identify(
            self.empty_file,
            langid.sample_kwargs,
            self.nlp,
            None,
        )
        self.assertEqual(df["langs"][0], {})

    def test_file_concat(self):
        out = [
            "test/test_util/.file-concat.xml",
            "test/test_util/.file-concat-clean.xml",
        ]
        langid.file_concat(self.files, "test/test_util/.file-concat", self.clean_kwargs)
        for file in out:
            with open(file) as f:
                text = f.read()
            tag = '<file path="test/test_util/text-file.txt">'
            tag2 = '<file path="test/test_util/text-file-2.txt">'
            self.assertIn(tag, text)
            self.assertIn(tag2, text)
            pathlib.Path(file).unlink(missing_ok=True)

    def test_file_stats(self):
        out = "test/test_util/.file-stats"
        langid.file_stats(self.files, out)
        with open(out + ".csv") as f:
            text = f.read()
        _string = "chars_q0,chars_q1,chars_q2,chars_q3,chars_q4"
        self.assertIn(_string, text)
        pathlib.Path(out + ".csv").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
