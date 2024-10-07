import pathlib
import unittest

import fitz

from corpusama.source import pdf


class TestPDF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("test/test_source/sample-urls.txt") as f:
            cls.urls = f.readlines()
        cls.filenames = [
            f"test/test_source/sample-urls-{x}.pdf" for x in range(len(cls.urls))
        ]

    def setUp(cls):
        pass

    def test_clean_text(self):
        ref = "This is a text\n\nThat's not clean."
        text = " This   is a text\n\n\n\n  \n\t That's not clean.��"
        clean = pdf.clean_text(text)
        self.assertEqual(clean, ref)

    def test_extract_text(self):
        text = pdf.extract_text("test/test_source/sample.pdf")
        # check text
        self.assertIn("Lorem ipsum", text)
        # check whitespace between blocks
        self.assertIn("\n\n", text)

    @unittest.skip("make get requests manually")
    def test_request(self):
        file = pathlib.Path(self.filenames[0])
        pdf.get_request(file, self.urls[0])
        self.assertTrue(file.exists())
        file.unlink(missing_ok=True)

    def test_try_extract(self):
        # raises an error
        with self.assertRaises(fitz.FileDataError):
            pdf.extract_text("test/test_source/sample-corrupt.pdf", True)
        # shouldn't raise an error
        pdf._try_extract("test/test_source/sample-corrupt.pdf", True)

    def test_ExtractFiles(self):
        files = ["test/test_source/sample-corrupt.pdf", "test/test_source/sample.pdf"]
        files = [pathlib.Path(f) for f in files]
        extractor = pdf.ExtractFiles()
        extractor.run(files, 5)
        self.assertTrue(files[1].with_suffix(".txt").exists())
        files[1].with_suffix(".txt").unlink()


if __name__ == "__main__":
    unittest.main()
