#!/usr/bin/env bash
# ==============================================================================
# Script: bootstrap.sh
# Descripción: Orquestador automatizado de extremo a extremo para levantar o
#              destruir el entorno local (Terraform + Kind + ArgoCD + Monitoring)
# Uso: ./scripts/bootstrap.sh [up|down|status]
# ==============================================================================

# Modo estricto de Bash:
# -e: Salir inmediatamente si un comando falla
# -u: Tratar variables no definidas como error
# -o pipefail: Capturar fallos en cualquier punto de una tubería (pipe)
set -euo pipefail

# --- Colores y formato para logs ---
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # Sin color

# --- Directorios base (independiente desde dónde se llame el script) ---
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly TF_DIR="${REPO_ROOT}/terraform/environments/local"

# --- Funciones de Logging ---
log_info()    { echo -e "${BLUE}[INFO] $(date +'%H:%M:%S')${NC} - $*"; }
log_success() { echo -e "${GREEN}[OK]   $(date +'%H:%M:%S')${NC} - $*"; }
log_warn()    { echo -e "${YELLOW}[WARN] $(date +'%H:%M:%S')${NC} - $*"; }
log_error()   { echo -e "${RED}[ERR]  $(date +'%H:%M:%S')${NC} - $*" >&2; }

# --- 1. Verificación de prerrequisitos ---
check_prerequisites() {
    log_info "Verificando herramientas necesarias en el sistema..."
    local tools=("docker" "terraform" "kubectl" "helm" "kind")

    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "La herramienta '$tool' no está instalada o no está en el PATH."
            exit 1
        fi
    done

    if ! docker info &> /dev/null; then
        log_error "El demonio de Docker no está corriendo. Inícialo antes de continuar."
        exit 1
    fi

    log_success "Todos los prerrequisitos están instalados y Docker está activo."
}

# --- 2. Aprovisionamiento de Infraestructura con Terraform ---
provision_infra() {
    log_info "Iniciando aprovisionamiento del clúster Kind con Terraform..."
    
    # Si la estructura está directamente en /terraform en vez de /environments/local, ajusta la ruta automáticamente
    local target_tf_dir="$TF_DIR"
    if [[ ! -d "$target_tf_dir" ]]; then
        target_tf_dir="${REPO_ROOT}/terraform"
    fi

    pushd "$target_tf_dir" > /dev/null
    terraform init -upgrade
    terraform apply -auto-approve
    popd > /dev/null

    log_info "Esperando a que todos los nodos de Kubernetes estén en estado Ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=180s
    log_success "Clúster de Kubernetes aprovisionado y nodos listos."
}

# --- 3. Despliegue de ArgoCD (GitOps) ---
deploy_argocd() {
    log_info "Desplegando ArgoCD en el clúster..."

    if ! kubectl get namespace argocd &> /dev/null; then
        kubectl create namespace argocd
    fi

    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

    log_info "Esperando a que el servidor de ArgoCD esté disponible (puede tardar 1-2 min)..."
    kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

    if [[ -f "${REPO_ROOT}/gitops/argocd/application.yaml" ]]; then
        log_info "Aplicando manifiesto GitOps para devops-api..."
        kubectl apply -f "${REPO_ROOT}/gitops/argocd/application.yaml"
    else
        log_warn "No se encontró gitops/argocd/application.yaml, omitiendo creación de Application."
    fi

    log_success "ArgoCD desplegado y configurado correctamente."
}

# --- 4. Despliegue del Stack de Observabilidad (Prometheus & Grafana) ---
deploy_monitoring() {
    log_info "Configurando repositorio Helm de prometheus-community..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
    helm repo update

    if ! helm status monitoring -n monitoring &> /dev/null; then
        log_info "Instalando kube-prometheus-stack en el namespace 'monitoring'..."
        helm install monitoring prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --create-namespace \
            --set grafana.adminPassword="admin" \
            --wait \
            --timeout 5m
    else
        log_info "El release 'monitoring' ya existe en el clúster. Omitiendo instalación."
    fi

    # Aplicar ServiceMonitor y Alertas si existen en las rutas del proyecto
    for manifest in "${REPO_ROOT}/monitoring/servicemonitor.yaml" \
                    "${REPO_ROOT}/helm/templates/servicemonitor.yaml" \
                    "${REPO_ROOT}/monitoring/alerts/api-rules.yaml"; do
        if [[ -f "$manifest" ]]; then
            log_info "Aplicando manifiesto de observabilidad: $(basename "$manifest")"
            kubectl apply -f "$manifest"
        fi
    done

    log_success "Stack de observabilidad activo."
}

# --- 5. Resumen final y extracción de credenciales ---
print_summary() {
    local argo_pass=""
    argo_pass=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d || echo "No disponible aún")

    echo ""
    echo -e "${GREEN}======================================================================${NC}"
    echo -e "${GREEN} 🚀 PLATAFORMA DEVOPS DESPLEGADA CON ÉXITO ${NC}"
    echo -e "${GREEN}======================================================================${NC}"
    echo -e "Credenciales de acceso:"
    echo -e "  • ${YELLOW}ArgoCD${NC}  -> Usuario: admin | Password: ${argo_pass}"
    echo -e "  • ${YELLOW}Grafana${NC} -> Usuario: admin | Password: admin"
    echo ""
    echo -e "Comandos rápidos de Port-Forward:"
    echo -e "  kubectl port-forward svc/argocd-server -n argocd 8080:443 &"
    echo -e "  kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80 &"
    echo -e "  kubectl port-forward svc/devops-api -n default 8000:80 &"
    echo -e "${GREEN}======================================================================${NC}"
}

# --- 6. Destrucción limpia del entorno ---
teardown_environment() {
    log_warn "Destruyendo el clúster y limpiando el entorno local..."
    local target_tf_dir="$TF_DIR"
    if [[ ! -d "$target_tf_dir" ]]; then
        target_tf_dir="${REPO_ROOT}/terraform"
    fi

    pushd "$target_tf_dir" > /dev/null
    terraform destroy -auto-approve
    popd > /dev/null

    log_success "Infraestructura destruida correctamente."
}

# --- Punto de entrada principal (Main) ---
main() {
    local action="${1:-up}"

    case "$action" in
        up)
            check_prerequisites
            provision_infra
            deploy_argocd
            deploy_monitoring
            print_summary
            ;;
        down)
            teardown_environment
            ;;
        status)
            kubectl get nodes
            echo "---"
            kubectl get pods -A
            ;;
        *)
            echo "Uso: $0 {up|down|status}"
            exit 1
            ;;
    esac
}

main "$@"