#!/bin/bash
# ANT-12 VPS Commands — ejecutar en /root/ants-infra/supabase-ants/
# Copiar y pegar uno por uno en el VPS

# 1. Ir al directorio correcto
cd /root/ants-infra/supabase-ants

# 2. Descargar script de reparacion
curl -fsSL "https://raw.githubusercontent.com/mhgutie/ants-ai-gateway/feat/ant-12-supabase-network-hardening/scripts/repair_compose_ports.py" -o /tmp/repair_compose_ports.py

# 3. Instalar PyYAML
pip3 install pyyaml -q

# 4. Dry-run para ver que va a hacer
python3 /tmp/repair_compose_ports.py --file docker-compose.yml --dry-run

# 5. Aplicar reparacion (quita 5432/6543, restaura otros ports:, valida YAML)
python3 /tmp/repair_compose_ports.py --file docker-compose.yml

# 6. Verificar YAML valido
docker compose config --quiet && echo "YAML_OK"

# 7. Reiniciar pooler con nueva config
docker compose up -d supabase-pooler supavisor

# 8. Verificar: 5432 y 6543 deben DESAPARECER de ss
sleep 5 && ss -ltnp | egrep '(:5432|:6543|:8000|:8443|:8010)' && docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "pooler|kong|gateway|NAME"

# 9. Migracion 002 (workflow_runs + latency_ms en model_usage)
curl -fsSL "https://raw.githubusercontent.com/mhgutie/ants-ai-gateway/feat/ant-12-supabase-network-hardening/sql/migrations/002_add_workflow_runs.sql" -o /tmp/002_migration.sql && docker exec -i supabase-db psql -U postgres -d postgres < /tmp/002_migration.sql && echo "MIGRATION_002_OK"

# 10. Verificar tablas
docker exec supabase-db psql -U postgres -d postgres -c "\dt public.*" | grep -E "workflow_runs|model_usage|projects|specs|tasks"
