"""Methods to classify document languages and save results to the `_lang` table."""
import fasttext
import pandas as pd

from corpusama.util import convert, decorator, langid, parallel, util


def make_langid(
    self,
    table: str,
    size: int = 5000,
    cores=0,
) -> None:
    @decorator.while_loop
    def langid_batch(self, size) -> bool:
        """Processes a batch of table records to make attributes."""

        if table == "_pdf":
            query = "SELECT * FROM _pdf LIMIT ?,?;"
        if table == "_raw":
            query = "SELECT * FROM _raw WHERE body_html IS NOT null LIMIT ?,?;"
        # TODO WHERE id IS NOT null - body_html should be text column var
        batch, offset = self.db.fetch_batch(self.lang_run, size, query)
        if not batch:
            return False
        cols = self.db.tables[table]
        df = pd.DataFrame.from_records(batch, columns=cols)
        pdf_dir = self.config.get("pdf_dir")
        text_column = self.config.get("text_column")
        add_langid = AddLangID(table, pdf_dir, text_column)
        df = parallel.run(df, add_langid.make, self.cores)
        df["lang_date"] = util.now()
        self.db.insert(df, "_lang")
        self.lang_run += 1
        return True

    self.lang_run = 0
    self.cores = parallel.set_cores(cores)
    langid_batch(self, size)


class AddLangID:
    def _make_filepath(self, df: pd.DataFrame):
        df["local_file"] = (
            df["id"].astype(str) + "/" + df["file_id"].astype(str) + ".txt"
        )
        df["local_file"] = self.pdf_dir + df["local_file"]
        return df["local_file"].values

    def make(self, df: pd.DataFrame):
        # shape data for source table
        if self.table == "_raw":
            is_file = False
            s = df[self.text_column].apply(convert.html_to_text).values
        elif self.table == "_pdf":
            is_file = True
            s = self._make_filepath(df)
        # run language id
        model = fasttext.load_model(self.model_file)
        lid = langid.LangID(
            s,
            self.sample_kwargs,
            None,
            model,
            self.threshold,
            is_file=is_file,
        )
        # add file_id = 0 if using html_body
        if self.text_column in df.columns:
            df["file_id"] = 0
        # select columns and reset indexes
        df = df[["id", "file_id"]]
        lid.df = lid.df[["lid"]]
        df.reset_index(drop=True, inplace=True)
        lid.df.reset_index(drop=True, inplace=True)
        return pd.concat([df, lid.df], axis=1)

    def __init__(
        self,
        table: str,
        pdf_dir: str,
        text_column: str,
        model_file: str = "./fastText/lid.176.bin",
        sample_kwargs: dict | None = None,
        threshold: float = 0.6,
    ) -> None:
        self.pdf_dir = pdf_dir
        self.text_column = text_column
        self.threshold = threshold
        self.table = table
        self.model_file = model_file
        if not sample_kwargs:
            self.sample_kwargs = dict(
                sample_size=0,
                tries=5,
                min_len=10,
                drops=langid.drop_all,
            )
