# Corpusama

## About

Corpusama is a language corpus management tool that provides a semi-automated pipeline for creating corpora from the [ReliefWeb](https://reliefweb.int/) database of humanitarian texts (managed by the United Nations Office for the Coordination of Humanitarian Affairs).

The goal of building language corpora from ReliefWeb is to study humanitarian discourse: what concepts exist among actors, how their usage changes over time, what's debated about them, their practical/ideological implications, etc.

Corpusama can build corpora with texts from the ReliefWeb API. [Contact ReliefWeb](https://reliefweb.int/contact) to discuss acceptable uses for your project: users are responsible for how they access and utilize ReliefWeb. This software is for nonprofit research; it is offered to ensure the reproducibility of research and to build on previous work. Feel free to reach out if you have questions or suggestions.

## General requirements

ReliefWeb is a large database with over 1 million humanitarian reports, each of which may include PDF attachments and texts in multiple languages. Upwards of 500 GB of space may be required for managing and processing files. Downloading this data at a reasonable rate takes weeks. Dependencies also require ~< 10 GB of space and benefit from a fast CPU and GPU (a GPU is needed for processing large amounts of data).

## Basic installation

Clone this repo and install dependencies in in a virtual environment (tested on Python 3.12). These are the main packages: `pip install click defusedxml nltk pandas PyMuPDF PyYAML requests stanza`.

```bash
python3 -m venv .venv
source ${PWD}/.venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Reproducing corpora

Corpora can be generated using the following code snippet. The notes below describe the process and important considerations in more detail.

```bash
### INITIAL SETUP
git clone https://github.com/engisalor/corpusama && cd corpusama
# get dependencies and models, unit test
bash rw_corpora_setup.sh "<EMAIL_USED_FOR_RELIEFWEB_API>"

### RUN PERIODICALLY TO GENERATE UP-TO-DATE CORPORA
# generate EN, FR & ES corpora (.vert.xz) for a date range
bash rw_corpora_update.sh "<START_DATE>" "<END_DATE>" # <YYYY_MM_DD> format
```

### On package setup: `rw_corpora_setup.sh`

1. Clone the repo and CD to the directory.
2. Stanza and NLTK models will be downloaded to `~/`. These resources will be reused until updated manually. Requires ~<10 GB for dependencies and models.
3. After installing dependencies, `unittest` will run to ensure proper setup. As of `2024/11/01` no tests should fail.
4. See ReliefWeb's terms and conditions before using its service/data. An email is required for making API calls (stored in files ending in `*secret.yml`).

### On generating corpora: `rw_corpora_update.sh`

1. This script produces a series of compressed vertical corpus files in
   a CoNLLU-based format using Stanza NLP.
    - fetches ReliefWeb data for a date range
    - processes with Stanza NLP into CoNLLU
    - converts to SkE-compatible vertical foramt
    - runs a secondary pipeline to add sentence-level language metadata and UUIDs for doc and docx structures (technically optional)
2. After completion, `.vert.xz` files can be stored and used. The rest of the project can be deleted if CoNLLU and other files aren't desired. Downloaded data will keep accumulating for every run. Storing all of ReliefWeb takes ~500 GB and weeks to download/process. This script is intended for sequential, chronological updates only, not a mix of overlapping or dijointed dates.
3. This script reuses `config/reliefweb_2000+.yml` to define settings.
   A custom date range is supplied to define what texts to download. Use a YYYY-MM-DD format. The example below collects data for January 2020:

```bash
# get a month of data
bash rw_corpora_update.py "2020-01-01" "2020-02-01"
```

This produces these vertical files (and intermediate formats) as long as documents of each language are detected in the chosen date range:

- `reliefweb_en_2020-01-01_2020-02-01.1.txt.vert.xz`
- `reliefweb_fr_2020-01-01_2020-02-01.1.txt.vert.xz`
- `reliefweb_es_2020-01-01_2020-02-01.1.txt.vert.xz`

4. Vertical files are ready to be compiled in Sketch Engine. See these directories for corpus configuration files:

- https://github.com/engisalor/corpusama/tree/main/registry
- https://github.com/engisalor/corpusama/tree/main/registry_subcorp

5. This script has been tested for use with a recent Core i7 laptop with an NVIDIA GPU. Testing is done on Fedora Linux and Ubuntu to a lesser extent. Default settings attempt to be reasonable and reduce errors, but a number of issues may arise throughout the process. Verifying output data at each phase and becoming familiar with the code base are recommended. If in doubt, please reach out.

See more in-depth explanations of software and data formats below.

## Corpus sizes

|Name|ID|Types|Tokens|Docs|
|-|-|-|-|-|
|ReliefWeb English 2023 | rw_en23 | 1,683,494,268 | 2,079,244,974 |884,528|
|ReliefWeb French 2023 | rw_fr23 | 210,112,455 | 248,413,974 | 109,592 |
|ReliefWeb Spanish 2023 | rw_es23 | 125,983,910 | 150,712,952 | 79,697 |

- Dates cover January 1, 2000 through December 31, 2023 (until next update)

## Corpus structures

- `<doc>` delineates documents, which may be HTML text or extracted PDF text
  - contains the most pertinent metadata for linguistic analysis
  - `doc.id` refers to the Report ID (which can be shared by its 1 HTML text and 0+ associated PDFs)
  - `doc.file_id` refers to PDF content for a report
- `<docx>` is the XZ archive containing a set of documents
- `<s>` is a sentence boundary
  - `s.id` refers to the sentence number in a document, starting at 1
  - `s.lang` if implemented, refers to the Stanza language identification result for the sentence, with English, Spanish, French, and None as the possible values (None being sentences too short to analyze)
- a `ref` value is given for `doc` and `docx` structures, which may be a unique sequential number or a UUID (preferably the latter)

## Subcorpora

- `doc_html` and `doc_pdf` split the corpus by document type
- `lang_*` splits the corpus by sentence language: mostly used to identify pockets of unwanted noise; does not strictly refer to each language ID result (see the `registry_subcorp` files for precise definitions)
- `source_single` and `source_multi` split the corpus by documents that have only one 'author' in the `doc.source__name` value or multiple authors

## Stanza

[Stanza](https://github.com/stanfordnlp/stanza) is a Python NLP package from Stanford. Models for languages may need to be downloaded with its `download()` function if this doesn't happen automatically.

## Deprecated packages

Earlier versions relied on FreeLing and fastText NLP tools. See the history of this README for old installation instructions. These tools perform better on machines without a dedicated GPU, whereas Stanza can run on a CPU but more slowly.

## Configuration files

Various settings are supplied to build corpora. The `config/` directory stores YAML files with many settings. The [config/reliefweb_2000+.yml](/config/reliefweb_2000%2B.yml) is one example. It specifies a few things:

```yaml
# the API where data is collected from
source: reliefweb
# an SQL schema for the database that stores API data
schema: corpusama/database/schema/reliefweb.sql
# the name of the database
db_name: data/reliefweb_2000+.db
# the column containing textual data (i.e., corpus texts)
text_column: body_html
# the daily maximum number of API calls
quota: 1000
# a dictionary specifying how to throttle API calls
wait_dict: {"0": 1, "5": 49, "10": 99, "20": 499, "30": null}
# API parameters used to generate calls
parameters:
	<various ReliefWeb API parameters>
attributes:
	<ReliefWeb API metadata fields, some of which will be included in a corpus>
```

In this case, `reliefweb_2000+` has parameters to get all text-based reports (in any language) starting from 1 January 2000.

Each configuration file is accompanied by another that supplies secrets. It has the same filename but uses the suffix `.secret.yml`, e.g., `reliefweb_2000+.secret.yml`:

```yml
# where to store PDF files locally
pdf_dir: /a/local/filepath/
# API url and appname
url: https://api.reliefweb.int/v1/reports?appname=<YOUR EMAIL ADDRESS>
```

To get started, make a secrets file for `reliefweb_2000+` or design your own configuration files.

## Usage example

This is an example to verify installation and describe the general workflow of corpus creation.

### Corpusama

The `corpusama` package has all the modules needed to manage data collection and corpus preparation. It's controlled with a `Corpus` object. Modules can also be imported and used independently, but this is mostly useful for development purposes.

How to build a database:

```py
from corpusama.corpus.corpus import Corpus

# instantiate a Corpus object
corp = Corpus("config/reliefweb_2000+.yml")
# this makes/opens a database in `data/`
# the database is accessible via `corp.db`
# view the database with a GUI application like <https://sqlitebrowser.org/>
# (helpful for inspecting each stage of data manipulation)

# get records that haven't been downloaded yet
corp.rw.get_new_records(1) # this example stops after 1 API call
# (downloads up to 1000 records chronologically)

# download associated PDFs
corp.rw.get_pdfs()
# (most reports don't have PDFs; some have several)

# extract PDF text
corp.rw.extract_pdfs()
# doesn't include OCR capabilities
# extracts to TXT files in same parent dir as PDF

# run language identification on texts
corp.make_langid("_pdf") # TXT files extracted from PDFs
corp.make_langid("_raw") # HTML data stored within API responses

# make corpus XML <doc> attributes for a language
corp.make_attribute("fr")
# there should be a few French documents in the first 1000 API results (example breaks if otherwise)

# export the combined texts into one TXT file
df = corp.export_text("fr")
# produces `reliefweb_fr.1.txt`
# this files can be processed with a pipeline to make a vertical file
```

### Export format

The above workflow generates text files with ReliefWeb reports surrounded by `<doc>` XML tags, by default in batches of up to 10,000 reports per output file. Here is a fragment of a single report:

```xml
<doc id="302405" file_id="0" country__iso3="pse" country__shortname="oPt" date__original="2009-03-25T00:00:00+00:00" date__original__year="2009" format__name="News and Press Release" primary_country__iso3="pse" primary_country__shortname="oPt" source__name="Palestinian Centre for Human Rights" source__shortname="PCHR" source__type__name="Non-governmental Organization" theme__name="Health|Protection and Human Rights" title="OPT: PCHR appeals for action to save lives of Gaza Strip patients" url="https://reliefweb.int/node/302405" >
The Palestinian Centre for human rights
(PCHR) is appealing to the Ministries of Health in the Ramallah and Gaza
Governments to take all possible measures to facilitate referrals for Gazan
patients who need urgent medical treatment outside Gaza.
The Centre is alarmed at the deterioration
of patient's health following two key political decisions on healthcare
provision. In January 2009, the Ramallah Ministry of Health (MOH) cancelled
financial coverage for all Palestinian patients in Israeli hospitals, including
those who in the middle of long term treatment.
[...]
</doc>
```

Once the content of these files is inspected, they can be compressed with `xz` or a similar tool before further processing.

### Pipelines

#### TLDR

These are the main commands for using the Stanza pipeline to process the above-mentioned TXT files. Use the `--help` flag to learn more.

- base script: `python3 ./pipeline/stanza/base_pipeline.py`

- generate CoNLLU files: `python3 ./pipeline/stanza/base_pipeline.py to-conll`
- convert CoNLLU to vertical: `python3 ./pipeline/stanza/base_pipeline.py conll-to-vert`

#### More details

Files in the `pipeline/` directory are used to complete corpus creation. The current version of Corpusama relies on the Stanza pipeline. Run `python pipeline/stanza/base_pipeline.py --help` for an overview. This has been tested with an NVIDIA 4070m GPU (8 GB). Also adjust the arguments below in `stanza.Pipeline` when fine-tuning memory management:

```py
self.nlp = stanza.Pipeline(
    tokenize_batch_size=32,   #  Stanza default=32
    mwt_batch_size=50,        #  Stanza default=50
    pos_batch_size=100,       #  Stanza default=5000
    lemma_batch_size=50,      #  Stanza default=50
    depparse_batch_size=5000, #  Stanza default=5000
)
```

If possible, the dependency parsing batch size should be "set larger than the number of words in the longest sentence in your input document" ([see documentation](https://stanfordnlp.github.io/stanza/neural_pipeline.html)). Managing memory issues in the GPU-based Stanza pipeline may be necessary. See `error_corrections.md` for a list of steps taken to build the corpora with an Nvidia 4070.

The first output format is `.conllu` (see https://universaldependencies.org/format.html). Here's a sample:

```bash
# newdoc
# id = 302405
# file_id = 0
# country__iso3 = pse
# country__shortname = oPt
# date__original = 2009-03-25T00:00:00+00:00
# date__original__year = 2009
# format__name = News and Press Release
# primary_country__iso3 = pse
# primary_country__shortname = oPt
# source__name = Palestinian Centre for Human Rights
# source__shortname = PCHR
# source__type__name = Non-governmental Organization
# theme__name = Health|Protection and Human Rights
# title = OPT: PCHR appeals for action to save lives of Gaza Strip patients
# url = https://reliefweb.int/node/302405
# text = The Palestinian Centre for human rights (PCHR) is appealing to the Ministries of Health in the Ramallah and Gaza Governments to take all possible measures to facilitate referrals for Gazan patients who need urgent medical treatment outside Gaza.
# sent_id = 0
1	The	the	DET	DT	Definite=Def|PronType=Art	3	det	_	start_char=0|end_char=3
2	Palestinian	Palestinian	ADJ	NNP	Degree=Pos	3	amod	_	start_char=4|end_char=15
3	Centre	Centre	PROPN	NNP	Number=Sing	11	nsubj	_	start_char=16|end_char=22
[...]
```

CoNLLU can then be converted to a vertical format recognized by [Sketch Engine](https://www.sketchengine.eu/my_keywords/conll-format/):

```xml
<doc id="302405" file_id="0" country__iso3="pse" country__shortname="oPt" date__original="2009-03-25T00:00:00+00:00" date__original__year="2009" format__name="News and Press Release" primary_country__iso3="pse" primary_country__shortname="oPt" source__name="Palestinian Centre for Human Rights" source__shortname="PCHR" source__type__name="Non-governmental Organization" theme__name="Health|Protection and Human Rights" title="OPT: PCHR appeals for action to save lives of Gaza Strip patients" url="https://reliefweb.int/node/302405">
<s id="0">
1	The	the	DET	DT	Definite=Def|PronType=Art	3	det	_	start_char=0|end_char=3
2	Palestinian	Palestinian	ADJ	NNP	Degree=Pos	3	amod	_	start_char=4|end_char=15
3	Centre	Centre	PROPN	NNP	Number=Sing	11	nsubj	_	start_char=16|end_char=22
```

The TXT, CoNLLU and vertical formats have their own use cases for NLP tasks. Viewing the corpus (e.g., in Sketch Engine) also requires making a corpus [configuration file](https://www.sketchengine.eu/documentation/corpus-configuration-file-all-features/) and other steps beyond this introduction.

Generating and verifying checksums is also recommended for sharing and versioning:

```bash
# generate
sha256sum reliefweb* > hashes.txt

# verify
sha256sum -c hashes.txt
```

## Resources

- [Stanza Treebanks](https://stanfordnlp.github.io/stanza/performance.html)
- [Universal Dependencies](https://universaldependencies.org/)
- [Ancora treebank documentation (Spanish pipeline)](https://clic.ub.edu/corpus/en/documentation)
- [French GSD treebank documentation (French pipeline)](https://universaldependencies.org/treebanks/fr_gsd/index.html)
- [Penn treebank tagset (English pipeline)](https://www.sketchengine.eu/penn-treebank-tagset/)

## Acknowledgements

Support comes from the [Humanitarian Encyclopedia](https://humanitarianencyclopedia.org/) and the [LexiCon research group](https://lexicon.ugr.es/) at the University of Granada. See the paper below for references and funding disclosures.

Dependencies have included these academic works, which have their corresponding bibliographies: [Stanza](https://github.com/stanfordnlp/stanza), [FreeLing](https://nlp.lsi.upc.edu/freeling/) and [fastText](https://github.com/facebookresearch/fastText).

Subdirectories with a `ske_` prefix are from [Sketch Engine](https://www.sketchengine.eu/) under [AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html), [MPL](https://www.mozilla.org/MPL/2.0), and/or other pertinent licenses. See their [bibliography](https://www.sketchengine.eu/bibliography-of-sketch-engine/) and [website](https://corpus.tools/) with open-source corpus tools.

Other attributions are indicated in individual files. [NoSketch Engine](https://nlp.fi.muni.cz/trac/noske) is a related software used downstream in some projects.

## Citation

Please consider citing the papers below. `CITATION.cff` can be used if citing the software directly.

```bibtex
@inproceedings{isaacs_humanitarian_2023,
	location = {Brno, Czech Republic},
	title = {Humanitarian reports on {ReliefWeb} as a domain-specific corpus},
	url = {https://elex.link/elex2023/wp-content/uploads/elex2023_proceedings.pdf},
	pages = {248--269},
	booktitle = {Electronic lexicography in the 21st century. Proceedings of the {eLex} 2023 conference},
	publisher = {Lexical Computing},
	author = {Isaacs, Loryn},
	editor = {Medveď, Marek and Měchura, Michal and Kosem, Iztok and Kallas, Jelena and Tiberius, Carole and Jakubíček, Miloš},
	date = {2023}
}

@inproceedings{isaacs-etal-2024-humanitarian-corpora,
    title = "Humanitarian Corpora for {E}nglish, {F}rench and {S}panish",
    author = "Isaacs, Loryn  and
      Chamb{\'o}, Santiago  and
      Le{\'o}n-Ara{\'u}z, Pilar",
    editor = "Calzolari, Nicoletta  and
      Kan, Min-Yen  and
      Hoste, Veronique  and
      Lenci, Alessandro  and
      Sakti, Sakriani  and
      Xue, Nianwen",
    booktitle = "Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation (LREC-COLING 2024)",
    month = may,
    year = "2024",
    location = "Torino, Italia",
    publisher = "ELRA and ICCL",
    url = "https://aclanthology.org/2024.lrec-main.738",
    pages = "8418--8426",
}
```
