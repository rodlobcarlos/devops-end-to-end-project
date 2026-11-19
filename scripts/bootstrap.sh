#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

ACTION="${1:-up}"
TF_DIR="terraform/enviroments/local"

if [[ "$ACTION" == "up" ]]; then
  echo "1. Comprobando herramientas..."
  for cmd in docker terraform kubectl helm kind; do
    command -v "$cmd" >/dev/null || { echo "Error: falta instalar $cmd"; exit 1; }
  done

  echo "2. Creando clúster con Terraform..."
  cd "$TF_DIR" && terraform init && terraform apply -auto-approve && cd - >/dev/null
  kubectl wait --for=condition=Ready nodes --all --timeout=180s

  echo "3. Instalando ArgoCD..."
  kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply --server-side --force-conflicts -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
  kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
  kubectl apply -f gitops/argocd/application.yaml

  echo "4. Instalando Prometheus y Grafana..."
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
  helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
    --namespace monitoring --create-namespace --set grafana.adminPassword="admin" --wait

  kubectl apply -f monitoring/alerts/api-rules.yaml
  kubectl apply -f helm/templates/servicemonitor.yaml

  PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
  echo "✅ Todo listo! Usuario ArgoCD: admin | Password: $PASS"

elif [[ "$ACTION" == "down" ]]; then
  echo "Destruyendo entorno..."
  cd "$TF_DIR" && terraform destroy -auto-approve && cd - >/dev/null
  echo "✅ Entorno eliminado."

else
  echo "Uso: ./scripts/bootstrap.sh [up|down]"
  exit 1
fi