```markdown

\# Incident Postmortem: Cascading Degradation in Order Processing Due to Downstream Gateway Timeout



\*\*Incident Reference:\*\* INC-20260929-01  

\*\*Date:\*\* 2026-09-29  

\*\*Status:\*\* Resolved  

\*\*Severity:\*\* SEV-2 (Major Service Degradation)  

\*\*Authors / On-Call SRE:\*\* Sanjiv Jadhav  



```



\---



\## 1. Executive Summary



On September 29, 2026, between 19:34:10 IST and 19:35:12 IST, the Order Service (`order-service`) experienced severe performance degradation during peak load testing. The service error rate climbed to \*\*38.68%\*\*, while tail latency (\*\*p99\*\*) breached defined Service Level Objectives (SLOs), spiking from a baseline of \*\*346.39 ms\*\* to \*\*2,051.66 ms\*\*. Overall platform throughput dropped by \*\*74.65%\*\* (from 37.76 req/s to 9.57 req/s) due to synchronous thread pool exhaustion.



The root cause was identified as intermittent network stalls and thread sleep conditions injected into the downstream Payment Service (`payment-service`), triggering HTTP request timeouts that cascaded upstream. The incident was mitigated within \*\*12 seconds\*\* by triggering a zero-downtime rolling update with corrected environment configurations. Permanent architectural remediation includes implementing an in-process circuit breaker and exponential backoff retry policies.



\---



\## 2. Impact on Metrics \& SLOs



| Metric | Target / SLO | Baseline (Pre-Incident) | Under Incident (Degraded) | Post-Mitigation (Recovered) |

| --- | --- | --- | --- | --- |

| \*\*Availability (Success Rate)\*\* | $\\ge 99.0\\%$ | \*\*100.0%\*\* (0.0% errors) | \*\*61.32%\*\* (38.68% errors) | \*\*100.0%\*\* (0.0% errors) |

| \*\*Throughput\*\* | Baseline capacity | \*\*37.76 req/s\*\* | \*\*9.57 req/s\*\* (-74.6%) | \*\*38.81 req/s\*\* |

| \*\*p50 Latency (Median)\*\* | $< 250\\text{ ms}$ | \*\*201.81 ms\*\* | \*\*76.95 ms\*\* | \*\*200.50 ms\*\* |

| \*\*p95 Latency\*\* | $< 300\\text{ ms}$ | \*\*301.03 ms\*\* | \*\*2,028.07 ms\*\* | \*\*297.60 ms\*\* |

| \*\*p99 Tail Latency\*\* | $< 350\\text{ ms}$ | \*\*346.39 ms\*\* | \*\*2,051.66 ms\*\* | \*\*308.71 ms\*\* |

| \*\*Failed Requests\*\* | $0$ | $0$ | \*\*229 / 592 requests\*\* | $0$ |

| \*\*Mean Time to Recovery (MTTR)\*\* | $< 60\\text{ s}$ | — | — | \*\*12 seconds\*\* |



\*Note: The anomalous drop in median latency ($p50$ falling to 76.95 ms) was caused by client-side fast-failing once internal connection pools became fully saturated.\*



\---



\## 3. Incident Timeline (All times in IST)



\* \*\*19:33:00\*\* — Baseline stress run completed successfully: 2,272 requests delivered at 37.76 req/s with 0 failures; HPA autoscaled `order-service` pods from 2 to 4 replicas upon crossing the 50% CPU threshold.

\* \*\*19:34:10\*\* — Chaos scenario initiated: `CHAOS\_MODE=true` environment variable deployed to `deployment/payment-deployment`.

\* \*\*19:34:25\*\* — Prometheus alert rules triggered: `HighHttpErrorRate (> 5%)` fired across the cluster.

\* \*\*19:34:40\*\* — Grafana RED dashboards indicated severe thread contention: Order Service active client threads blocked waiting on downstream responses exceeding 2.0s timeouts. Total throughput collapsed to 9.57 req/s.

\* \*\*19:35:12\*\* — Load test finished: 229 out of 592 requests returned HTTP 500/502/504 errors (38.68% error rate). Tail latency registered at 2,051.66 ms.

