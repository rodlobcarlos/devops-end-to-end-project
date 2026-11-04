#!/bin/bash
echo "Generando tráfico sobre la API..."

while true; do
  # Petición exitosa
  curl -s http://localhost:8000/items > /dev/null
  
  # Petición a healthz
  curl -s http://localhost:8000/healthz > /dev/null

  # Petición con error simulado (si tienes configurado parámetro de error)
  curl -s "http://localhost:8000/items?fail=true" > /dev/null

  sleep 0.2
done