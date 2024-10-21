import lzma
import unittest
from hashlib import blake2b
from pathlib import Path
from shutil import copy

from corpusama.util import util


class Test_Util(unittest.TestCase):
    def test_unique_xml_attrs(self):
        tags = ['<doc id="1" name="a" ></doc>', '<doc id="2" name="a" x="1.1" ></doc>']
        self.assertEqual(util.unique_xml_attrs(tags), {"name", "id", "x"})

    def test_clean_xml_tokens(self):
        invalid = ["\x0b", "\x0b", "\x0c", "\x0c", "\x1c", "\x1d", "\x1e"]
        item = "a ".join(invalid)
        self.assertEqual(util.clean_xml_tokens(item), "a a a a a a ")
        self.assertEqual(util.clean_xml_tokens(1), 1)
        self.assertEqual(util.clean_xml_tokens(None), None)

    def test_xml_quoteattr(self):
        self.assertEqual(util.xml_quoteattr(1), '"1"')
        self.assertEqual(
            util.xml_quoteattr("A str w/ & and trailing whitespace "),
            '"A str w/ &amp; and trailing whitespace"',
        )
        self.assertEqual(util.xml_quoteattr(None), None)

    def test_set_ref(self):
        ref_files = Path("test/test_util/").glob("set_ref_*.vert.REF")
        ref_files = sorted([x for x in ref_files])
        src_files = Path("test/test_util/").glob("set_ref_*.vert.SRC")
        src_files = sorted([x for x in src_files])
        for file in src_files:
            copy(file, file.with_suffix(""))
        out_files = Path("test/test_util/").glob("set_ref_*.vert")
        out_files = sorted([x for x in out_files])
        util.set_ref(out_files)
        orig_files = Path("test/test_util/").glob("set_ref_*ORIGINAL")
        orig_files = sorted([x for x in orig_files])
        ref = [blake2b(open(x, "rb").read()).hexdigest() for x in ref_files]
        src = [blake2b(open(x, "rb").read()).hexdigest() for x in src_files]
        out = [blake2b(open(x, "rb").read()).hexdigest() for x in out_files]
        orig = [blake2b(open(x, "rb").read()).hexdigest() for x in orig_files]
        # test output files overwrite originals with new ref values
        self.assertListEqual(ref, out)
        # test renamed original files are generated correctly
        self.assertListEqual(src, orig)
        for file in [*out_files, *orig_files]:
            file.unlink()

    def test_set_ref_xz(self):
        ref_files = Path("test/test_util/").glob("set_ref_*.vert.REF")
        ref_files = sorted([x for x in ref_files])
        src_files = Path("test/test_util/").glob("set_ref_*.vert.SRC")
        src_files = sorted([x for x in src_files])
        for file in src_files:
            with open(file) as source:
                txt = source.read()
            with lzma.open(file.with_suffix(".xz"), "wb") as out:
                out.write(txt.encode())
        in_files = Path("test/test_util/").glob("set_ref_*.vert.xz")
        in_files = sorted([x for x in in_files])
        util.set_ref(in_files)
        out_files = Path("test/test_util/").glob("set_ref_*.vert")
        out_files = sorted([x for x in out_files])
        ref = [blake2b(open(x, "rb").read()).hexdigest() for x in ref_files]
        out = [blake2b(open(x, "rb").read()).hexdigest() for x in out_files]
        # test output files overwrite originals with new ref values
        self.assertListEqual(ref, out)
        orig_files = Path("test/test_util/").glob("set_ref_*ORIGINAL")
        orig_files = sorted([x for x in orig_files])
        for file in [*out_files, *orig_files]:
            file.unlink()

    def test_set_ref_not_iterable(self):
        with self.assertRaises(TypeError):
            util.set_ref("single_file.vert")


if __name__ == "__main__":
    unittest.main()
