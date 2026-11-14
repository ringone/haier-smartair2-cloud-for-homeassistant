# Requisitos — Haier SmartAir2 Local

**Especificação:** v0.2; incremento Marketplace/2026.11 autorizado para implementação, restantes propostas sujeitas a revisão.
**Implementação de referência:** proposta 0.3.0 sem release publicada; base Git `5b77363a05225311fb85ef89eb16136b26440acd` mais as alterações da branch `feat/local-only` e o incremento `chore/marketplace-ha-2026.11`, derivado de `2b4412d8e9ccc905e034cec677b3bcbdff9f5c26`. Não confundir a árvore modificada com o conteúdo original desses commits.
**Objetivo:** transformar as decisões do fork em comportamentos verificáveis, com rastreabilidade e lacunas explícitas. Este documento não altera o funcionamento do software nem aprova automaticamente funcionalidades novas.

## 1. Âmbito e decisões de origem

- **DEC-01 — Exclusivamente local:** decisão explícita do utilizador; eliminar dependência da Haier cloud, incluindo configuração e arranque.
- **DEC-02 — Preservação local:** manter transporte/protocolo existentes, entidades, identidade MAC e histórico; migração sem eliminar a entrada.
- **DEC-03 — Compatibilidade desconhecida:** tornar explícito que não sabemos a validade noutros aparelhos, módulos Wi-Fi ou firmware. A combinação documentada é AS35TADHRA-TH + MK-QTWIFI-04(B), baseada em capturas e calibração anteriores, não num teste físico desta versão nesta sessão.
- **DEC-04 — Marketplace/2026.11:** implementação autorizada pelo utilizador numa branch derivada da local-only; adotar API native, mínimo 2026.11.0 e verificação de distribuição, sem merge/release nem novo suporte físico.
- **Implementação:** requisito extraído do código atual, não uma nova promessa de compatibilidade.
- **Critério derivado / Proposta:** recomendação de qualidade ou evolução que requer aprovação antes de aumentar o escopo.

Inclui configuração/opções, migração, TCP local, seleção de codec, ciclo de vida, controlos implementados, telemetria, alarmes, histórico, privacidade, testes e entrega. Exclui cloud, hOn, módulos encrypted/cloud-only, descoberta automática, garantia universal V2/V3, precisão metrológica e alterações de firmware do aparelho. IPv6 e hostnames estão fora do formato MAC:IPv4 atual.

### Estado, prioridade e evidência não são a mesma coisa

- **Implementado:** há código/documentação correspondente; **não significa** cobertura integral ou validação física.
- **Parcial:** há uma lacuna conhecida de cumprimento/declaração.
- **Pendente:** não foi implementado; não se deve anunciar como disponível.
- **P0:** obrigatório antes de considerar conforme uma release que inclua o requisito aprovado; **P1:** importante; **P2:** melhoria planeada. A prioridade de uma proposta não a torna aprovada.
- **E01–E36:** evidência automatizada concretamente identificada no apêndice. Uma evidência associada pode cobrir apenas parte do critério; consultar sempre a lacuna descrita.
- **Inspeção:** leitura de código/documentação ou comparação de artefactos, não um ensaio operacional.
- **Físico pendente:** sem ar condicionado real nesta sessão. Testes com capturas/simulador não estabelecem compatibilidade noutro hardware.

**Inventário:** 41 requisitos: 34 implementado, 3 parcial, 4 pendente. Estes totais **não são uma taxa de conformidade nem de cobertura**.

## 2. Requisitos funcionais

### RF-001 — Operação sem cloud
- **Prioridade:** P0.
- **Origem:** DEC-01.
- **Estado da implementação:** Implementado.
- **Requisito:** A integração deverá configurar, migrar, arrancar e controlar por LAN sem autenticação Haier, HTTP, MQTT ou fallback cloud.
- **Critérios de aceitação:**
  - Com a Internet e DNS externo bloqueados, configurar/migrar uma entrada e receber estado do simulador local deverá funcionar.
  - A integração não deverá solicitar e-mail, palavra-passe, região ou client ID, nem importar o transporte cloud removido.
  - Uma falha LAN deverá resultar em erro/repetição local, nunca numa tentativa cloud.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/config_flow.py`, `custom_components/haier_smartair2/const.py`.
- **Evidência existente:** E01, E13, E21.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-002 — Dispositivos explicitamente mapeados
- **Prioridade:** P0.
- **Origem:** DEC-01 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** A lista de dispositivos deverá resultar exclusivamente do mapa local efetivo MAC:IPv4.
- **Critérios de aceitação:**
  - Cada par válido deverá criar um cliente local e um coordenador com o MAC normalizado correspondente.
  - Dispositivos não presentes no mapa não deverão ser descobertos através da conta Haier.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** E05, E21.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-003 — Validação integral do mapa
- **Prioridade:** P0.
- **Origem:** Implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** A configuração e as opções deverão aceitar apenas mapas não vazios de MACs hexadecimais e IPv4 literais válidos, rejeitando a entrada integral se algum par for inválido.
- **Critérios de aceitação:**
  - Aceitar MAC com 12 dígitos sem separadores ou seis grupos de dois dígitos separados por dois-pontos; normalizar para maiúsculas sem separadores.
  - Rejeitar hostname, IPv6, MAC inválido, par vazio, vírgula final, MAC/IP duplicado, 0.0.0.0, multicast e 255.255.255.255.
  - Mostrar invalid_local_map junto do campo; não guardar parcialmente os pares válidos nem executar DNS.
- **Código/documentação:** `custom_components/haier_smartair2/local_map.py`, `custom_components/haier_smartair2/config_flow.py`.
- **Evidência existente:** E01, E02.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-004 — Alteração de opções sem recriar a entrada
- **Prioridade:** P1.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** O utilizador deverá poder alterar o mapa local nas opções, provocando recarregamento sem apagar a entrada.
- **Critérios de aceitação:**
  - Guardar um mapa válido deverá acionar o listener de reload da mesma entrada.
  - Alterar apenas o IP de um MAC não deverá alterar o entry_id nem os unique_id associados a esse MAC.
- **Código/documentação:** `custom_components/haier_smartair2/config_flow.py`, `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** E01, E03, E05.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Falta um teste de ponta a ponta do callback de opções → reload → preservação do registo. A existência do listener foi inspecionada.

