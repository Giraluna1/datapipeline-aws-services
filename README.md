# Energy Data Lake Pipeline

Arquitectura por capas (Medallion): landing → bronze → silver → gold, con gobierno en Lake Formation, orquestación nativa en AWS Glue (sin EventBridge) y carga a Redshift desde la zona procesada.

## Arquitectura
- Capas S3: landing, bronze, silver, gold, glue-assets, archive.
- Esquema de particiones: year/month/day en bronze, silver y gold.
- Catálogo: Glue Data Catalog con database por entorno; crawlers por capa.
- Orquestación: Glue Workflow + Triggers (SCHEDULED y CONDICIONALES).
- DWH: carga Gold → Redshift mediante COPY Parquet con Redshift Data API.

## Región y nombres de buckets
- Región: se define en `infrastructure/environments/<env>.tfvars` con `aws_region`. Ejemplo: `us-east-1` (US East - N. Virginia).
- Nombres de buckets: se generan automáticamente en el módulo S3 como:
  `<project_name>-s3-<layer>-<environment>-<storage_class_suffix>`
  Ejemplos en `dev` con `project_name=energy`:
  - landing: `energy-s3-landing-dev-standard`
  - bronze: `energy-s3-bronze-dev-standard`
  - silver: `energy-s3-silver-dev-standard`
  - gold: `energy-s3-gold-dev-standard`
  - glue-assets: `energy-s3-glue-assets-dev-standard`

## Orquestación (sin EventBridge)
- Se usa el orquestador nativo de Glue:
  - Workflow: `energy-workflow-<env>`.
  - Trigger programado (`SCHEDULED`): inicia Bronze con `var.glue_cron_expression`.
  - Triggers condicionales: Silver tras Bronze, Gold tras Silver, Redshift tras Gold.
  - Crawlers condicionales: se disparan después de cada etapa (bronze/silver/gold).
- Configura la periodicidad en `glue_cron_expression` dentro del tfvars del entorno.

## Catálogo automático y Lake Formation
- Glue Crawlers detectan esquemas y particiones automáticamente en landing/bronze/silver/gold.
- Lake Formation:
  - Se registran los buckets de cada capa como recursos de LF.
  - Se otorga `DATA_LOCATION_ACCESS` al rol de Glue.
  - Define `lf_admin_arns` en tfvars para establecer administradores del lago de datos.
  - Para consumidores (Athena/otros), concede permisos SELECT/Describe en base/tablas según sea necesario.

## Procesos
- Bronze (landing → bronze):
  - Lectura: `landing/{proveedores,clientes,transacciones}` (CSV con header).
  - Normalización/tipado básico (transacciones tipa kWh, precio y fecha).
  - Escritura: Parquet particionado en `bronze/<dataset>/year=YYYY/month=MM/day=DD/`.
- Silver (bronze → gold):
  - Lectura: `bronze/transacciones/`.
  - Curado: escribe `gold/transacciones_curated/` manteniendo el esquema de negocio (ver `data/sample` como referencia) en Parquet particionado.
  - Agregaciones: total_kwh (sum), avg_precio_kwh (avg) por tipo_energia, ciudad, fecha_transaccion.
  - Escritura del agregado: `gold/transacciones_agg/` en Parquet particionado.
  - Curado adicional: si existen, copia y tipa `bronze/proveedores/` → `gold/proveedores/` y `bronze/clientes/` → `gold/clientes/` en Parquet particionado.
- Gold → Redshift:
  - Job dedicado que ejecuta `COPY` desde `gold/transacciones_agg/` con formato Parquet usando Redshift Data API e IAM Role.

## Despliegue
1. Edita `infrastructure/environments/<env>.tfvars` (ver sección Variables).
2. Ejecuta:
   - `./scripts/deploy.sh dev plan`
   - `./scripts/deploy.sh dev apply`
3. Carga CSVs en `landing/proveedores/`, `landing/clientes/`, `landing/transacciones/`.
4. El Workflow de Glue correrá según `glue_cron_expression`. También puedes iniciarlo manualmente.

