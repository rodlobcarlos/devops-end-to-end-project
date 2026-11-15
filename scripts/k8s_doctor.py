#!/usr/bin/env python3
"""
k8s_doctor.py - Herramienta CLI de auditoría SRE y diagnóstico de salud
para el clúster Kubernetes (Kind) y alertas de Prometheus.

Uso:
    python3 scripts/k8s_doctor.py
    python3 scripts/k8s_doctor.py --json
    python3 scripts/k8s_doctor.py --prom-url http://localhost:9090
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

NAMESPACES_TO_CHECK = ["default", "argocd", "monitoring"]
MAX_RESTARTS_THRESHOLD = 3


def run_kubectl_json(args: list[str]) -> dict:
    """Ejecuta un comando kubectl con salida JSON y devuelve el diccionario parseado."""
    cmd = ["kubectl", *args, "-o", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        return {"error": exc.stderr.strip() or str(exc)}
    except FileNotFoundError:
        return {"error": "El binario 'kubectl' no está instalado o no se encuentra en el PATH."}


def check_nodes() -> list[dict]:
    """Verifica el estado Ready de todos los nodos del clúster."""
    data = run_kubectl_json(["get", "nodes"])
    if "error" in data:
        return [{"name": "cluster-connection", "healthy": False, "reason": data["error"]}]

    nodes_report = []
    for item in data.get("items", []):
        name = item["metadata"]["name"]
        conditions = item.get("status", {}).get("conditions", [])
        ready_cond = next((c for c in conditions if c["type"] == "Ready"), None)
        is_ready = ready_cond is not None and ready_cond["status"] == "True"
        nodes_report.append({
            "name": name,
            "healthy": is_ready,
            "status": "Ready" if is_ready else "NotReady",
        })
    return nodes_report


def check_pods(namespaces: list[str]) -> list[dict]:
    """Audita el estado y reinicios de los pods en los namespaces indicados."""
    issues = []
    for ns in namespaces:
        data = run_kubectl_json(["get", "pods", "-n", ns])
        if "error" in data:
            issues.append({"namespace": ns, "pod": "N/A", "issue": data["error"]})
            continue

        for item in data.get("items", []):
            pod_name = item["metadata"]["name"]
            phase = item.get("status", {}).get("phase", "Unknown")

            if phase not in ("Running", "Succeeded"):
                issues.append({
                    "namespace": ns,
                    "pod": pod_name,
                    "issue": f"Fase anómala: {phase}",
                })

            for cs in item.get("status", {}).get("containerStatuses", []):
                restarts = cs.get("restartCount", 0)
                if restarts >= MAX_RESTARTS_THRESHOLD:
                    issues.append({
                        "namespace": ns,
                        "pod": pod_name,
                        "issue": f"Reinicios elevados en contenedor '{cs['name']}': {restarts}",
                    })
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting and waiting.get("reason") in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                    issues.append({
                        "namespace": ns,
                        "pod": pod_name,
                        "issue": f"Contenedor bloqueado: {waiting.get('reason')}",
                    })
    return issues


def check_prometheus_alerts(prom_url: str) -> dict:
    """Consulta la API de alertas de Prometheus para detectar alertas Firing o Pending."""
    endpoint = f"{prom_url.rstrip('/')}/api/v1/alerts"
    try:
        req = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            alerts = payload.get("data", {}).get("alerts", [])
            active = [
                {
                    "name": a.get("labels", {}).get("alertname", "Unknown"),
                    "state": a.get("state", "unknown"),
                    "severity": a.get("labels", {}).get("severity", "none"),
                    "summary": a.get("annotations", {}).get("summary", ""),
                }
                for a in alerts
                if a.get("state") in ("firing", "pending")
            ]
            return {"reachable": True, "active_alerts": active}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "reachable": False,
            "error": f"No se pudo conectar a Prometheus en {prom_url} ({exc}). ¿Está activo el port-forward?",
            "active_alerts": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría de salud SRE para clúster Kubernetes y Prometheus.")
    parser.add_argument("--prom-url", default="http://localhost:9090", help="URL base de Prometheus")
    parser.add_argument("--json", action="store_true", help="Imprimir el diagnóstico en formato JSON")
    args = parser.parse_args()

    nodes = check_nodes()
    pod_issues = check_pods(NAMESPACES_TO_CHECK)
    prom_status = check_prometheus_alerts(args.prom_url)

    has_critical_issues = (
        any(not n["healthy"] for n in nodes)
        or len(pod_issues) > 0
        or any(a["state"] == "firing" for a in prom_status.get("active_alerts", []))
    )

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_healthy": not has_critical_issues,
        "nodes": nodes,
        "pod_issues": pod_issues,
        "prometheus": prom_status,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("\n=== 🩺 K8S & SRE HEALTH DOCTOR ===")
        print(f"Fecha (UTC): {report['timestamp']}\n")

        print("1. Estado de Nodos:")
        for n in nodes:
            icon = "✅" if n["healthy"] else "❌"
            print(f"   {icon} {n['name']}: {n.get('status', n.get('reason'))}")

        print("\n2. Auditoría de Pods (default, argocd, monitoring):")
        if not pod_issues:
            print("   ✅ Todos los pods están Running y sin reinicios anómalos.")
        else:
            for issue in pod_issues:
                print(f"   ❌ [{issue['namespace']}] {issue['pod']} -> {issue['issue']}")

        print("\n3. Estado de Alertas en Prometheus:")
        if not prom_status["reachable"]:
            print(f"   ⚠️  {prom_status['error']}")
        elif not prom_status["active_alerts"]:
            print("   ✅ Sin alertas activas (Firing/Pending).")
        else:
            for alert in prom_status["active_alerts"]:
                icon = "🔥" if alert["state"] == "firing" else "⏳"
                print(f"   {icon} {alert['name']} [{alert['state'].upper()}] - {alert['summary']}")

        print("\n==================================")
        print("Resultado global:", "SALUDABLE ✅" if not has_critical_issues else "REQUIERE ATENCIÓN ❌")

    return 1 if has_critical_issues else 0


if __name__ == "__main__":
    sys.exit(main())