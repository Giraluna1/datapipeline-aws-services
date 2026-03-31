# Energy Data Lake Pipeline — Descripción detallada

Este repositorio contiene una solución completa para un Data Lake en AWS orientado a procesar archivos CSV (proveedores, clientes, transacciones) y producir datasets analíticos listos para consumo en Athena y Redshift. La solución sigue una arquitectura por capas (Medallion: landing → bronze → silver → gold) y está diseñada para que tú solamente edites los scripts Python (Glue jobs) en `processes/<capa>/...` y el CI se encargue de sincronizarlos al bucket de Glue.

(El README completo con guía de despliegue y configuración ya viene incluido en el repo. Revisa la sección "Configurar permisos y políticas" para instrucciones IAM.)
