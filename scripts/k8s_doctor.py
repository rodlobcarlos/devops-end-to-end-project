#!/usr/bin/env python3
import json
import subprocess
import sys
import urllib.request

NAMESPACES = ["default", "argocd", "monitoring"]
IGNORE_ALERTS = {
    "Watchdog",
    "KubeControllerManagerInstanceUnreachable",
    "KubeSchedulerInstanceUnreachable",
    "KubeProxyInstanceUnreachable",
    "etcdMembersDown",
    "etcdInsufficientMembers",
    "TargetDown",
}


def check_pods() -> bool:
    all_ok = True
    for ns in NAMESPACES:
        out = subprocess.check_output(["kubectl", "get", "pods", "-n", ns, "-o", "json"])
        pods = json.loads(out).get("items", [])
        for pod in pods:
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase")
            if phase != "Running":
                print(f"❌ [{ns}] {name} está en estado {phase}")
                all_ok = False
    if all_ok:
        print("✅ Todos los pods están en estado Running.")
    return all_ok


def check_alerts() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:9090/api/v1/alerts", timeout=3) as res:
            alerts = json.loads(res.read()).get("data", {}).get("alerts", [])
    except Exception:
        print("⚠️ No se pudo conectar a Prometheus en localhost:9090 (revisa el port-forward).")
        return True

    firing = [
        a["labels"]["alertname"]
        for a in alerts
        if a["state"] == "firing" and a["labels"]["alertname"] not in IGNORE_ALERTS
    ]

    if firing:
        print(f"🔥 Alertas críticas activas: {', '.join(firing)}")
        return False

    print("✅ Sin alertas críticas en Prometheus.")
    return True


if __name__ == "__main__":
    print("--- 🩺 Chequeo de Salud del Clúster ---")
    pods_ok = check_pods()
    alerts_ok = check_alerts()

    if pods_ok and alerts_ok:
        print("Resultado: SALUDABLE ✅")
        sys.exit(0)
    else:
        print("Resultado: REQUIERE ATENCIÓN ❌")
        sys.exit(1)