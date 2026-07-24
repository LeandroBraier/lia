#!/bin/bash
echo "🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker)..."
docker-compose up -d --build
echo "✅ Servidor iniciado en http://localhost:8502"
open http://localhost:8502
