# ADR-001 — Eliminar a dependência Haier cloud

## Estado e origem

**Objetivo aceite pelo utilizador:** funcionamento exclusivamente local, sem login ou consultas Haier. Esta decisão não aprova automaticamente todas as propostas do backlog nem declara compatibilidade física.

Base analisada: `5b77363a05225311fb85ef89eb16136b26440acd`. Implementação preparada na branch `feat/local-only`.

## Contexto

O controlo de aparelhos mapeados já podia ser feito por TCP na LAN, mas o arranque obtinha sempre dispositivos, nomes e typeIdentifier da conta Haier. Falhas de autenticação/API podiam impedir o uso local. Aparelhos sem mapa ou com falha de ligação inicial recorriam ao transporte MQTT cloud.

A auditoria identificou também falta de validação TLS, ciclo de EOF, cache cloud obsoleta, erro de API ocultado e limpeza incompleta de recursos. Os resultados estão na [auditoria inicial](../auditoria-inicial.md).

## Alternativas consideradas

- **Corrigir e manter cloud opcional:** manteria credenciais, API privada e superfície de rede externa; não corresponde à opção local-only escolhida.
- **Manter descoberta cloud apenas no arranque:** continuaria a exigir Haier/Internet e não cumpriria RF-001.
- **Guardar metadata cloud uma vez:** exigiria uma forma explícita de obter/guardar esse perfil. A configuração antiga não persistia o typeIdentifier; não se deve inventar essa informação na migração.
- **Só local com mapa manual:** corresponde à decisão aprovada e elimina o transporte cloud ativo.

## Decisão aplicada

- Remover o transporte cloud e os seus imports/constantes exclusivos.
- Configurar dispositivos através de MAC:IPv4, sem conta/região/client ID.
- Migrar a entrada em lugar e preservar domínio, identidade MAC e chave do histórico.
- Preservar transporte LAN, codecs, bytes de controlo e conversões existentes.
- Selecionar atualmente o codec por dimensões de estado conhecidas, com rejeição das dimensões não reconhecidas e avisos de que a regra é heurística.
- Limpar recursos locais em falhas/cancelamentos, sem fallback cloud.

## Consequências e riscos aceites apenas como limitações documentadas

- Não há descoberta automática nem suporte a módulos encrypted/cloud-only.
- O utilizador precisa do MAC/IP e de acesso plaintext TCP 56800.
- Uma falha no arranque de um dispositivo pode impedir o setup da respetiva entrada; isolamento completo por aparelho não é garantido.
- Dimensão/checksum não identificam de forma universal o layout semântico. Perfil explícito por dispositivo é RP-001, ainda pendente.
- A combinação documentada é AS35TADHRA-TH + MK-QTWIFI-04(B); a validade noutro hardware/firmware é desconhecida. A versão local-only não foi testada num aparelho físico nesta sessão.
- Os defeitos locais de comandos concorrentes e hvac_mode combinado permanecem RP-002/RP-003. A sua presença deve ser indicada no PR, não ocultada por checks verdes.
- O transporte LAN continua plaintext; retirar a cloud não cria cifragem/autenticação local.

## Verificação e rastreabilidade

RF-001–RF-016 cobrem o objetivo arquitetural, configuração/migração e ciclo de vida. Os restantes requisitos tratam controlos, histórico, qualidade e propostas; consultar a [matriz](../matriz-requisitos.csv).

Testes atuais demonstram a ausência do caminho cloud nos fluxos exercitados, invariantes de migração e tráfego em loopback. Os testes históricos demonstram os achados no commit base, sem restaurar cloud no pacote atual. Validação física e aprovação para release continuam separadas.
