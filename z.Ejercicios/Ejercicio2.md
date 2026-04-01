# Ejercicio 2: Arquitectura AWS – Sistema de Recomendación de Compra/Venta de Dólares en Tiempo Real

## Supuestos

| # | Supuesto |
|---|----------|
| 1 | El modelo ya está entrenado y desplegado |
| 2 | El re-entrenamiento es offline/periódico, no en tiempo real |
| 3 | El precio del dólar lo consulta Lambda directamente a una API externa (ej: Fixer.io, XE API) antes de llamar a SageMaker |
| 4 | Un solo Lambda puede manejar los 3 pasos si el volumen es bajo (se puede partir después) |
| 5 | Los usuarios tienen una app móvil o web con la que interactúan con la plataforma |
| 6 | El canal de notificación principal es push notification vía app |

---

## Arquitectura Simplificada
┌─────────────────────────────────────────────────────────────┐
│                    INGESTA                                   │
│                                                             │
│  [App usuario]  [API precio dólar externa]                  │
│       │                  │                                  │
│       └────────┬─────────┘                                  │
│                ▼                                            │
│         [API Gateway]                                       │
│                │                                            │
│                ▼                                            │
│      [Kinesis Data Streams]   ← como Pub/Sub               │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│               PROCESAMIENTO + PREDICCIÓN                     │
│                                                             │
│          [AWS Lambda]         ← como Cloud Functions        │
│               │                                             │
│               ├── lee perfil usuario → [DynamoDB]           │
│               │                        (portafolio +        │
│               │                         historial)          │
│               │                                             │
│               └── llama modelo  → [SageMaker Endpoint]      │
│                                   (retorna: COMPRAR /       │
│                                    VENDER / NADA)           │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                 NOTIFICACIÓN                                 │
│                                                             │
│          [AWS Lambda]                                       │
│               │  si score > umbral                          │
│               ▼                                             │
│            [SNS]  → Push notification al usuario            │
└─────────────────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│            ALMACENAMIENTO (sin análisis por ahora)          │
│                                                             │
│   [Kinesis Firehose] → [S3]   ← todo queda guardado        │
│                                  para re-entrenar           │
│                                  el modelo después          │
└─────────────────────────────────────────────────────────────┘


---

## Servicios AWS utilizados

| Servicio | Para qué | Equivalente GCP |
|---|---|---|
| **API Gateway** | Recibir eventos de la app | Cloud Endpoints |
| **Kinesis Data Streams** | Cola de mensajes en tiempo real | Pub/Sub |
| **AWS Lambda** | Lógica: enriquecer + llamar modelo + notificar | Cloud Functions |
| **DynamoDB** | Perfil y portafolio del usuario | Firestore |
| **SageMaker Endpoint** | Servir el modelo ML | Vertex AI Endpoint |
| **SNS** | Enviar push notification | Firebase Cloud Messaging |
| **S3 + Kinesis Firehose** | Guardar todo para re-entrenamiento futuro | GCS |

---

## Flujo Narrativo

1. El usuario realiza una acción en la app (o se actualiza el precio del dólar)
2. **API Gateway** recibe el evento y lo publica en **Kinesis Data Streams**
3. **AWS Lambda** consume el stream, lee el perfil y portafolio del usuario desde **DynamoDB**
4. Lambda invoca el **SageMaker Endpoint** con los datos del usuario + precio actual
5. SageMaker retorna: `{ accion: "COMPRAR", score: 0.89 }`
6. Si `score > umbral` → Lambda dispara notificación vía **SNS** → Push al usuario
7. Todo el evento queda almacenado en **S3** vía **Kinesis Firehose** para re-entrenamiento futuro

---

## Escalabilidad futura (mejoras opcionales)

Si el volumen crece o el negocio lo requiere, se pueden agregar:

- **AWS Glue** → para ETL y feature engineering automatizado
- **Amazon Redshift** → Data Warehouse para análisis histórico
- **SageMaker Pipelines + Model Monitor** → MLOps: re-entrenamiento automático y detección de drift
- **Amazon QuickSight** → Dashboard de KPIs para el equipo de negocio
- **Amazon CloudWatch + X-Ray** → Observabilidad y trazabilidad end-to-end
