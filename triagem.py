"""Regra de prioridade do Queue Foi?, independente da interface."""

from datetime import datetime


def chave_prioridade(chamado):
    """Cria os critérios que o sorted compara da esquerda para a direita.

    Menores valores vêm primeiro: alto recebe 0, médio 1 e baixo 2.
    Negamos o número de usuários para que uma quantidade maior venha antes.
    A quantidade de setores distintos só decide se impacto e usuários empatam.
    A abertura mais antiga decide depois dos setores.
    O ID crescente mantém uma ordem definida quando os outros critérios empatam.
    """
    ordem_impacto = {"alto": 0, "medio": 1, "baixo": 2}
    abertura = datetime.strptime(
        f"{chamado['data_abertura']} {chamado['hora_abertura']}",
        "%Y-%m-%d %H:%M",
    )
    return (
        ordem_impacto[chamado["impacto"]],
        -chamado["usuarios_afetados"],
        # set elimina repetições sem modificar a lista do JSON.
        -len(set(chamado["setores_afetados"])),
        abertura,
        chamado["id"],
    )


def ordenar_chamados(chamados):
    """Devolve uma nova lista em ordem de atendimento, preservando a original.

    Exemplo: dois chamados de impacto alto afetam 10 e 30 usuários.
    O de 30 vem primeiro. Com usuários iguais, mais setores vêm antes da data.
    """
    return sorted(chamados, key=chave_prioridade)
