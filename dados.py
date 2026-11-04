"""Leitura e validação da base local, sem corrigir ou descartar registros."""

import json
from datetime import datetime
from pathlib import Path


def validar_chamados(chamados):
    """Confere o esquema completo antes de liberar os dados para os cálculos.

    A validação para no primeiro erro e identifica a posição, o ID disponível
    e o campo. Assim o grupo pode corrigir a origem sem produzir uma fila parcial.
    A lista vazia é válida; a interface apresenta esse caso separadamente.
    """
    if not isinstance(chamados, list):
        raise ValueError("A base deve conter uma lista de chamados.")

    campos_texto = (
        "titulo", "descricao", "usuario_abertura",
        "data_abertura", "hora_abertura", "tipo", "impacto",
    )
    obrigatorios = (
        "id", *campos_texto, "setores_afetados", "usuarios_afetados",
        "tempo_estimado_min", "recursos_necessarios",
    )
    ids_encontrados = set()

    for posicao, chamado in enumerate(chamados, start=1):
        contexto = f"Registro {posicao}"
        if not isinstance(chamado, dict):
            raise ValueError(f"{contexto}: deve ser um dicionário.")
        contexto += f" (ID {chamado.get('id', 'não informado')})"

        for campo in obrigatorios:
            if campo not in chamado:
                raise ValueError(f"{contexto}: campo obrigatório '{campo}' ausente.")

        # bool é uma subclasse de int em Python. type(...) is int impede
        # aceitar true/false do JSON como ID, quantidade ou tempo.
        if type(chamado["id"]) is not int:
            raise ValueError(f"{contexto}: 'id' deve ser inteiro.")
        if chamado["id"] in ids_encontrados:
            raise ValueError(f"{contexto}: 'id' duplicado.")
        ids_encontrados.add(chamado["id"])

        for campo in campos_texto:
            if not isinstance(chamado[campo], str) or not chamado[campo].strip():
                raise ValueError(f"{contexto}: '{campo}' deve ser texto não vazio.")

        if chamado["impacto"] not in ("alto", "medio", "baixo"):
            raise ValueError(f"{contexto}: 'impacto' deve ser alto, medio ou baixo.")

        for campo in ("usuarios_afetados", "tempo_estimado_min"):
            if type(chamado[campo]) is not int or chamado[campo] < 0:
                raise ValueError(f"{contexto}: '{campo}' deve ser inteiro não negativo.")

        for campo in ("setores_afetados", "recursos_necessarios"):
            itens = chamado[campo]
            if (
                not isinstance(itens, list) or not itens
                or any(not isinstance(item, str) or not item.strip() for item in itens)
            ):
                raise ValueError(
                    f"{contexto}: '{campo}' deve ser lista não vazia de textos não vazios."
                )

        # strptime verifica o calendário. O round-trip também exige zeros
        # à esquerda, pois strptime sozinho aceita datas como 2026-1-2.
        for campo, formato in (
            ("data_abertura", "%Y-%m-%d"), ("hora_abertura", "%H:%M"),
        ):
            try:
                valor = chamado[campo]
                if datetime.strptime(valor, formato).strftime(formato) != valor:
                    raise ValueError()
            except ValueError:
                raise ValueError(
                    f"{contexto}: '{campo}' inválido; formato esperado {formato}."
                ) from None


def carregar_chamados(caminho=None):
    """Lê UTF-8, valida a lista completa e devolve os registros originais.

    O caminho opcional permite testar bases pequenas. Por padrão, o JSON fica
    ao lado deste módulo, independentemente da pasta usada no terminal.
    """
    if caminho is None:
        caminho = Path(__file__).parent / "chamados.json"

    try:
        # O with fecha o arquivo mesmo se a leitura ou a decodificação falhar.
        with open(caminho, encoding="utf-8") as arquivo:
            chamados = json.load(arquivo)
    except FileNotFoundError:
        raise ValueError("Arquivo chamados.json não encontrado.") from None
    except UnicodeError:
        raise ValueError("O arquivo de chamados deve estar salvo em UTF-8.") from None
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"JSON inválido na linha {erro.lineno}, coluna {erro.colno}."
        ) from None
    except OSError:
        raise ValueError("Não foi possível ler o arquivo de chamados. Confira as permissões.") from None

    validar_chamados(chamados)
    return chamados