### RF-005 — Recuperação de entrada sem mapa
- **Prioridade:** P0.
- **Origem:** DEC-01 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Uma entrada migrada sem mapa utilizável deverá falhar de forma explícita e permitir recuperação pelas opções.
- **Critérios de aceitação:**
  - Não abrir clientes nem declarar setup bem-sucedido com zero dispositivos quando o mapa é vazio ou inválido.
  - Indicar a necessidade de configurar MAC:IPv4; manter a entrada e o seu histórico para posterior correção.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/config_flow.py`.
- **Evidência existente:** E06, E01.
- **Verificação:** Parcial.
- **Lacuna/limitação:** O fluxo de opções e a falha acionável estão testados separadamente; falta demonstrar a recuperação completa pela interface real.

### RF-006 — Migração V1 → V2 em lugar
- **Prioridade:** P0.
- **Origem:** DEC-02.
- **Estado da implementação:** Implementado.
- **Requisito:** A migração deverá manter a identidade da entrada e remover os campos de ligação cloud dos dados/opções ativos.
- **Critérios de aceitação:**
  - Preservar entry_id, unique_id legado da entrada e identificadores MAC das entidades; não apagar a entrada.
  - Gravar version=2 e remover username, password, region e client_id de data/options.
  - Não tentar migrar uma versão futura desconhecida; não consultar rede.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** E03, E21.
- **Verificação:** Parcial.
- **Lacuna/limitação:** E03/E21 cobrem a migração normal. Falta um teste dedicado de rejeição de versão futura. O unique_id/título legado pode continuar a conter o e-mail antigo como metadado; não é utilizado para autenticação.

### RF-007 — Precedência exata das opções na migração
- **Prioridade:** P0.
- **Origem:** DEC-02 + regressão encontrada.
- **Estado da implementação:** Implementado.
- **Requisito:** A migração deverá preservar a semântica original de substituição integral do campo local_ips por options, sem unir mapas antigos e novos.
- **Critérios de aceitação:**
  - Se options contiver local_ips, migrar esse campo inteiro; usar data apenas quando a opção não existir.
  - Não ressuscitar dispositivos retirados nas opções; uma opção vazia deverá continuar vazia.
  - Preservar texto ativo inválido para correção nas opções, sem recuperar silenciosamente um mapa antigo.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** E03, E04.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-008 — Identidade e nomes dos dispositivos
- **Prioridade:** P0.
- **Origem:** DEC-02.
- **Estado da implementação:** Implementado.
- **Requisito:** O domínio e unique_id das entidades deverão continuar baseados no MAC normalizado, reutilizando o dispositivo já existente no registo.
- **Critérios de aceitação:**
  - Manter o domínio haier_smartair2 e, para climate, haier_smartair2_<MAC>.
  - Os restantes unique_id deverão manter os sufixos existentes de cada plataforma; mudar o IP não deverá criar nova identidade.
  - Reutilizar o nome existente quando disponível, sem apagar name_by_user; usar um nome local estável quando não existir registo.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/climate.py`, `custom_components/haier_smartair2/sensor.py`, `custom_components/haier_smartair2/binary_sensor.py`, `custom_components/haier_smartair2/switch.py`, `custom_components/haier_smartair2/select.py`.
- **Evidência existente:** E05, E11, E20, E21.
- **Verificação:** Parcial.
- **Lacuna/limitação:** E21 confirma o unique_id climate e consulta ao registo, mas não testa um reinício completo com todas as entidades previamente registadas. Não exige mudar nomes nem entity_id escolhidos pelo utilizador.

### RF-009 — Seleção limitada de codec
- **Prioridade:** P0.
- **Origem:** DEC-03 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** A seleção automática atual deverá ser descrita e tratada como heurística dos formatos conhecidos, não como identificação inequívoca do equipamento.
- **Critérios de aceitação:**
  - Em estado lógico já validado 6D01, os formatos atualmente reconhecidos são bloco de 24 bytes → codec V2 e 32 bytes → codec V3.
  - Rejeitar tipo/subcomando ou comprimento não reconhecido antes de iniciar controlo pelo coordenador.
  - Não concluir que um frame de dimensão reconhecida tem necessariamente um layout semântico compatível; ver RP-001.
- **Código/documentação:** `custom_components/haier_smartair2/local_setup.py`, `custom_components/haier_smartair2/__init__.py`, `docs/compatibility.md`.
- **Evidência existente:** E05, E08.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Testes usam formatos conhecidos/sintéticos; a exclusividade das dimensões entre modelos não foi demonstrada. Falta teste direto de subcomando/tipo incorreto na função de seleção.

### RF-010 — Compatibilidade e incerteza visíveis
- **Prioridade:** P0.
- **Origem:** DEC-03.
- **Estado da implementação:** Implementado.
- **Requisito:** O fork deverá declarar que a validade noutros aparelhos, módulos Wi-Fi e firmware é desconhecida, distinguindo evidência histórica de testes físicos atuais.
- **Critérios de aceitação:**
  - Exibir aviso no README e nos ecrãs de configuração/opções en, pt e pl.
  - Identificar AS35TADHRA-TH + MK-QTWIFI-04(B) como a combinação documentada, sem afirmar teste físico da versão local nesta sessão.
  - Não anunciar o V2 LAN como hardware validado nem converter relatos cloud/PRs upstream em compatibilidade local confirmada.
- **Código/documentação:** `README.md`, `docs/compatibility.md`, `docs/protocol-as35.md`, `custom_components/haier_smartair2/translations/en.json`, `custom_components/haier_smartair2/translations/pt.json`, `custom_components/haier_smartair2/translations/pl.json`.
- **Evidência existente:** E12.
- **Verificação:** Inspeção documental + cobertura automática parcial.
- **Lacuna/limitação:** Os textos foram inspecionados; E12 verifica estrutura/local-only, não todas as afirmações de compatibilidade. Acrescentar um teste de presença dos avisos para prevenir remoção acidental.

### RF-011 — Transporte LAN e envelope existentes
- **Prioridade:** P0.
- **Origem:** DEC-02.
- **Estado da implementação:** Implementado.
- **Requisito:** A comunicação deverá usar o transporte TCP plaintext e envelope LAN já implementados, sem alterar bytes de controlo para acomodar aparelhos não verificados.
- **Critérios de aceitação:**
  - Usar o IPv4 configurado e TCP 56800 em produção; manter o envelope de 80 bytes, marcadores, MAC, sequência e comprimento.
  - Continuar a emitir os polls normal e estendido e os comandos existentes.
  - Qualquer alteração futura de framing/codec deverá ter captura/evidência e regressão correspondente, não apenas uma hipótese de compatibilidade.
- **Código/documentação:** `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/codec.py`.
- **Evidência existente:** E19, E21.
- **Verificação:** Parcial.
- **Lacuna/limitação:** A sessão confirmou estes ficheiros byte a byte iguais à base 5b77363. O smoke usa porta loopback efémera por patch de teste; não valida fisicamente TCP 56800 no aparelho.

