<p align="center"><img src="assets/icon.png" width="160" alt="Scent Smart"></p>

# Scent Smart

Integração Bluetooth local para Home Assistant. Testada com um difusor **Scent-B501F (GAS-501F)**. A compatibilidade com outros modelos não foi verificada.

## Instalação

**HACS:** em Integrações → Repositórios personalizados, adicione `https://github.com/megahitz/scent-smart` como integração. Instale **Scent Smart** e reinicie o Home Assistant.

**Manual:** copie `custom_components/scent_smart/` para `/config/custom_components/scent_smart/` e reinicie o Home Assistant.

Depois, em Configurações → Dispositivos e serviços → Adicionar integração, escolha **Scent Smart** e informe o endereço Bluetooth do aparelho. A descoberta automática não está disponível nesta versão.

É necessário um adaptador Bluetooth ou proxy ESPHome com suporte a conexões ativas próximo ao aparelho. O dispositivo pode aceitar apenas uma conexão central de cada vez; encerre outros clientes Bluetooth antes de controlá-lo pelo Home Assistant.

## Entidades

| Entidade | Função |
|---|---|
| Modo de Trabalho | Liga ou desliga o ciclo autônomo. |
| Tempo de Borrifada | Altera o programa 1: 5–200 s, passo 5 s. |
| Tempo de Pausa | Altera o programa 1: 20–300 s, passo 5 s. |
| Borrifar Agora | Tenta iniciar uma borrifada usando o programa 1 existente. Veja as limitações abaixo. |
| Estado | Última resposta de estado confirmada e atributos de diagnóstico. |

Os demais controles legados de programa, ventilador, trava, iluminação e seleção de programa não estão disponíveis nesta versão. A janela horária já existente no aparelho é preservada, mas não pode ser editada aqui.

## Funcionamento e limitações

- A integração conecta apenas durante ações explícitas; **não há consulta no início nem polling**. A conexão ou um comando pode produzir bipes.
- Depois de reiniciar o Home Assistant, o estado e os intervalos podem ficar como **desconhecidos** até uma ação retornar dados válidos. Valores anteriores podem ficar desatualizados se o aparelho for alterado por outro controle.
- Alterar um intervalo consulta o programa existente, preserva seus outros campos e verifica os cinco programas após a escrita. Uma confirmação de recebimento por si só não é tratada como prova de alteração.
- Se um comando expirar ou a conexão falhar após o envio, o resultado é **desconhecido**: o aparelho pode ter executado o comando. Verifique antes de repetir.
- O botão de borrifada exige estado conhecido e programa 1 habilitado. Com o modo ligado, reaplica o programa; essa ação foi testada em um GAS-501F. Com o modo desligado, tenta ligá-lo temporariamente e desligá-lo após o tempo configurado. Esse fluxo completo não foi validado no aparelho; uma interrupção de energia ou falha de conexão pode impedir a restauração. Não use onde permanecer ligado seja problemático.
- O aparelho mantém sua própria programação horária: remover uma restrição no Home Assistant não altera essa janela. Não há garantia de operação contínua durante o minuto final de uma janela encerrada em 23:59.

## Testes offline

Na raiz do repositório, execute:

```bash
python3 -m unittest discover -s tests -v
```

Os testes simulam Home Assistant e Bluetooth; não substituem testes no aparelho. Os detalhes de protocolo validados estão em [docs/protocolo.md](docs/protocolo.md).
