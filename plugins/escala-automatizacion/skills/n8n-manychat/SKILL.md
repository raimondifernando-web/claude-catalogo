---
name: n8n-manychat
description: Expert guidance for integrating ManyChat with N8N using the n8n-nodes-manychat community node. Use when building automations that connect N8N with ManyChat, managing subscribers, triggering flows, handling tags or custom fields, or automating WhatsApp Business communications via ManyChat from N8N.
sync: cowork
---

# N8N + ManyChat Integration

Guía completa para automatizar ManyChat desde N8N usando el community node `n8n-nodes-manychat`.

---

## Instalación del Community Node

En N8N, ir a: **Settings → Community Nodes → Install**

Escribir el nombre del paquete:
```
n8n-nodes-manychat
```

Versión mínima de N8N requerida: 2.0.0

---

## Autenticación

1. En ManyChat: **Settings → API → Generate Token**
2. En N8N: crear credencial tipo **API Token (Bearer Token)**
3. Pegar el token en el campo correspondiente

El token tiene formato: `PAGE_ID:TOKEN_STRING`

---

## Recursos y Operaciones Disponibles

### Resource: `page` — Gestión de la cuenta/página

| Operación | Descripción |
|-----------|-------------|
| Get page info | Info básica de la página conectada |
| Get tags | Listar todos los tags existentes |
| Create tag | Crear un nuevo tag |
| Remove tag (by ID / by name) | Eliminar tags |
| Get custom fields | Listar campos personalizados de subscribers |
| Create custom field | Crear nuevo campo personalizado |
| Get bot fields | Obtener variables globales del bot |
| Create bot field | Crear variable global |
| Set bot field (by ID / by name) | Actualizar variable individual |
| Set multiple bot fields | Actualizar múltiples variables a la vez |
| Get flows | Listar flows disponibles para trigger |
| Get growth tools | Listar growth tools activos |
| Get one-time notification topics | Temas de notificación única |

### Resource: `subscriber` — Gestión de contactos

| Operación | Descripción |
|-----------|-------------|
| Get subscriber info | Datos completos de un subscriber por ID |
| Get by user ref | Buscar por referencia externa |
| Search (name / custom field / system field) | Buscar subscribers por criterios |
| Create unified subscriber | Crear subscriber nuevo |
| Update subscriber | Actualizar datos de un subscriber |
| Add tag (by ID / by name) | Agregar tag a un subscriber |
| Remove tag (by ID / by name) | Quitar tag de un subscriber |
| Verify signed request | Verificar solicitudes firmadas de ManyChat |

---

## Patrones de Automatización Clave

### 1. Trigger flow cuando ocurre un evento externo

```
Trigger (Webhook/Schedule) → Buscar subscriber en ManyChat → Trigger flow al subscriber
```

**Caso de uso**: Cuando se cierra una venta en Odoo → enviar secuencia de bienvenida por WhatsApp

```json
// Nodo ManyChat - Send Flow
{
  "resource": "subscriber",
  "operation": "sendFlow",
  "subscriberId": "{{ $json.manychat_id }}",
  "flowId": "content20240101120000:flow_id_aqui"
}
```

### 2. Sincronizar datos externos con subscriber

```
Trigger → Buscar subscriber → Actualizar custom fields → (opcional) Trigger confirmación
```

**Caso de uso**: Cliente completa formulario Netlify → actualizar campos en ManyChat

```json
// Nodo ManyChat - Update Subscriber
{
  "resource": "subscriber",
  "operation": "update",
  "subscriberId": "{{ $json.id }}",
  "customFields": {
    "campo_estado": "interesado",
    "campo_fuente": "{{ $json.utm_source }}"
  }
}
```

### 3. Segmentar por tags automáticamente

```
Trigger → Evaluar condición (IF node) → Agregar tag A o tag B → Log
```

**Caso de uso**: Según ROAS de campaña → tagear subscribers como "alta-conversión" o "nurturing"

### 4. Webhook de ManyChat → N8N (sentido inverso)

ManyChat puede enviar datos a N8N cuando un usuario interactúa:

1. En N8N: crear nodo **Webhook** → copiar la URL
2. En ManyChat: usar **HTTP Request Action** dentro de un flow
3. POST de ManyChat → N8N → procesamiento → (opcional) respuesta a ManyChat

**Payload típico que envía ManyChat:**
```json
{
  "id": "subscriber_id",
  "first_name": "Ana",
  "last_name": "García",
  "phone": "+5491112345678",
  "custom_fields": {
    "interes": "productos_b2b"
  }
}
```

---

## Integración con WhatsApp Business

ManyChat actúa como capa oficial de WhatsApp Business API. La integración N8N → ManyChat → WhatsApp funciona así:

- **N8N no habla directamente con WhatsApp** → siempre va por ManyChat
- Los flows de ManyChat pueden ser de tipo WhatsApp
- Para enviar mensajes de WhatsApp desde N8N, hay que triggear un flow de WhatsApp en ManyChat

**Restricciones importantes de WhatsApp Business:**
- Solo se pueden iniciar conversaciones con templates pre-aprobados (si han pasado más de 24hs desde el último mensaje del usuario)
- Dentro de la ventana de 24hs, se puede enviar cualquier contenido
- ManyChat gestiona esto automáticamente al triggear flows

---

## Patrones para un e-commerce

### Flujo: Lead nuevo en Meta Ads → Welcome sequence WhatsApp

```
Meta Ads Lead webhook → N8N recibe datos → 
Buscar/crear subscriber en ManyChat → 
Agregar tag "lead-meta-ads" → 
Trigger flow "bienvenida-whatsapp"
```

### Flujo: Seguimiento post-cotización

```
Schedule (daily 9am) → Query CRM leads con status "cotizado" → 
Para cada lead sin respuesta → Verificar si tiene subscriber en ManyChat → 
Si sí: trigger flow "seguimiento-cotizacion" → Log resultado
```

### Flujo: Notificación de ROAS al equipo

```
Schedule (semanal lunes 8am) → Calcular ROAS de la semana → 
IF ROAS < objetivo → Enviar alerta por WhatsApp al equipo via ManyChat →
Crear nota de resumen en la herramienta de gestión que use el equipo
```

---

## Errores Comunes y Soluciones

| Error | Causa probable | Solución |
|-------|---------------|----------|
| 401 Unauthorized | Token inválido o expirado | Regenerar token en ManyChat Settings → API |
| 404 Not Found | Subscriber ID o Flow ID incorrecto | Verificar IDs con operación de búsqueda primero |
| 429 Rate Limit | Demasiadas requests simultáneas | Agregar nodo "Wait" entre iteraciones (500ms) |
| Flow no disponible | Flow no está publicado en ManyChat | Publicar el flow antes de triggearlo desde N8N |

---

## Obtener IDs necesarios

**Flow ID**: En ManyChat, abrir el flow → la URL contiene el ID (ej: `flow_id_abc123`)

**Subscriber ID**: Usar operación "Search subscriber" antes de operar sobre un subscriber específico

**Tag ID**: Usar operación "Get tags" de la página para obtener todos los IDs

---

## Referencias

- GitHub del node: https://github.com/xAL95/n8n-nodes-manychat
- ManyChat API docs: https://api.manychat.com/swagger
- N8N community nodes docs: https://docs.n8n.io/integrations/community-nodes/
