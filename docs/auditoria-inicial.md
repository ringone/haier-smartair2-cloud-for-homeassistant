# Auditoria inicial e preservação dos testes

## 1. Âmbito e proveniência

A análise inicial incidiu sobre o commit **`5b77363a05225311fb85ef89eb16136b26440acd`** do fork. Os sete testes originais de telemetria passavam, mas não cobriam os caminhos cloud, todos os serviços climate ou comandos concorrentes.

As sondas usaram código real desse estado com fronteiras simuladas: sockets que devolvem EOF, respostas JSON de erro, transportes e objetos Home Assistant mínimos. **Não houve autenticação na Haier, controlo de um aparelho real ou simulação de resultados de uma chamada Haier que não tivesse sido efetuada.** Os testes são de comportamento do código, não ensaios da infraestrutura Haier.

### Evidência retida da análise anterior

- [`evidence/initial-audit-probes.json`](evidence/initial-audit-probes.json): saída preservada das sondas iniciais que demonstraram perda de alterações, cache cloud offline, EOF, TLS desativado, `hvac_mode` ignorado e erro de API interpretado como lista vazia.
- [`evidence/initial-local-only-tdd.log`](evidence/initial-local-only-tdd.log): registo RED/GREEN retido do desenvolvimento local-only. Foram substituídos prefixos de caminhos absolutos e normalizados espaços de apresentação no fim das linhas, não os resultados das asserções.
- [`evidence/provenance.json`](evidence/provenance.json): SHA-256 das fontes originais e dos ficheiros arquivados, transformações feitas e instante do arquivo. A data de arquivo **não é** uma data inventada da execução original.

O log retém estados intermédios, incluindo falhas e correções. Não equivale a uma sequência de commits intermédios reconstituível nem à execução atual da suite.

### Sondas históricas agora permanentes

[`tests/test_baseline_audit.py`](../tests/test_baseline_audit.py) volta a exercitar o código do commit fixo através de `git show`, sem restaurar `cloud.py` na integração atual. Apenas os símbolos necessários são extraídos; os efeitos de rede são substituídos e as repetições de EOF são interrompidas deliberadamente por uma sentinela.

**Um teste histórico verde significa que reproduziu o defeito esperado no código antigo. Não significa que esse comportamento incorreto seja aceite no produto atual, nem que todos os defeitos tenham sido corrigidos.** Os testes atuais local-only verificam separadamente a ausência do caminho cloud e a preservação dos fluxos locais.

As sondas permanentes foram reconstruídas e executadas agora para tornar os achados reproduzíveis. A evidência JSON/log acima é a retida da análise anterior; não se atribui retroativamente à análise inicial uma suite que só agora ficou no repositório.

## 2. Registo de achados e destino

As linhas indicadas referem-se sempre ao **commit base**, não à versão em que `cloud.py` foi removido.

### AUD-001 — TLS sem validação de identidade

- **Base:** `cloud.py:47–53,149–150,173,205–206,242`.
- **Evidência inicial:** contexto com `check_hostname=False` e `verify_mode=CERT_NONE`; inspeção dos pedidos com `ssl=False`.
- **Consequência:** cifragem sem autenticação do servidor, permitindo impersonação a um intermediário capaz de intercetar a ligação.
- **Destino nesta alteração:** transporte cloud eliminado; não foi criada uma implementação TLS cloud corrigida.
- **Rastreabilidade:** RF-001, RNF-004.

### AUD-002 — EOF do gateway sem condição de saída

- **Base:** `cloud.py:208–214`.
- **Evidência:** `recv()` simulado a devolver `b""` não faz progredir o ciclo; sentinela limita o ensaio para não ocupar a máquina indefinidamente.
- **Consequência:** thread do executor e arranque/reconexão podem ficar presos após o servidor fechar antes de completar a resposta.
- **Destino:** código cloud eliminado, em vez de manter uma alternativa de fallback.
- **Rastreabilidade:** RF-001, RF-016.

### AUD-003 — Dependência cloud não declarada

- **Base:** `cloud.py:25` importa `paho.mqtt.client`, com `manifest.json` a declarar `requirements: []`.
- **Natureza da evidência:** inspeção de dependências. A falha depende de o ambiente não ter a biblioteca instalada por outra integração; não é apresentada como uma falha inevitável de todas as instalações.
- **Destino:** import e transporte eliminados. A integração já não precisa diretamente dessa dependência.
- **Rastreabilidade:** RNF-004. A inspeção é distinta das sondas dinâmicas do JSON inicial.

