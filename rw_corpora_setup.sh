#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <USER_EMAIL> (required for using ReliefWeb API)"
    exit 1
fi

# initial setup
PDF_DIR=$PWD/data/pdf/
python3 -m venv .venv
source $PWD/.venv/bin/activate
# install dependencies
pip install -U pip
pip install -r requirements.txt
# download resources
python3 << EOL
import stanza
import nltk
nltk.download("punkt_tab")
stanza.download("english")
stanza.download("french")
stanza.download("spanish")
stanza.download("multilingual")
EOL
# generate untracked files
mkdir -p $PDF_DIR
cat > $PWD/test/config-example.secret.yml << EOL
pdf_dir: ${PDF_DIR}
url: https://api.reliefweb.int/v1/reports?appname=${USER_EMAIL}
EOL
cat > $PWD/config/reliefweb_2000+.secret.yml << EOL
pdf_dir: ${PDF_DIR}
url: https://api.reliefweb.int/v1/reports?appname=${USER_EMAIL}
EOL
# unittest
python3 -m unittest
