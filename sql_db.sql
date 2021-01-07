CREATE TABLE IF NOT EXISTS subscribers (
    id integer NOT NULL,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    expires_at integer NOT NULL);