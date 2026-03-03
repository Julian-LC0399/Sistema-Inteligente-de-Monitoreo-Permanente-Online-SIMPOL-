# SIMPOL: Sistema Inteligente de Monitoreo Permanente Online 🏦

**SIMPOL** es la plataforma centralizada de monitoreo del **Banco Caroní**, diseñada para la vigilancia constante de la infraestructura tecnológica. Su objetivo es proporcionar visibilidad en tiempo real sobre el estado de los servidores y servicios críticos mediante la integración de telemetría local y externa.

## 🚀 Propósito del Proyecto
Este sistema permite a los analistas de infraestructura visualizar métricas de rendimiento, garantizando la continuidad operativa del banco a través de un panel de control intuitivo, seguro y profesional.

## 🛠️ Funcionalidades Core
- **Panel de Control (Dashboard):** Visualización de métricas de CPU y RAM.
- **Integración PRTG:** Conexión vía API con sensores específicos (ID: 2094) para datos de red.
- **Seguridad de Acceso:** Módulo de login con validación BINARY en MySQL.
- **Auditoría Automatizada:** Registro histórico de eventos y rendimiento en base de datos.
- **Interfaz Corporativa:** Diseño adaptado a la identidad visual del banco con indicadores de estado de conexión.

## 📦 Requisitos Técnicos
Para ejecutar **SIMPOL**, se requiere:
- **Python 3.x**
- **MySQL Server** (Base de datos: `monitoreo_banco`)
- **Librerías:** `streamlit`, `mysql-connector-python`, `pandas`, `psutil`, `requests`.