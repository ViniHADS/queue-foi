# Queue Foi?

Cada chamado no seu lugar. Projeto educacional do Checkpoint 6 de Pensamento Computacional com Python, desenvolvido para triagem de chamados de TI.

## Integrantes

- Gabriel Lesser Donato
- Jorge Meert
- Vinicius Araujo

## Solução

Aplicação em Python com Streamlit e um único arquivo CSS, sem API externa ou banco de dados. Lê `chamados.json` e oferece dois menus:

- **Painel de métricas:** total de chamados, chamados por impacto, gráfico por tipo, média do tempo estimado de resolução e total de setores distintos atingidos.
- **Fila de atendimento:** próximo chamado destacado e demais chamados em ordem, com posição, ID, título, tipo, impacto, usuários afetados, quantidade e nomes dos setores e abertura.

A base é apenas consultada. Esta versão não cadastra, altera ou conclui chamados. Os dados e textos usam UTF-8 e a interface está em português brasileiro.

## Estratégia de triagem

Os critérios são comparados nesta ordem:

1. Maior impacto: alto, médio e baixo.
2. Maior quantidade de usuários afetados.
3. Maior quantidade de setores distintos atingidos.
4. Data e hora de abertura mais antigas.
5. Menor ID, para tornar o resultado determinístico em caso de empate completo.

O impacto representa a gravidade do problema; a quantidade de usuários representa seu alcance. Os setores só decidem entre chamados com impacto e quantidade de usuários iguais; a antiguidade é o critério seguinte. Por exemplo, entre dois chamados de impacto alto afetando 10 e 30 pessoas, o de 30 vem primeiro, mesmo que seja mais recente.

Se dois chamados de impacto alto afetam 20 usuários cada, aquele que atinge três setores vem antes do que atinge apenas um, mesmo sendo mais recente. Repetir um setor na lista não aumenta a prioridade. A caixa de prioridades na tela da fila explica os cinco critérios.

O total de chamados e as contagens por impacto são indicadores gerais; não alteram a prioridade individual. O total de setores distintos considera cada nome de setor uma vez em toda a base, mesmo que apareça em vários chamados. Não calculamos pessoas únicas, pois não há identificação de todos os usuários afetados para eliminar sobreposições.

Esta regra não garante que um chamado de impacto baixo ultrapasse um de impacto alto após muito tempo de espera. É uma decisão simplificada para a atividade. Não usamos o tempo estimado como prioridade, pois uma resolução rápida não implica maior urgência.

## Como a solução funciona

O fluxo do programa é: **leitura do JSON → validação → ordenação e cálculo das métricas → apresentação no Streamlit**.

### Leitura e estruturas de dados

A função `carregar_chamados()`, em `dados.py`, abre o arquivo com `encoding="utf-8"` e usa `json.load()` para converter seu conteúdo em estruturas do Python. A base vira uma lista, cada chamado vira um dicionário e os campos de setores e recursos permanecem como listas. O arquivo original não é modificado.

Antes de devolver a base, essa função chama `validar_chamados()`. Se houver erro, a interface apresenta a mensagem e interrompe os cálculos, evitando mostrar uma fila incompleta.

### Funções e responsabilidades

| Função | Responsabilidade |
|---|---|
| `carregar_chamados()` | Ler o JSON, tratar falhas de leitura e devolver a base validada. |
| `validar_chamados()` | Conferir a estrutura, os campos obrigatórios, os tipos e os valores. |
| `chave_prioridade()` | Representar os cinco critérios de comparação de cada chamado. |
| `ordenar_chamados()` | Criar uma nova lista na ordem de atendimento. |
| `calcular_metricas()` | Percorrer os chamados e devolver as contagens, a média e o total de setores distintos. |

Essa separação permite testar a lógica sem depender da interface. O arquivo `streamlit_app.py` chama essas funções e apresenta seus resultados nos dois menus.

### Como a ordenação é feita

A função `ordenar_chamados()` usa `sorted(chamados, key=chave_prioridade)`. O resultado é uma nova lista; a ordem da lista original é preservada.

