# Sistema de Logging de API - SafeTrace

## Visão Geral

Sistema completo de logging implementado para rastrear todas as chamadas à API do Blockchair e o processo de análise de transações. Os logs fornecem visibilidade completa sobre:

- Todas as requisições HTTP feitas à API do Blockchair
- Rate limiting e retries
- Circuit breaker (resiliência)
- Cache hits/misses
- Processamento de transações e endereços
- Entidades sinalizadas e análise de risco

## Níveis de Log

### INFO
Mensagens principais sobre o fluxo de execução:
- Início e conclusão de análises
- Chamadas de API bem-sucedidas
- Entidades sinalizadas encontradas
- Resultados finais de análise

### DEBUG
Detalhes técnicos para troubleshooting:
- Parâmetros de requisições
- Cache hits/misses
- Processamento de nós no BFS
- Parsing de transações

### WARNING
Situações que requerem atenção:
- Rate limiting atingido
- Limite de endereços processados
- Erros em nós específicos

### ERROR
Falhas que impedem operações:
- Transações não encontradas
- Falhas de API
- Erros de parsing

## Logs por Componente

### 1. BlockchairProvider ([blockchair.py](../app/providers/blockchair.py))

#### Requisições HTTP
```
INFO: [Blockchair API] GET https://api.blockchair.com/ethereum/dashboards/transaction/{hash}
DEBUG: [Blockchair API] Query params: {...}
DEBUG: [Blockchair API] Attempt 1/3 - Request #42
INFO: [Blockchair API] ✓ Success - Status 200
DEBUG: [Blockchair API] Response data keys: ['data', 'context']
```

#### Rate Limiting
```
DEBUG: [Blockchair API] Rate limiting: waiting 0.100s before next request
WARNING: [Blockchair API] Rate limit hit (429) - Retry after: 60s
INFO: [Blockchair API] Waiting 60.00s before retry 2/3
```

#### Timeout e Retries
```
WARNING: [Blockchair API] Request timeout after 30s
INFO: [Blockchair API] Retrying after timeout - waiting 2.00s
ERROR: [Blockchair API] Timeout error after 3 attempts
```

#### Circuit Breaker
```
INFO: [Circuit Breaker] State change: CLOSED -> HALF_OPEN (testing recovery)
ERROR: [Circuit Breaker] State change: HALF_OPEN -> OPEN after 5 failures
INFO: [Circuit Breaker] State change: OPEN -> CLOSED (recovered)
```

#### Transações
```
INFO: [Blockchair] Fetching transaction 0x5c504ed432cb... on ethereum
DEBUG: [Blockchair] API path: ethereum/dashboards/transaction/0x5c504ed432cb...
DEBUG: [Blockchair] Transaction data received - type: ACCOUNT
DEBUG: [Blockchair] Parsing Account-based transaction for ethereum
INFO: [Blockchair] ✓ Account transaction parsed - from: 0x742d35cc... to: 0x169ad600... value: 1.50000000, internal txs: 2
```

Para transações UTXO:
```
DEBUG: [Blockchair] Parsing UTXO transaction - hash: 3e5e7c2b45df...
DEBUG: [Blockchair] Found 2 inputs
DEBUG: [Blockchair] Found 3 outputs
INFO: [Blockchair] ✓ UTXO transaction parsed - 2 inputs, 3 outputs, value: 0.05000000 BTC
```

#### Metadados de Endereço
```
INFO: [Blockchair] Fetching address metadata for 0x742d35cc6634... on ethereum
DEBUG: [Blockchair] API path: ethereum/dashboards/address/0x742d35cc6634...
INFO: [Blockchair] ✓ Address metadata retrieved - balance: 15.75, tx_count: 234, tags: 1
```

#### Health Check
```
INFO: [Blockchair] Performing health check...
INFO: [Blockchair] ✓ Health check passed - Circuit breaker: CLOSED, Requests: 127
```

### 2. TransactionTracerService ([tracer.py](../app/services/tracer.py))

#### Análise Completa
```
INFO: [Tracer] Starting risk analysis for tx 0x5c504ed432cb... on ethereum (depth: 3)
INFO: [Tracer] ✓ Cache hit for risk report: 0x5c504ed432cb...
```

Ou sem cache:
```
DEBUG: [Tracer] Fetching initial transaction 0x5c504ed432cb...
INFO: [Tracer] ✓ Initial transaction fetched - Type: ACCOUNT
DEBUG: [Tracer] Found 1 source addresses
INFO: [Tracer] Starting BFS traversal - Queue size: 1, Max depth: 3
```

#### BFS Traversal
```
DEBUG: [Tracer BFS] Starting traversal - Initial queue size: 1
DEBUG: [Tracer BFS] Processing batch at depth 0 - 1 nodes
DEBUG: [Tracer BFS] Processing batch at depth 1 - 3 nodes
DEBUG: [Tracer BFS] Processing batch at depth 2 - 7 nodes
```

#### Processamento de Nós
```
DEBUG: [Tracer Node] Processing 0x742d35cc6634... at depth 1
DEBUG: [Tracer Node] Address 0x742d35cc6634... has tags: ['EXCHANGE']
INFO: [Tracer Node] ⚠ Flagged entity found: 0x742d35cc6634... (tags: 1, contribution: 15.50)
DEBUG: [Tracer Node] Skipping further tracing - definitive tag found
```

