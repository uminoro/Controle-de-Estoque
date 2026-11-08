PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS categoria (
 id INTEGER PRIMARY KEY,
 nome TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(nome)) BETWEEN 1 AND 60)
);
CREATE TABLE IF NOT EXISTS produto (
 id INTEGER PRIMARY KEY,
 categoria_id INTEGER NOT NULL REFERENCES categoria(id),
 codigo TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(codigo)) BETWEEN 1 AND 30),
 nome TEXT NOT NULL CHECK(length(trim(nome)) BETWEEN 1 AND 100),
 minimo INTEGER NOT NULL DEFAULT 0 CHECK(typeof(minimo) = 'integer' AND minimo >= 0),
 saldo INTEGER NOT NULL DEFAULT 0 CHECK(typeof(saldo) = 'integer' AND saldo >= 0)
);
CREATE TABLE IF NOT EXISTS movimentacao (
 id INTEGER PRIMARY KEY,
 produto_id INTEGER NOT NULL REFERENCES produto(id),
 tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA','SAIDA')),
 quantidade INTEGER NOT NULL CHECK(typeof(quantidade) = 'integer' AND quantidade > 0),
 observacao TEXT NOT NULL DEFAULT '' CHECK(length(observacao) <= 200),
 criado_em TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
