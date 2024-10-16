import lzma
import re
import shutil
import unittest
from hashlib import blake2b
from pathlib import Path

from click.testing import CliRunner

from pipeline.stanza import base_pipeline

# NOTE rw_en.txt.conllu.REF has only one \n at EOF to pass pre-commit reqs.
# By default conllu files produces \n\n: tests must ignore this difference.


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
        cls.temp_conll = Path("test/test_pipeline/files/rw_en_temp.txt.conllu")

    def setUp(self):
        f = Path("test/test_pipeline/files/rw_en.txt.conllu.REF")
        shutil.copy(f, self.temp_conll)
        with open(self.temp_conll, "a") as f:
            f.write("\n")

    def tearDown(self) -> None:
        tmp_files = Path("test/test_pipeline/files").glob("*_temp.*")
        for file in tmp_files:
            file.unlink()

    def test_conll_to_vert(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails."""
        out = Path("test/test_pipeline/files/rw_en_temp.txt.vert")
        ref = Path("test/test_pipeline/files/rw_en.txt.vert.REF")
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [str(self.temp_conll), "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        self.assertEqual(file_hash(out), file_hash(ref))

    def test_conll_to_vert_splice_mwt(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails.

        <doc id="EN test cases">:
        - <s id="0"> `can't` (middle, hyphen)
        - <s id="1"> `cannot` (no hyphen)
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
        f = Path("test/test_pipeline/files/splice_mwt.conllu.REF")
        temp = Path("test/test_pipeline/files/splice_mwt_temp.conllu")
        out = Path("test/test_pipeline/files/splice_mwt_temp.vert")
        ref = Path("test/test_pipeline/files/splice_mwt.vert.REF")
        shutil.copy(f, temp)
        with open(temp, "a") as f:
            f.write("\n")
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [str(temp), "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        self.assertEqual(file_hash(out), file_hash(ref))
        out.unlink(missing_ok=True)

    def test_conll_to_vert_read_xz(self):
        """Compares file hashes. Use diff on out & ref if assertEqual fails."""
        f = Path("test/test_pipeline/files/rw_en.txt.conllu.REF")
        temp = Path("test/test_pipeline/files/rw_en_temp.txt.conllu.xz")
        out = Path("test/test_pipeline/files/rw_en_temp.txt.vert")
        ref = Path("test/test_pipeline/files/rw_en.txt.vert.REF")
        with open(f) as source:
            with lzma.open(temp, "w") as o:
                o.write(source.read().encode())
                o.write("\n".encode())
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [str(temp), "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        self.assertEqual(file_hash(out), file_hash(ref))

    def test_conll_to_vert_write_xz(self):
        """Checks if output file exists."""
        f = str(self.temp_conll)
        out = self.temp_conll.with_suffix(".vert.xz")
        result = self.runner.invoke(base_pipeline.conll_to_vert, [f, "--compress"])
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(out.exists())

    def test_conll_to_vert_write_xz_keep(self):
        """Checks if output file exists."""
        f = str(self.temp_conll)
        out = self.temp_conll.with_suffix(".vert")
        out_xz = self.temp_conll.with_suffix(".vert.xz")
        result = self.runner.invoke(
            base_pipeline.conll_to_vert, [f, "--compress", "--keep"]
        )
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(out.exists())
        self.assertTrue(out_xz.exists())

    def test_conll_to_vert_write_xz_no_force(self):
        """Checks if output file exists."""
        f = str(self.temp_conll)
        out = self.temp_conll.with_suffix(".vert")
        out_xz = self.temp_conll.with_suffix(".vert.xz")
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


class TestToConll(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.runner = CliRunner()
        cls.file_original = Path("test/test_pipeline/files/rw_en.txt")
        cls.file = Path("test/test_pipeline/files/rw_en_temp.txt")
        shutil.copy(cls.file_original, cls.file)

    def tearDown(self) -> None:
        tmp_files = Path("test/test_pipeline/files").glob("*_temp.*")
        for file in tmp_files:
            file.unlink()

    def test_to_conll(self):
        out = self.file.with_suffix(".txt.conllu")
        ref_file = self.file_original.with_suffix(".txt.conllu.REF")
        with open(ref_file) as f:
            ref_lines = f.readlines()
        result = self.runner.invoke(
            base_pipeline.to_conll, [str(self.file), "--lang", "en"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(out) as f:
            out_lines = f.readlines()
        self.assertListEqual(ref_lines[:18], out_lines[:18])

    def test_to_conll_from_xz(self):
        file_xz = self.file.with_suffix(".txt.xz")
        with open(self.file) as source:
            with lzma.open(file_xz, "w") as o:
                o.write(source.read().encode())
        out = self.file.with_suffix(".txt.xz.conllu")
        ref_file = self.file_original.with_suffix(".txt.conllu.REF")
        with open(ref_file) as f:
            ref_lines = f.readlines()
        result = self.runner.invoke(
            base_pipeline.to_conll, [str(file_xz), "--lang", "en"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(out) as f:
            out_lines = f.readlines()
        self.assertListEqual(ref_lines[:18], out_lines[:18])


if __name__ == "__main__":
    unittest.main()
