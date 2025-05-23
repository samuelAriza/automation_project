# Gestión y Tipificación de Casos Estudiantiles - EAFIT

Este proyecto implementa una solución híbrida para la gestión de casos estudiantiles en la Universidad EAFIT, integrando un **asistente virtual** desarrollado con Microsoft Bot Framework y una **aplicación administrativa** construida con **Power Apps**, ambos conectados a una lista centralizada de **SharePoint** para el almacenamiento y gestión de los datos.

---

## 📌 Componentes del Proyecto

### 🤖 1. Bot de Microsoft Teams

El bot se encarga de:
- Atender solicitudes de estudiantes relacionadas con casos académicos, financieros, técnicos y administrativos.
- Proporcionar soluciones automatizadas o escalamiento cuando sea necesario.
- Registrar las interacciones y actualizaciones directamente en SharePoint.

#### Archivos relevantes:
- `bot.py`: Contiene la clase `EchoBot` con toda la lógica de diálogos, prompts, validaciones y casos.
- `sharepoint_helper.py`: Encapsula la conexión con SharePoint Online a través de Microsoft Graph API.
- `app.py`: Define el servidor `aiohttp` para exponer el bot mediante endpoint `/api/messages`.

### 🧩 2. Aplicación Power Apps

PowerApp es utilizada por asesores administrativos para:
- Visualizar, filtrar y editar casos estudiantiles.
- Validar datos ingresados por estudiantes.
- Asignar responsables y realizar seguimiento a los casos.

#### Ubicación:
- La configuración de PowerApps se encuentra en la carpeta `PowerApp/` bajo el archivo `power_apps.txt`.

---

## 🗃️ Modelo de Datos (SharePoint)

Se usa una lista de SharePoint con los siguientes campos relevantes:

- `Title`: ID del estudiante
- `CorreoInstitucional`, `Nombre`, `Apellido`, `Carrera`, `Semestre`
- `TipoDeCaso`, `SubtipoDeCaso`, `Descripción`, `FechaSolicitud`
- `Estado`, `Urgencia`, `AsignadoA`, `Notas`, `FechaSeguimiento`
- `EnlaceReuniónVirtual`, `IDInteracciónBot`, `RequiereEscalamiento`

Estos campos son manejados tanto por el bot como por Power Apps para mantener una única fuente de verdad.

---

## ⚙️ Instalación y Ejecución del Bot
```env
APP_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
APP_PASSWORD=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
SHAREPOINT_SITE_ID=xxx
SHAREPOINT_LIST_ID=xxx

Instala las dependencias:
pip install -r requirements.txt

Ejecuta el servidor del bot:
python app.py

Expón tu servidor con ngrok para recibir mensajes desde Microsoft Teams:
ngrok http 3978

Actualiza NGROK_URL en app.py con la URL generada.
```

🧪 Tecnologías Utilizadas
- Microsoft Bot Framework SDK v4
- SharePoint + Microsoft Graph API
- Microsoft Power Apps
- Python 3.9+
- aiohttp
- MSAL (Microsoft Authentication Library)

🛠️ Funcionalidades Clave
- Procesamiento de múltiples tipos y subtipos de casos.
- Validaciones condicionales (ej. semestre < 6 para cambio de pensum).
- Registro automático de interacciones en SharePoint.
- GUI intuitiva para administradores en Power Apps.
- Escalamiento automatizado con enlaces de reunión.

👥 Créditos
Este proyecto fue desarrollado como parte de la asignatura Sistemas de Información en la Universidad EAFIT por Samuel Andrés Ariza Gómez y Andrés Vélez Rendón, con el objetivo de modernizar los canales de atención estudiantil utilizando herramientas de la nube de Microsoft.

📂 Estructura del Proyecto
```
.
├── app.py                   # Servidor del bot con aiohttp
├── bot.py                   # Lógica del bot con Microsoft Bot Framework
├── sharepoint_helper.py     # Acceso a datos con Microsoft Graph API
├── requirements.txt         # Dependencias de Python
├── PowerApp/
│   └── power_apps.txt       # Descripción técnica de la Power App
└── README.md
