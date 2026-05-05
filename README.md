# Matriz Energetica Ecuador - Regulacion de las Telecomunicaciones
## Universidad de Cuenca  
## Facultad de Ingenieria  
## Grupo 1  
## Integrantes: David Alejandro Montaño Bravo, Sebastián Josué Pesántez Jiménez, Dario Xavier Portilla Loja.


Simulador de la matriz energetica del Ecuador con interfaz grafica (PyQt6) y microservicio de scraping de CENACE (FastAPI + Playwright).

El sistema tiene dos componentes:

1. Aplicacion principal (raiz del proyecto): GUI y logica de simulacion.
2. Microservicio (`cenace_scraper_service`): obtiene y expone datos operativos de CENACE por API local.

## Requisitos previos

- Python 3.11 o superior
- `pip` actualizado
- Windows PowerShell
- Dos terminales abiertas para ejecutar ambos componentes en paralelo

## Instalacion rapida

### 1) Entorno virtual de la aplicacion principal (raiz)

Desde la raiz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Este entorno instala dependencias de la GUI y del programa principal.

### 2) Entorno virtual del microservicio (`cenace_scraper_service`)

Desde la raiz del proyecto:

```powershell
Set-Location .\cenace_scraper_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Instalacion de Playwright (obligatoria en microservicio):

```powershell
python -m playwright install
```

Si deseas instalar solo Chromium:

```powershell
python -m playwright install chromium
```

## Inicio rapido (dos terminales)

Importante: iniciar primero el microservicio y luego la aplicacion principal.

### Terminal 1: microservicio

```powershell
Set-Location "g:\My Drive\Universidad\10. DECIMO\Regulacion\Energetico\energetic-marix-ec\cenace_scraper_service"
.\.venv\Scripts\Activate.ps1
python -m main
```

### Terminal 2: programa principal (GUI)

```powershell
Set-Location "g:\My Drive\Universidad\10. DECIMO\Regulacion\Energetico\energetic-marix-ec"
.\.venv\Scripts\Activate.ps1
python -m src.main
```

## Verificacion rapida

Con el microservicio arriba, valida salud:

```powershell
python -c "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health'))['status'])"
```

Si devuelve `healthy` o `degraded`, el servicio esta respondiendo.

