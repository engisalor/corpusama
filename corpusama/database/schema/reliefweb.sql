CREATE TABLE IF NOT EXISTS _log (
'api_params_hash' TEXT PRIMARY KEY,
'api_params' TEXT NOT NULL UNIQUE,
'api_input' TEXT NOT NULL,
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
'lang_date' TEXT NOT NULL,
'lid' TEXT,
FOREIGN KEY('id') REFERENCES _raw ('id')
PRIMARY KEY ('id', 'file_id')
);

CREATE TABLE IF NOT EXISTS _attr (
'id' INTEGER NOT NULL,
'doc_tag' TEXT NOT NULL,
FOREIGN KEY('id') REFERENCES _raw ('id')
PRIMARY KEY ('id')
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
