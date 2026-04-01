# Ejercicio 3 – Preguntas Generales

---
## 1. ¿Qué experiencias has tenido como ingeniero de datos en AWS? ¿Cuál ha sido el proyecto más retador y por qué?

Mi experiencia directa en AWS ha incluido dos flujos principales:

El primero fue un **ETL básico con S3 + Lambda + Athena**: Lambda Functions disparaban o 
complementaban partes del proceso, los datos transformados se almacenaban en **S3 en formato 
Parquet**, y **Athena** los consultaba directamente sobre S3 mediante SQL, sin Glue Data Catalog 
— una solución simple y serverless donde Athena infería o tenía el schema definido manualmente.

El segundo fue un **job de AWS Glue de S3 a Redshift**, con transformaciones escritas en 
**Python**, donde Glue se encargaba del procesamiento y la carga hacia Redshift como destino 
analítico final.

Sin embargo, mi fortaleza principal está en **GCP**, y considero que eso me da una ventaja 
importante: entender la **lógica detrás de cada servicio en la nube** hace que la curva de 
aprendizaje entre plataformas sea mucho más corta, ya que los patrones arquitectónicos se repiten.

En cuanto a proyectos retadores, he tenido dos que destacan especialmente:

**Proyecto 1 – Streaming de datos de robótica (GCP):**
Mensajes llegando **cada 5 segundos desde sensores de un robot**, en **formato Avro altamente 
anidado**, representando el heartbeat del robot. El reto fue el **desanidamiento de esa 
estructura compleja** para servir a dos equipos con necesidades distintas:
- Al **equipo de ML**: un dataset limpio y plano en **BigQuery**, alimentado desde **Vertex AI**, 
  para entrenar modelos de robótica.
- Al **equipo de hardware**: data relacional en **PostgreSQL**, con estructura optimizada para 
  consultas operativas.

Orquestar ese doble destino, garantizar la integridad del schema Avro y mantener la latencia 
baja fue lo que hizo este proyecto técnicamente muy exigente.

**Proyecto 2 – Flex Template de Dataflow con VPC Shared (GCP):**
Configurar un **Flex Template de Dataflow** para recibir datos desde un servidor **SFTP**, 
enrutando la conexión a través de un **VPC Shared** para cumplir restricciones de red corporativa, 
trayendo los archivos a **GCS** y luego transformándolos para almacenarlos en **PostgreSQL en 
Cloud SQL**. Adicionalmente, en este proyecto se implementó **Dataplex** (el servicio de Data 
Catalog y gobernanza de datos de GCP) para catalogar y gobernar los activos de datos del flujo.

El reto aquí fue la complejidad de la configuración de red con el VPC Shared, la parametrización 
del Flex Template para que fuera reutilizable, y la integración con Dataplex para dejar todo 
el lineage documentado.

---

## 2. ¿Qué estrategias has aplicado para crear los recursos necesarios en AWS y mantener una arquitectura y pipelines de datos?

Aunque mi experiencia directa en AWS está en crecimiento, las estrategias que aplico parten de buenas prácticas transversales a cualquier nube:

- **Infraestructura como código (IaC):** Definir los recursos con herramientas como **AWS CloudFormation** o **Terraform**, evitando la creación manual. Esto garantiza reproducibilidad, control de versiones y facilita el trabajo en equipo.
- **Ambientes separados:** Mantener entornos de desarrollo, staging y producción aislados, con permisos diferenciados por ambiente.
- **Principio de mínimo privilegio (IAM):** Cada servicio o pipeline debe tener únicamente los permisos que necesita. Nunca roles con acceso total.
- **Modularidad en los pipelines:** Construir los flujos por etapas independientes (ingesta, transformación, carga), de manera que un fallo no comprometa todo el proceso y sea fácil de depurar.
- **Monitoreo y alertas desde el inicio:** Configurar **CloudWatch** con alarmas sobre fallos, latencias o costos inesperados antes de llevar algo a producción.
- **Documentación del lineage de datos:** Saber de dónde viene cada dato, qué transformaciones tuvo y dónde está almacenado. En AWS, el **Glue Data Catalog** apoya esto de forma nativa.
- **Control de costos:** Revisar el sizing de los recursos (especialmente en Glue y Redshift) y usar clases de almacenamiento en S3 según la frecuencia de acceso.

---

## 3. ¿Qué consideraciones tomarías al decidir entre almacenar datos en Amazon S3, RDS o Redshift?

La decisión depende de varios factores clave:

| Consideración | Amazon S3 | Amazon RDS | Amazon Redshift |
|---|---|---|---|
| **Tipo de dato** | Cualquier formato (JSON, Parquet, CSV, Avro, imágenes, etc.) | Datos relacionales estructurados | Datos estructurados para análisis |
| **Uso principal** | Almacenamiento crudo, datalake, archivos | Transacciones operacionales (OLTP) | Análisis histórico y reportes (OLAP) |
| **Concurrencia** | Ilimitada en lectura, sin motor de consulta propio | Alta concurrencia transaccional, muchos usuarios simultáneos escribiendo/leyendo registros | Consultas analíticas pesadas, menor concurrencia pero sobre grandes volúmenes |
| **Formato requerido** | Flexible, el consumidor decide cómo leerlo | Filas y columnas relacionales (SQL estándar) | Columnar, optimizado para agregaciones y scans masivos |
| **Consumidor del dato** | Pipelines, Glue, Athena, aplicaciones de ML | Aplicaciones backend que necesitan lecturas/escrituras en tiempo real | Equipos de analítica, dashboards, reportes de negocio |
| **Costo** | Muy bajo por GB almacenado | Medio, depende del motor e instancia | Alto en cómputo, pero eficiente para queries analíticas |

