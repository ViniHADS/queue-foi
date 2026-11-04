"""Interface do Queue Foi?: painel de métricas e fila de atendimento."""

from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

from dados import carregar_chamados
from metricas import calcular_metricas
from triagem import ordenar_chamados


# O tema cuida dos componentes nativos; o único CSS do projeto estiliza
# apenas as classes que criamos. Path evita depender da pasta de execução.
st.set_page_config(page_title="Queue Foi? | Triagem de TI", layout="wide")
st.html(Path(__file__).parent / "assets" / "estilos.css")
st.html("""
<header class="qf-cabecalho">
    <span class="qf-etiqueta">SUPORTE DE TI · CHECKPOINT 6</span>
    <h1>Queue Foi?</h1>
    <p>Cada chamado no seu lugar. O próximo atendimento começa aqui.</p>
</header>
""")

menu = st.segmented_control(
    "Navegação", ["Painel de métricas", "Fila de atendimento"],
    default="Painel de métricas", selection_mode="single", required=True,
)

# A base tem apenas 30 registros: a leitura local é pequena e dispensa cache.
# Interrompemos a tela em caso de erro para não mostrar métricas incompletas.
try:
    chamados = carregar_chamados()
    fila = ordenar_chamados(chamados)
    metricas = calcular_metricas(chamados)
except (OSError, UnicodeError, ValueError, KeyError, TypeError) as erro:
    st.error(
        "Não foi possível carregar os chamados. Confira o arquivo chamados.json. "
        f"Detalhe: {erro}"
    )
    st.stop()

if not chamados:
    st.info("Nenhum chamado registrado. A base chamados.json está vazia.")
    st.stop()

nomes_impacto = {"alto": "Alto", "medio": "Médio", "baixo": "Baixo"}

if menu == "Painel de métricas":
    st.subheader("Visão geral")
    st.caption("Indicadores calculados a partir de todos os chamados da base.")
    with st.container(horizontal=True):
        st.metric("Chamados registrados", metricas["total"], border=True)
        st.metric("Setores distintos atingidos", metricas["total_setores"], border=True)
        media = f"{metricas['media_minutos']:.1f}".replace(".", ",")
        st.metric("Resolução estimada média", f"{media} min", border=True)

    # Cada linha contém uma categoria e sua contagem. Streamlit desenha
    # o gráfico; a regra de cálculo continua no nosso Python, em metricas.py.
    with st.container(border=True):
        st.subheader("Chamados por tipo")
        tipos = [
            {"Tipo": tipo, "Chamados": quantidade}
            for tipo, quantidade in metricas["por_tipo"].items()
        ]
        st.bar_chart(tipos, x="Tipo", y="Chamados", color="#2457C5")

    st.subheader("Distribuição por impacto")
    st.dataframe(
        [{"Impacto": nomes_impacto[impacto], "Chamados": quantidade}
         for impacto, quantidade in metricas["por_impacto"].items()],
        hide_index=True,
    )
else:
    st.subheader("Fila de atendimento")
    # Caixa sempre visível: a regra pode ser consultada sem abrir um expander.
    with st.container(border=True):
        st.markdown("**Como definimos a prioridade**")
        st.markdown(
            "1. Maior impacto: alto → médio → baixo.\n"
            "2. Maior quantidade de usuários afetados.\n"
            "3. Maior quantidade de setores distintos atingidos.\n"
            "4. Abertura mais antiga.\n"
            "5. Menor ID."
        )
        st.caption(
            "Setores só desempatam chamados com o mesmo impacto e a mesma "
            "quantidade de usuários. Total de chamados e contagens por impacto "
            "são métricas do painel e não entram na prioridade individual."
        )
    proximo = fila[0]

    # escape impede que títulos e outros textos do JSON sejam interpretados
    # como HTML. O cartão apresenta a decisão já calculada em triagem.py.
    titulo = escape(proximo["titulo"])
    tipo = escape(proximo["tipo"])
    impacto = proximo["impacto"]
    setores = sorted(set(proximo["setores_afetados"]))
    abertura_proximo = datetime.strptime(
        f"{proximo['data_abertura']} {proximo['hora_abertura']}", "%Y-%m-%d %H:%M",
    ).strftime("%d/%m/%Y %H:%M")
    st.html(f"""
    <section class="qf-proximo">
        <span class="qf-etiqueta">PRÓXIMO ATENDIMENTO · #{escape(str(proximo['id']))}</span>
        <h2>{titulo}</h2>
        <span class="qf-impacto qf-{impacto}">Impacto {nomes_impacto[impacto].lower()}</span>
        <p>{tipo} · {proximo['usuarios_afetados']} usuários afetados</p>
        <p>{len(setores)} setores distintos: {escape(", ".join(setores))}</p>
        <p>Abertura: {abertura_proximo}</p>
    </section>
    """)
    st.write(proximo["descricao"])

    st.subheader(f"Demais chamados ({len(fila) - 1})")
    # O primeiro já está destacado. A tabela começa na posição 2 para não
    # duplicá-lo e mantém a sequência calculada em triagem.py.
    linhas = []
    for posicao, chamado in enumerate(fila[1:], start=2):
        abertura = datetime.strptime(
            f"{chamado['data_abertura']} {chamado['hora_abertura']}",
            "%Y-%m-%d %H:%M",
        )
        linhas.append({
            "Posição": posicao, "ID": chamado["id"],
            "Título": chamado["titulo"], "Tipo": chamado["tipo"],
            "Impacto": nomes_impacto[chamado["impacto"]],
            "Usuários afetados": chamado["usuarios_afetados"],
            "Quantidade de setores": len(set(chamado["setores_afetados"])),
            "Setores atingidos": ", ".join(sorted(set(chamado["setores_afetados"]))),
            "Abertura": abertura.strftime("%d/%m/%Y %H:%M"),
        })
    if linhas:
        st.dataframe(linhas, hide_index=True)
        st.caption("A coluna Posição indica a ordem oficial de atendimento.")
    else:
        st.info("Este é o único chamado da fila.")

st.caption(
    "Queue Foi? · Triagem educacional. A base é apenas consultada; "
    "esta versão não altera nem conclui chamados."
)
