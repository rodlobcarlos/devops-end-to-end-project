# Cloud-Native DevOps & SRE Showcase Platform

[![Continuous Integration and security](https://github.com/rodlobcarlos/devops-end-to-end-project/actions/workflows/ci.yml/badge.svg)](https://github.com/rodlobcarlos/devops-end-to-end-project/actions/workflows/ci.yml)
![Security: Trivy](https://img.shields.io/badge/Security-Trivy%20Scanned-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Kind-326ce5?logo=kubernetes&logoColor=white)
![IaC](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)
![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange?logo=argo&logoColor=white)
![Observability](https://img.shields.io/badge/Observability-Prometheus%20%26%20Grafana-F46800?logo=prometheus&logoColor=white)

Proyecto monorepo integral que reproduce a coste cero un ciclo de vida de desarrollo de software (SDLC) completo con enfoque Cloud-Native, DevSecOps y observabilidad SRE.

---

## 🏛 Arquitectura del Sistema

```mermaid
graph TD
    A[Desarrollador / Git Push] -->|Pull Request / Push| B[GitHub Actions]
    subgraph CI / DevSecOps
        B --> C[Linters: Ruff & Hadolint]
        C --> D[Tests: Pytest]
        D --> E[Vulnerability Scan: Trivy]
        E --> F[Container Build & Push: GHCR]
    end
    subgraph IaC
        G[Terraform] -->|Aprovisionamiento| H[Cluster Kind 3 Nodos]
    end
    subgraph GitOps
        F -.-> I[ArgoCD]
        I -->|Auto-Sync & Reconcile| J[Kubernetes Cluster]
    end
    subgraph Workload & SRE
        J --> K[FastAPI Pods: Multi-stage Distroless]
        K --> L[HPA: CPU & Memory Auto-scaling]
        K -->|Scrape /metrics| M[Prometheus Operator]
        M --> N[Grafana RED Dashboard]
        M --> O[PrometheusRules Alerting]
    end
