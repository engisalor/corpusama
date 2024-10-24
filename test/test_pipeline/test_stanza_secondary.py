import lzma
import unittest
from collections import OrderedDict
from pathlib import Path
from shutil import copy
from types import GeneratorType

from click.testing import CliRunner

from pipeline.stanza import secondary_pipeline


class TestConllToVert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self) -> None:
        pass

    def test_conll_to_vert(self):
        pass


class TestSecondaryPipelineUtils(unittest.TestCase):
    def test_chunk(self):
        gen = secondary_pipeline.chunks([1] * 10, 5)
        ref = [[1] * 5, [1] * 5]
        self.assertTrue(isinstance(gen, GeneratorType))
        self.assertEqual(str([x for x in gen]), str(ref))

    def test_get_xml_attrs(self):
        dt = secondary_pipeline.get_xml_attrs('<s id="5" lang="es">')
        ref = OrderedDict({"id": '"5"', "lang": '"es"'})
        self.assertDictEqual(dt, ref)

    def test_update_s_tag(self):
        dt = OrderedDict({"id": '"5"', "lang": '"es"'})
        s = secondary_pipeline.update_s_tag(dt)
        ref = '<s id="5" lang="es">\n'
        self.assertEqual(s, ref)

    def test_update_doc_tag(self):
        line = '<doc id="1" file_id="5">'
        s, n = secondary_pipeline.update_doc_tag(line, 0)
        ref = '<doc id="1" file_id="5" ref="1">\n'
        self.assertEqual(s, ref)
        self.assertEqual(1, n)

    def test_sort_files(self):
        files = ["file.2.vert", "file.1.vert", "file.10.vert"]
        files = [Path(x) for x in files]
        ref = ["file.1.vert", "file.2.vert", "file.10.vert"]
        out = secondary_pipeline.sort_files(files)
        self.assertListEqual(out, [Path(x) for x in ref])


class TestSecondaryPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()

    def test_langid(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        result = self.runner.invoke(secondary_pipeline.langid, [str(file)])
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".vert.lid.tsv.REF")) as f:
            ref = f.read()
        with open(file.with_suffix(".vert.lid.tsv")) as f:
            out = f.read()
        self.assertEqual(ref, out)
        file.with_suffix(".vert.lid.tsv").unlink()

    def test_langid_all_short(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        result = self.runner.invoke(
            secondary_pipeline.langid, [str(file), "--short=10", "--overwrite"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".vert.lid.tsv")) as f:
            out = f.read()
        self.assertEqual("", out)
        file.with_suffix(".vert.lid.tsv").unlink()

    def test_langid_all_long(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        result = self.runner.invoke(
            secondary_pipeline.langid, [str(file), "--long=2", "--overwrite"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".vert.lid.tsv")) as f:
            out = f.read()
        self.assertEqual("1\ten\n12\tes\n", out)
        file.with_suffix(".vert.lid.tsv").unlink()

    def test_langid_small_batch(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        result = self.runner.invoke(
            secondary_pipeline.langid, [str(file), "--batch=1", "--overwrite"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".vert.lid.tsv")) as f:
            out = f.read()
        self.assertEqual("1\ten\n12\tes\n", out)
        file.with_suffix(".vert.lid.tsv").unlink()

    def test_main(self):
        file1 = Path("test/test_pipeline/files/file.1.vert")
        file2 = Path("test/test_pipeline/files/file.2.vert")
        result = self.runner.invoke(
            secondary_pipeline.main, [str(file1), str(file2), "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        for file in [file1, file2]:
            with open(file.with_suffix(".vert.TMP")) as f:
                out = f.read()
            with open(file.with_suffix(".vert.TMP.REF")) as f:
                ref = f.read()
            self.assertEqual(ref, out)
            file.with_suffix(".vert.TMP").unlink()

    def test_main_with_langid(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        result = self.runner.invoke(secondary_pipeline.langid, [str(file)])
        self.assertTrue(result.exit_code == 0)
        result = self.runner.invoke(
            secondary_pipeline.main, [str(file), "--langid", "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".vert.TMP")) as f:
            out = f.read()
        with open(file.with_suffix(".vert.TMP.REF_lid")) as f:
            ref = f.read()
        self.assertEqual(ref, out)
        file.with_suffix(".vert.TMP").unlink()
        file.with_suffix(".vert.lid.tsv").unlink()

    def test_main_clear(self):
        src_file = Path("test/test_pipeline/files/file.1.vert")
        file = Path("test/test_pipeline/files/file-copy.1.vert")
        copy(src_file, file)
        result = self.runner.invoke(
            secondary_pipeline.main, [str(file), "--clear", "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file) as f:
            out = f.read()
        with open("test/test_pipeline/files/file.1.vert.TMP.REF") as f:
            ref = f.read()
            ref = ref.replace("file.1.vert", "file-copy.1.vert")
        self.assertEqual(ref, out)
        file.unlink()

    def test_main_compress(self):
        file = Path("test/test_pipeline/files/file.1.vert")
        file_xz = file.with_suffix(".vert.xz.TMP")
        file_xz.unlink(missing_ok=True)
        result = self.runner.invoke(secondary_pipeline.main, [str(file)])
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(file_xz.exists())
        file_xz.unlink()

    def test_main_compress_clear(self):
        src_file = Path("test/test_pipeline/files/file.1.vert")
        file = Path("test/test_pipeline/files/file-copy.1.vert")
        copy(src_file, file)
        file_xz = file.with_suffix(".vert.xz")
        file_xz.unlink(missing_ok=True)
        result = self.runner.invoke(secondary_pipeline.main, [str(file), "--clear"])
        self.assertTrue(result.exit_code == 0)
        self.assertTrue(file_xz.exists())
        self.assertFalse(file.exists())
        file_xz.unlink()

    def test_main_from_xz(self):
        src_file = Path("test/test_pipeline/files/file.1.vert")
        file = Path("test/test_pipeline/files/file-copy.1.vert.xz")
        with open(src_file) as src:
            with lzma.open(file, "wb") as out:
                _src = src.read()
                out.write(_src.encode())
        result = self.runner.invoke(
            secondary_pipeline.main, [str(file), "--no-compress"]
        )
        self.assertTrue(result.exit_code == 0)
        with open(file.with_suffix(".TMP")) as f:
            out = f.read()
        with open("test/test_pipeline/files/file.1.vert.TMP.REF") as f:
            ref = f.read()
            ref = ref.replace("file.1.vert", "file-copy.1.vert.xz")
        self.assertEqual(ref, out)
        file.unlink()
        tmp = Path("test/test_pipeline/files/file-copy.1.vert.TMP")
        tmp.unlink()


if __name__ == "__main__":
    unittest.main()
