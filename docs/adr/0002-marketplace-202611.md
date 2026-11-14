# ADR-002 — Marketplace e Home Assistant 2026.11

- **Estado:** implementado em branch para revisão; sem autorização de merge/release.
- **Base:** `feat/local-only`, commit `2b4412d8e9ccc905e034cec677b3bcbdff9f5c26`.
- **Branch:** `chore/marketplace-ha-2026.11`.

## Contexto e autorização

O utilizador pediu a implementação das lacunas identificadas na análise Marketplace/2026.11, numa branch nova derivada da local-only. Esta alteração não reintroduz cloud nem alarga a compatibilidade física do protocolo. As decisões DEC-01/02/03 e os registos iniciais permanecem válidos.

## Decisões

1. Adotar a API climate `native_current_temperature`, `native_target_temperature` e `_attr_native_temperature_unit`, deixando a conversão Celsius/Fahrenheit para a classe base e o serviço climate do Home Assistant.
2. Declarar **Home Assistant 2026.11.0 como mínimo**. Não manter uma promessa de 2024.11.0 sem evidência e não introduzir adapters de APIs antigas apenas para preservar esse número. O CI deve exercitar o mínimo e o patch estável 2026.11 fixado no workflow.
3. Manter os retornos booleanos de setup/unload/migração: a documentação de 2026.11 continua a permiti-los para integrações customizadas, sem depreciação. Não confundir a regra do core com um requisito do Marketplace.
4. Verificar metadados/estrutura por análise estática e executar os mecanismos reais do Marketplace com distribuição substituída por fixtures locais explícitas. Não chamar a isso instalação pela UI, catálogo remoto, GitHub real ou validação física.
5. Conservar domínio, config entry e IDs MAC. Uma colisão de gestão entre o repositório original e o fork deve ser recusada pelo Marketplace antes da escrita; os testes não devem contorná-la apagando a configuração.
6. Continuar a guardar o histórico no Store do Home Assistant, fora da pasta substituída nas atualizações.
7. Manter a versão preparada **0.3.0**, ainda não publicada. Criar/alterar release, submeter ao catálogo ou fazer merge exige autorização separada. Preparar checklist e instruções não equivale a publicar.

## Verificação e limites

- TDD da migração climate: a regressão de import observa os três avisos legados antes da alteração e passa depois, sem suprimir logs.
- Framework real: registo de entidade, máquina de estados e service bus climate em Celsius/Fahrenheit; o coordenador/dispositivo é uma fixture e não confirma efeitos físicos.
- O smoke LAN existente mantém servidor TCP em loopback e verifica migração/setup/controlo/unload.
- A validação Marketplace é detalhada em `docs/marketplace.md`; os relatórios devem indicar precisamente os boundaries substituídos e os cenários realmente executados.
- Permanecem pendentes ensaio físico, perfil semântico explícito e os defeitos locais RP-002/RP-003. Não alterar bytes do codec ou transporte para esta manutenção.

## Fontes de decisão

- https://contributors.home-assistant.io/blog/2026/10/08/climate-native-temperature/
- https://contributors.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/
- https://contributors.home-assistant.io/marketplace/guides/releases/
