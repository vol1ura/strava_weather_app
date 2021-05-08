/*DROP TABLE IF EXISTS subscribers;*/

CREATE TABLE IF NOT EXISTS subscribers (
    id integer NOT NULL PRIMARY KEY,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    expires_at integer NOT NULL);

/*DROP TABLE IF EXISTS settings;*/

CREATE TABLE IF NOT EXISTS settings (
    id integer NOT NULL PRIMARY KEY,
    icon integer NOT NULL,
    humidity integer NOT NULL,
    wind integer NOT NULL,
    aqi integer NOT NULL,
    lan text NOT NULL);