## Exportar resultados desde Redshift a CSV
- La capa golden en Redshift refleja los esquemas del sample en `data/sample`.
- Script para exportar CSV local desde Redshift:
  - Variables de entorno: `AWS_REGION`, `REDSHIFT_CLUSTER_ID`, `REDSHIFT_DATABASE`, `REDSHIFT_DB_USER`, `REDSHIFT_SECRET_ARN`, `EXPORT_OUTPUT_DIR`.
  - Ejecuta: `python redshift/export_to_csv.py` → genera `exports/transacciones.csv` y `exports/proveedores.csv`.
  - Ubicación: `redshift/export_to_csv.py`.

## Exportar resultados desde Athena a CSV (UNLOAD)
- Tarea de Silver: `athena_export.py` ejecuta UNLOAD de vistas lógicas a S3:
  - `v_clientes` → `s3://<gold>/exports/v_clientes/`
  - `v_ventas` → `s3://<gold>/exports/v_ventas/`
  - `v_compras` → `s3://<gold>/exports/v_compras/`
- Depende de que `athena_views.py` haya creado las vistas y del `GLUE_DATABASE`/`ATHENA_OUTPUT` configurados.

## Consultas con Athena
- Define:
  - `GLUE_DATABASE` = `${project_name}_db_${environment}` (creada por Terraform).
  - `ATHENA_OUTPUT` = ruta S3 para resultados (definida en tfvars).
- Ejecuta el script de ejemplo: `python athena/athena_queries.py`.

## Permisos y políticas (IAM)
- Rol de Glue (servicio): lectura/escritura en S3 por capas, acceso al Glue Catalog (DB/Tables/Partitions), integración con Lake Formation, escribir logs en CloudWatch, consultar con Athena y usar Secrets Manager, y Redshift Data API.
- Lake Formation: `DATA_LOCATION_ACCESS` al rol de Glue y administración del lago mediante `lf_admin_arns`.
- Compartición: para consumo (Athena u otros), otorga permisos SELECT/Describe en la base/tablas desde Lake Formation.

## Variables por entorno (tfvars)
- `aws_region` (e.g., `us-east-1`)
- `project_name`, `environment`
- `common_tags`
- `storage_tier_defaults`, `lifecycle_days`
- `secret_names = { app_secret = "<arn-o-nombre-del-secret>" }`
- `redshift = { secret_arn, iam_role_arn, database, db_user, cluster_id }`
- `athena_output_s3 = "s3://<bucket>/athena-results/<env>/"` (puedes usar el bucket glue-assets)
- `glue_cron_expression` (expresión CRON de Glue)
- `lf_admin_arns = ["arn:aws:iam::<account>:role/<role-admin>", ...]`
- `deployer_service_account_name` = nombre siguiendo el patrón `sa-<proyecto>-<ambiente>-<recurso>-<zona>-<temp>`

## Archivo tfvars para QA (lab)
- Se incluye `infrastructure/environments/qa.tfvars` con `environment = "lab"`.
- Ejemplos de nombres siguiendo los patrones pedidos:
  - Service account: `sa-energy-lab-deployer-us-east-1-temp`.
  - Secret Redshift/usuario: `db_user-energy-lab-redshift-us-east-1-temp`.

## Rutas de entrada/salida
- Entrada: `landing/{proveedores,clientes,transacciones}/` (CSV).
- Bronze: `bronze/<dataset>/` (Parquet particionado).
- Silver: `silver/transacciones/` (intermedio si se requiere).
- Gold: `gold/transacciones/` (Parquet particionado, listo para consulta y DWH).

## Ubicación del código
- Infraestructura: `infrastructure/terraform/**`
- Jobs de Glue:
  - Bronze: `processes/bronze/energy_ingestion/tasks/bronze_ingestion.py`
  - Silver: `processes/silver/energy_processing/tasks/silver_processing.py`
  - DWH: `processes/dwh/redshift_load/tasks/redshift_load.py`

## Notas
- No se usa EventBridge ni Lambda para programar; todo se orquesta con Glue Workflow + Triggers.
- `awswrangler` se inyecta en los jobs con `--additional-python-modules`.