\* \*\*19:36:00\*\* — Mitigation initiated: Rollback deployment triggered via `kubectl set env deployment/payment-deployment CHAOS\_MODE="false"`.

\* \*\*19:36:12\*\* — Rollout completed with zero dropped pods (`maxSurge: 1`, `maxUnavailable: 0`). Full system recovery validated at 12 seconds MTTR.

\* \*\*19:37:15\*\* — Post-incident validation run executed: 2,335 requests processed at 38.81 req/s with 0 errors and p99 latency normalized to 308.71 ms.



\---



\## 4. Root Cause Analysis (5 Whys)



1\. \*\*Why did the Order Service return HTTP 502/504 status codes to end users?\*\*

The synchronous HTTP client calls from `order-service` to `payment-service:5001/process-payment` exceeded the client timeout threshold of 2.0 seconds.

2\. \*\*Why were requests to `payment-service` timing out?\*\*

The Payment Service was running with an active chaos configuration that injected synthetic 2.0-second sleeps and internal 500 errors into \~40% of transactions.

3\. \*\*Why did throughput across the entire platform collapse by \~75%?\*\*

Because the Order Service handled calls synchronously without concurrency bounding. Incoming threads were held waiting for downstream socket responses, exhausting the web server's available worker pool.

4\. \*\*Why did the Order Service continue forwarding traffic to a failing downstream dependency?\*\*

The Order Service lacked an automated mechanism (Circuit Breaker) to track failure rates and short-circuit calls when the dependency was confirmed degraded.

5\. \*\*Why was there no fast fallback?\*\*

The application architecture lacked localized degradation handling or queue-based asynchronous decoupling between checkout placement and payment execution.



\---



\## 5. What Went Well vs. What Went Wrong



\### What Went Well



\* \*\*Kubernetes Orchestration:\*\* Deployments with `maxSurge: 1` and `maxUnavailable: 0` enabled an in-place configuration rollout with zero dropped connections during recovery.

\* \*\*Observability:\*\* Prometheus real-time scraping and Grafana histogram buckets immediately surfaced the exact divergence between p50 and p99 latencies.

\* \*\*HPA Dynamics:\*\* The Horizontal Pod Autoscaler correctly detected CPU threshold increases and scaled replicas up from 2 to 4 pods under sustained concurrency.

\* \*\*Fast MTTR:\*\* System returned to full operational performance within 12 seconds of deploying the mitigation.



\### What Went Wrong



\* \*\*Cascading Failure:\*\* A fault in a downstream component degraded upstream frontend capacity, impacting completely valid user orders.

\* \*\*Lack of Circuit Breaking:\*\* The Order Service exhausted worker threads waiting for requests that were guaranteed to fail.

\* \*\*Missing Retry Backoff:\*\* No exponential backoff with jitter was configured, causing transient spikes to manifest as hard client errors.



\---



\## 6. Action Items \& Remediation Plan



| Item | Action | Type | Owner | Target Date | Status |

| --- | --- | --- | --- | --- | --- |

| \*\*ACT-01\*\* | Implement client-side \*\*Circuit Breaker\*\* (trip threshold: 3 consecutive failures, cooldown: 5s) to fail fast with HTTP 503 instead of tying up worker threads. | Architecture | Sanjiv Jadhav | 2026-10-02 | In Progress |

| \*\*ACT-02\*\* | Add \*\*Exponential Backoff with Full Jitter\*\* on idempotent downstream requests to absorb transient network blips. | Code | Sanjiv Jadhav | 2026-10-03 | In Progress |

| \*\*ACT-03\*\* | Configure Alertmanager integration to page on-call when `p99 > 500ms` for $> 2$ consecutive evaluation periods. | Observability | Sanjiv Jadhav | 2026-10-05 | Pending |

| \*\*ACT-04\*\* | Evaluate migration of payment processing from synchronous HTTP REST to an asynchronous message broker (e.g., RabbitMQ / Kafka) with dead-letter queuing. | Architecture | Team | 2026-10-15 | Proposed |



```



```

