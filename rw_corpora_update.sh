#!/bin/bash

source $PWD/.venv/bin/activate

echo """
1. Starting ReliefWeb corpus update. This generates EN, FR & ES corpora
   by downloading API data and processing it with Stanza NLP. Having a
   GPU is highly recommended.

2. This script produces a series of compressed vertical corpus files in
   a CoNLLU-based format.

3. After completion, this project can be deleted. If not deleted,
   downloaded data will keep accumulating for every run. Storing all of
   ReliefWeb takes ~500 GB and weeks to download/process.

4. This script reuses config/reliefweb_2000+.yml to define settings.
   Next you will enter a date range for texts to be downloaded. Use a
   YYYY-MM-DD format. The example below collects data for January 2020:

   START_DATE = 2020-01-01
   END_DATE   = 2020-02-01
"""

read -p "Enter start date: " START_DATE
read -p "Enter end date:   " END_DATE
read -p "Are you sure? Press any button to continue."

echo "... get and process source data"
python3 rw_corpora_update.py "${START_DATE}" "${END_DATE}" || exit 1

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

echo "... rw_corpora_update.sh finished without breaking"
