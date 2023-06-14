#!/bin/bash
set -euo pipefail

THISDIR=$(readlink -f $(dirname ${BASH_SOURCE[0]}))
UNINORM="$THISDIR/uninorm_4"
BASE="$THISDIR/spanish/base_pipeline_v6.py"
GUESSER="$THISDIR/spanish/gennum_guess.py"

$UNINORM | $BASE | $GUESSER
