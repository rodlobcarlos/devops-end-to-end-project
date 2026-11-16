#!/usr/bin/env python3
import re
import sys

if len(sys.argv) != 2:
    print("Uso: python3 scripts/update_gitops_tag.py <nuevo_tag>")
    sys.exit(1)

new_tag = sys.argv[1]
values_path = "gitops/helm/devops-api/values.yaml"

with open(values_path, "r") as f:
    content = f.read()

updated = re.sub(r'(tag:\s*)"[^"]+"', f'\\1"{new_tag}"', content)

with open(values_path, "w") as f:
    f.write(updated)

print(f"✅ Tag actualizado a '{new_tag}' en {values_path}")