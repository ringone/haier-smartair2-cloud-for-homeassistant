# Nomes das entidades em português de Portugal

Esta revisão altera apenas os rótulos de entidades e opções em `translations/pt.json`. É trabalho de desenvolvimento posterior à versão publicada 0.3.0: abrir ou integrar o PR não publica uma atualização. A revisão abrange os 45 textos da secção `entity`; 24 foram alterados e os restantes mantidos por já serem adequados. Os formulários de configuração, inglês e polaco não foram alterados.

## Critérios de linguagem e significado

- Usar nomes curtos, em português de Portugal, que distingam o que é medido ou controlado. Um permutador não é o ar da divisão: não substituir o seu sensor por «Temperatura interior».
- Preferir «permutador» a «bateria» na interface doméstica. «Bateria» também é um termo técnico de AVAC; não se trata de classificar a palavra como português incorreto.
- Usar «comando à distância», «bloqueio», «autolimpeza», «silencioso» e «modo noturno» em vez de traduções literais pouco naturais no contexto.
- Manter «Health» como designação da função: não prometer ionização, purificação, esterilização ou benefícios para a saúde sem validação do equipamento. As posições Health são posições do seletor, não a função do interruptor.
- Não atribuir uma localização ou função física mais precisa do que a evidência permite. Os rótulos de entrada/saída da unidade exterior não afirmam que se mede ar, refrigerante ou a descarga do compressor. A localização exata da sonda de saída permanece por confirmar.
- Identificar a válvula de expansão como «valor bruto», sem inventar percentagem ou posição de abertura. «Potência elétrica» continua a ser um valor reportado; 0 W não demonstra ausência de consumo.
- As novas palavras não alteram pedidos de controlo, leituras, unidades, posições ou funções. RP-002/RP-003 e as limitações de hardware continuam por resolver.

## Identidade, nomes personalizados e atualização

O RF-008 protege a identidade e os nomes personalizados, não congela os rótulos padrão. A sua redação foi clarificada nesse sentido.

- Manter domínio, `unique_id`, chaves de tradução, sufixos e opções internas. Não regenerar `entity_id` já registados nem apagar/recriar entidades ou a entrada de configuração para mudar um nome.
- Preservar o nome personalizado da entidade e `name_by_user` do dispositivo. Se alguém escolheu explicitamente um nome antigo, esta revisão não o deve substituir.
- Novas instalações podem receber identificadores sugeridos a partir dos novos nomes. Isso é diferente de mudar identificadores numa instalação existente.
- Os nomes traduzidos dependem do idioma do servidor/registo do Home Assistant; não basta mudar o idioma do utilizador no frontend para renomear entidades existentes. Esta revisão não força a mudança de idioma das entidades.
- Depois de instalar uma futura versão que inclua a revisão, reiniciar o Home Assistant para carregar o código/traduções substituídos. Se houver um nome personalizado que se queira mudar, usar o campo de nome na interface sem alterar o identificador da entidade. Não editar `.storage` manualmente.

O harness `tests/ha_entity_names_compat.py` usa o carregador real de traduções, plataformas e Stores do Home Assistant, com coordenadores V2/V3 simulados: verifica 31 identidades e os 45 textos pt, opções internas, nomes padrão anteriores e nomes personalizados. Guarda e recarrega os registos numa nova instância Home Assistant dentro do mesmo processo. Os registos anteriores são fixtures sintéticas, não uma execução da integração antiga. Não há reinício de processo, hot-reload de traduções, frontend, recorder em produção ou AC físico. Os testes não provam novos modelos de hardware.

## Rótulos alterados

| Chave interna preservada | Antes | Depois |
|---|---|---|
| `sensor.indoor_coil_temperature.name` | Temperatura da bateria interior | Temperatura do permutador interior |
| `sensor.outdoor_coil_temperature.name` | Temperatura da bateria exterior | Temperatura do permutador exterior |
| `sensor.outdoor_in_temperature.name` | Temperatura de admissão exterior | Temperatura de entrada da unidade exterior |
| `sensor.outdoor_out_temperature.name` | Temperatura de descarga exterior | Temperatura de saída da unidade exterior |
| `sensor.compressor_current.name` | Corrente do compressor | Corrente elétrica do compressor |
| `sensor.power.name` | Potência | Potência elétrica |
| `sensor.expansion_valve.name` | Válvula de expansão | Válvula de expansão (valor bruto) |
| `sensor.operation_source.state.remote` | Comando | Comando à distância |
| `sensor.operation_source.state.panel` | Painel | Painel do aparelho |
| `binary_sensor.indoor_fan.name` | Ventoinha interior em funcionamento | Ventilador interior em funcionamento |
| `binary_sensor.outdoor_fan.name` | Ventoinha exterior em funcionamento | Ventilador exterior em funcionamento |
| `binary_sensor.four_way_valve.name` | Válvula de 4 vias | Válvula de quatro vias |
| `switch.health.name` | Saúde | Função Health |
| `switch.display.name` | Luz do painel | Iluminação do painel |
| `switch.self_clean.name` | Limpeza automática | Autolimpeza |
| `switch.lock_remote.name` | Travar o comando | Bloqueio do comando à distância |
| `select.vertical_swing.name` | Direção vertical | Direção vertical do fluxo de ar |
| `select.vertical_swing.state.auto` | Oscilar | Oscilação automática |
| `select.vertical_swing.state.health_up` | Fluxo saudável para cima | Posição Health para cima |
| `select.vertical_swing.state.health_down` | Fluxo saudável para baixo | Posição Health para baixo |
| `climate.ac.state_attributes.fan_mode.state.quiet` | Silêncio | Silencioso |
| `climate.ac.state_attributes.preset_mode.state.none` | Nenhum | Sem predefinição |
| `climate.ac.state_attributes.preset_mode.state.boost` | Potência | Turbo |
| `climate.ac.state_attributes.preset_mode.state.sleep` | Sono | Modo noturno |

## Referências

Consultadas em 2026-11-17. As fontes dos fabricantes servem para terminologia, não para garantir compatibilidade ou funcionalidades no AS35 documentado.

- [Home Assistant: nomes e idioma das entidades](https://contributors.home-assistant.io/core/entities/naming/).
- [Home Assistant: registo, identidade e alterações do utilizador](https://contributors.home-assistant.io/core/entities/registry/).
- [Home Assistant: traduções das entidades](https://contributors.home-assistant.io/core/quality-scale/entity-translations/).
- [Haier Portugal: uso de «autolimpeza»](https://haier-ac.pt/pearl-premium-haier/).
- [Daikin Portugal: uso de «permutador de calor interior»](https://www.daikin.pt/pt_pt/particular/inspiration/articles/the-advantages-of-renewable-energy.html).
- [Protocolo AS35 e limites dos sensores](protocol-as35.md).
