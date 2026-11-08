import tempfile
import unittest
from pathlib import Path
from app import EstoqueService

class TestEstoque(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / 'teste.db'
        self.s = EstoqueService(self.caminho)
        self.c = self.s.cadastrar_categoria({'nome':'Papelaria'})

    def tearDown(self):
        self.tmp.cleanup()

    def produto(self):
        return self.s.cadastrar_produto({'nome':'Caneta azul', 'codigo':'CAN001', 'categoria_id':self.c, 'minimo':3})

    def mover(self, p, tipo, quantidade):
        return self.s.movimentar({'produto_id':p,'tipo':tipo,'quantidade':quantidade})

    def test_CT01_cadastro_e_persistencia(self):
        self.produto()
        estado = EstoqueService(self.caminho).consultar()
        self.assertEqual(estado['produtos'][0]['nome'], 'Caneta azul')
        self.assertEqual(estado['produtos'][0]['saldo'], 0)

    def test_CT02_nome_vazio(self):
        with self.assertRaisesRegex(ValueError, 'Nome'):
            self.s.cadastrar_produto({'nome':'  ','codigo':'C1','categoria_id':self.c,'minimo':0})
        self.assertEqual(self.s.consultar()['produtos'], [])

    def test_CT03_codigo_duplicado(self):
        self.produto()
        with self.assertRaisesRegex(ValueError, 'já cadastrado'):
            self.produto()
        self.assertEqual(len(self.s.consultar()['produtos']), 1)

    def test_CT04_entrada(self):
        p=self.produto(); self.mover(p, 'ENTRADA',10)
        estado=self.s.consultar()
        self.assertEqual(estado['produtos'][0]['saldo'],10)
        self.assertEqual(estado['movimentos'][0]['quantidade'],10)

    def test_CT05_saida_valida(self):
        p=self.produto(); self.mover(p,'ENTRADA',10); self.mover(p,'SAIDA',4)
        estado=self.s.consultar()
        self.assertEqual(estado['produtos'][0]['saldo'],6)
        self.assertEqual(len(estado['movimentos']),2)

    def test_CT06_saida_sem_saldo(self):
        p=self.produto(); self.mover(p,'ENTRADA',10)
        with self.assertRaisesRegex(ValueError,'Saldo insuficiente'):
            self.mover(p,'SAIDA',11)
        estado=self.s.consultar()
        self.assertEqual(estado['produtos'][0]['saldo'],10)
        self.assertEqual(len(estado['movimentos']),1)

    def test_CT07_quantidades_invalidas(self):
        p=self.produto()
        for q in (0,-1,1.5,True,'2'):
            with self.subTest(q=q), self.assertRaises(ValueError):
                self.mover(p,'ENTRADA',q)
        self.assertEqual(self.s.consultar()['movimentos'],[])

    def test_CT08_referencias_invalidas(self):
        with self.assertRaisesRegex(ValueError,'Categoria não encontrada'):
            self.s.cadastrar_produto({'nome':'Teste','codigo':'T1','categoria_id':999,'minimo':0})
        with self.assertRaisesRegex(ValueError,'Produto não encontrado'):
            self.mover(999,'ENTRADA',1)

    def test_CT09_categoria_duplicada(self):
        with self.assertRaisesRegex(ValueError,'já cadastrada'):
            self.s.cadastrar_categoria({'nome':'papelaria'})

    def test_CT10_texto_sql_como_dado(self):
        nome="Teste'); DROP TABLE produto; --"
        self.s.cadastrar_produto({'nome':nome,'codigo':'SQL1','categoria_id':self.c,'minimo':0})
        self.assertEqual(self.s.consultar()['produtos'][0]['nome'],nome)

if __name__=='__main__':
    unittest.main(verbosity=2)
