# Astroflora Backend

Sistema de ingesta de datos de sensores IoT para dispositivos Arduino/ESP32 construido con FastAPI. Proporciona recolecci�n de datos en tiempo real, streaming WebSocket y autenticaci�n de usuarios.

## =� Configuraci�n del Entorno de Desarrollo

### Requisitos Previos

- Python 3.8 o superior
- PostgreSQL 12 o superior
- Git

### 1. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate
```

### 2. Instalar Dependencias

```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# Verificar instalaci�n
pip list
```

### 3. Configuraci�n de Base de Datos

Crear un archivo `.env` en la ra�z del proyecto:

```bash
# Configuraci�n de base de datos
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=astroflora

# Autenticaci�n JWT
SECRET_KEY=tu_secret_key_super_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4. Inicializar Base de Datos

```bash
# Crear usuario administrador de prueba
python scripts/create_admin_user.py
```

### 5. Ejecutar Aplicaci�n

```bash
# Modo desarrollo con recarga autom�tica
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# La aplicaci�n estar� disponible en: http://localhost:8000
# Documentaci�n API: http://localhost:8000/docs
```

## >� Ejecutar Pruebas

```bash
# Ejecutar todas las pruebas
pytest

# Pruebas con cobertura
pytest --cov

# Pruebas verbose
pytest -v
```

## =� Est�ndares del Proyecto

### Estructura de C�digo

- **Principio de Responsabilidad �nica**: Cada m�dulo tiene una responsabilidad espec�fica
- **Arquitectura en Capas**: API � Services � Models � Database
- **Dependencias**: Uso de FastAPI Depends() para gesti�n de dependencias
- **Tipado**: Usar type hints en todas las funciones

### Convenciones de C�digo

- **Nomenclatura**: Snake_case para variables y funciones, PascalCase para clases
- **Documentaci�n**: Docstrings en espa�ol para funciones p�blicas
- **Imports**: Organizados en bloques (stdlib, third-party, local)
- **Async/Await**: Usar funciones as�ncronas para operaciones I/O

### Modelos de Datos

- **ORM Models** (`src/models/orm.py`): Representaci�n de base de datos
- **DTOs** (`src/models/dto.py`): Validaci�n y serializaci�n con Pydantic
- **UUIDs**: Usar UUID4 como primary keys para todos los modelos

## = Flujo de Trabajo Git

### Commits

**Formato de Commit Messages:**
```
tipo(scope): descripci�n breve

Descripci�n m�s detallada si es necesaria.

- Detalle 1
- Detalle 2
```

**Tipos permitidos:**
- `feat`: Nueva funcionalidad
- `fix`: Correcci�n de errores
- `refactor`: Refactorizaci�n de c�digo
- `docs`: Cambios en documentaci�n
- `test`: A�adir o modificar pruebas
- `chore`: Cambios en herramientas o configuraci�n

**Ejemplos:**
```bash
feat(sensors): add CO2 sensor data validation
fix(auth): resolve JWT token expiration issue
refactor(database): optimize sensor data queries
```

### Pull Requests

**Requisitos para PR:**

1. **Branch naming**: `feature/descripcion-breve` o `fix/descripcion-breve`
2. **Pruebas**: Todas las pruebas deben pasar (`pytest`)
3. **Code Review**: M�nimo 1 aprobaci�n requerida
4. **Sin conflictos**: Resolver conflictos con `main` antes del merge
5. **Documentaci�n**: Actualizar documentaci�n si es necesario

**Plantilla de PR:**
```markdown
## =� Descripci�n
Breve descripci�n de los cambios realizados.

## >� Pruebas
- [ ] Pruebas unitarias a�adidas/actualizadas
- [ ] Pruebas de integraci�n verificadas
- [ ] Pruebas manuales realizadas

## =� Documentaci�n
- [ ] README actualizado si es necesario
- [ ] Comentarios de c�digo a�adidos
- [ ] CLAUDE.md actualizado si es necesario

##  Checklist
- [ ] C�digo sigue los est�ndares del proyecto
- [ ] No hay hardcoded secrets o passwords
- [ ] Variables de entorno documentadas
```

### Reglas de Escalaci�n

**Para cambios menores** (< 50 l�neas):
- 1 reviewer requerido
- Merge directo despu�s de aprobaci�n

**Para cambios medianos** (50-200 l�neas):
- 2 reviewers requeridos
- Discusi�n de arquitectura si es necesario

**Para cambios mayores** (> 200 l�neas):
- 2+ reviewers requeridos
- Discusi�n previa del dise�o
- Posible divisi�n en PRs m�s peque�os
- Consideraciones de performance y escalabilidad

**Para cambios cr�ticos** (seguridad, base de datos):
- Review obligatorio del tech lead
- Pruebas de regresi�n completas
- Plan de rollback documentado

## =� Monitoreo y Escalabilidad

### M�tricas Clave
- Latencia de endpoints API
- Conexiones WebSocket activas
- Throughput de ingesta de sensores
- Uso de memoria y CPU

### Estrategias de Escalaci�n
- **Horizontal**: Load balancer + m�ltiples instancias
- **Database**: Connection pooling y read replicas
- **Caching**: Redis para datos frecuentemente accedidos
- **Message Queue**: Para procesar datos de sensores as�ncronamente

### L�mites Actuales
- 1000 conexiones WebSocket concurrentes
- 10,000 eventos de sensores/minuto
- 100MB payload m�ximo por request

## = Seguridad

- **Autenticaci�n**: JWT con expiraci�n configurable
- **Validaci�n**: Pydantic para todos los inputs
- **Secrets**: Variables de entorno, nunca hardcoded
- **CORS**: Configurado solo para dominios permitidos

## =� Soporte

Para dudas sobre el proyecto:
1. Revisar documentaci�n en `/docs`
2. Consultar issues existentes en GitHub
3. Crear nuevo issue con etiquetas apropiadas

---

*Documentaci�n actualizada: $(date '+%Y-%m-%d')*