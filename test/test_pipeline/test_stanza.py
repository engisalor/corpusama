import lzma
import re
import unittest
from hashlib import blake2b
from pathlib import Path

from click.testing import CliRunner

from pipeline.stanza import base_pipeline


def file_hash(file):
    with open(file, "rb") as f:
        txt = f.read()
    return blake2b(txt).digest().hex()


class TestOtherFuncs(unittest.TestCase):
    def test_wrap_lines(self):
        doc = "A wra-\npped word."
        ref = "A wrapped \nword."
        a = re.compile(r"( \w+)-\n(\w+ *)")
        doc = a.sub(base_pipeline.wrap_lines, doc)
        self.assertEqual(ref, doc)


class TestConllToVert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()
        cls.rw_en_file = Path("test/test_pipeline/files/rw_en.txt.conllu")
        cls.splice_mwt_file = Path("test/test_pipeline/files/splice_mwt.conllu")
        cls.rw_en_file_xz = cls.rw_en_file.with_suffix(".conllu.xz")
        with open(cls.rw_en_file) as source:
            with lzma.open(cls.rw_en_file_xz, "w") as o:
                o.write(source.read().encode())

    def tearDownClass(cls):
        cls.rw_en_file_xz.unlink(missing_ok=True)

    def test_conll_to_vert(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails."""
        f = str(self.rw_en_file)
        out = self.rw_en_file.with_suffix(".vert")
        ref = self.rw_en_file.with_suffix(".vert.REF")
        result = self.runner.invoke(base_pipeline.conll_to_vert, [f, "--no-compress"])
        self.assertEqual(file_hash(out), file_hash(ref))
        self.assertTrue(result.exit_code == 0)
        out.unlink()

    def test_conll_to_vert_splice_mwt(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails.

        <doc id="EN test cases">:
        - <s id="0"> `can't` (middle, hypen)
        - <s id="1"> `cannot` (no hypen)
        - <s id="2"> `families'` (start, end, plural possessive)
        - <s id="3"> `Stakeholders'` (start, preceded by mwt w/ same positions 1-2)
        - <s id="4"> `Girl's` (singular possessive)
        - <s id="5"> `wasn't`
        - <s id="6"> `Don't`

        <doc id="ES test cases">:
        - <s id="0"> `del` (de+el)
        - <s id="1"> `decirlo` (verb+el)
        - <s id="2"> `apropiárselo` (three tokens)
        """
        f = str(self.splice_mwt_file)
        out = self.splice_mwt_file.with_suffix(".vert")
        ref = self.splice_mwt_file.with_suffix(".vert.REF")
        result = self.runner.invoke(base_pipeline.conll_to_vert, [f, "--no-compress"])
        self.assertEqual(file_hash(out), file_hash(ref))
        self.assertTrue(result.exit_code == 0)
        out.unlink()

    def test_conll_to_vert_read_xz(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails."""
        f = str(self.rw_en_file)
        out = self.rw_en_file.with_suffix(".vert")
        ref = self.rw_en_file.with_suffix(".vert.REF")
        result = self.runner.invoke(base_pipeline.conll_to_vert, [f, "--no-compress"])
        self.assertTrue(result.exit_code == 0)
        self.assertEqual(file_hash(out), file_hash(ref))
        out.unlink(missing_ok=True)

    def test_conll_to_vert_write_xz(self):
        """Checks if output file exists."""
        f = str(self.rw_en_file)
        out = self.rw_en_file.with_suffix(".vert.xz")
        result = self.runner.invoke(base_pipeline.conll_to_vert, [f, "--compress"])
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(out.exists())
        out.unlink()

    def test_conll_to_vert_write_xz_keep(self):
        """Checks if output file exists."""
        f = str(self.rw_en_file)
        out = self.rw_en_file.with_suffix(".vert")
        out_xz = self.rw_en_file.with_suffix(".vert.xz")
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--compress", "--keep"]
        )
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(out.exists())
        self.assertTrue(out_xz.exists())
        out.unlink()
        out_xz.unlink()

    def test_conll_to_vert_write_xz_no_force(self):
        """Checks if output file exists."""
        f = str(self.rw_en_file)
        out = self.rw_en_file.with_suffix(".vert")
        out_xz = self.rw_en_file.with_suffix(".vert.xz")
        # no compress
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--no-compress", "--force"]
        )
        self.assertTrue(result.exit_code == 0)
        result2 = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--no-compress", "--no-force"]
        )
        self.assertTrue(result2.exit_code == 1)
        self.assertTrue("already exists" in str(result2.exception))
        # compress, only .xz exists
        result3 = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--compress", "--force"]
        )
        self.assertTrue(result3.exit_code == 0)
        out.unlink(missing_ok=True)
        result4 = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--compress", "--no-force"]
        )
        self.assertTrue(result4.exit_code == 1)
        self.assertTrue("already exists" in str(result4.exception))
        out.unlink(missing_ok=True)
        out_xz.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
