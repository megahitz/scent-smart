# Scent Smart

Integração BLE local para Home Assistant, testada com o difusor GAS-501F.

Veja a [documentação do projeto](https://github.com/megahitz/scent-smart) para instalação, entidades, testes e limitações. A integração usa conexões sob demanda; após reiniciar o Home Assistant, os estados podem permanecer desconhecidos até uma ação obter resposta válida.

O botão de borrifada exige estado conhecido e programa 1 habilitado. O fluxo de borrifada com o modo desligado não foi validado ponta a ponta no aparelho e uma falha pode impedir o retorno ao estado anterior.
