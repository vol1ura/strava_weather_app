-- subscribers
CREATE TABLE IF NOT EXISTS subscribers (
    id integer NOT NULL PRIMARY KEY,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    expires_at integer NOT NULL);

-- settings
CREATE TABLE IF NOT EXISTS settings (
    id integer NOT NULL PRIMARY KEY,
    units text NOT NULL);
