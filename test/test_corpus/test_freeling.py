import unittest

from corpusama.corpus import freeling


class Test_FreeLing_Run(unittest.TestCase):
    def test_load_nlp(self):
        fl = freeling.FreeLing()
        vert = fl.run("Una frase en español.")
        ref = "<doc>\n<s>\nUna\tDI0FS0\tuno-x\nfrase\tNCFS000\tfrase-n\nen\tSP\ten-i\nespañol\tNCMS000\tespañol-n\n.\tFp\t.-x\n</s>\n</doc>"  # noqa: E501
        self.assertEqual(vert, ref)
