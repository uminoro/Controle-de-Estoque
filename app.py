"""Protótipo local de estoque. Execute: python app.py. Sem pacotes externos."""
from dataclasses import dataclass
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
import sqlite3

BASE = Path(__file__).resolve().parent

@dataclass
class Categoria:
    id: int
    nome: str

    def validar(self):
        return texto(self.nome, 'Nome da categoria', 60)

@dataclass
class Produto:
    id: int
    categoria_id: int
    codigo: str
    nome: str
    minimo: int = 0
    saldo: int = 0

    def precisa_reposicao(self):
        return self.saldo <= self.minimo

@dataclass
class Movimentacao:
    id: int
    produto_id: int
    tipo: str
    quantidade: int
    observacao: str = ''
    criado_em: str = ''

    def delta(self):
        return self.quantidade if self.tipo == 'ENTRADA' else -self.quantidade

def texto(valor, campo, limite):
    if not isinstance(valor, str) or not 1 <= len(valor.strip()) <= limite:
        raise ValueError(f'{campo}: informe de 1 a {limite} caracteres.')
    return valor.strip()

def inteiro(valor, campo, minimo=0):
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo or valor > 1000000000:
        raise ValueError(f'{campo}: informe um inteiro entre {minimo} e 1000000000.')
    return valor

class EstoqueService:
    def __init__(self, banco):
        self.banco = str(banco)
        with closing(self.conectar()) as con:
            con.executescript((BASE / 'schema.sql').read_text(encoding='utf-8'))

    def conectar(self):
        con = sqlite3.connect(self.banco, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys = ON')
        return con

    def cadastrar_categoria(self, dados):
        nome = Categoria(0, dados.get('nome')).validar()
        with closing(self.conectar()) as con, con:
            try:
                return con.execute('INSERT INTO categoria(nome) VALUES (?)', (nome,)).lastrowid
            except sqlite3.IntegrityError:
                raise ValueError('Categoria já cadastrada.') from None

    def cadastrar_produto(self, dados):
        nome = texto(dados.get('nome'), 'Nome', 100)
        codigo = texto(dados.get('codigo'), 'Código', 30).upper()
        categoria = inteiro(dados.get('categoria_id'), 'Categoria', 1)
        minimo = inteiro(dados.get('minimo'), 'Estoque mínimo')
        with closing(self.conectar()) as con, con:
            if not con.execute('SELECT id FROM categoria WHERE id=?', (categoria,)).fetchone():
                raise ValueError('Categoria não encontrada.')
            try:
                return con.execute(
                    'INSERT INTO produto(categoria_id,codigo,nome,minimo) VALUES (?,?,?,?)',
                    (categoria, codigo, nome, minimo)).lastrowid
            except sqlite3.IntegrityError:
                raise ValueError('Código de produto já cadastrado.') from None

    def movimentar(self, dados):
        produto_id = inteiro(dados.get('produto_id'), 'Produto', 1)
        quantidade = inteiro(dados.get('quantidade'), 'Quantidade', 1)
        tipo = dados.get('tipo')
        if tipo not in ('ENTRADA', 'SAIDA'):
            raise ValueError('Tipo de movimentação inválido.')
        obs = dados.get('observacao', '')
        if not isinstance(obs, str) or len(obs.strip()) > 200:
            raise ValueError('Observação: no máximo 200 caracteres.')
        movimento = Movimentacao(0, produto_id, tipo, quantidade, obs.strip())
        with closing(self.conectar()) as con, con:
            # A transação impede que duas saídas consumam o mesmo saldo.
            con.execute('BEGIN IMMEDIATE')
            produto = con.execute('SELECT saldo FROM produto WHERE id=?', (produto_id,)).fetchone()
            if produto is None:
                raise ValueError('Produto não encontrado.')
            if produto['saldo'] + movimento.delta() < 0:
                raise ValueError('Saldo insuficiente. A saída não foi registrada.')
            con.execute('UPDATE produto SET saldo=saldo+? WHERE id=?',
                        (movimento.delta(), produto_id))
            return con.execute(
                'INSERT INTO movimentacao(produto_id,tipo,quantidade,observacao) VALUES (?,?,?,?)',
                (produto_id, tipo, quantidade, movimento.observacao)).lastrowid

    def consultar(self):
        with closing(self.conectar()) as con:
            categorias = [dict(r) for r in con.execute('SELECT * FROM categoria ORDER BY nome')]
            produtos = [dict(r) for r in con.execute('''SELECT p.*, c.nome AS categoria
                FROM produto p JOIN categoria c ON c.id=p.categoria_id ORDER BY p.nome''')]
            movimentos = [dict(r) for r in con.execute('''SELECT m.*, p.nome AS produto, p.codigo
                FROM movimentacao m JOIN produto p ON p.id=m.produto_id ORDER BY m.id DESC''')]
        return {'categorias': categorias, 'produtos': produtos, 'movimentos': movimentos}

class Handler(BaseHTTPRequestHandler):
    service = None

    def enviar(self, status, corpo, tipo='application/json; charset=utf-8'):
        if not isinstance(corpo, bytes):
            corpo = json.dumps(corpo, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(corpo)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(corpo)

    def host_valido(self):
        return self.headers.get('Host') in ('127.0.0.1:8000', 'localhost:8000')

    def do_GET(self):
        if not self.host_valido():
            return self.enviar(403, {'erro': 'Host não permitido.'})
        rota = urlsplit(self.path).path
        if rota == '/api/dados':
            return self.enviar(200, self.service.consultar())
        arquivos = {'/': ('index.html','text/html'), '/app.js': ('app.js','text/javascript'),
                    '/style.css': ('style.css','text/css')}
        if rota not in arquivos:
            return self.enviar(404, {'erro':'Página não encontrada.'})
        nome, mime = arquivos[rota]
        self.enviar(200, (BASE / 'static' / nome).read_bytes(), mime + '; charset=utf-8')

    def do_POST(self):
        if not self.host_valido() or self.headers.get('Origin') not in (
                'http://127.0.0.1:8000', 'http://localhost:8000'):
            return self.enviar(403, {'erro': 'Origem não permitida.'})
        rotas = {'/api/categorias': self.service.cadastrar_categoria,
                 '/api/produtos': self.service.cadastrar_produto,
                 '/api/movimentos': self.service.movimentar}
        acao = rotas.get(urlsplit(self.path).path)
        if not acao:
            return self.enviar(404, {'erro':'Operação não encontrada.'})
        try:
            tamanho = int(self.headers.get('Content-Length', '0'))
            if tamanho < 1 or tamanho > 8192 or self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Requisição inválida.')
            dados = json.loads(self.rfile.read(tamanho))
            if not isinstance(dados, dict):
                raise ValueError('Dados inválidos.')
            registro = acao(dados)
            self.enviar(201, {'id': registro, 'mensagem':'Registro salvo com sucesso.'})
        except (ValueError, UnicodeError) as erro:
            self.enviar(400, {'erro': str(erro)})
        except sqlite3.Error:
            self.enviar(500, {'erro':'Não foi possível acessar o banco de dados.'})

if __name__ == '__main__':
    Handler.service = EstoqueService(os.environ.get('ESTOQUE_DB', str(BASE / 'estoque.db')))
    print('Estoque local em http://127.0.0.1:8000 - encerre com Ctrl+C', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
