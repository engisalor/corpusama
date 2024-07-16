# Error correction log

Some troubleshooting may be necessary to generate different corpora, particularly for managing GPU and CPU resources. This file is a record of steps taken to address issues with the Stanza pipeline while processing sets of files on a device with an 8 GB GPU. Filenames follow this format: `<corpusFamily_languageISO_startDate_endDate.txt.xz>`.

### reliefweb_en_2000-01-01_2023-12-31.43.txt.xz

2024-06-28

The Stanza pipeline failed on ReliefWeb `<doc id="686127" file_id="1759063"...` due to thousands of lines containing only one character, either an asterisk or hash:

```txt
#
*

#
*

#
*
#
*
```

This was due to the PDF text extractor identifying thousands of points on a map as text. These lines were removed using the snippet below (followed by compressing with `xz` again). Only this RW report was modified.

```py
import lzma
txt = "reliefweb_en_2000-01-01_2023-12-31.43.txt.xz"
with lzma.open(txt, "rt") as f:
    with open("reliefweb_en_2000-01-01_2023-12-31.43.clean.txt", "w") as out:
        switch = False
        for i, line in enumerate(f):
            if line.startswith('<doc id="686127" file_id="1759063"'):
                switch = True
            if switch and line.startswith('</doc'):
                switch = False

            if switch:
                if line in ["*\n", "#\n"]:
                    pass
                else:
                    out.write(line)
            else:
                out.write(line)
```

### reliefweb_en_2000-01-01_2023-12-31.46.txt.xz

2024/07/09

Raised a CUDA out of memory error, which was traced to `doc id="989226" file_id="1799894"`, due to tabular data and/or data without sentence-delimiting punctuation. The `force` parameter was reduced from `10` to `8`.

`time python pipeline/stanza/base_pipeline.py -csuwvV --force 8 en rw/reliefweb_en_2000-01-01_2023-12-31.46.txt.xz`

### reliefweb_en_2000-01-01_2023-12-31.52.txt.xz

2024/07/09

Raised another error: reducing `force` to `8` also fixed the issue. `8` will be set as the default in the future.

### reliefweb_en_2000-01-01_2023-12-31.1.txt.xz

2024/07/09

Also run with `force=8`.