**Regla práctica:**
- Si es un **dato crudo o en tránsito** → **S3**
- Si es el **backend de una aplicación** que necesita transacciones → **RDS**
- Si el equipo de **analítica o negocio** va a hacer consultas SQL sobre millones de registros → **Redshift**

En muchos proyectos los tres coexisten: S3 como datalake base, RDS para la capa operacional y Redshift para la capa analítica.

---

## 4. ¿Qué beneficios y desventajas ves al utilizar AWS Glue en comparación con Lambda o Step Functions para orquestación ETL?

### AWS Glue ✅
**Beneficios:**
- Todo en un solo lugar: catálogo de datos, ETL, orquestación y schedulers dentro del mismo servicio.
- **Autoescalado nativo** sobre Spark: no necesitas gestionar clústeres, Glue los administra.
- Soporte nativo de **Data Governance** a través del Glue Data Catalog (schemas, lineage).
- Los **Glue Workflows** permiten orquestar múltiples jobs con dependencias entre ellos.
- Muy **intuitivo para configurarse**, especialmente para perfiles de datos sin experiencia profunda en Spark.
- Conectores nativos con S3, Redshift, RDS, DynamoDB, entre otros.

**Desventajas:**
- **Costo elevado** para jobs pequeños o muy frecuentes (el mínimo de facturación por job puede ser costoso si el volumen no lo justifica).
- **Cold start** de los workers Spark: el arranque puede tardar varios minutos.
- Menos flexible para lógica muy personalizada o casos de uso que no son puramente ETL.
- Puede ser excesivo para transformaciones simples o de bajo volumen.

---

### AWS Lambda + Step Functions ⚡
**Beneficios:**
- **Muy bajo costo** para procesos ligeros, de corta duración y baja frecuencia.
- Sin cold start relevante para funciones pequeñas.
- Step Functions permite orquestar flujos complejos con estados, reintentos, condiciones y paralelismo con **control granular**.
- Ideal para **pipelines event-driven** (reacción a eventos de S3, Kinesis, etc.).

**Desventajas:**
- Lambda **no está diseñada para procesamiento de datos masivos**: tiene límite de 15 minutos de ejecución y memoria limitada.
- No tiene catálogo de datos ni data governance integrado; hay que construirlo aparte.
- Step Functions orquesta la ejecución, pero **no transforma datos por sí sola**: cada paso depende de lo que hagas dentro de Lambda u otro servicio.
- La configuración de flujos complejos puede volverse verbosa y difícil de mantener.

---

**Conclusión práctica:**
- Usa **Glue** cuando el volumen de datos es grande, necesitas Spark, quieres data catalog integrado o el proceso es un ETL clásico.
- Usa **Lambda + Step Functions** cuando el proceso es ligero, event-driven, necesitas reactividad inmediata o quieres control fino sobre cada paso del flujo.
- En proyectos maduros, **ambos conviven**: Lambda para eventos en tiempo real y Glue para procesamiento batch.

---

## 5. ¿Cómo garantizarías la integridad y seguridad de los datos de un datalake construido en Amazon S3?

### Organización por zonas

La base de una buena arquitectura de datalake está en separar los datos según el nivel de tratamiento que han recibido:

```
s3://datalake-bucket/
├── landing/       ← datos tal como llegan, formato original
├── raw/           ← datos estandarizados (Parquet/Avro/ORC), histórico preservado
├── curated/       ← datos limpios, validados, con calidad garantizada
├── refined/       ← datos agregados, enriquecidos, listos para consumo analítico
└── sandbox/       ← espacio aislado para experimentos y pruebas
```

| Zona | Descripción |
|---|---|
| **Landing** | Recibe los datos en su forma original sin ninguna modificación. Es el punto de entrada. |
| **Raw** | Datos crudos organizados y con formato estandarizado (ej: Parquet). Se mantiene el histórico completo. |
| **Curated** | Datos procesados, validados y con calidad garantizada. Esquemas consistentes y sin duplicados. |
| **Refined** | Datos agregados, combinados y enriquecidos. Listos para consumo por analítica o modelos de ML. |
| **Sandbox** | Espacio aislado para pruebas. No afecta las zonas productivas. Acceso restringido y controlado. |

---

### Seguridad e integridad

- **IAM + Bucket Policies:** Cada zona tiene permisos diferenciados. No todos los roles pueden escribir en todas las zonas. Por ejemplo, solo el pipeline de ingesta escribe en Landing; analítica solo lee desde Refined.
- **AWS KMS:** Cifrado en reposo para todos los buckets, con llaves administradas por el equipo de seguridad.
- **S3 Versioning:** Habilitado en zonas Raw y Curated para recuperar versiones anteriores ante errores de procesamiento.
- **S3 Object Lock:** En zonas como Raw, para garantizar inmutabilidad de los datos históricos (útil en contextos regulados como banca).
- **AWS Glue Data Catalog:** Registro centralizado de schemas, lo que previene escrituras con estructuras incorrectas.
- **AWS CloudTrail + S3 Access Logs:** Auditoría completa de quién accedió o modificó qué archivo y cuándo.
- **Amazon Macie:** Detección automática de datos sensibles (PII) almacenados en S3, crítico en contextos bancarios.
- **Lifecycle Policies:** Mover datos antiguos de Landing y Raw a S3 Glacier para reducir costos sin perder el histórico.