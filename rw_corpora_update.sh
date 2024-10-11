#!/bin/bash

source $PWD/.venv/bin/activate

if [ $# -ne 2 ]; then
    echo "Usage: $0 <START_DATE> <END_DATE> (both in YYYY-MM-DD format)"
    exit 1
fi

echo "... get and process source data"
python3 rw_corpora_update.py "${$1}" "${$2}" || exit 1
echo "... convert source files to .conllu (run Stanza NLP)"
ES_FILES=$(find -name reliefweb_es*.txt)
FR_FILES=$(find -name reliefweb_fr*.txt)
EN_FILES=$(find -name reliefweb_en*.txt)
python3 ./pipeline/stanza/base_pipeline.py to-conll -l es $ES_FILES || exit 1
python3 ./pipeline/stanza/base_pipeline.py to-conll -l fr $FR_FILES || exit 1
python3 ./pipeline/stanza/base_pipeline.py to-conll -l en $EN_FILES || exit 1
echo "... convert files to .vert and compress"
CONLLU_FILES=$(find -name reliefweb_*.txt.conllu)
python3 ./pipeline/stanza/base_pipeline.py conll-to-vert $CONLLU_FILES || exit 1
echo "... rw_corpora_update.sh completed"
