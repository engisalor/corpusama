#!/bin/bash
# bash pipeline/run.sh <PIPELINE> <COMPRESS (t/f)> <FILE>

if [ $1 == "ske_es" ]
  then
    PIPELINE=freeling_spanish_v6.sh
elif [ $1 == "ske_fr" ]
  then
    PIPELINE=freeling_french_v3.sh
else
  echo INVALID PIPELINE value '($1)': must be in '(ske_es ske_fr)', not $1
fi

if [ $2 == "t" ]
  then
    cat "$3" | pipeline/$1/$PIPELINE | xz -z > "${3%.*}.vert.xz"
elif [ $2 == "f" ]
  then
    cat "$3" | pipeline/$1/$PIPELINE > "${3%.*}.vert"
else
  echo INVALID COMPRESS value '($2)': must be t or f, not $2
fi
