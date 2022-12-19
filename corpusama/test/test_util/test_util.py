import unittest

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


if __name__ == "__main__":
    unittest.main()
