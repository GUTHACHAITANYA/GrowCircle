# Architectural Evaluation: Kafka and Kubernetes Assessment

**Product**: GrowCircle ("Farm to everyone, full circle")  
**Evaluation Date**: October 2026  
**Status**: Adopt Serverless Containers (AWS App Runner / ECS Fargate) & Redis Streams; Defer Kubernetes and Apache Kafka until measurable bottleneck thresholds are met.

---

## 1. Executive Summary

As mandated by the Phase 6 engineering requirements, we conducted a rigorous architectural assessment of whether **Kubernetes (K8s)** and **Apache Kafka** are justified for GrowCircle’s pilot deployment in the AWS Mumbai (`ap-south-1`) region.

Our empirical benchmarks establish that:
1. **Measured Throughput**: GrowCircle’s FastAPI modular monolith with PostgreSQL (PostGIS) and Redis achieves **527.13 requests/second** with **27.19 ms median latency (p50)** and **122.51 ms 95th-percentile latency (p95)** on concurrent stress tests.
2. **Current Workload**: Across the four Andhra Pradesh pilot districts (Guntur, NTR, Kurnool, Annamayya), expected peak concurrent traffic is approximately **150 to 500 requests/second** across all five doors (IVR callbacks, WhatsApp webhooks, and Web).
3. **Conclusion**: Introducing Kubernetes or Kafka at this phase introduces massive operational complexity, substantial cloud infrastructure cost, and severe maintenance overhead **without delivering measurable performance improvements**.

---

## 2. Evaluation Matrix

| Criterion | Current Stack (FastAPI + Redis + App Runner / Fargate) | Proposed Alternative: Kubernetes (EKS) | Proposed Alternative: Apache Kafka (MSK) |
| :--- | :--- | :--- | :--- |
| **Operational Overhead** | Zero cluster ops; automated OS patching; container auto-restart | High: Control plane upgrades, etcd maintenance, CNI/ingress plugins, node pool drain | High: Cluster sizing, partition rebalancing, consumer lag tuning, ZooKeeper/KRaft quorum |
| **Monthly Fixed Cost** | ~₹8,000 – ₹18,000 / month (Pay-per-request + serverless containers) | ~₹45,000 – ₹85,000 / month (EKS cluster fee + minimum 3 node groups) | ~₹35,000 – ₹60,000 / month (MSK minimum 3-broker cluster) |
| **Autoscaling Latency** | 30–60 seconds (zero to N container scaling) | 2–5 minutes (cluster autoscaler node provisioning) | Manual partition repartitioning; broker scaling |
| **Team Cognitive Load** | Low: Standard Dockerfile and single repository CI/CD | High: Helm charts, Kustomize, RBAC, NetworkPolicies, ServiceMeshes | High: Schema registry, serialization formats, partition keys |
| **Suitability for Pilot** | **Optimal** | **Over-engineered** | **Over-engineered** |

---

## 3. Deep-Dive: Why Kubernetes is Deferred

### 3.1 What We Gained Without Kubernetes
- **Zero Control Plane Maintenance**: AWS App Runner / ECS Fargate manages the underlying EC2 instances, virtualization, kernel security patches, and load balancing automatically.
- **Direct Terraform Infrastructure**: As configured in `infra/terraform/app.tf`, the container scales dynamically from 2 to 10 instances based on active concurrency (`max_concurrency = 100`).
- **Rapid Incident Recovery**: Fast deployment rollbacks via ECR tag pointer changes without complex ingress/mesh routing failures.

### 3.2 Measurable Thresholds for Future Kubernetes Adoption
We will only consider migrating to Kubernetes if any of the following empirical metrics are sustained for 30 consecutive days:
1. **Microservice Splitting**: Team scales beyond 4 independent engineering squads, requiring $> 25$ independent microservices with distinct deployment lifecycles.
2. **GPU Hardware Slicing**: Custom deep learning speech inference workloads (e.g. self-hosted Whisper/Bhashini STT models) requiring dedicated GPU node pools with fractional GPU time-slicing.
3. **Multi-Cloud Hybrid Deployments**: Requirements from state governments or agricultural co-ops to run instances on sovereign on-premise hardware alongside cloud deployments.

---

## 4. Deep-Dive: Why Apache Kafka is Deferred

### 4.1 Redis Streams & Celery vs Kafka
- **Event Volume**: Pilot operations generate ~50 to 200 events/second during peak 7:00 AM mandi price distribution and morning harvest logging.
- **Throughput Capability**: Redis Streams handles up to **50,000 messages/second** with sub-millisecond latencies on a standard `cache.t4g.medium` instance.
- **Simplicity**: Redis already serves as the session cache, token-bucket rate limiter, and Celery task broker. Introducing Kafka introduces a redundant distributed storage engine.

### 4.2 Measurable Thresholds for Future Kafka Adoption
We will only evaluate migrating to Kafka if any of the following conditions occur:
1. **Event Ingestion Velocity**: Sustained event throughput exceeds **25,000 messages/second** across pan-India mandi arrival streams.
2. **Long-Term Event Replay**: Business requirement for $> 30$-day immutable event log retention where new consumers need to replay state transitions from historical checkpoints.
3. **Complex Event Stream Processing**: Multi-stream stateful joins (e.g., Flink/Kafka Streams) correlating GPS telemetry from 5,000+ simultaneous transit trucks with weather radar data.

---

## 5. Architectural Decision
**Proceed with AWS Mumbai (`ap-south-1`) deployment using Terraform, RDS PostgreSQL (PostGIS), ElastiCache Redis, and App Runner serverless containers.**
Re-evaluate this decision after 6 months of live pilot operations or upon reaching 100,000 active farmers.
