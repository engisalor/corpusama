"""Methods for managing corpus tagsets."""
import logging
import pathlib
import re

from corpusama.util import decorator

logger = logging.getLogger(__name__)


def export_tagset(self) -> None:
    """Exports a tagset to text file.

    Notes:
        - Tags are found in corpus vertical content and unique values
            are saved to ``/data/<database_name>.tagset.txt``.
        - A warning is logged if tags are found that don't exist in the
            corpus's current tagset file."""

    def find_xpos(vert: str) -> set:
        """Gets a set of xpos values from vertical content."""

        return set(re.findall(r"\n.*?\t(.*?)\t", vert))

    @decorator.timer
    def save_tagset(self, size: int = 100):
        """Runs methods to make and then save a tagset.

        Args:
            size: The number of vertical files to process in a batch."""

        self.tagset_new = set()
        self.tagset_run = 0
        tagset_batch(self, size)
        dir = pathlib.Path("data")
        filepath = dir / self.db_name.with_suffix(".tagset.txt")
        with open(filepath, "w") as f:
            f.write("\n".join(sorted(self.tagset_new)))

    @decorator.while_loop
    def tagset_batch(self, size):
        """Gets tagsets from a batch of vertical content.

        Args:
            size: The number of vertical files to process in a batch."""

        query = "SELECT vert from _vert LIMIT ?,?;"
        batch, offset = self.db.fetch_batch(self.tagset_run, size, query)
        if not batch:
            return False
        for doc in batch:
            self.tagset_new.update(find_xpos(doc[0]))
        self.tagset_run += 1
        return True

    def check_tagset(self, t: int):
        """Warns if tags don't already exist in the tagset file.

        Args:
            t: execution time - used by the timer decorator."""

        new = [tag for tag in self.tagset_new if tag not in self.tagset.keys()]
        tags_n = len(self.tagset_new)
        f = pathlib.Path(self.tagset_file)
        if new:
            logger.warning(f"{tags_n} tags - NEW {new} - file {f.stem} {t:,}s")
        else:
            logger.debug(f"{tags_n} tags - no new - {f.stem} - {t:,}s")

    _, t = save_tagset(self)
    check_tagset(self, t)
