"""Verificações da regra de triagem, validação, métricas e interface.

Execute com: python -m unittest discover -s tests -v
Usamos unittest da biblioteca padrão para evitar outra dependência.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from dados import carregar_chamados, validar_chamados
from metricas import calcular_metricas
from triagem import ordenar_chamados


RAIZ = Path(__file__).resolve().parents[1]


def exemplo(**alteracoes):
    """Monta um registro válido pequeno para isolar os critérios nos testes."""
    chamado = {
        "id": 1, "titulo": "Falha de rede", "descricao": "Sem conexão.",
        "usuario_abertura": "aluno", "data_abertura": "2026-11-02",
        "hora_abertura": "09:00", "setores_afetados": ["TI"],
        "tipo": "Rede", "usuarios_afetados": 10, "impacto": "alto",
        "tempo_estimado_min": 30, "recursos_necessarios": ["Suporte"],
    }
    chamado.update(alteracoes)
    return chamado


class TesteTriagem(unittest.TestCase):
    def test_criterios_na_ordem_correta(self):
        # Cada par favorece um critério e desfavorece o seguinte.
        pares = [
            (exemplo(impacto="alto", usuarios_afetados=1),
             exemplo(id=2, impacto="medio", usuarios_afetados=100)),
            (exemplo(impacto="medio"), exemplo(id=2, impacto="baixo")),
            (exemplo(usuarios_afetados=20),
             exemplo(id=2, setores_afetados=["TI", "RH"])),
            (exemplo(setores_afetados=["TI", "RH"], hora_abertura="10:00"),
             exemplo(id=2, hora_abertura="08:00")),
            (exemplo(data_abertura="2026-11-01", hora_abertura="17:00"),
             exemplo(id=2, data_abertura="2026-11-02", hora_abertura="08:00")),
            (exemplo(hora_abertura="08:00"), exemplo(id=2)),
            (exemplo(), exemplo(id=2)),
        ]
        for primeiro, segundo in pares:
            with self.subTest(primeiro=primeiro, segundo=segundo):
                self.assertEqual(ordenar_chamados([segundo, primeiro]), [primeiro, segundo])

    def test_setores_repetidos_nao_aumentam_prioridade(self):
        repetido = exemplo(id=2, setores_afetados=["TI", "TI"])
        self.assertEqual(ordenar_chamados([repetido, exemplo()])[0]["id"], 1)

    def test_fila_preserva_base_e_todos_os_ids(self):
        base = carregar_chamados()
        original = deepcopy(base)
        fila = ordenar_chamados(base)
        self.assertEqual(base, original)
        self.assertIsNot(fila, base)
        self.assertEqual(sorted(c["id"] for c in fila), sorted(c["id"] for c in base))
        self.assertEqual(len(set(c["id"] for c in fila)), 30)


class TesteMetricas(unittest.TestCase):
    def test_base_fornecida(self):
        resultado = calcular_metricas(carregar_chamados())
        self.assertEqual(resultado["total"], 30)
        self.assertEqual(resultado["por_impacto"], {"alto": 12, "medio": 8, "baixo": 10})
        self.assertEqual(resultado["por_tipo"],
                         {"Sistema": 10, "Computador": 5, "Acesso": 7, "Impressora": 3, "Rede": 5})
        self.assertEqual(resultado["media_minutos"], 43)

    def test_setores_distintos_e_media(self):
        base = [exemplo(setores_afetados=["TI", "TI", "RH"]),
                exemplo(id=2, setores_afetados=["RH", "Vendas"], tempo_estimado_min=60)]
        resultado = calcular_metricas(base)
        self.assertEqual(resultado["total_setores"], 3)
        self.assertEqual(resultado["media_minutos"], 45)

    def test_vazio_e_unitario(self):
        self.assertEqual(calcular_metricas([])["total_setores"], 0)
        self.assertEqual(calcular_metricas([])["media_minutos"], 0)
        self.assertEqual(calcular_metricas([exemplo()])["total"], 1)


class TesteDados(unittest.TestCase):
    def test_campos_obrigatorios(self):
        for campo in exemplo():
            chamado = exemplo()
            del chamado[campo]
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, campo):
                validar_chamados([chamado])

    def test_valores_invalidos(self):
        casos = [
            ("id", True), ("id", "1"), ("titulo", ""),
            ("descricao", " "), ("usuario_abertura", None), ("tipo", ""),
            ("impacto", "urgente"), ("usuarios_afetados", -1),
            ("usuarios_afetados", 1.5), ("usuarios_afetados", True),
            ("tempo_estimado_min", -1), ("tempo_estimado_min", False),
            ("setores_afetados", []), ("setores_afetados", "TI"),
            ("setores_afetados", [""]), ("recursos_necessarios", []),
            ("recursos_necessarios", [1]), ("data_abertura", "2026-02-30"),
            ("data_abertura", "2026-1-2"), ("hora_abertura", "25:00"),
            ("hora_abertura", "9:00"),
        ]
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                with self.assertRaisesRegex(ValueError, campo):
                    validar_chamados([exemplo(**{campo: valor})])

    def test_estrutura_duplicados_e_contexto(self):
        for base in ({}, [1], [None], [exemplo(), exemplo()]):
            with self.subTest(base=base), self.assertRaises(ValueError):
                validar_chamados(base)
        with self.assertRaisesRegex(ValueError, r"Registro 2.*ID 2.*titulo"):
            validar_chamados([exemplo(), exemplo(id=2, titulo="")])
        validar_chamados([])
        validar_chamados([exemplo(usuarios_afetados=0, tempo_estimado_min=0)])

    def test_arquivo_ausente_invalido_e_utf8(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "base.json"
            with self.assertRaisesRegex(ValueError, "não encontrado"):
                carregar_chamados(caminho)
            caminho.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "linha 1"):
                carregar_chamados(caminho)
            caminho.write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                carregar_chamados(caminho)
            caminho.write_text(json.dumps([exemplo()], ensure_ascii=False), encoding="utf-8")
            self.assertEqual(carregar_chamados(caminho)[0]["titulo"], "Falha de rede")


class TesteInterface(unittest.TestCase):
    def abrir(self):
        """AppTest executa o app sem precisar iniciar um servidor no navegador."""
        return AppTest.from_file(str(RAIZ / "streamlit_app.py")).run(timeout=20)

    def test_dois_menus_e_fila(self):
        app = self.abrir()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "30")
        self.assertEqual(app.metric[1].value, str(calcular_metricas(carregar_chamados())["total_setores"]))
        app.segmented_control[0].set_value("Fila de atendimento").run()
        self.assertFalse(app.exception)
        tabela = app.dataframe[0].value
        fila = ordenar_chamados(carregar_chamados())
        self.assertEqual(tabela["ID"].tolist(), [c["id"] for c in fila[1:]])
        self.assertEqual(tabela["Posição"].tolist(), list(range(2, 31)))
        self.assertIn("Setores atingidos", tabela.columns)
        self.assertIn("Quantidade de setores", tabela.columns)
        self.assertTrue(any("Como definimos" in item.value for item in app.markdown))

    def test_interface_vazia_unitaria_e_invalida(self):
        with patch("dados.carregar_chamados", return_value=[]):
            app = self.abrir()
            self.assertFalse(app.exception)
            self.assertTrue(app.info)
            self.assertFalse(app.metric)
        with patch("dados.carregar_chamados", return_value=[exemplo()]):
            app = self.abrir()
            app.segmented_control[0].set_value("Fila de atendimento").run()
            self.assertFalse(app.exception)
            self.assertFalse(app.dataframe)
            self.assertTrue(any("único" in aviso.value for aviso in app.info))
        with patch("dados.carregar_chamados", side_effect=ValueError("Registro 1: titulo ausente")):
            app = self.abrir()
            self.assertFalse(app.exception)
            self.assertIn("titulo", app.error[0].value)
            self.assertFalse(app.metric)


if __name__ == "__main__":
    unittest.main()
