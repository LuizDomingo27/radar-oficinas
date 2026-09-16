"""app_envios — área "Envios" do Radar de Oficinas.

Acompanhamento dos envios de peças às oficinas (peças, minutos, matéria-prima,
data de envio), com dados ao vivo na tabela ``Envios_Radar`` do Neon.

Declara o contrato da área (colunas da planilha, tabela, vocabulário) e delega
as telas e as agregações ao núcleo compartilhado ``app_common.movimentacao``,
que é o mesmo usado por ``app_recebimento``.
"""
