<!-- BEGIN:Python-agent-rules -->

# This is NOT the python you know

This block is written and re-added by Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:python-agent-rules -->

## Documentação obrigatória do fluxo do produto
- Siga as boas praticas de desenvolvimento de software
- Cada camada com a sua responsabilidade
- teste tudo que fizer de implementação
- todo codigo deve ter tratamento de erros e exceçoes
- app nunca pode quebrar por falta de testes e tratamento de excecoes
- sempre veja o aperformance de cada recurso
- nao faca commit sem permicao
- nuca deixe codigo obsoleto ou orfão.
- sempre use o ambiente local para realizar os teste, quando for subir o APP.

Toda implementação que altere ou crie comportamento visível do aplicativo deve atualizar, na mesma mudança, `docs/guia-fluxo-operacional.html`.

- Explique o propósito em linguagem de negócio e descreva o fluxo completo, do início ao resultado.
- Registre os papéis envolvidos, a tela usada, os dados de entrada, as decisões, as exceções e o que o sistema salva.
- Atualize a simulação end-to-end quando a implementação afetar autenticação, Ordem Mestre, conferências, distribuição, entrega ao PUP, conclusão ou acompanhamento.
- Confirme que nomes de telas, botões, status, permissões e resultados no guia continuam iguais ao comportamento do app.

Uma mudança de produto só está completa quando código, testes e explicação operacional estão atualizados em conjunto.
