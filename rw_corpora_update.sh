#!/bin/bash

source $PWD/.venv/bin/activate

if [ $# -ne 2 ]; then
    echo "Usage: $0 <START_DATE> <END_DATE> (both in YYYY-MM-DD format)"
    exit 1
fi

echo "... get and process source data"
python3 rw_corpora_update.py "${1}" "${2}" || exit 1
echo "... convert source files to .conllu (run Stanza NLP)"
ES_FILES=$(find -name "reliefweb_es*.txt")
FR_FILES=$(find -name "reliefweb_fr*.txt")
EN_FILES=$(find -name "reliefweb_en*.txt")
python3 ./pipeline/stanza/base_pipeline.py to-conll -l es $ES_FILES || exit 1
python3 ./pipeline/stanza/base_pipeline.py to-conll -l fr $FR_FILES || exit 1
python3 ./pipeline/stanza/base_pipeline.py to-conll -l en $EN_FILES || exit 1
echo "... convert files to .vert and compress"
CONLLU_FILES=$(find -name "reliefweb_*.txt.conllu")
python3 ./pipeline/stanza/base_pipeline.py conll-to-vert --no-compress $CONLLU_FILES || exit 1
EN_VERT_FILES=$(find -name "reliefweb_en*.vert")
FR_VERT_FILES=$(find -name "reliefweb_fr*.vert")
ES_VERT_FILES=$(find -name "reliefweb_es*.vert")
echo "... base_pipeline completed"
echo "... start secondary pipeline"
echo "... run sentence-level language identification for ES"
python3 ./pipeline/stanza/secondary_pipeline.py lingid $ES_VERT_FILES || exit 1
echo "... update structures for ES, inc. langid"
python3 ./pipeline/stanza/secondary_pipeline.py main $ES_VERT_FILES --clear --langid || exit 1
echo "... update structures for EN and FR"
python3 ./pipeline/stanza/secondary_pipeline.py main $EN_VERT_FILES --clear || exit 1
python3 ./pipeline/stanza/secondary_pipeline.py main $FR_VERT_FILES --clear || exit 1
echo "... secondary pipeline completed"
echo "... rw_corpora_update.sh completed"