A chave de cada chamado é uma tupla com impacto, usuários, setores distintos, abertura e ID. O Python compara esses valores da esquerda para a direita, consultando o próximo somente em caso de empate. Alto, médio e baixo recebem os valores 0, 1 e 2. Como `sorted` ordena de forma crescente, as quantidades de usuários e setores entram com sinal negativo para que as maiores apareçam primeiro. A abertura é convertida em `datetime`, permitindo comparar data e horário corretamente.

Usamos `set` para contar setores sem repetições. Isso não altera a lista de setores do JSON. A estratégia usa comparação por critérios, sem somar pesos ou pontuações.

### Como as métricas são calculadas

| Métrica | Cálculo |
|---|---|
| Total de chamados | `len(chamados)`. |
| Chamados por impacto | Um dicionário começa com zero para alto, médio e baixo; cada registro incrementa sua categoria. |
| Chamados por tipo | Um dicionário acumula uma unidade para cada ocorrência de um tipo. |
| Resolução estimada média | Soma de `tempo_estimado_min` dividida pelo total de chamados. |
| Setores distintos atingidos | União dos nomes de setores em um `set`, seguida da contagem com `len`. |

Se a base estiver vazia, a função devolve média zero para evitar divisão por zero, e a interface mostra uma mensagem em vez dos indicadores. O Streamlit desenha o gráfico com as contagens calculadas pelo programa; ele não define a regra de triagem.

## Organização

- `streamlit_app.py`: interface e navegação.
- `dados.py`: leitura do JSON em UTF-8 e validação antes dos cálculos.
- `metricas.py`: cálculos com listas e dicionários.
- `triagem.py`: comparação e ordenação dos chamados.
- `assets/estilos.css`: estilos das classes próprias.
- `.streamlit/config.toml`: tema dos componentes nativos.
- `chamados.json`: base fornecida para a atividade, preservada.
- `tests/test_projeto.py`: testes com unittest e Streamlit AppTest.

O JSON usa `recursos_necessarios`, diferente de `recurso_necessario` no enunciado. Esse campo não participa da nossa regra de prioridade.

## Validação dos dados

A aplicação confere a leitura do arquivo em UTF-8, a sintaxe JSON, a lista principal, cada registro como dicionário e todos os campos obrigatórios da base. Também verifica:

- ID inteiro e único; valores booleanos não são aceitos como inteiros.
- Textos obrigatórios não vazios.
- Impacto restrito a `alto`, `medio` e `baixo`.
- Data válida em `AAAA-MM-DD` e horário em `HH:MM`.
- Usuários afetados e tempo estimado como inteiros não negativos.
- Setores e recursos como listas não vazias de textos não vazios.

O primeiro erro interrompe os cálculos com uma mensagem que identifica o registro e o campo. Nenhum registro é corrigido ou descartado silenciosamente. Uma lista vazia é válida e recebe uma mensagem própria; uma base unitária mostra apenas o próximo chamado.

A contagem de setores usa os nomes exatamente como estão no JSON: grafias e capitalizações diferentes são consideradas setores diferentes. A base é estática e não existe atualização de status ou autenticação. Ordenar visualmente a tabela não muda a posição oficial calculada, indicada pela coluna Posição.

## Execução

Requer Python 3.10 ou superior. No terminal, dentro da pasta do projeto:

```bash
python -m venv .venv
```

Ative o ambiente no macOS/Linux:

```bash
source .venv/bin/activate
```

Ou no PowerShell do Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Instale e execute:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Abra o endereço local mostrado no terminal. Encerre com `Ctrl+C`.

## Conferência da base fornecida

O painel deve mostrar 30 chamados: 12 de impacto alto, 8 médio e 10 baixo, 21 setores distintos e média estimada de 43 minutos. A fila deve conter os 30 IDs sem duplicação, somando o destaque e a tabela. O programa informa quando o JSON está ausente, inválido ou vazio.

## Testes

Com a `.venv` ativada, execute na raiz do projeto:

```bash
python -m unittest discover -s tests -v
```

A suíte contém 12 testes, incluindo subcasos para critérios de ordenação, setores repetidos, preservação da base, métricas, dados inválidos e os dois menus. Também cobre lista vazia e base com um chamado. O AppTest verifica a execução dos componentes; não substitui a inspeção visual no navegador.
