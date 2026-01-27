# poly

Script sencillo para interactuar con Polymarket desde local y/o un VPS.

## Objetivo
Automatizar tareas básicas (consultas, señales y ejecución) de forma clara y reproducible.

## Estado
En construcción.

## Configuración

### 1. Credenciales
Necesitas las Claves de API (Project Keys) desde tu [Perfil de Builder en Polymarket](https://polymarket.com/settings?tab=builder).

1.  Copia el archivo de ejemplo:
    ```bash
    cp .env.example .env
    ```
2.  Rellena `POLY_API_KEY`, `POLY_API_SECRET`, y `POLY_API_PASSPHRASE`.
3.  (Opcional) `POLY_PRIVATE_KEY`: Solo es necesaria para firmar y enviar órdenes. Si no se configura, el script se ejecutará en modo "Solo Lectura".

### 2. Ejecutar en Local
**Prerrequisitos:** Python 3.10+

1. Crear y activar el entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar el script:
   ```bash
   python poly_client.py
   ```

### 3. Ejecutar con Docker (Recomendado para VPS)
**Prerrequisitos:** Docker y Docker Compose

1. Construir e iniciar en segundo plano:
   ```bash
   docker-compose up --build -d
   ```
2. Ver logs en tiempo real:
   ```bash
   docker-compose logs -f
   ```
3. Detener los contenedores:
   ```bash
   docker-compose down
   ```

## Solución de Problemas
- **Error: `Non-hexadecimal digit found`:** Asegúrate de que `POLY_PRIVATE_KEY` en tu archivo `.env` esté vacío (si no la vas a usar) o sea una cadena hexagonal válida que comience por `0x`. No dejes el texto de ejemplo `your_private_key`.
