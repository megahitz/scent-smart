# Notas de protocolo — GAS-501F

[English](protocol.md) | **Português (Brasil)**

Informações aplicáveis ao aparelho testado. Não é uma especificação para todos os difusores BLE.

- Serviço `FFE0`, característica `FFE1`; mensagens são enviadas por escrita sem resposta e recebidas por notificação.
- Estrutura: `55 AA | LEN | CMD | payload | CK | 5A`, com comprimento igual ao tamanho do payload mais um e checksum complementar dos bytes do início ao fim do payload.
- A consulta `0x08` obteve uma lista `0x88` com cinco programas no aparelho testado. Uma alteração de intervalo usa o registro completo e verifica a lista novamente.
- O comando `0x14` grava um programa. Não trate um ACK isolado como confirmação dos valores.
- A operação `0x12` controla o modo de trabalho; a integração exige uma resposta de estado compatível antes de confirmar a ação.
- A operação `0x01` pode substituir o programa pelo ciclo padrão de 60/200 segundos. **Não a use como consulta de estado.**
- Ainda não foi validada uma consulta de estado geral sem alterar o modo. As condições de entrega de notificações e o comportamento de outros modelos podem ser diferentes.

Antes de enviar comandos desconhecidos, registre a configuração atual e avalie as consequências. Falhas e timeouts após uma escrita não provam que o aparelho ignorou o comando.