### RF-012 — Arranque com prazo limitado
- **Prioridade:** P0.
- **Origem:** Implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** O arranque de cada dispositivo deverá aguardar um primeiro estado válido com prazo limitado, sem uma espera infinita.
- **Critérios de aceitação:**
  - Manter timeout de ligação de 10 s e prazo de 15 s por dispositivo para a sequência inicial definida no setup.
  - Aceitar um primeiro estado que chegue com atraso dentro do prazo; falhar e limpar recursos quando excedido.
  - Os limites são por dispositivo/operação, não uma promessa de duração máxima global do arranque Home Assistant.
  - Vincular o coordenador ao ConfigEntry real durante o primeiro refresh, respeitando o ciclo de vida Home Assistant.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/coordinator.py`.
- **Evidência existente:** E07, E08, E10.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Os testes aceleram o prazo; falta ensaio temporal real de timeout e de vários dispositivos sem resposta.

### RF-013 — Integridade dos frames recebidos
- **Prioridade:** P0.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Só frames LAN/EPP estruturalmente válidos deverão atualizar o estado corrente.
- **Critérios de aceitação:**
  - Verificar marcador LAN, cabeçalho/tamanho EPP, checksum e CRC quando sinalizado, mantendo o tratamento existente de FF/55.
  - Ignorar subcomandos não tratados para efeitos de estado; frames inválidos não deverão renovar o prazo de frescura.
  - Permitir retenção local de frames inválidos para diagnóstico, sem os exportar integralmente.
- **Código/documentação:** `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/codec.py`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E14, E16, E17, E19.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Há captures reais, formas inválidas e retenção testadas; falta matriz dedicada de corrupção de cada campo, checksum/CRC e timeout sob fluxo contínuo inválido.

### RF-014 — Frescura e indisponibilidade
- **Prioridade:** P0.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** A integração não deverá usar um estado local expirado como base para novos comandos e deverá sinalizar a perda de ligação.
- **Critérios de aceitação:**
  - Frames normais/estendidos deixam de ser considerados recentes quando atingem o limite de 40 s.
  - Na desconexão, limpar frames e alarmes e notificar os consumidores.
  - Sem estado recente, recusar escrita em vez de fabricar um bloco de controlo; apresentar indisponibilidade conforme a plataforma.
- **Código/documentação:** `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/coordinator.py`.
- **Evidência existente:** E19, E20.
- **Verificação:** Parcial.
- **Lacuna/limitação:** O reset em desconexão é coberto; falta teste com relógio controlado para expiração exata e tentativa de comando sem estado recente.

### RF-015 — Reconexão sem cloud
- **Prioridade:** P0.
- **Origem:** DEC-01 + DEC-02.
- **Estado da implementação:** Implementado.
- **Requisito:** Após falha local ou ausência de estado válido, o cliente deverá poder reconectar pela LAN sem autenticação ou fallback externo.
- **Critérios de aceitação:**
  - Encerrar a ligação sem estado válido, limpar dados da sessão anterior e tentar novo acesso nos ciclos locais seguintes.
  - Não duplicar tarefas de leitura/keepalive nem recuperar alarmes de uma ligação antiga.
  - Uma sessão nova deverá voltar a apresentar valores apenas depois de receber estado válido.
- **Código/documentação:** `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/coordinator.py`.
- **Evidência existente:** E19.
- **Verificação:** Parcial.
- **Lacuna/limitação:** A desconexão e limpeza são testadas; falta teste fim a fim com corte e reposição do servidor, várias reconexões e ausência de tarefas órfãs.

### RF-016 — Limpeza no erro e no unload
- **Prioridade:** P0.
- **Origem:** DEC-02.
- **Estado da implementação:** Implementado.
- **Requisito:** Uma falha/cancelamento de setup ou unload bem-sucedido deverá fechar os clientes criados e descarregar o histórico pendente.
- **Critérios de aceitação:**
  - Cobrir erro de ligação, primeiro estado em falta, layout recusado, cancelamento, refresh e forwarding parcial de plataformas.
  - Tentar parar todos os clientes mesmo que um stop falhe; limpar runtime_data de setup falhado.
  - Quando as plataformas recusarem unload, não declarar unload completo nem destruir recursos ainda em uso.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E08, E09, E21.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Faltam testes de stop individual a falhar e de plataformas a devolverem unload=False; os restantes cenários principais têm automação.

### RF-017 — Controlos climate básicos
- **Prioridade:** P1.
- **Origem:** Implementação retida.
- **Estado da implementação:** Implementado.
- **Requisito:** O perfil implementado deverá expor leitura de temperatura, ligar/desligar, modos HVAC e temperatura alvo através de climate.
- **Critérios de aceitação:**
  - Expor off, auto, cool, heat, dry e fan_only, conforme o codec implementado.
  - Declarar alvo 16–30 °C com passo de 1 °C e encaminhar pedidos válidos para os comandos existentes.
  - Não confundir existência de métodos/entidades com confirmação física de cada modo; pedidos combinados estão tratados em RP-003.
- **Código/documentação:** `custom_components/haier_smartair2/climate.py`, `custom_components/haier_smartair2/const.py`, `custom_components/haier_smartair2/codec.py`, `tests/ha_climate_compat.py`.
- **Evidência existente:** E21, E25, E26, E27.
- **Verificação:** Implementação inspecionada; automação parcial; físico pendente.
- **Lacuna/limitação:** O harness climate regista uma entidade real e verifica leituras/serviços de temperatura em Celsius/Fahrenheit com coordenador-fixture; não exercita todos os modos HVAC nem efeitos físicos. RP-003 continua pendente.

### RF-018 — Ventilação e presets por codec
- **Prioridade:** P1.
- **Origem:** Implementação retida.
- **Estado da implementação:** Implementado.
- **Requisito:** Expor apenas os modos de ventilação/presets declarados pelo codec, mantendo as regras existentes de flags.
- **Critérios de aceitação:**
  - V3: quiet como modo de ventilação e Power/boost e Sleep como presets; V2 mantém quiet/turbo como definidos pelo codec.
  - Ao selecionar velocidade normal, limpar quiet/turbo de acordo com o método atual; boost e sleep não deverão ficar ativos em simultâneo nos comandos que os selecionam.
  - Os efeitos físicos, incluindo retorno da ventoinha a auto em quiet, deverão ser confirmados no equipamento antes de anunciados como validados para outro perfil.
- **Código/documentação:** `custom_components/haier_smartair2/climate.py`, `custom_components/haier_smartair2/codec.py`.
- **Evidência existente:** Nenhum teste dedicado identificado.
- **Verificação:** Inspeção; testes dedicados e físico pendentes.
- **Lacuna/limitação:** Falta teste de cada método de ventilação/preset, combinações de flags e confirmação física. Fonte atual: leitura do código e capturas/notas do perfil AS35.

### RF-019 — Funções adicionais e autolimpeza
- **Prioridade:** P1.
- **Origem:** Implementação retida.
- **Estado da implementação:** Implementado.
- **Requisito:** No perfil V3 atual, expor Health, luz, autolimpeza, bloqueio do comando e aquecimento elétrico sem presumir suporte noutros módulos.
- **Critérios de aceitação:**
  - Cada switch deverá encaminhar a flag correspondente e refletir o estado recebido.
  - Recusar iniciar autolimpeza quando o estado conhecido indicar auto, heat ou sleep.
  - Não apresentar o pedido de aquecimento elétrico como prova do estado físico do aquecedor: os campos de comando e atuador são distintos.
- **Código/documentação:** `custom_components/haier_smartair2/switch.py`, `custom_components/haier_smartair2/codec.py`, `custom_components/haier_smartair2/binary_sensor.py`.
- **Evidência existente:** E15, E21.
- **Verificação:** Inspeção e automação parcial; físico pendente.
- **Lacuna/limitação:** O smoke envia health=True e instancia switches; faltam testes dos cinco serviços, guardas de autolimpeza e resposta física.

### RF-020 — Aletas verticais e posição fixa
- **Prioridade:** P1.
- **Origem:** Implementação retida.
- **Estado da implementação:** Implementado.
- **Requisito:** Manter os comandos verticais existentes e recuperar a última posição fixa conhecida ao desativar swing.
- **Critérios de aceitação:**
  - Manter as posições e códigos definidos em select._POSITIONS; distinguir swing automático de posição fixa.
  - Quando houver uma posição fixa anterior, reutilizá-la ao desligar swing; sem histórico usar o fallback existente.
  - Não expor controlo horizontal como funcionalidade confirmada no AS35 documentado.
- **Código/documentação:** `custom_components/haier_smartair2/select.py`, `custom_components/haier_smartair2/coordinator.py`, `custom_components/haier_smartair2/codec.py`.
- **Evidência existente:** Nenhum teste dedicado identificado.
- **Verificação:** Inspeção; testes dedicados e físico pendentes.
- **Lacuna/limitação:** Faltam regressões de ida/volta por posição, restauro após swing e validação física. A posição fixa anterior é mantida em memória, não prometida entre reinícios.

### RF-021 — Telemetria sem inventar medições
- **Prioridade:** P1.
- **Origem:** DEC-03 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Expor conversões e unidades apenas nos termos do perfil documentado, preservando valores desconhecidos como desconhecidos/indisponíveis.
- **Critérios de aceitação:**
  - As capturas de referência deverão manter as temperaturas e frequências esperadas nos testes existentes.
  - Códigos de atuador 2/3 deverão ser desconhecidos, não convertidos em True; sentinelas deverão manter None.
  - O campo de válvula deverá permanecer em unidades brutas sem uma escala física inventada; 0 W nas capturas não prova consumo real nulo.
- **Código/documentação:** `custom_components/haier_smartair2/codec.py`, `custom_components/haier_smartair2/sensor.py`, `custom_components/haier_smartair2/binary_sensor.py`, `docs/protocol-as35.md`.
- **Evidência existente:** E14, E15, E20.
- **Verificação:** Automatizada nas capturas; precisão física não estabelecida.
- **Lacuna/limitação:** As conversões das capturas estão cobertas, mas não validam precisão metrológica nem comportamento de outros modelos.

### RF-022 — Alarmes com ciclo de vida de sessão
- **Prioridade:** P0.
- **Origem:** Implementação retida.
- **Estado da implementação:** Implementado.
- **Requisito:** Tratar 04/0F5A com payload de oito bytes como bitmap big-endian e manter estado desconhecido até haver relatório.
- **Critérios de aceitação:**
  - Preservar o significado dos bits 0–63 conforme o parser e rejeitar a forma incorreta.
  - Aceitar relatório antes do primeiro estado normal, limpar alarmes após relatório zero e voltar a desconhecido na desconexão.
  - Expor números dos bits ativos sem inventar a correspondência para códigos exibidos no aparelho.
- **Código/documentação:** `custom_components/haier_smartair2/codec.py`, `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/coordinator.py`, `custom_components/haier_smartair2/binary_sensor.py`.
- **Evidência existente:** E16, E19, E20.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-023 — Histórico limitado e persistente
- **Prioridade:** P1.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Manter histórico privado por entrada, persistente em disco e limitado por idade e quantidade.
- **Critérios de aceitação:**
  - Reter no máximo 20 000 registos por entrada; eliminar registos anteriores a sete dias nas operações de carga, snapshot/gravação ou exportação.
  - Usar gravação diferida com atraso definido de 120 s e flush no unload; não prometer perda zero perante crash/energia antes do flush.
  - Recarregar os registos recentes do mesmo entry_id sem depender da cloud.
- **Código/documentação:** `custom_components/haier_smartair2/packet_history.py`, `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** E17, E18, E21.
- **Verificação:** Automatizada na lógica; persistência fim a fim parcial.
- **Lacuna/limitação:** E17 usa um store de teste e E21 atravessa o store real no unload. Falta um ensaio de dois processos/reinício Home Assistant com ficheiro real.

