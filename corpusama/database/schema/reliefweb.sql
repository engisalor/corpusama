CREATE TABLE IF NOT EXISTS _log (
'api_params_hash' TEXT PRIMARY KEY,
'api_params' TEXT NOT NULL UNIQUE,
'api_date' TEXT NOT NULL,
'count' INTEGER,
'total_count' INTEGER,
FOREIGN KEY('api_params_hash') REFERENCES _raw ('api_params_hash')
);

CREATE TABLE IF NOT EXISTS _pdf (
'id' INTEGER NOT NULL,
'file_id' INTEGER NOT NULL UNIQUE,
'description' TEXT,
'filename' TEXT NOT NULL,
'filesize' INTEGER,
'url' TEXT NOT NULL UNIQUE,
'mimetype' TEXT NOT NULL,
FOREIGN KEY('id') REFERENCES _raw ('id')
);

CREATE TABLE IF NOT EXISTS _lang (
'id' INTEGER NOT NULL,
'file_id' INTEGER NOT NULL,
'top_lang' TEXT,
'top_size' REAL,
FOREIGN KEY('id') REFERENCES _raw ('id')
PRIMARY KEY ('id', 'file_id')
);

CREATE TABLE IF NOT EXISTS _vert (
'id' INTEGER PRIMARY KEY,
'vert_date' TEXT NOT NULL,
'attr' TEXT,
'vert' TEXT NOT NULL,
FOREIGN KEY('id') REFERENCES _raw ('id')
);

CREATE TABLE IF NOT EXISTS _archive (
'year' TEXT PRIMARY KEY,
'doc_count' TEXT NOT NULL,
'archive_date' TEXT,
'archive' BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS _raw  (
'api_params_hash' TEXT NOT NULL,
'id' INTEGER PRIMARY KEY,
'country' TEXT,
'date' TEXT,
'disaster' TEXT,
'disaster_type' TEXT,
'feature' TEXT,
'file' TEXT,
'format' TEXT,
'headline' TEXT,
'image' TEXT,
'language' TEXT,
'ocha_product' TEXT,
'origin' TEXT,
'primary_country' TEXT,
'redirects' TEXT,
'source' TEXT,
'status' TEXT,
'theme' TEXT,
'title' TEXT,
'url' TEXT,
'url_alias' TEXT,
'vulnerable_groups' TEXT,
'body' TEXT,
'body_html' TEXT
);
