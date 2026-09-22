-- 東大生向け情報交換掲示板のスキーマ。
-- 時刻はすべて UNIX エポックミリ秒（INTEGER）。カーソルページングで素直に比較できるため。

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  handle        TEXT    NOT NULL UNIQUE,      -- 英数字とアンダースコア
  display_name  TEXT    NOT NULL,
  password_hash TEXT,                          -- ゲストは NULL
  bio           TEXT    NOT NULL DEFAULT '',
  is_guest      INTEGER NOT NULL DEFAULT 0,
  is_admin      INTEGER NOT NULL DEFAULT 0,
  verified_at   INTEGER,                       -- 東大メール確認済みの時刻
  verified_kind TEXT,                          -- 'u-tokyo' など
  created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token      TEXT PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf       TEXT    NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- 認証コード（東大メール確認）。メール送信は外部に任せ、ここでは検証だけを持つ。
CREATE TABLE IF NOT EXISTS email_codes (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email_hash TEXT    NOT NULL,   -- 生のアドレスは保存しない
  domain     TEXT    NOT NULL,
  code_hash  TEXT    NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_email_codes_user ON email_codes(user_id);

CREATE TABLE IF NOT EXISTS boards (
  slug          TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  description   TEXT NOT NULL DEFAULT '',
  verified_only INTEGER NOT NULL DEFAULT 0,  -- 東大メール確認済みだけが書ける板
  position      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS media (
  id          TEXT PRIMARY KEY,               -- ランダム16進
  uploader_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  mime        TEXT    NOT NULL,
  width       INTEGER NOT NULL DEFAULT 0,
  height      INTEGER NOT NULL DEFAULT 0,
  bytes       INTEGER NOT NULL DEFAULT 0,
  sha256      TEXT    NOT NULL,
  status      TEXT    NOT NULL,               -- approved / pending / blocked
  score       REAL    NOT NULL DEFAULT 0,
  reason      TEXT    NOT NULL DEFAULT '',
  details     TEXT    NOT NULL DEFAULT '{}',
  created_at  INTEGER NOT NULL,
  reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_media_status ON media(status, created_at);
CREATE INDEX IF NOT EXISTS idx_media_sha ON media(sha256);

-- 二度と載せない画像のハッシュ（管理者がブロックしたもの＋初期ブロックリスト）
CREATE TABLE IF NOT EXISTS blocked_hashes (
  sha256     TEXT PRIMARY KEY,
  reason     TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  board        TEXT    REFERENCES boards(slug) ON DELETE SET NULL,
  body         TEXT    NOT NULL DEFAULT '',
  anonymous    INTEGER NOT NULL DEFAULT 0,
  parent_id    INTEGER REFERENCES posts(id) ON DELETE CASCADE,
  root_id      INTEGER,                       -- スレッドの先頭（自分自身のこともある）
  created_at   INTEGER NOT NULL,
  deleted_at   INTEGER,
  deleted_by   TEXT                           -- 'author' / 'moderator'
);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_board ON posts(board, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_parent ON posts(parent_id, created_at);

CREATE TABLE IF NOT EXISTS post_media (
  post_id  INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  media_id TEXT    NOT NULL REFERENCES media(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (post_id, media_id)
);

CREATE TABLE IF NOT EXISTS likes (
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_post ON likes(post_id);

CREATE TABLE IF NOT EXISTS reposts (
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_reposts_post ON reposts(post_id);
CREATE INDEX IF NOT EXISTS idx_reposts_user ON reposts(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS follows (
  follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followee_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (follower_id, followee_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_followee ON follows(followee_id);

CREATE TABLE IF NOT EXISTS dm_threads (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_lo    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- id の小さいほう
  user_hi    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  UNIQUE (user_lo, user_hi)
);

CREATE TABLE IF NOT EXISTS dm_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  thread_id  INTEGER NOT NULL REFERENCES dm_threads(id) ON DELETE CASCADE,
  sender_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body       TEXT    NOT NULL,
  created_at INTEGER NOT NULL,
  read_at    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_dm_messages_thread ON dm_messages(thread_id, id);

CREATE TABLE IF NOT EXISTS reports (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  target_type TEXT    NOT NULL,   -- 'post' / 'media' / 'user'
  target_id   TEXT    NOT NULL,
  reason      TEXT    NOT NULL,
  note        TEXT    NOT NULL DEFAULT '',
  created_at  INTEGER NOT NULL,
  resolved_at INTEGER,
  resolution  TEXT
);
CREATE INDEX IF NOT EXISTS idx_reports_open ON reports(resolved_at, created_at DESC);
