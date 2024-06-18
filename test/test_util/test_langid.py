import pathlib
import unittest

# import fasttext
# import pandas as pd
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
        # cls.model = fasttext.load_model("./fastText/lid.176.bin")
        cls.file = "test/test_util/text-file.txt"
        cls.files = [cls.file, "test/test_util/text-file-2.txt"]
        cls.empty_file = "test/test_util/empty-file.txt"
        cls.sample_kwargs = dict(
            sample_size=0,
            tries=5,
            min_len=3,
            drops=langid.drop_all,
        )

    @classmethod
    def tearDownClass(cls):
        pass

    def test_clean_lines(self):
        lines = ["a", "  \n\n # 34 abcde  � "]
        ref = ["a", "abcde"]
        self.assertEqual(langid.clean_lines(lines, langid.drop_all), ref)

    def test_sample_lines(self):
        lines = ["a", "b", "c", "  \n\n # 34 abcde  � ", "fghij"]
        ref = sorted(["a", "abcde", "b", "c", "fghij"])
        sam = sorted(langid.sample_lines(lines, 0, 3, langid.drop_all))
        self.assertEqual(sam, ref)

    def test_identify_stanza(self):
        dt = langid.identify_stanza(self.file, True, self.sample_kwargs, self.nlp)
        self.assertTrue("en" in dt["langs"])

    def test_identify_stanza_empty(self):
        dt = langid.identify_stanza(self.empty_file, True, self.sample_kwargs, self.nlp)
        self.assertEqual(dt["langs"], [])

    # def test_identify_fasttext(self):
    #     dt = langid.identify_fasttext(self.file, True, self.sample_kwargs, self.model)
    #     self.assertTrue("en" in dt["langs"])

    # def test_fasttext_empty_full(self):
    #     dt = langid.identify_fasttext(
    #         self.empty_file, True, self.sample_kwargs, self.model
    #     )
    #     self.assertEqual(dt["langs"], [])

    def test_identify(self):
        df = langid.identify(self.file, self.sample_kwargs, self.nlp, None)
        self.assertEqual(df["tool"][0], "stanza")

    def test_identify_empty_no_fa(self):
        df = langid.identify(
            self.empty_file,
            self.sample_kwargs,
            self.nlp,
            None,
        )
        self.assertEqual(df["tool"][0], "stanza")

    # def test_LangID_texts_only_fa_with_empty(self):
    #     # NOTE: could break if text languages aren't predicted correctly
    #     texts = [
    #         "hello, my name is John\nand I speak English",
    #         " ",
    #         "hola, mi nombre es José\ny hablo español",
    #     ]
    #     lid = langid.LangID(
    #         texts, self.sample_kwargs, None, self.model, 0.6, is_file=False
    #     )
    #     self.assertTrue(pd.isnull(lid.df["file"][0]))
    #     self.assertEqual(lid.df["l1"][0], "en")
    #     self.assertTrue(pd.isnull(lid.df["l1"][1]))
    #     self.assertEqual(lid.df["l1"][2], "es")

    def test_file_concat(self):
        out = [
            "test/test_util/.file-concat.xml",
            "test/test_util/.file-concat-clean.xml",
        ]
        langid.file_concat(self.files, "test/test_util/.file-concat")
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
