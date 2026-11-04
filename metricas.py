"""Métricas calculadas com listas e dicionários do Python."""


def calcular_metricas(chamados):
    """Devolve contagens e média para o painel.

    Inicializamos os impactos com zero para exibir também categorias ausentes.
    A média usa tempos estimados: não representa tempo real de atendimento.
    """
    por_impacto = {"alto": 0, "medio": 0, "baixo": 0}
    por_tipo = {}
    tempo_total = 0
    setores_distintos = set()

    for chamado in chamados:
        por_impacto[chamado["impacto"]] += 1
        # get devolve zero quando encontramos um tipo pela primeira vez.
        tipo = chamado["tipo"]
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        tempo_total += chamado["tempo_estimado_min"]
        # A união guarda cada nome de setor uma única vez na base inteira.
        setores_distintos.update(chamado["setores_afetados"])

    total = len(chamados)
    return {
        "total": total,
        "total_setores": len(setores_distintos),
        "por_impacto": por_impacto,
        "por_tipo": por_tipo,
        # A condição evita divisão por zero quando a base está vazia.
        "media_minutos": tempo_total / total if total else 0,
    }