#### Cache
```
DEBUG: [Tracer Cache] Transaction cache hit: 0x5c504ed432cb...
DEBUG: [Tracer Cache] Transaction cache miss - fetching from provider: 0x7d3e9b8a...
DEBUG: [Tracer Cache] Address metadata in-memory cache hit: 0x742d35cc...
DEBUG: [Tracer Cache] Address metadata persistent cache hit: 0x169ad600...
DEBUG: [Tracer Cache] Address metadata cache miss - fetching from provider: 0x8f2a1b3c...
```

#### Resultado Final
```
INFO: [Tracer] BFS complete - Addresses: 15, Transactions: 12, API calls: 8
DEBUG: [Tracer] Flagged entities: 2, Circular paths: 0, Clustering: 0.125
DEBUG: [Tracer] Calculating advanced risk score...
INFO: [Tracer] ✓ Analysis complete - Risk: 35.5 (MEDIUM), Flagged: 2
```

## Monitoramento em Produção

### Railway Logs
No Railway, você verá logs completos como:

```
2026-01-23 21:46:53 INFO: [Tracer] Starting risk analysis for tx 0x5c504ed432cb... on ethereum (depth: 3)
2026-01-23 21:46:53 INFO: [Blockchair] Fetching transaction 0x5c504ed432cb... on ethereum
2026-01-23 21:46:53 INFO: [Blockchair API] GET https://api.blockchair.com/ethereum/dashboards/transaction/0x5c504ed432cb...
2026-01-23 21:46:53 DEBUG: [Blockchair API] Attempt 1/3 - Request #1
2026-01-23 21:46:54 INFO: [Blockchair API] ✓ Success - Status 200
2026-01-23 21:46:54 DEBUG: [Blockchair] Transaction data received - type: ACCOUNT
2026-01-23 21:46:54 INFO: [Blockchair] ✓ Account transaction parsed - from: 0x742d35cc... to: 0x169ad600... value: 1.50000000, internal txs: 0
2026-01-23 21:46:54 INFO: [Tracer] ✓ Initial transaction fetched - Type: ACCOUNT
2026-01-23 21:46:54 DEBUG: [Tracer] Found 1 source addresses
2026-01-23 21:46:54 INFO: [Tracer] Starting BFS traversal - Queue size: 1, Max depth: 3
...
2026-01-23 21:46:57 INFO: [Tracer] ✓ Analysis complete - Risk: 35.5 (MEDIUM), Flagged: 2
```

### Verificar Chamadas de API

Para verificar se a API do Blockchair foi chamada, procure por:

1. **Requisições HTTP**:
   ```
   [Blockchair API] GET https://api.blockchair.com/...
   ```

2. **Contador de Requisições**:
   ```
   [Blockchair API] Attempt 1/3 - Request #{número}
   ```

3. **Respostas de Sucesso**:
   ```
   [Blockchair API] ✓ Success - Status 200
   ```

4. **Contador de API Calls no Tracer**:
   ```
   [Tracer] BFS complete - ... API calls: {número}
   ```

## Configuração de Log Level

Para ajustar o nível de logs, configure a variável de ambiente no Railway:

```bash
LOG_LEVEL=DEBUG  # Para logs detalhados
LOG_LEVEL=INFO   # Para logs padrão (recomendado)
LOG_LEVEL=WARNING # Apenas avisos e erros
```

## Troubleshooting

### Problema: "Não vejo logs de API"
**Possíveis causas**:
- Cache está sendo usado (veja `[Tracer Cache] ... cache hit`)
- Log level está em WARNING ou superior
- API não está sendo chamada devido a erros anteriores

**Solução**: Procure por logs de cache ou aumente o log level para DEBUG

### Problema: "Muitas chamadas de API"
**Indício nos logs**:
```
WARNING: [Blockchair API] Rate limit hit (429)
```

**Solução**: Ajuste `RATE_LIMIT_PER_SECOND` ou adicione uma API key válida

### Problema: "Circuit breaker OPEN"
**Indício nos logs**:
```
ERROR: [Circuit Breaker] State change: ... -> OPEN after 5 failures
```

**Solução**: Verifique a conectividade com o Blockchair ou se a API key é válida

## Análise de Performance

Com os logs você pode:

1. **Medir cache hit rate**:
   ```
   Cache hits / Total requests = eficiência do cache
   ```

2. **Identificar gargalos**:
   - Timestamps entre logs mostram onde há delays
   - Procure por delays em `Rate limiting: waiting`

3. **Monitorar uso de API**:
   - Conte `[Blockchair API] GET` para ver requisições reais
   - Compare com `API calls: {n}` no final da análise

4. **Detectar problemas de qualidade**:
   - Muitos `Flagged entity found` pode indicar rede suspeita
   - `Circular path detected` indica ciclos de lavagem
   - `High clustering detected` sugere redes de mixagem

## Próximos Passos

Para análise ainda mais avançada, considere:

1. **Exportar logs para ferramentas de análise**:
   - Railway -> Datadog/New Relic
   - Agregação de métricas
   - Alertas automáticos

2. **Dashboards customizados**:
   - Taxa de sucesso de API
   - Tempo médio de análise
   - Distribuição de risk scores

3. **Auditoria de conformidade**:
   - Logs completos de quem analisou o quê
   - Rastreamento de decisões de risco
   - Evidências para reguladores