### AUD-004 — Comandos próximos desfazem alterações

- **Base:** `coordinator.py:94–109` e `codec.py:338–386`.
- **Evidência:** Health=True e painel=False, calculados a partir do mesmo estado antigo, originam um segundo frame com Health=False.
- **Destino:** **pendente**, não corrigido pela remoção da cloud. O caminho local mantém este risco.
- **Rastreabilidade:** RP-002. O teste histórico preserva a demonstração; falta uma regressão do comportamento desejado e a respetiva correção.

### AUD-005 — Pedido de temperatura ignora `hvac_mode`

- **Base:** `climate.py:171–174`.
- **Evidência:** temperature=24 e hvac_mode=off resultam em target_temp=24 e power=True.
- **Destino:** **pendente**, sem alteração funcional ao serviço climate neste PR.
- **Rastreabilidade:** RP-003.

### AUD-006 — Cache cloud continua disponível após desconexão

- **Base:** `cloud.py:117–121,297–303` e `coordinator.py:71–92`.
- **Evidência inicial:** transporte offline com estado em cache é novamente aceite pelo coordenador; revisão também identificou que o callback cloud não limpa frames/online.
- **Destino:** caminho cloud eliminado. Não se transfere o estado cloud antigo para o transporte local, cujo ciclo de limpeza permanece coberto por testes próprios.
- **Rastreabilidade:** RF-001, RF-014.

### AUD-007 — Erro da API tratado como conta sem dispositivos

- **Base:** `cloud.py:173–187` e `__init__.py:82–83,117–135`.
- **Evidência:** resposta JSON sintética com retCode=10001/retInfo=token expired resulta em `[]`, sem exceção.
- **Destino:** descoberta/API cloud eliminadas. Um mapa local vazio não é tratado como setup bem-sucedido sem aparelhos.
- **Rastreabilidade:** RF-001, RF-002, RF-005.

### AUD-008 — Falha parcial de setup não para cloud já iniciada

- **Base:** `__init__.py:117–130` e `cloud.py:218–250`.
- **Evidência:** revisão independente executou setup com cloud iniciada e falha posterior de refresh local; o tratamento de erro parava o cliente local e fazia flush, mas não chamava cloud.async_stop().
- **Destino:** recurso cloud eliminado; a implementação local-only tem limpeza de todos os clientes locais e de plataformas parcialmente encaminhadas.
- **Rastreabilidade:** RF-016, E08, E09.

## 3. Como repetir os testes sem contactar a Haier

```sh
# O commit histórico precisa de existir no clone; o job de testes usa fetch-depth: 0.
git cat-file -e 5b77363a05225311fb85ef89eb16136b26440acd^{commit}
python -m unittest discover -s tests -p 'test_baseline_audit.py' -v
python tests/local_only_worker.py -v
python -m unittest discover -s tests -v
python tests/check_requirements.py
```

Um clone shallow que não contenha a base deve obter esse histórico antes do ensaio; a ausência da base não deve ser ocultada como teste passado. As sondas não criam sockets de rede, não precisam de credenciais Haier e não devem efetuar pedidos reais à Haier.

O smoke separado `tests/ha_localonly_smoke.py` usa **um simulador TCP em loopback** e Home Assistant real. Esse ensaio é diferente de um ensaio puramente em memória e diferente de um teste num aparelho físico. As limitações completas constam de [`requisitos.md`](requisitos.md) e [`compatibility.md`](compatibility.md).

## 4. Leitura correta do estado atual

- Defeitos do caminho cloud deixaram de ser alcançáveis porque esse caminho foi removido; não se promete uma implementação cloud corrigida ou suporte a módulos encrypted/cloud-only.
- AUD-004 e AUD-005 continuam no backlog e devem manter-se visíveis na revisão, requisitos e PR.
- A heurística de dimensão V2/V3 continua experimental. Documentá-la não a torna uma identificação garantida de outro aparelho/módulo.
- Testes unitários, histórico reproduzível, checks estáticos e simulador são evidência de software; não substituem validação física nem constituem autorização para publicar suporte a novo hardware.
