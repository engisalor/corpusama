CREATE TABLE IF NOT EXISTS rw_log (
'params_hash' TEXT PRIMARY KEY,
'parameters' TEXT NOT NULL UNIQUE,
'api_input' TEXT NOT NULL,
'api_date' TEXT NOT NULL,
'count' INTEGER,
'total_count' INTEGER,
FOREIGN KEY('params_hash') REFERENCES rw_raw('params_hash')
);

CREATE TABLE IF NOT EXISTS rw_pdf (
'id' INTEGER NOT NULL,
'file_id' TEXT NOT NULL UNIQUE,
'description' TEXT,
'filename' TEXT NOT NULL,
'filesize' INTEGER NOT NULL,
'url' TEXT NOT NULL UNIQUE,
'mimetype' TEXT NOT NULL,
FOREIGN KEY('id') REFERENCES rw_raw('id')
);

CREATE TABLE IF NOT EXISTS rw_corpus (
'id' INTEGER PRIMARY KEY,
'vert' TEXT NOT NULL,
'last_mod' TEXT NOT NULL,
FOREIGN KEY('id') REFERENCES rw_raw('id')
);

CREATE TABLE IF NOT EXISTS rw_raw (
'params_hash' TEXT NOT NULL,
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
'source' TEXT,
'status' TEXT,
'theme' TEXT,
'title' TEXT,
'url' TEXT,
'url_alias' TEXT,
'vulnerable_group' TEXT,
'body' TEXT,
'body_html' TEXT
);
