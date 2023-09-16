# Corpusama

## About

Corpusama is a language corpus management tool. Its initial goal is to develop a semi-automated pipeline for creating corpora from the [ReliefWeb](https://reliefweb.int/) database of humanitarian texts (managed by the United Nations Office for the Coordination of Humanitarian Affairs). Corpusama has received funding from the [Humanitarian Encyclopedia](https://humanitarianencyclopedia.org/).

## Purpose

The goal of building language corpora from ReliefWeb is to study humanitarian discourse: what concepts exist among actors, how their usage changes over time, what's debated about them, their practical/ideological implications, etc. While ReliefWeb reports are searchable, converting them into a tokenized and lemmatized corpus gives researchers a much more powerful way to study language.

## Disclaimer

Corpusama can build corpora with texts from the ReliefWeb API. [Contact ReliefWeb](https://reliefweb.int/contact) to discuss acceptable uses for your project: users are responsible for how they access and utilize ReliefWeb. This software is for nonprofit research (see Acknowledgements/Citation sections).

This software is not designed to be stable for third parties: code may change without notice. It is offered to ensure the reproducibility of research and to build on previous work. Feel free to reach out if you have questions or suggestions.

## General requirements

ReliefWeb is a large database with over 1 million humanitarian reports, each of which may include PDF attachments and texts in multiple languages. Upwards of **500 GB of space** may be required for managing and processing files. Downloading this data at a reasonable rate **takes weeks**. Dependencies also require several GB of space and benefit from a fast CPU/GPU.

## Installation

> Note: Some aspects of Corpusama work without setting up all third party software: e.g., downloading ReliefWeb API data only requires core modules. Building corpora (producing vertical files) may only require one pipeline software, e.g., FreeLing or Stanza. Examine your needs before installing everything. *Designed and tested on Linux only*.

### Python dependencies

Clone this repo and install dependencies in in a virtual environment.

```bash
python3 -m venv .venv
source ${PWD}/.venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### fastText

fastText is a text classifier that's used for language identification. It has a Python package that's included in `requirements.txt` but models are downloaded separately. See [their website](https://fasttext.cc/docs/en/language-identification.html) for details. This is the default configuration:

```bash
mkdir fastText
cd fastText
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
```

### FreeLing

Follow FreeLing's [install from source](https://freeling-user-manual.readthedocs.io/en/latest/installation/installation-linux/) instructions. Releases are available [on GitHub](https://github.com/TALP-UPC/FreeLing/releases). After its dependencies are installed, FreeLing's installation could look like this:

```bash
wget https://github.com/TALP-UPC/FreeLing/releases/download/4.2/FreeLing-src-4.2.1.tar.gz
wget https://github.com/TALP-UPC/FreeLing/releases/download/4.2/FreeLing-langs-src-4.2.1.tar.gz

tar -xf FreeLing-src-4.2.1.tar.gz
tar -xf FreeLing-langs-src-4.2.1.tar.gz

# installs FreeLing to $CWD/.local-only
FLINSTALL=$PWD/.local-only
mkdir $FLINSTALL
cd FreeLing-4.2.1
mkdir build
  cd build
  cmake .. -DPYTHON3_API=ON -DCMAKE_INSTALL_PREFIX=$FLINSTALL
  make -j 3 install # define number of processors to speed up install
```

Two files are needed to use FreeLing via Python: `pyfreeling.py` and `_pyfreeling.so`, found in `$FLINSTALL/share/freeling/APIs/python3/`. Add this directory to `$PYTHONPATH` and `$LD_LIBRARY_PATH` or just copy the two files to the root directory *and* the pipeline being used, e.g.:

```bash
# option 1: append these lines to ~/.bashrc with proper path
export PYTHONPATH="${PYTHONPATH}:PATH/TO/CORPUSAMA/.local-only/share/freeling/APIs/python3"
export LD_LIBRARY_PATH=PATH/TO/CORPUSAMA/.local-only/lib;PATH/TO/CORPUSAMA/.local-only/share/freeling/APIs/python3

# option 2: copy files wherever needed
DIR=$PWD/.local-only/share/freeling/APIs/python3
cp $DIR/pyfreeling.py $PWD & cp $DIR/_pyfreeling.so $PWD
cp $DIR/pyfreeling.py $PWD/pipeline/ske_fr/ & cp $DIR/_pyfreeling.so $PWD/pipeline/ske_fr/
```

FreeLing also requires a locale installed for each language to be used: refer to your Linux distribution.

### Stanza

[Stanza](https://github.com/stanfordnlp/stanza) is a Python NLP package. Models for languages may need to be downloaded with its `download()` function if this doesn't happen automatically.

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

Make a secrets file for `reliefweb_2000+` or design other pairs of configuration files.

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

### Pipelines

Files in the `pipeline/` directory are used to complete corpus creation. Each pipeline is designed to be a standalone script that's run in bash. Execute a pipeline after exporting an XML-tagged TXT file (`reliefweb_fr.1.txt` in the above example).

To process a text file, run `pipeline/run.sh` with the desired arguments.

**`pipeline/run.sh` positional arguments**

- *$1* the pipeline to use (corresponds to a subdirectory in `pipeline/`)
- *$2* whether to compress the output file: either `t` (for `.vert.xz`) or `f` (for `.vert`)
- *$3* the text file to process (can include XML tags w/ corpus structure attributes)

This example uses Sketch Engine's French pipeline, which normally requires a `.gender_dict` file (see `pipeline/ske_fr/gennum_guess.py`). We'll use an empty file for now:

```bash
touch pipeline/ske_fr/frtenten17_fl2_term_ref.gender_dict
bash pipeline/run.sh ske_fr f reliefweb_fr.1.txt
```

The output is `reliefweb_fr.1.vert`, a vertical corpus file with content that looks like this:

```xml
<!-- the attributes for the corpus document -->
<doc id="59033" file_id="0" country__shortname="Indonesia|Timor-Leste" date__original="2000-01-31T00:00:00+00:00" date__original__year="2000" format__name="UN Document" primary_country__shortname="Indonesia" source__name="UN Security Council" source__shortname="UN SC" source__spanish_name="El Consejo de Seguridad" source__type__name="International Organization" title="Rapport de la Commission d'enquête internationale sur le Timor Oriental adressé au Secrétaire Général" url="https://reliefweb.int/node/59033" >
<!-- part of the first sentence -->
<s>
A/54/726	Z	a/54/726-m	a/54/726	Z	a/54/726	0	0
S/2000/59	NP00000	S/2000/59-n	s/2000/59	NP00000	S/2000/59	F	S
ASSEMBLÉE	NPFS000	ASSEMBLÉE-n	assemblée	NPFS000	ASSEMBLÉE	F	S
GÉNÉRALE	AQ0FS00	général-j	général	AQ0FS00	général	F	S
Cinquante-quatrième	NPCS000	Cinquante-quatrième-n	cinquante-quatrième	NPCS000	Cinquante-quatrième	F	S
session	NCFS000	session-n	session	NCFS000	session	F	S
Point	NPMS000	Point-n	point	NPMS000	Point	M	S
96	Z	96-m	96	Z	96	0	0
```

Vertical files can be loaded into compatible corpus linguistics tools.

### Batch pipeline execution

To process multiple text files, try:

```bash
# option 1: parallel
# add a line for each additional file, up to the device's number of CPUs-1
(trap 'kill 0' SIGINT; \
bash pipeline/run.sh PIPELINE COMPRESS FILE0 &
bash pipeline/run.sh PIPELINE COMPRESS FILE1 &
wait)

# option 2: sequential
for file in rw/reliefweb_fr.{1..9}.txt; do
    echo start ${file}
    $(bash pipeline/run.sh ske_fr t ${file})
    echo done ${file}
done
```

### Designing pipelines

Pipelines can be modified as needed. For convenience, execution is managed with `pipeline/run.sh`. This script finds and executes a chain of commands, e.g. `pipeline/ske_fr/freeling_french_v3.sh`, all of which can be modified. This depends on the software being used (FreeLing, Stanza, ...) and requires understanding all the technical aspects of corpus creation.

### Using corpora

After 1) building a database with `corpusama`, 2) exporting the texts for a language to TXT files, and 3) running these files through a pipeline, the resulting `.vert.xz` files make up a completed corpus. Viewing the corpus (e.g., in Sketch Engine) also requires making a corpus [configuration file](https://www.sketchengine.eu/documentation/corpus-configuration-file-all-features/) and other steps beyond this introduction.

## Acknowledgements

Support comes from the [Humanitarian Encyclopedia](https://humanitarianencyclopedia.org/) and the [LexiCon research group](https://lexicon.ugr.es/) at the University of Granada. See the paper below for references and funding disclosures.

Dependencies include these academic works, which have their corresponding bibliographies: [Stanza](https://github.com/stanfordnlp/stanza), [FreeLing](https://nlp.lsi.upc.edu/freeling/) and [fastText](https://github.com/facebookresearch/fastText).

Subdirectories with a `ske_` prefix are from [Sketch Engine](https://www.sketchengine.eu/) under [AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html), [MPL](https://www.mozilla.org/MPL/2.0), and/or other pertinent licenses. See their [bibliography](https://www.sketchengine.eu/bibliography-of-sketch-engine/) and [website](https://corpus.tools/) with open-source corpus tools.

Other attributions are indicated in individual files. [NoSketch Engine](https://nlp.fi.muni.cz/trac/noske) is a related software used downstream in some projects.

## Citation

Please cite the paper below. `CITATION.cff` can be used if citing the software directly.

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
```
