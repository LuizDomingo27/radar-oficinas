"""
app_common/movimentacao — núcleo compartilhado das áreas de MOVIMENTAÇÃO DE PEÇAS.

"Envios" (peças que saem para as oficinas) e "Recebimento" (peças que voltam
delas) são a MESMA tela sobre contratos de dados diferentes: mesmos indicadores
(peças, minutos, ordens, oficinas), mesmas granularidades, mesmos gráficos e a
mesma consulta paginada por ordem. O que muda entre elas é o vocabulário, a
coluna de data e o conjunto de colunas persistidas.

Por isso a mecânica vive aqui, uma vez só, e cada área declara apenas o seu
``AreaMovimentacao`` em ``core/config.py``. Sem isso, um ajuste de tooltip ou de
paleta viraria duas edições espelhadas — e elas divergiriam na primeira pressa.

Camadas dentro do pacote (mesma direção de sempre: ui → services → core):
    area.py       → core:     contrato de colunas, vocabulário, descritor da área
    analytics.py  → services: agregações (sem Streamlit)
    data_loader.py→ services: leitura do Neon
    ui/           → ui:       cards, gráficos, filtros, CSS e orquestração de tela
"""
