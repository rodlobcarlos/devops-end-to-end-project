#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

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


def check_pods() -> tuple[bool, int, list[str]]:
    all_ok = True
    total_pods = 0
    failed_pods = []

    for ns in NAMESPACES:
        out = subprocess.check_output(["kubectl", "get", "pods", "-n", ns, "-o", "json"])
        pods = json.loads(out).get("items", [])
        total_pods += len(pods)
        for pod in pods:
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase")
            if phase != "Running":
                msg = f"[{ns}] {name} está en estado {phase}"
                print(f"❌ {msg}")
                failed_pods.append(msg)
                all_ok = False

    if all_ok:
        print("✅ Todos los pods están en estado Running.")
    return all_ok, total_pods, failed_pods


def check_alerts() -> tuple[bool, bool, list[str]]:
    try:
        with urllib.request.urlopen("http://localhost:9090/api/v1/alerts", timeout=3) as res:
            alerts = json.loads(res.read()).get("data", {}).get("alerts", [])
    except Exception:
        print("⚠️ No se pudo conectar a Prometheus en localhost:9090 (revisa el port-forward).")
        return True, False, []

    firing = [
        a["labels"]["alertname"]
        for a in alerts
        if a["state"] == "firing" and a["labels"]["alertname"] not in IGNORE_ALERTS
    ]

    if firing:
        print(f"🔥 Alertas críticas activas: {', '.join(firing)}")
        return False, True, firing

    print("✅ Sin alertas críticas en Prometheus.")
    return True, True, []


def save_html(healthy: bool, total_pods: int, failed_pods: list[str], prom_ok: bool, firing: list[str]) -> None:
    nodes_out = subprocess.check_output(["kubectl", "get", "nodes", "-o", "json"])
    nodes = json.loads(nodes_out).get("items", [])
    ready_nodes = sum(
        1 for n in nodes
        if any(c["type"] == "Ready" and c["status"] == "True" for c in n.get("status", {}).get("conditions", []))
    )

    bloque_pods = (
        "<p class='ok'>✅ Todos los pods están corriendo correctamente (Running).</p>"
        if not failed_pods
        else "<ul class='err'>" + "".join(f"<li>❌ {p}</li>" for p in failed_pods) + "</ul>"
    )

    if not prom_ok:
        bloque_alertas = "<p class='warn'>⚠️ No conectado a Prometheus en localhost:9090 (activa el port-forward).</p>"
    elif not firing:
        bloque_alertas = "<p class='ok'>✅ Ninguna alerta crítica activa.</p>"
    else:
        bloque_alertas = "<ul class='err'>" + "".join(f"<li>🔥 {a}</li>" for a in firing) + "</ul>"

    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    datos = {
        "{{COLOR}}": "#16a34a" if healthy else "#dc2626",
        "{{FECHA}}": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "{{ESTADO_GLOBAL}}": "SALUDABLE ✅" if healthy else "REQUIERE ATENCIÓN ❌",
        "{{N_NODOS}}": f"{ready_nodes}/{len(nodes)}",
        "{{N_PODS}}": str(total_pods),
        "{{N_ALERTAS}}": str(len(firing)),
        "{{BLOQUE_PODS}}": bloque_pods,
        "{{BLOQUE_ALERTAS}}": bloque_alertas,
    }
    for k, v in datos.items():
        html = html.replace(k, v)

    with open("cluster_report.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    print("--- 🩺 Chequeo de Salud del Clúster ---")
    pods_ok, total_pods, failed_pods = check_pods()
    alerts_ok, prom_ok, firing = check_alerts()
    healthy = pods_ok and alerts_ok

    save_html(healthy, total_pods, failed_pods, prom_ok, firing)

    import webbrowser
    webbrowser.open("cluster_report.html")
    
    if healthy:
        print("Resultado: SALUDABLE ✅ (Informe: cluster_report.html)")
        sys.exit(0)
    else:
        print("Resultado: REQUIERE ATENCIÓN ❌ (Informe: cluster_report.html)")
        sys.exit(1)