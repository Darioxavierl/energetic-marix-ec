"""
Script de verificación de la estructura del proyecto
"""
import sys
import json
from pathlib import Path

def verify_structure():
    """Verifica que la estructura de archivos esté completa"""

    project_root = Path(__file__).parent.parent
    checks = []

    # Directorios
    dirs_to_check = [
        'src', 'src/ui', 'src/models', 'src/shared',
        'config', 'data', 'data/centrales',
        'web', 'web/html', 'web/js', 'web/css',
        'tests', 'docs'
    ]

    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        exists = dir_path.exists()
        checks.append(('DIR', dir_name, exists))

    # Archivos críticos
    files_to_check = [
        'pyproject.toml',
        'requirements.txt',
        '.gitignore',
        'config/settings.py',
        'data/centrales/centrales_ecuador.json',
        'src/main.py',
        'src/ui/main_window.py',
        'src/ui/map_widget.py',
        'src/models/power_plant.py',
        'web/html/map_container.html',
        'web/js/map_handler.js',
        'web/css/map_styles.css',
        'tests/test_models.py'
    ]

    for file_name in files_to_check:
        file_path = project_root / file_name
        exists = file_path.exists()
        checks.append(('FILE', file_name, exists))

    # Verificar JSON válido
    json_file = project_root / 'data/centrales/centrales_ecuador.json'
    json_valid = False
    centrales_count = 0
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                json_valid = True
                centrales_count = len(data.get('data', {}).get('centrales', []))
        except:
            json_valid = False

    checks.append(('JSON', 'centrales_ecuador.json (valid)', json_valid))
    checks.append(('COUNT', f'Centrales en JSON', centrales_count >= 15))

    # Imprimir resultados
    print("\n" + "="*60)
    print("VERIFICACION DE ESTRUCTURA - HITO 1")
    print("="*60)

    passed = 0
    failed = 0

    for check_type, item, result in checks:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {check_type:8} {item}")
        if result:
            passed += 1
        else:
            failed += 1

    print("="*60)
    print(f"TOTAL: {passed} OK, {failed} FAILED")
    print(f"Centrales cargadas: {centrales_count}")
    print("="*60 + "\n")

    return failed == 0

if __name__ == '__main__':
    success = verify_structure()
    sys.exit(0 if success else 1)
