#!/usr/bin/env python3
import re
import sys
from time import sleep

import requests

from corpusama.corpus.corpus import Corpus

if __name__ == "__main__":
    # format dates
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    for date in [start_date, end_date]:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            raise ValueError(f" '{date}' is not a valid YYYY-MM-DD value")
    start_date = f"{start_date}T00:00:00+00:00"
    end_date = f"{end_date}T00:00:00+00:00"

    # instantiate corpus controller
    corp = Corpus("config/reliefweb_2000+.yml")

    # update date range
    n = 1
    if not corp.rw.config["parameters"]["filter"]["conditions"][n]["field"] == "date":
        msg = f"condition {n} should have `field=date`: change the list index `n`."
        raise ValueError(msg)

    corp.rw.config["parameters"]["filter"]["conditions"][n]["value"][
        "from"
    ] = start_date
    corp.rw.config["parameters"]["filter"]["conditions"][n]["value"]["to"] = end_date
    new_filter = corp.rw.config["parameters"]["filter"]["conditions"][n]["value"]
    print(f"... new date filter: {new_filter}")

    # update sqlite database
    corp.rw.get_new_records()

    # download associated PDFs, retry to handle known errors
    n_retries = 20
    max_retries = 20
    pause = 60
    success = False
    while n_retries < max_retries:
        try:
            corp.rw.get_pdfs()
            print("... success")
            success = True
            n_retries = max_retries
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
        ) as e:
            n_retries += 1
            print(f"... retrying after {pause} seconds: {e}")
            sleep(pause)
    if not success:
        raise ValueError("reached maximum number of retries: check exceptions")

    # extract PDF text to TXT file in same location
    corp.rw.extract_pdfs()

    # run language identification
    corp.make_langid("_pdf")
    corp.make_langid("_raw")

    # make corpus XML <doc> attributes for languages
    corp.make_attribute("es")
    corp.make_attribute("fr")
    corp.make_attribute("en")

    # export the XML-tagged texts in chunks of <= 10,000
    corp.export_text("es", start_date=start_date[:10], end_date=end_date[:10])
    corp.export_text("fr", start_date=start_date[:10], end_date=end_date[:10])
    corp.export_text("en", start_date=start_date[:10], end_date=end_date[:10])