### RF-024 — Amostragem do histórico
- **Prioridade:** P2.
- **Origem:** Implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Guardar alterações de pacotes, amostras periódicas de pacotes repetidos e todos os relatórios de alarme recebidos.
- **Critérios de aceitação:**
  - Para o mesmo dispositivo/tipo/subcomando, suprimir repetição idêntica antes de cinco minutos e guardar nova amostra após esse intervalo.
  - Guardar imediatamente uma alteração e não suprimir relatórios de tipo 04 idênticos.
  - Aplicar os limites de retenção sem bloquear o processamento do transporte.
- **Código/documentação:** `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E17, E18.
- **Verificação:** Automatizada nos cenários exercitados.

### RF-025 — Diagnóstico partilhável sem endereços
- **Prioridade:** P0.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Exportar diagnósticos com dispositivos anonimizados e bytes completos apenas dos layouts de telemetria explicitamente permitidos.
- **Critérios de aceitação:**
  - Incluir timestamp UTC, alias do dispositivo, tipo/subcomando, tamanho e erro de validação, sem envelope LAN, MAC/IP ou credenciais.
  - Para frames desconhecidos/inválidos, exportar metadados e epp_hex=None; preservar bytes apenas no store local privado.
  - Permitir exportação da entrada e filtragem por dispositivo.
- **Código/documentação:** `custom_components/haier_smartair2/diagnostics.py`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E17.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Há teste de anonimização e filtro de dispositivo; falta uma matriz de todas as variantes permitidas e uma revisão contra dados inesperados nas posições não mapeadas.

### RF-026 — Remoção deliberada do histórico
- **Prioridade:** P1.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Só a remoção explícita da entrada deverá apagar o respetivo store; reload/migração/unload não deverão equivaler a eliminação.
- **Critérios de aceitação:**
  - Reload e migração deverão conservar a chave de armazenamento baseada no mesmo entry_id.
  - async_remove_entry deverá remover apenas o store dessa entrada.
  - Documentar que eliminar a entrada remove o histórico e não é o procedimento normal de atualização.
- **Código/documentação:** `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/packet_history.py`, `README.md`.
- **Evidência existente:** E03, E17.
- **Verificação:** Inspeção e cobertura parcial.
- **Lacuna/limitação:** Falta teste de async_remove_entry com store real e duas entradas para provar isolamento da eliminação.


## 3. Requisitos não funcionais e de entrega

### RNF-001 — Compatibilidade Home Assistant declarada com evidência
- **Prioridade:** P1.
- **Origem:** DEC-04 + critério de qualidade.
- **Estado da implementação:** Implementado.
- **Requisito:** A gama de versões Home Assistant anunciada deverá corresponder às versões efetivamente ensaiadas, ou ser explicitamente indicada como não verificada.
- **Critérios de aceitação:**
  - Declarar 2026.11.0 como mínimo em hacs.json e executar o smoke LAN e os testes climate com Python compatível.
  - Exercitar também o patch estável 2026.11 fixado na matriz CI, mantendo evidência por versão.
  - Não emitir avisos das propriedades climate antigas; o mínimo e a matriz não equivalem a compatibilidade física.
- **Código/documentação:** `hacs.json`, `README.md`, `tests/ha_localonly_smoke.py`, `tests/ha_climate_compat.py`, `.github/workflows/telemetry-tests.yaml`.
- **Evidência existente:** E21, E25, E26, E27.
- **Verificação:** Automatizada em Home Assistant 2026.11.0 e 2026.11.1; CI do SHA exato a confirmar na entrega.
- **Lacuna/limitação:** O suporte anterior a 2026.11.0 foi retirado da declaração, não validado retroativamente. Não se promete suporte a versões futuras sem ensaio nem validação física.

### RNF-002 — Ciclo assíncrono sem tarefas infinitas de arranque
- **Prioridade:** P0.
- **Origem:** DEC-02 + implementação.
- **Estado da implementação:** Implementado.
- **Requisito:** Leitura/keepalive deverão correr como tarefas de fundo e o armazenamento não deverá fazer I/O síncrono no ciclo de eventos.
- **Critérios de aceitação:**
  - Arrancar as tarefas locais com a API de background tasks e cancelá-las no stop.
  - Usar o Store Home Assistant para leitura/gravação, sem novos ficheiros síncronos no caminho de pacotes.
  - Não anunciar latência garantida ou escalabilidade sem ensaio de carga.
- **Código/documentação:** `custom_components/haier_smartair2/local.py`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E21.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Falta teste completo de bootstrap/async_block_till_done e teste de carga com vários dispositivos; inspeção confirma as APIs assíncronas atuais.

### RNF-003 — Localização sem regressão de entidades
- **Prioridade:** P1.
- **Origem:** DEC-02 + DEC-03.
- **Estado da implementação:** Implementado.
- **Requisito:** Manter configuração/opções e avisos em en, pt e pl, preservando as traduções de entidades existentes.
- **Critérios de aceitação:**
  - Os formulários deverão pedir somente local_ips e ter mensagem de mapa inválido nas três línguas.
  - Os avisos de compatibilidade deverão estar presentes nas três línguas.
  - Os objetos entity das traduções deverão permanecer iguais aos da base 5b77363 enquanto não houver mudança funcional aprovada.
- **Código/documentação:** `custom_components/haier_smartair2/translations/en.json`, `custom_components/haier_smartair2/translations/pt.json`, `custom_components/haier_smartair2/translations/pl.json`.
- **Evidência existente:** E12.
- **Verificação:** Parcial.
- **Lacuna/limitação:** A comparação de entity e avisos foi executada por inspeção programática nesta sessão; ainda não integra um teste permanente dedicado.

### RNF-004 — Dependências e metadados local-only
- **Prioridade:** P0.
- **Origem:** DEC-01.
- **Estado da implementação:** Implementado.
- **Requisito:** Não manter dependências diretas cloud na integração e identificar corretamente a classe de IoT no manifesto.
- **Critérios de aceitação:**
  - Remover cloud.py e constantes SDK/gateway usadas apenas pela cloud; não importar paho.mqtt ou criptografia cloud no código da integração.
  - Declarar iot_class=local_push e a versão preparada 0.3.0.
  - Não confundir bibliotecas internas do próprio Home Assistant com uma dependência direta desta integração.
- **Código/documentação:** `custom_components/haier_smartair2/const.py`, `custom_components/haier_smartair2/manifest.json`, `custom_components/haier_smartair2/__init__.py`, `custom_components/haier_smartair2/config_flow.py`.
- **Evidência existente:** E01, E13, E21.
- **Verificação:** Automação de imports/ficheiros e inspeção do manifesto.

### RNF-005 — Verificação local, regressões e CI
- **Prioridade:** P0.
- **Origem:** Critério de qualidade derivado.
- **Estado da implementação:** Parcial.
- **Requisito:** Cada alteração funcional deverá ter regressão relevante, verificação local e execução dos checks antes de publicação.
- **Critérios de aceitação:**
  - Passar compileall, unidade, worker isolado, smoke real-HA e verificação de whitespace; rever o diff.
  - Não usar o número de testes como cobertura de todos os requisitos: declarar separadamente lacunas e testes físicos.
  - Antes de publicar, exigir checks remotos aplicáveis para a revisão exata; não atribuir ao novo pacote o CI de um commit antigo.
- **Código/documentação:** `.github/workflows/telemetry-tests.yaml`, `.github/workflows/hassfest.yaml`, `.github/workflows/validate.yaml`, `tests/test_local_only.py`, `tests/check_requirements.py`, `tests/test_requirements_traceability.py`, `tests/test_baseline_audit.py`.
- **Evidência existente:** E01, E21, E24.
- **Verificação:** Parcial.
- **Lacuna/limitação:** Os checks locais foram executados; o estado do CI remoto deve ser consultado no SHA exato do PR. Continuam por concluir os testes identificados nas lacunas e a validação física.

### RNF-006 — Entrega reproduzível e rollback
- **Prioridade:** P1.
- **Origem:** DEC-02 + critério derivado.
- **Estado da implementação:** Implementado.
- **Requisito:** Entregar pacote/patch identificáveis, com instruções de atualização e reversão que não apaguem a entrada por engano.
- **Critérios de aceitação:**
  - O ZIP deverá incluir a integração local e avisos, excluir cloud.py e artefactos de cache, e indicar o estado não publicado.
  - O patch deverá aplicar sem erros sobre 5b77363a05225311fb85ef89eb16136b26440acd.
  - Instruir backup da pasta e configuração; explicar substituição integral, conservação da entrada e remoção de credenciais pela migração.
- **Código/documentação:** `README.md`, `custom_components/haier_smartair2/manifest.json`.
- **Evidência existente:** Nenhum teste dedicado identificado.
- **Verificação:** Verificação de artefactos; rollback operacional pendente.
- **Lacuna/limitação:** O pacote e patch foram verificados nesta sessão. Falta ensaio completo de rollback com cópia de configuração real. Este documento não publica nem altera os pacotes anteriores.

### RNF-007 — Limites de segurança LAN e armazenamento
- **Prioridade:** P0.
- **Origem:** Critério de segurança derivado.
- **Estado da implementação:** Parcial.
- **Requisito:** Documentar que o transporte é plaintext e que os dados privados locais não são equivalentes a um diagnóstico anonimizável.
- **Critérios de aceitação:**
  - Informar que a porta LAN não deverá ser exposta diretamente à Internet e que se pressupõe rede local de confiança.
  - Identificar o store privado como contendo identificadores/frames brutos e recomendar cuidado ao partilhar backups.
  - Não afirmar cifragem/autenticação de ponta a ponta nem proteção de um módulo vulnerável apenas por eliminar a cloud.
- **Código/documentação:** `README.md`, `docs/compatibility.md`, `docs/protocol-as35.md`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E17.
- **Verificação:** Parcial.
- **Lacuna/limitação:** O store privado e plaintext estão documentados; a recomendação explícita de não expor a porta e uma avaliação de ameaças completa ainda não foram formalizadas. Requisito derivado, sujeito a aprovação.


### RNF-008 — Gates estáticos de distribuição Marketplace
- **Prioridade:** P1.
- **Origem:** DEC-04 + regras oficiais de publicação.
- **Estado da implementação:** Implementado.
- **Requisito:** Verificar a estrutura/metadados do candidato por análise estática sem importar ou executar o produto, distinguindo política do projeto de requisitos gerais do Marketplace.
- **Critérios de aceitação:**
  - Verificar hacs.json, mínimo 2026.11.0, uma integração, domínio estável, manifest/versão, HTTPS, codeowners, flow, categoria conhecida e imagens 256/512.
  - Verificar textos de configuração en/pt/pl e fallback inglês sem obrigar tradução completa das entidades em todas as línguas.
  - Usar os marcadores oficiais ha-marketplace no README e distinguir primeira instalação, atualização e release ainda não publicada.
  - Rejeitar fixtures negativas e executar também o checker sobre a árvore real no CI; não tratar o checker como certificação de segurança ou de catálogo.
- **Código/documentação:** `tests/check_marketplace.py`, `tests/test_marketplace_metadata.py`, `hacs.json`, `README.md`, `docs/marketplace.md`, `.github/workflows/telemetry-tests.yaml`.
- **Evidência existente:** E28, E29, E30, E31.
- **Verificação:** Automatizada em fixtures negativas e na árvore do candidato.
- **Lacuna/limitação:** AST/JSON/cabeçalhos PNG não provam toda a tradução dinâmica, rendering, aceitação no catálogo ou compatibilidade física. A categoria e os marcadores são opções de política do projeto, não bloqueios universais da plataforma.

### RNF-009 — Transações Marketplace preservam dados externos
- **Prioridade:** P0.
- **Origem:** DEC-04 + regras de instalação Marketplace.
- **Estado da implementação:** Implementado.
- **Requisito:** Exercitar os mecanismos reais de instalação/atualização/rollback do Marketplace com entrega local explícita do candidato, sem apagar identidade ou dados fora da pasta da integração.
- **Critérios de aceitação:**
  - Instalar e atualizar os ficheiros atuais pelo IntegrationRepository real, retirando ficheiros obsoletos e preservando ConfigEntry/Store e histórico-fixture externos.
  - Restaurar byte a byte a instalação anterior quando o manifest escrito está ausente, sem versão, com versão inválida ou domínio discordante; limpar uma primeira instalação falhada.
  - Recusar outro repositório dono do mesmo domínio e alterações de domínio antes de substituir ficheiros; não contornar a proteção apagando entradas.
  - Bloquear DNS/ligações e recusar pedidos fora da fixture de distribuição; verificar hashes do core instalado inalterados.
- **Código/documentação:** `tests/ha_marketplace_smoke.py`, `docs/marketplace.md`, `custom_components/haier_smartair2/packet_history.py`.
- **Evidência existente:** E32, E33, E34, E35, E36.
- **Verificação:** Automatizada no Marketplace real 2026.11.0 e 2026.11.1, com entrega substituída por fixtures locais.
- **Lacuna/limitação:** Sem frontend, GitHub/catálogo remoto, recorder ativo ou setup do AC. O SQLite é uma fixture de identidade, não prova de histórico real do recorder. A transferência de gestão upstream→fork continua por ensaiar; a recusa de colisão não a implementa.

### RNF-010 — Publicação coerente e controlada
- **Prioridade:** P1.
- **Origem:** DEC-04 + regras oficiais de releases/catálogo.
- **Estado da implementação:** Parcial.
- **Requisito:** Distinguir versão preparada, release distribuída e inclusão no catálogo, exigindo autorização e evidência antes de publicar.
- **Critérios de aceitação:**
  - Identificar 0.3.0 como candidato não publicado e 0.2.3 como release estável observada; o link normal não seleciona automaticamente a branch candidata.
  - Antes de publicar, confirmar tag/manifest coincidentes, mínimo suportado, notas de migração/backup e CI verde para o conteúdo exato.
  - Submeter o catálogo apenas após release e aprovação separada, sem afirmar que HACS/hassfest fazem essa inclusão automaticamente.
- **Código/documentação:** `README.md`, `docs/marketplace.md`, `docs/adr/0002-marketplace-202611.md`, `tests/check_marketplace.py`.
- **Evidência existente:** E28, E29.
- **Verificação:** Gates e documentação preparados; publicação e catálogo pendentes.
- **Lacuna/limitação:** Não existe release pública 0.3.0 criada por este incremento. Tag/release, submissão ao catálogo, UI real, hardware e merge não foram autorizados nem são substituídos por CI local.

## 4. Propostas e evolução — estado individual explícito

### RP-001 — Perfil explícito por dispositivo
- **Prioridade:** P1.
- **Origem:** Proposta após limitação identificada.
- **Estado da implementação:** Pendente.
- **Requisito:** Antes de alargar compatibilidade, permitir escolher/persistir um perfil concreto por dispositivo e não tratar apenas a dimensão como identificação.
- **Critérios de aceitação:**
  - Guardar o perfil sem consulta cloud e sem mudar a identidade MAC.
  - Definir comportamento seguro para perfil desconhecido/discordante; não enviar comandos de controlo por inferência não aceite.
  - Documentar que selecionar manualmente um perfil também não prova compatibilidade física.
- **Código/documentação:** `custom_components/haier_smartair2/config_flow.py`, `custom_components/haier_smartair2/local_setup.py`, `custom_components/haier_smartair2/__init__.py`.
- **Evidência existente:** Nenhum teste dedicado identificado.
- **Verificação:** Sem cobertura: proposta de evolução.
- **Lacuna/limitação:** Não implementado nem aprovado como extensão de escopo nesta especificação. Os avisos atuais não implementam este mecanismo.

### RP-002 — Comandos concorrentes sem perda de alterações
- **Prioridade:** P0.
- **Origem:** Achado reproduzido na revisão.
- **Estado da implementação:** Pendente.
- **Requisito:** Serializar/reconciliar comandos do mesmo aparelho para que uma escrita baseada num estado antigo não desfaça uma alteração anterior pendente.
- **Critérios de aceitação:**
  - Com estado inicial Health=False e painel=True, pedidos concorrentes Health=True e painel=False deverão preservar ambos os efeitos.
  - Usar os frames realmente enviados como oráculo; um lock que continue a reutilizar o snapshot antigo não será suficiente.
  - Definir timeout, falha e confirmação das alterações pendentes sem inventar confirmação física.
- **Código/documentação:** `custom_components/haier_smartair2/coordinator.py`, `custom_components/haier_smartair2/codec.py`, `tests/test_baseline_audit.py`.
- **Evidência existente:** E22.
- **Verificação:** Defeito conhecido; auditoria histórica disponível; regressão desejada pendente.
- **Lacuna/limitação:** A sonda inicial foi preservada e E22 reproduz permanentemente a falha no commit base. Continua a faltar a regressão do comportamento desejado no produto atual e a correção; a remoção cloud não resolveu este defeito.

### RP-003 — Respeito pelo hvac_mode em set_temperature
- **Prioridade:** P0.
- **Origem:** Achado reproduzido na revisão.
- **Estado da implementação:** Pendente.
- **Requisito:** O serviço combinado de temperatura deverá respeitar o modo HVAC solicitado, sem ligar contrariando um pedido off.
- **Critérios de aceitação:**
  - Com temperature=24 e hvac_mode=off, não emitir power=True.
  - Com heat/cool, aplicar o modo pedido juntamente com a temperatura segundo o contrato do serviço.
  - Definir/documentar o comportamento quando só se fornece temperatura e testar cada combinação.
- **Código/documentação:** `custom_components/haier_smartair2/climate.py`, `tests/test_baseline_audit.py`.
- **Evidência existente:** E23.
- **Verificação:** Defeito conhecido; auditoria histórica disponível; regressão desejada pendente.
- **Lacuna/limitação:** O método atual ignora hvac_mode e força power=True quando há temperatura. A sonda inicial foi preservada e E23 reproduz a falha no commit base; continuam pendentes a correção e a regressão do comportamento desejado no produto atual.

### RP-004 — Atualização das APIs climate descontinuadas
- **Prioridade:** P2.
- **Origem:** DEC-04 + avisos do smoke Home Assistant.
- **Estado da implementação:** Implementado.
- **Requisito:** Migrar as propriedades climate descontinuadas para a API native sem alterar a unidade do dispositivo ou a identidade.
- **Critérios de aceitação:**
  - Usar native_current_temperature, native_target_temperature e _attr_native_temperature_unit sem adaptar pelos membros legados.
  - Preservar leituras nativas em Celsius e conversão de estados/comandos pelo framework em Celsius/Fahrenheit.
  - Rejeitar pedidos de temperatura fora dos limites antes do comando; não suprimir os avisos para fingir conformidade.
- **Código/documentação:** `custom_components/haier_smartair2/climate.py`, `tests/ha_climate_compat.py`, `tests/ha_localonly_smoke.py`.
- **Evidência existente:** E25, E26, E27.
- **Verificação:** Automatizada em framework real; registo de entidade, estado e service bus.
- **Lacuna/limitação:** O coordenador/dispositivo do teste climate é uma fixture; não confirma efeitos físicos nem corrige RP-002/RP-003. O mínimo suportado é agora 2026.11.0.

### RP-005 — Evitar o mesmo dispositivo em entradas diferentes
- **Prioridade:** P2.
- **Origem:** Proposta de robustez derivada.
- **Estado da implementação:** Pendente.
- **Requisito:** Considerar deteção de MAC já configurado noutra entrada para evitar clientes concorrentes para um módulo de sessão única.
- **Critérios de aceitação:**
  - Ao criar/editar uma entrada com MAC já usado por outra, mostrar conflito acionável sem iniciar outra sessão.
  - Permitir mudar IP na própria entrada e preservar entradas legadas durante migração.
  - Não considerar a unicidade dentro de um mapa como prova de unicidade entre entradas.
- **Código/documentação:** `custom_components/haier_smartair2/config_flow.py`, `custom_components/haier_smartair2/local_map.py`.
- **Evidência existente:** Nenhum teste dedicado identificado.
- **Verificação:** Sem cobertura: proposta de evolução.
- **Lacuna/limitação:** Só há validação de duplicados dentro do próprio mapa. Proposta ainda não aprovada; não há teste físico de concorrência entre entradas.

## 5. Plano de aceitação e critérios de release

### 5.1 Verificação automática já executada

Na validação local-only inicial foram executados 20 casos unitários distintos: sete testes originais e treze do worker isolado. Nesse snapshot, `unittest discover` apresentava oito casos de topo porque um deles executa o worker como subprocesso; não somar novamente esse wrapper para inflacionar o total. A suite foi entretanto ampliada com a auditoria histórica e o verificador de rastreabilidade; os totais do snapshot local-only constam de `docs/evidence/verification-local.json`. O incremento Marketplace tem relatório separado em `docs/evidence/verification-marketplace.json` e CI do seu próprio commit. Os testes históricos têm finalidade forense e são contabilizados separadamente dos testes do produto atual.
O smoke E21 com Home Assistant 2026.11.0 instanciou 29 entidades, confirmou identidade climate e efetuou polling/comando/unload com um servidor TCP em loopback, sem imports/ligações cloud observados nos caminhos protegidos. **Não é um arranque integral de uma instalação real:** forwarding/unload de plataformas são substituídos no harness e as entidades são recolhidas em memória. Não demonstra registo completo de entidades, UI, dashboards, automações ou hardware físico.
Compilação, Ruff (seleção F) e diff --check passaram. Estes resultados são evidência da árvore ensaiada; alterações posteriores exigem nova execução.

```sh
python -m compileall -q custom_components
python tests/local_only_worker.py -v
python -m unittest discover -s tests -v
python tests/ha_localonly_smoke.py  # processo separado com Home Assistant >= 2026.11
python tests/ha_climate_compat.py -v
python tests/check_marketplace.py
python tests/ha_marketplace_smoke.py
ruff check --select F custom_components tests
git diff HEAD --check
```

### 5.2 Testes a acrescentar — planeados, não executados

- Integridade: matriz de cabeçalho, comprimento, checksum, CRC, stuffing e fluxo inválido que não renova o timeout (RF-013).
- Recuperação: corte/reposição do servidor, expiração com relógio controlado, múltiplas reconexões e tarefas órfãs (RF-014/RF-015).
- Lifecycle: stop individual a falhar, unload=False, recuperação real por Options e reload completo (RF-004/RF-005/RF-016).
- Controlos: cada método climate, flags, guardas, aletas e restauro; regressões permanentes das falhas RP-002 e RP-003.
- Persistência: reinício entre processos, eliminação de uma entrada sem afetar outra e rollback real (RF-023/RF-026/RNF-006).
- Compatibilidade: manter a matriz do mínimo/patch atual em cada revisão; perfil explícito continua pendente (RNF-001/RP-001). A migração native é agora verificada por RP-004.

### 5.3 Validação física — obrigatória para declarar hardware verificado

Estado de todos os casos abaixo: **não executado nesta sessão**. Responsável e janela de teste: **por definir**. Usar apenas hardware cujo ensaio foi autorizado e manter um meio conhecido de voltar ao estado anterior.
- **TA-01:** registar modelo exato do AC, referência do módulo e firmware se disponível, sem publicar MAC, IP, credenciais ou capturas privadas.
- **TA-02:** bloquear Internet mantendo LAN; arrancar/reiniciar Home Assistant e confirmar o mesmo aparelho, identidade e estado físico.
- **TA-03:** comparar primeiro leituras com o display/comando; só depois testar ligar/desligar, temperatura e modos, um de cada vez.
- **TA-04:** testar velocidades, quiet e presets; registar o estado pedido, reportado e observado, incluindo efeitos laterais.
- **TA-05:** ensaiar funções extra apenas se o hardware as suportar e com procedimento de recuperação. Não acionar aquecimento elétrico/autolimpeza por tentativa num módulo desconhecido.
- **TA-06:** observar posições verticais e restauro de swing, sem forçar mecanismos danificados. Horizontal permanece fora do perfil AS35 documentado.
- **TA-07:** interromper/restabelecer Wi-Fi e verificar indisponibilidade, recuperação, alarmes e ausência de sessões antigas.
- **TA-08:** confirmar persistência após reinício e ensaiar reversão com backup completo da configuração e da pasta, não apenas do código.

### 5.4 Gates de publicação e aceitação

1. Rever e aprovar quais requisitos pertencem à release. O presente documento é uma proposta, não uma aprovação tácita de todo o backlog.
2. Para cada requisito aprovado, cumprir os critérios ou registar explicitamente a exceção, risco, responsável pela aceitação e evidência. Nenhuma exceção foi aprovada por este documento.
3. Não declarar conformidade completa enquanto existirem lacunas dos requisitos aprovados. Os defeitos conhecidos de comandos (RP-002/RP-003) continuam pendentes, apesar dos testes atuais passarem.
4. Só usar a expressão hardware verificado após TA-01–TA-08 aplicáveis, com resultado guardado por combinação de modelo/módulo/firmware. Até lá: experimental e apenas evidência documentada.
5. Rever os avisos de compatibilidade, manifesto, dependências, pacote e procedimento de rollback; executar os checks no exato conteúdo entregue.
6. Publicação/PR/release no GitHub exige autenticação e verificação remota da alteração. A branch/PR deve ser verificada remotamente após o envio; este documento não autoriza merge nem release.

## 6. Limitações e decisões ainda por aprovar

- A heurística 24/32 bytes não exclui um layout incompatível de igual dimensão. Um aviso não implementa a proteção por perfil de RP-001.
- O arranque atual é por entrada: um aparelho configurado que falhe pode impedir o setup dessa entrada; isolamento independente de aparelhos no bootstrap não é um comportamento garantido.
- O transporte local é plaintext; não foi feita uma auditoria do firmware do módulo nem um ensaio de segurança da rede.
- O store privado contém identificadores e frames brutos; a anonimização do export não anonimiza backups locais.
- Mantêm-se os defeitos de comandos concorrentes e hvac_mode combinado. Os avisos de API climate foram resolvidos no incremento DEC-04; isso não corrige esses controlos.
- O mínimo anunciado foi elevado de 2024.11.0 não verificado para 2026.11.0; os resultados por versão constam da evidência Marketplace e do CI.
- Prazos, responsáveis, metas de desempenho/carga e política de suporte a novos modelos: **por definir**, sem valores inventados.

## 7. Catálogo de evidências e rastreabilidade

Cada referência abaixo aponta para um símbolo real do repositório. A matriz CSV adjacente permite filtrar requisito, prioridade, estado, evidência e lacuna. As referências não significam que um único teste cobre todos os critérios do requisito.

- **E01:** `tests/local_only_worker.py::OfflineTests.test_import_and_configuration_never_load_cloud`.
- **E02:** `tests/local_only_worker.py::MapTests.test_map_validation`.
- **E03:** `tests/local_only_worker.py::MigrationTests.test_migration_preserves_identity_uses_effective_map_and_removes_credentials`.
- **E04:** `tests/local_only_worker.py::MigrationTests.test_migration_keeps_whole_field_options_precedence`.
- **E05:** `tests/local_only_worker.py::RuntimeTests.test_setup_uses_local_map_and_preserves_registry_name_and_identity`.
- **E06:** `tests/local_only_worker.py::RuntimeTests.test_missing_map_fails_actionably_before_opening_any_client`.
- **E07:** `tests/local_only_worker.py::RuntimeTests.test_setup_waits_for_a_late_first_status`.
- **E08:** `tests/local_only_worker.py::RuntimeTests.test_setup_failures_stop_all_clients_and_flush_history`.
- **E09:** `tests/local_only_worker.py::RuntimeTests.test_forward_failure_unloads_partial_platforms_and_cleans_runtime`.
- **E10:** `tests/local_only_worker.py::RuntimeTests.test_coordinator_is_bound_to_config_entry_for_framework_first_refresh`.
- **E11:** `tests/local_only_worker.py::RuntimeTests.test_setup_prefers_entry_scoped_device_registry_lookup`.
- **E12:** `tests/local_only_worker.py::PackagingTests.test_all_localized_forms_are_local_only`.
- **E13:** `tests/local_only_worker.py::PackagingTests.test_cloud_implementation_and_constants_are_removed`.
- **E14:** `tests/test_local_telemetry.py::DecodeTests.test_real_temperatures_and_actuators`.
- **E15:** `tests/test_local_telemetry.py::DecodeTests.test_other_two_bit_values`.
- **E16:** `tests/test_local_telemetry.py::DecodeTests.test_alarm_bitmap_and_shape`.
- **E17:** `tests/test_local_telemetry.py::HistoryTests.test_capture_reload_sampling_redaction_and_retention`.
- **E18:** `tests/test_local_telemetry.py::HistoryTests.test_bounded_history`.
- **E19:** `tests/test_local_telemetry.py::HistoryTests.test_local_loop_updates_and_discards_old_alarms`.
- **E20:** `tests/test_local_telemetry.py::HistoryTests.test_binary_sensors_unknown_and_alarm_clear`.
- **E21:** `tests/ha_localonly_smoke.py::main`.

- **E22:** `tests/test_baseline_audit.py::BaselineCloudAuditTests.test_bug_concurrent_commands_overwrite_previous_full_snapshot`.
- **E23:** `tests/test_baseline_audit.py::BaselineCloudAuditTests.test_bug_combined_hvac_off_temperature_command_powers_on`.
- **E24:** `tests/test_requirements_traceability.py::TraceabilityTests.test_valid_fixture_resolves_symbols_without_imports`.

E22/E23 são auditoria do código antigo: passar significa reproduzir o defeito, não cumprir o comportamento desejado de RP-002/RP-003. E24 verifica o verificador estrutural, não certifica conformidade dos requisitos.

## 8. Documentos de origem

- Decisões explícitas do utilizador nesta conversa: exclusivamente local, preservar funcionamento LAN e tornar a incerteza de compatibilidade visível.
- `README.md`, `docs/compatibility.md` e `docs/protocol-as35.md`: âmbito e limites de evidência.
- `custom_components/haier_smartair2/`: implementação atual inspecionada, não prova física de funcionamento.
- `tests/local_only_worker.py`, `tests/test_local_telemetry.py` e `tests/ha_localonly_smoke.py`: testes efetivos identificados acima.
- Achados da revisão anterior: RP-002/RP-003 foram reproduzidos em sondas e auditorias históricas; não integram ainda regressões do comportamento desejado no produto atual. Relatos upstream e PRs não são testes desta versão local.

**Âmbito do incremento documental inicial:** apenas especificação e rastreabilidade; escrever esses requisitos não aprovou automaticamente correções funcionais. O incremento posterior DEC-04 foi expressamente autorizado e implementa a API climate e a verificação Marketplace/2026.11 descritas nesta revisão, mantendo as restantes propostas pendentes.

- **E25:** `tests/ha_climate_compat.py::Climate202611Tests.test_00_import_uses_native_temperature_api_without_warnings`.

- **E26:** `tests/ha_climate_compat.py::ClimateRuntimeTests.test_fahrenheit_service_converts_to_native_celsius`.

- **E27:** `tests/ha_climate_compat.py::ClimateRuntimeTests.test_fahrenheit_state_is_converted_once`.

- **E28:** `tests/check_marketplace.py::validate`.

- **E29:** `tests/test_marketplace_metadata.py::MarketplaceMetadataTests.test_official_readme_marker_names`.

- **E30:** `tests/test_marketplace_metadata.py::MarketplaceMetadataTests.test_translations_and_brand_contract`.

- **E31:** `tests/test_marketplace_metadata.py::MarketplaceMetadataTests.test_domain_slug_is_validated_not_just_equal_to_folder`.

- **E32:** `tests/ha_marketplace_smoke.py::MarketplaceTransactionTests.test_install_update_preserves_identity_and_external_history`.

- **E33:** `tests/ha_marketplace_smoke.py::MarketplaceTransactionTests.test_invalid_written_manifest_rolls_back_byte_for_byte`.

- **E34:** `tests/ha_marketplace_smoke.py::MarketplaceTransactionTests.test_same_domain_owner_refused_before_content_or_backup_changes`.

- **E35:** `tests/ha_marketplace_smoke.py::MarketplaceTransactionTests.test_changed_domain_refused_before_file_replacement`.

- **E36:** `tests/ha_marketplace_smoke.py::OfflineGuardTests.test_dns_and_connections_are_denied_without_network`.
