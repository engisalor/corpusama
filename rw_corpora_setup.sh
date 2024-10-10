#!/bin/bash

# install notes
read -p """
1. Starting Corpusama setup. This script assumes you've already run the below:
   git clone https://github.com/engisalor/corpusama && cd corpusama

2. Stanza and NLTK models will be downloaded to ~/. These resources will be
   reused until updated manually. Requires ~<10 GB for dependencies and models.

3. After installing dependencies, unittest will run to ensure proper setup.
   As of 2024/10/09 no tests should fail.

4. See ReliefWeb's terms and conditions before using the service/its data.

Enter email address to use ReliefWeb's API: """ USER_EMAIL

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
mkdir $PDF_DIR
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
