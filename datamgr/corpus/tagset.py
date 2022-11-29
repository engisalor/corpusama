"""Methods to export data from a database."""
import logging
import pathlib
import re

from datamgr.util import decorator

logger = logging.getLogger(__name__)


def export_tagset(self):
    def find_xpos(vert: str):
        return set(re.findall(r"\n.*?\t(.*?)\t", vert))

    @decorator.timer
    def save_tagset(self, size=100):
        self.tagset_new = set()
        self.tagset_run = 0
        tagset_batch(self, size)
        dir = pathlib.Path("data")
        filepath = dir / self.db_name.with_suffix(".tagset.txt")
        with open(filepath, "w") as f:
            f.write("\n".join(sorted(self.tagset_new)))

    @decorator.while_loop
    def tagset_batch(self, size):
        query = "SELECT vert from _vert LIMIT ?,?;"
        batch, offset = self.db.fetch_batch(self.tagset_run, size, query)
        if not batch:
            return False
        for doc in batch:
            self.tagset_new.update(find_xpos(doc[0]))
        self.tagset_run += 1
        return True

    def check_tagset(self, t):
        new = [tag for tag in self.tagset_new if tag not in self.tagset.keys()]
        tags_n = len(self.tagset_new)
        f = pathlib.Path(self.tagset_file)
        if new:
            logger.warning(f"{tags_n} tags - NEW {new} - file {f.stem} {t:,}s")
        else:
            logger.debug(f"{tags_n} tags - no new - {f.stem} - {t:,}s")

    _, t = save_tagset(self)
    check_tagset(self, t)
