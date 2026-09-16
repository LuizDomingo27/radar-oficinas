"""app_recebimento — área "Recebimento" do Radar de Oficinas (peças recebidas).

Acompanhamento das peças cortadas que voltam das oficinas (peças, minutos,
matéria-prima, data de recebimento), com dados ao vivo na tabela
``Recebimento_Radar`` do Neon.

Declara o contrato da área e delega as telas e as agregações ao núcleo
compartilhado ``app_common.movimentacao``, o mesmo usado por ``app_envios``.
"""
