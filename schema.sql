-- table offers
CREATE TABLE offers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
          pro_id TEXT NOT NULL REFERENCES users(pro_id),
          price INTEGER NOT NULL CHECK(price BETWEEN 20 AND 100000),
          eta TEXT NOT NULL, message TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(request_id, pro_id)
        );

-- table requests
CREATE TABLE requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_id TEXT NOT NULL REFERENCES users(id),
          service TEXT NOT NULL, zone TEXT NOT NULL, details TEXT NOT NULL,
          budget INTEGER NOT NULL CHECK(budget BETWEEN 20 AND 100000),
          when_label TEXT NOT NULL, urgent INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','accepted','done','cancelled')),
          selected_offer INTEGER, rating INTEGER CHECK(rating BETWEEN 1 AND 5),
          created TEXT NOT NULL DEFAULT CURRENT_DATE
        );

-- table sessions
CREATE TABLE sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
          csrf TEXT NOT NULL, expires INTEGER NOT NULL
        );

-- table users
CREATE TABLE users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL,
          email TEXT NOT NULL COLLATE NOCASE UNIQUE, password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK (role IN ('client','pro','admin')),
          pro_id TEXT UNIQUE, services TEXT NOT NULL DEFAULT '[]',
          demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

-- index idx_offers_request
CREATE INDEX idx_offers_request ON offers(request_id);

-- index idx_requests_client
CREATE INDEX idx_requests_client ON requests(client_id);

-- index idx_requests_service_status
CREATE INDEX idx_requests_service_status ON requests(service, status);

-- table messages (messagerie privée liée à une demande et une offre)
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
  pro_id TEXT NOT NULL REFERENCES users(pro_id),
  sender_id TEXT NOT NULL REFERENCES users(id),
  body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 1000),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  read_at TEXT
);
CREATE INDEX idx_messages_thread ON messages(request_id,pro_id,id);
CREATE INDEX idx_messages_unread ON messages(request_id,pro_id,read_at);
