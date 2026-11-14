# Aplicação do SDLC neste fork

## Objetivo e limites

Este registo aplica o ciclo de desenvolvimento à mudança de integração híbrida para **exclusivamente local**, sem transformar um PR em rascunho numa release aprovada. A base analisada é `5b77363a05225311fb85ef89eb16136b26440acd`; as alterações são preparadas na branch `feat/local-only`. A `main` não deve ser alterada por este processo antes de revisão e aprovação de merge.

O objetivo local-only e a obrigação de explicitar a compatibilidade desconhecida foram decididos pelo utilizador. As propostas de perfil explícito, correção dos comandos concorrentes e serviço climate combinado continuam pendências: incluí-las na especificação não é implementá-las nem aprovar silenciosamente novo escopo. A evolução da API climate foi posteriormente autorizada no incremento Marketplace/2026.11 descrito abaixo.

## Fase 1 — Análise do problema e baseline

**Trabalho aplicado:** leitura do código, documentação, metadados e testes; execução dos sete testes iniciais; sondas isoladas dos caminhos não cobertos e revisão independente.

**Artefactos:** [auditoria inicial](auditoria-inicial.md), [JSON das sondas retido](evidence/initial-audit-probes.json), [proveniência](evidence/provenance.json) e testes históricos do commit fixo.

**Saída:** achados AUD-001–AUD-008 e distinção entre defeitos cloud, riscos locais ainda presentes e limitações de evidência. Os sete testes verdes não foram tratados como prova de ausência de bugs.

## Fase 2 — Requisitos e aceitação

**Trabalho aplicado:** especificação com IDs estáveis, origem, prioridade, critérios observáveis, implementação, evidência e lacunas; matriz para relacionar requisitos, código e testes.

**Artefactos:** [requisitos](requisitos.md), [matriz CSV](matriz-requisitos.csv) e verificador `tests/check_requirements.py`.

**Controlo:** distinguir estado de implementação de cobertura e validação física. O verificador deve detetar deriva entre Markdown/CSV, referências inexistentes e símbolos de teste inválidos, não certificar conformidade por contar testes.

**Gate:** os requisitos derivados e o backlog continuam sujeitos a revisão. Não atribuir responsáveis, prazos, compatibilidade ou metas de desempenho não acordados.

## Fase 3 — Arquitetura e decisão de solução

**Decisão:** remover cloud de configuração, migração, descoberta, controlo e fallback; não apenas desligar MQTT depois de um login obrigatório.

**Preservar:** domínio, IDs MAC, entry_id, histórico, transporte LAN, codecs e semântica existente. As opções mantêm a precedência integral do campo de mapa, sem recuperar dispositivos anteriormente removidos.

**Artefactos:** [ADR-001](adr/0001-local-only.md), [compatibilidade](compatibility.md) e [protocolo AS35](protocol-as35.md).

**Risco explícito:** a escolha automática V2/V3 por dimensão é uma heurística. Não há garantia de validade noutros aparelhos, módulos Wi-Fi ou firmware, nem teste físico da versão preparada nesta sessão. Não há um perfil explícito por dispositivo já implementado.

## Fase 4 — Desenvolvimento e controlo de mudanças

**Trabalho aplicado:** implementação em branch separada; testes RED/GREEN durante o desenvolvimento local-only; validação do mapa, migração, recuperação por opções, limpeza de recursos e atualizações localizadas da interface.

**Evidência:** [log RED/GREEN retido](evidence/initial-local-only-tdd.log). O log documenta a execução observada; não inventa commits intermédios nem prova por si só cobertura completa de cada requisito.

**Regra:** correções novas devem ter uma regressão que falhe pelo motivo esperado antes de alterar o produto. Não corrigir incidentalmente outros controlos ou bytes do protocolo sem evidência e escopo explícitos.

## Fase 5 — Verificação e validação

### Verificação de software

- Compilar os módulos e executar as suites unitárias e o worker isolado.
- Repetir os achados cloud/locais no código antigo do commit fixo, usando doubles limitados e sem contactar a Haier.
- Exercitar import, migração, setup, entidades, comando e unload com Home Assistant real e um servidor TCP em loopback.
- Executar o verificador de requisitos, Ruff e `git diff --check`.
- Rever fontes, ficheiros adicionados, dados arquivados e potenciais segredos antes de commit/push.

**Relatório:** [`evidence/verification-local.json`](evidence/verification-local.json), gerado a partir de comandos realmente executados. A contagem deve distinguir testes distintos de um wrapper que volta a executar a suite isolada. Teste histórico verde significa defeito reproduzido no baseline, não defeito corrigido no produto atual.

O smoke de Home Assistant instancia entidades e usa seams de forwarding/unload substituídos no harness. Não equivale a bootstrap integral, utilização da UI, registo persistente de todas as entidades, dashboards ou automações reais.

### Validação no contexto real

A validação num aparelho físico está **pendente**. O plano TA-01–TA-08 está nos requisitos: identificar modelo/módulo/firmware, confirmar leituras, ensaiar controlos autorizados, cortar/restabelecer LAN, reiniciar e verificar rollback. Não anunciar novo hardware como verificado antes de guardar essa evidência.

## Fase 6 — Revisão, integração e entrega controlada

**Procedimento desta alteração:**

