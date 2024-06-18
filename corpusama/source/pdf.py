"""A module for managing PDF content."""
import logging
import pathlib
import re
import time

import fitz
import requests

from corpusama.util import parallel

logger = logging.getLogger(__name__)


def clean_text(text: str, drops: str = "�\t") -> str:
    """Removes extra whitespace (multiple blank lines/spaces) and drops.

    Args:
        text: A string extracted from a PDF that needs cleaning.
        drops: Specific characters to remove (replaced with a space).
    """
    # remove unwanted characters
    text = text.translate(str.maketrans(drops, " " * len(drops)))
    # strip line whitespace
    text = re.sub(r" {0,}\n {0,}", r"\n", text)
    # remove extra spaces
    text = re.sub(r" {2,}", r" ", text)
    # remove extra lines
    text = re.sub(r"\n{3,}", r"\n\n", text)
    # strip trailing/leading whitespace
    text = text.strip()
    return text


def extract_text(file: str, clean: bool = True) -> str:
    """ "Extracts text from a PDF file w/ PyMuPDF; optionally cleans text.

    Args:
        file: Filepath to a PDF.
        clean: Whether to clean text before returning.

    Notes:
        - Reads PDFs with PyMuPDF on a text block level and joins blocks with `\\n\\n`.
        - Dehyphenates words split at the end of a line. This generally improves
            readability but inevitably joins a few intentionally hyphenated words that
            happen to be split by a line break. This can be mitigated in corpus queries
            by searching for a token both with and without hyphens.
        - Works for most PDFs, excepting corrupted files, etc.
        - Recognizes multiple columns, tables, text boxes for well-designed files:
            results vary w/ box positioning, etc.
    """
    file = pathlib.Path(file)
    doc = fitz.open(file)
    f1 = fitz.TEXTFLAGS_TEXT & fitz.TEXT_DEHYPHENATE & ~fitz.TEXT_PRESERVE_LIGATURES
    text = b""
    for page in doc:
        text += b"\n".join(
            [x[4].encode(errors="ignore") for x in page.get_text("blocks", flags=f1)]
        )
    if clean:
        return clean_text(text.decode())
    else:
        return text.decode()


def get_request(file: str, url: str, wait: int = 5) -> str:
    """Downloads a file using GET get_, returns status (raises if error != 404).

    Args:
        file: Filename.
        url: Request url.
        wait: Minimum number of seconds to throttle PDF requests (applies only if
            download time < `wait` seconds).
    """
    r = requests.get(url, stream=True, timeout=(6.05, 57))
    if r.status_code == 404:
        pass
    else:
        r.raise_for_status()
    t0 = time.perf_counter()
    with open(file, "wb") as f:
        f.write(r.content)
    t1 = time.perf_counter()
    t2 = t1 - t0
    if t2 < wait:
        time.sleep(wait - t2)
    return r.status_code


def _try_extract(file: str, clean: bool, n: int = 0) -> None:
    """Attempts `extract_text()`, raises a warning on error but doesn't break.

    Args:
        file: Filename.
        url: Request url.
        n: An integer that gets logged if an error occurs (managed by containing func).
    """
    file = pathlib.Path(file)
    try:
        text = extract_text(file, clean)
        with open(file.with_suffix(".txt"), "w") as f:
            f.write(text)
    except (fitz.fitz.FileDataError, RuntimeError, fitz.mupdf.FzErrorFormat) as e:
        logger.warning(f"{n} - {file} - {e}")


class ExtractFiles:
    """A class to run text extraction of PDFs.

    Args:
        clean: Whether to clean text after extraction.
        overwrite: Whether to overwrite existing TXT files.
    """

    def run(self, files: list, timeout: int = 30):
        """Method to run text extraction on files (saves files in same parent dirs).

        Args:
            files: List of PDF filepaths.
            timeout: Maximum allowed time for PDF extraction.
        """
        n = 0
        files = [pathlib.Path(f) for f in files]
        for x in range(len(files)):
            txt_file = files[x].with_suffix(".txt")
            logger.info(f"{x} - {txt_file}")
            _ = parallel.run_with_timeout(
                _try_extract, (files[x], self.clean, n), timeout
            )
            n += 1
        return []

    def __init__(self, clean: bool = True, overwrite: bool = False):
        self.clean = clean
        self.overwrite = overwrite
