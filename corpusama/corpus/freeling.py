"""Module to manage FreeLing.

FreeLing is an NLP package for generating corpora. Corpusama's implementation uses
FreeLing's built-in Python 3 API. See its "install from source" instructions and
the steps below as an example.

- Website: <https://nlp.lsi.upc.edu/freeling/>
- Documentation: <https://freeling-user-manual.readthedocs.io/en/latest/>

!!! info "FreeLing source install on Fedora Linux (enabling Python3 API)"
    ```bash
    # install dependencies
    sudo dnf install boost-devel boost-regex libicu-devel boost-system
    sudo dnf install boost-program-options boost-thread zlib-devel
    sudo dnf install swig python3-devel

    # install FreeLing to CWD
    wget https://github.com/TALP-UPC/FreeLing/releases/download/4.2/FreeLing-src-4.2.1.tar.gz  # noqa: E501
    tar -xf FreeLing-src-4.2.1.tar.gz
    cd FreeLing-4.2.1
    mkdir build
    cd build
    cmake .. -DPYTHON3_API=ON -DCMAKE_INSTALL_PREFIX=$PWD
    make install

    # copy API files
    cd .. && cd .. && cp -a $PWD/share/freeling/APIs/python3/. $PWD

    # test
    echo "Una frase en español." > $PWD/text-example.txt
    export LD_LIBRARY_PATH="$PWD/lib;$PWD/share/freeling/APIs/python3"
    export FREELINGDIR=$PWD
    ./sample.py < text-example.txt
    ```

!!! warning
    A copy of `_pyfreeling.so` and `pyfreeling.py`, which are generated in FreeLing's
    API directory during installation, must be available in the root Corpusama repo
    directory. This may be reconfigured depending on how FreeLing is installed: this
    may change in future versions.
"""
import logging
import os
import time

import pyfreeling
from corpusama.util import io


class FreeLing:
    """A class to configure and run FreeLing."""

    def _set_config_vars(self, config):
        """Replaces `<install_dir>` strings with proper location."""
        for k, v in config.items():
            if isinstance(v, str):
                config[k] = v.replace("<install_dir>", self.install_dir)
            elif isinstance(v, dict):
                self._set_config_vars(v)
        return config

    def _to_vertical(self, ls):
        """Converts a list of FreeLing results into vertical format."""
        out = ["<doc>"]
        for s in ls:
            ws = s.get_words()
            out.append("<s>")
            for w in ws:
                form = w.get_form()
                tag = w.get_tag()
                lempos = self.config.get("tagset").get(tag[0]).get("lpos")
                lemma = w.get_lemma()
                # ignore extra tags/lemmas
                if "+" in tag:
                    tag = tag.split("+")[0]
                if "+" in lemma:
                    lemma = lemma.split("+")[0]
                out.append("\t".join([form, tag, lemma + lempos]))
            out.append("</s>")
        out.append("</doc>")
        return "\n".join(out)

    def run(self, text: str):
        """Executes FreeLing on a file and returns vertical content."""
        sid = self.sp.open_session()
        t = self.tk.tokenize(text)
        ls = self.sp.split(sid, t, False)
        ls = self.mf.analyze_sentence_list(ls)
        ls = self.tg.analyze_sentence_list(ls)
        self.sp.close_session(sid)
        return self._to_vertical(ls)

    def __init__(
        self,
        install_dir: str = ".local-only",
        config_file: str = "corpusama/corpus/tagset/freeling_es.yml",
    ) -> None:
        """Creates a FreeLing object.

        Args:
            install_dir: Parent directory where FreeLing is installed.
            config_file: A YAML file with FreeLing settings and tagset.

        Notes:
            - Create one `FreeLing` instance and then execute `run()` on texts.
            - FreeLing may return nothing if a text has no sentences (no periods or
                similar punctuation).
            - See `corpusama/corpus/tagset/freeling_es.yml` for an example config file.
        """
        t0 = time.perf_counter()
        # config
        self.install_dir = install_dir
        config = io.load_yaml(config_file)
        self.config = self._set_config_vars(config)
        # env
        os.environ["LD_LIBRARY_PATH"] = self.config.get("LD_LIBRARY_PATH")
        # locale
        pyfreeling.util_init_locale("default")
        # options
        self.op = pyfreeling.analyzer_config()
        for k, v in self.config.get("config_opts").items():
            setattr(self.op.config_opt, k, v)
        for k, v in self.config.get("invoke_opts").items():
            setattr(self.op.invoke_opt, k, v)
        # analyzers
        self.tk = pyfreeling.tokenizer(self.config.get("tokenizer"))
        self.sp = pyfreeling.splitter(self.config.get("splitter"))
        self.mf = pyfreeling.maco(self.op)
        self.tg = pyfreeling.hmm_tagger(self.op)
        # log
        t1 = time.perf_counter()
        logging.debug(round(t1 - t0, 3))
