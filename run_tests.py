#!/usr/bin/env python3
"""
Script para ejecutar tests del eBay Order Processor.

Uso:
    python run_tests.py                    # Todos los tests
    python run_tests.py --unit             # Solo tests unitarios
    python run_tests.py --integration      # Solo tests de integración
    python run_tests.py --fast             # Tests rápidos (exclude slow)
    python run_tests.py --coverage         # Con cobertura de código
    python run_tests.py --verbose          # Verbose output
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, verbose=False):
    """Ejecutar comando y mostrar output."""
    if verbose:
        print(f"🚀 Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=not verbose, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error ejecutando tests:")
            if not verbose:
                print(result.stdout)
                print(result.stderr)
            return False
        else:
            if verbose:
                print("✅ Tests completados exitosamente")
            else:
                print(result.stdout)
            return True
            
    except FileNotFoundError:
        print("❌ Error: pytest no encontrado. Instala con: pip install pytest")
        return False


def main():
    parser = argparse.ArgumentParser(description="Ejecutar tests del eBay Order Processor")
    
    # Opciones de tipo de test
    parser.add_argument('--unit', action='store_true', 
                       help='Ejecutar solo tests unitarios')
    parser.add_argument('--integration', action='store_true',
                       help='Ejecutar solo tests de integración')
    parser.add_argument('--api', action='store_true',
                       help='Ejecutar solo tests de API')
    
    # Opciones de velocidad
    parser.add_argument('--fast', action='store_true',
                       help='Ejecutar solo tests rápidos (excluir lentos)')
    parser.add_argument('--slow', action='store_true',
                       help='Ejecutar solo tests lentos')
    
    # Opciones de output
    parser.add_argument('--coverage', action='store_true',
                       help='Ejecutar con cobertura de código')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Output verbose')
    parser.add_argument('--html', action='store_true',
                       help='Generar reporte HTML (requiere pytest-html)')
    
    # Opciones específicas
    parser.add_argument('--file', '-f', type=str,
                       help='Ejecutar tests de un archivo específico')
    parser.add_argument('--test', '-t', type=str,
                       help='Ejecutar un test específico')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='Ejecutar tests en paralelo (requiere pytest-xdist)')
    
    args = parser.parse_args()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('tests') and not os.path.exists('ebay_processor'):
        print("❌ Error: Ejecuta este script desde el directorio ebay_order_processor/")
        sys.exit(1)
    
    # Construir comando pytest
    cmd = ['python', '-m', 'pytest']
    
    # Agregar opciones según argumentos
    if args.verbose:
        cmd.extend(['-v', '-s'])
    
    # Marcadores para filtrar tests
    markers = []
    if args.unit:
        markers.append('unit')
    if args.integration:
        markers.append('integration')
    if args.api:
        markers.append('api')
    if args.fast:
        markers.append('not slow')
    if args.slow:
        markers.append('slow')
    
    if markers:
        cmd.extend(['-m', ' and '.join(markers)])
    
    # Cobertura
    if args.coverage:
        cmd.extend([
            '--cov=ebay_processor',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-report=xml'
        ])
    
    # Reporte HTML
    if args.html:
        cmd.extend(['--html=test_report.html', '--self-contained-html'])
    
    # Paralelo
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    # Archivo específico
    if args.file:
        cmd.append(f'tests/{args.file}')
    elif args.test:
        cmd.extend(['-k', args.test])
    else:
        cmd.append('tests/')
    
    # Mostrar información
    print("🧪 eBay Order Processor - Test Runner")
    print("=" * 50)
    
    if args.unit:
        print("📦 Tipo: Tests Unitarios")
    elif args.integration:
        print("🔗 Tipo: Tests de Integración")
    elif args.api:
        print("🌐 Tipo: Tests de API")
    else:
        print("🎯 Tipo: Todos los Tests")
    
    if args.fast:
        print("⚡ Velocidad: Solo tests rápidos")
    elif args.slow:
        print("🐌 Velocidad: Solo tests lentos")
    
    if args.coverage:
        print("📊 Cobertura: Habilitada")
    
    print("-" * 50)
    
    # Ejecutar tests
    success = run_command(cmd, args.verbose)
    
    if success:
        print("\n✅ ¡Todos los tests pasaron!")
        
        if args.coverage:
            print("\n📊 Reporte de cobertura generado en htmlcov/index.html")
        
        if args.html:
            print("\n📄 Reporte HTML generado en test_report.html")
            
    else:
        print("\n❌ Algunos tests fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main() 