1. Rever o diff completo e obter revisão independente dos riscos/erros de lógica.
2. Corrigir problemas novos encontrados e voltar a executar a verificação local.
3. Fazer commit na `feat/local-only`; enviar apenas essa branch, sem force push e sem atualizar `main`.
4. Abrir PR **em rascunho**, com resumo, requisitos, auditoria, testes executados e limitações.
5. Ler de volta a branch/PR e verificar SHA, base/head e estado draft; acompanhar os checks associados ao SHA exato.
6. Se um check falhar, guardar a causa, corrigir o problema aplicável e repetir os checks. Não chamar green a uma execução incompleta nem usar o CI do commit base para certificar o novo conteúdo.

A evidência remota autoritativa é a execução GitHub Actions do commit do PR, não um texto estático que se tornaria obsoleto ao criar outro commit. A referência do PR e o resultado real dos checks devem ser entregues ao utilizador após publicação da branch.

**Não faz parte da autorização atual:** merge na `main`, tag de release, publicação no Marketplace, instalação no Home Assistant do utilizador ou ativação de testes físicos. O manifesto 0.3.0 identifica a versão preparada, não uma release já publicada.

## Fase 7 — Aceitação, release e operação

**Gates ainda aplicáveis:** revisão do utilizador, decisão sobre os requisitos/propostas incluídos, aceitação explícita das limitações e validação física antes de declarar esse hardware verificado. Os defeitos locais RP-002/RP-003 devem continuar visíveis; não são resolvidos por retirar a cloud.

Para futura release: validar backup/rollback, instalar substituindo a pasta completa, conservar a entrada existente e deixar claro que a migração remove credenciais cloud. Reverter só os ficheiros de código pode não repor dados de configuração antigos; o backup deve incluir a configuração.

Para manutenção: relacionar problemas novos com requisitos/achados; recolher capturas anonimizadas e referência exata de hardware; atualizar a matriz e regressões; reexecutar CI. Não recolher credenciais, publicar o store privado ou inferir suporte de um modelo apenas pelo rótulo V2/V3.

## Estado que não deve ser confundido

- Código/documentação preparados ≠ release publicada.
- Autorização GitHub ≠ autorização para merge.
- Testes unitários verdes ≠ todos os requisitos satisfeitos.
- Simulador/frames conhecidos ≠ validação física ou compatibilidade universal.
- Remover a cloud ≠ corrigir uma biblioteca cloud ainda disponível para utilização.
- Avisar da heurística ≠ implementar identificação robusta/perfis por dispositivo.

## Incremento aprovado — Marketplace e Home Assistant 2026.11

**Base imutável:** `feat/local-only`, commit `2b4412d8e9ccc905e034cec677b3bcbdff9f5c26`. **Branch de trabalho:** `chore/marketplace-ha-2026.11`; não alterar `main` nem a branch base. A análise antecedente distinguiu regras de instalação, catálogo e APIs; o utilizador autorizou implementar as lacunas, não publicar uma release.

**Análise/requisitos:** rever regras oficiais de publicação e os anúncios das APIs; introduzir DEC-04 e rastreabilidade para os checks Marketplace. Manter os testes forenses e evidência inicial sem substituir os resultados antigos por execuções novas.

**Desenho:** [ADR-002](adr/0002-marketplace-202611.md). Mínimo declarado 2026.11.0; matriz com 2026.11.0 e patch estável 2026.11.1 fixado após consulta ao PyPI. A versão preparada continua 0.3.0 sem release pública. Retornos booleanos permanecem válidos para custom integrations e não são alterados por confusão com requisitos do core.

**Desenvolvimento/TDD:** a regressão de import climate falhou pelos três avisos de propriedades descontinuadas; a alteração mínima para `native_*` passou sem suprimir logs. Acrescentar provas reais de estados e serviços Celsius/Fahrenheit, valores desconhecidos, limites e identidade. O coordenador/dispositivo dessas provas é uma fixture; não houve comandos a um AC físico.

**Verificação:** além das suites existentes, executar o checker Marketplace e testes de fixtures negativas, registo/máquina de estados/service bus climate reais e o harness de transações Marketplace, em processos separados dos testes que substituem módulos Home Assistant. As fixtures de distribuição não representam releases ou respostas reais do GitHub. Ler o alcance e gates em [marketplace.md](marketplace.md).

**Evidência do incremento:** `docs/evidence/marketplace-climate-tdd.json`, `docs/evidence/marketplace-static-tdd.log` e `docs/evidence/verification-marketplace.json`. O último deve ser gerado da árvore final ensaiada; os ficheiros `verification-local.json` e `review-final.json` continuam a documentar o incremento anterior, não o estado atual.

**Revisão/entrega:** revisão independente antes de commit, envio apenas da branch de trabalho e PR em rascunho com base `feat/local-only`, para que o diff do incremento não repita as alterações local-only. Confirmar leitura remota de SHA/base/head, CI do novo conteúdo e preservação das branches base. Não mergear, criar tag/release, submeter catálogo nem instalar na instância do utilizador sem autorização separada.

**Validação e manutenção:** continuar com ensaio físico e aceitação pendentes; os mecanismos locais de instalação não provam UI/GitHub remoto, migração automática do gestor original para o fork nem conformidade de todos os requisitos. RP-002/RP-003 permanecem visíveis. Acompanhar deprecações e voltar a testar os patches suportados em cada revisão.
