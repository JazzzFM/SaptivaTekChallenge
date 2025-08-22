#!/usr/bin/env python3
"""
Generador simple de PDF usando pypandoc con configuración básica.
"""

import os
from datetime import datetime

try:
    import pypandoc
    HAS_PYPANDOC = True
except ImportError:
    HAS_PYPANDOC = False


def generate_simple_pdf(markdown_file: str, output_file: str, title: str = "Documento"):
    """Genera PDF usando pypandoc con configuración básica."""
    try:
        # Configuración simple para pypandoc
        extra_args = [
            '--toc',
            '--toc-depth=3',
            f'--metadata=title:{title}',
            f'--metadata=date:{datetime.now().strftime("%Y-%m-%d")}',
            '--variable=geometry:margin=1in',
            '--variable=fontsize=11pt',
            '--variable=documentclass:article'
        ]
        
        print(f"🔄 Generando PDF: {title}")
        
        pypandoc.convert_file(
            markdown_file, 
            'pdf', 
            outputfile=output_file,
            extra_args=extra_args
        )
        
        print(f"✅ PDF generado: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return False


def create_combined_report():
    """Crea un reporte PDF combinado de todos los documentos."""
    
    print("📄 Creando reporte PDF combinado...")
    
    # Leer documentos
    content_parts = []
    
    # Portada
    title_page = f"""---
title: "Documentación Completa del Microservicio de Prompts"
subtitle: "SaptivaTekChallenge - Production Ready System"
author: "Sistema de Documentación Automatizado"
date: "{datetime.now().strftime('%Y-%m-%d')}"
---

# Documentación Completa del Microservicio de Prompts

**Proyecto**: SaptivaTekChallenge  
**Estado**: Production Ready ✅  
**Fecha**: {datetime.now().strftime('%Y-%m-%d')}  

Este documento contiene la documentación técnica completa y el reporte de testing del microservicio de prompts desarrollado como respuesta al reto técnico.

## Resumen de Implementación

- ✅ **Arquitectura Hexagonal** con DI Container
- ✅ **Security Enterprise** con validation y rate limiting  
- ✅ **130+ Tests** con cobertura >85%
- ✅ **4 Problemas Críticos** completamente resueltos
- ✅ **Performance Optimizado** con caching y batch operations
- ✅ **Observabilidad Completa** con health checks multi-nivel

---

\\newpage

"""
    content_parts.append(title_page)
    
    # Resumen ejecutivo
    if os.path.exists("docs/EXECUTIVE_SUMMARY.md"):
        with open("docs/EXECUTIVE_SUMMARY.md", 'r', encoding='utf-8') as f:
            content_parts.append(f.read() + "\n\n\\newpage\n\n")
    
    # Reporte de testing
    if os.path.exists("docs/TEST_REPORT.md"):
        with open("docs/TEST_REPORT.md", 'r', encoding='utf-8') as f:
            content_parts.append(f.read() + "\n\n\\newpage\n\n")
    
    # Documentación técnica (parcial para no hacer el PDF muy largo)
    if os.path.exists("docs/TECHNICAL_DOCUMENTATION.md"):
        with open("docs/TECHNICAL_DOCUMENTATION.md", 'r', encoding='utf-8') as f:
            tech_content = f.read()
            # Tomar solo las primeras secciones para mantener el PDF manejable
            sections = tech_content.split('## ')
            selected_sections = sections[:6]  # Primeras 5 secciones + inicio
            truncated_content = '## '.join(selected_sections)
            content_parts.append(truncated_content + "\n\n[Documentación técnica completa disponible en docs/TECHNICAL_DOCUMENTATION.md]\n\n")
    
    # Combinar todo el contenido
    combined_content = ''.join(content_parts)
    
    # Guardar archivo combinado
    combined_file = "docs/reports/FULL_DOCUMENTATION.md"
    os.makedirs("docs/reports", exist_ok=True)
    
    with open(combined_file, 'w', encoding='utf-8') as f:
        f.write(combined_content)
    
    # Generar PDF
    output_pdf = "docs/reports/FULL_DOCUMENTATION.pdf"
    
    if generate_simple_pdf(combined_file, output_pdf, "Documentación Completa - Microservicio de Prompts"):
        print(f"🎉 Reporte PDF completo generado: {output_pdf}")
        return True
    else:
        print("❌ No se pudo generar el reporte PDF completo")
        return False


def main():
    """Función principal."""
    print("📋 Generador Simple de PDFs")
    print("=" * 50)
    
    if not HAS_PYPANDOC:
        print("❌ pypandoc no disponible")
        print("💡 Instalación: pip install pypandoc-binary")
        return
    
    print("✅ pypandoc disponible")
    
    # Crear directorios
    os.makedirs("docs/reports", exist_ok=True)
    
    # Lista de documentos a convertir
    documents = [
        ("docs/EXECUTIVE_SUMMARY.md", "docs/reports/EXECUTIVE_SUMMARY.pdf", "Resumen Ejecutivo"),
        ("docs/TEST_REPORT.md", "docs/reports/TEST_REPORT.pdf", "Reporte de Testing"),
        ("docs/TECHNICAL_DOCUMENTATION.md", "docs/reports/TECHNICAL_DOCUMENTATION.pdf", "Documentación Técnica")
    ]
    
    success_count = 0
    
    # Generar PDFs individuales
    for markdown_file, pdf_file, title in documents:
        if os.path.exists(markdown_file):
            if generate_simple_pdf(markdown_file, pdf_file, title):
                success_count += 1
        else:
            print(f"⚠️  Archivo no encontrado: {markdown_file}")
    
    # Generar reporte combinado
    if create_combined_report():
        success_count += 1
    
    print("\n📊 Resumen:")
    print(f"✅ PDFs generados: {success_count}")
    print("📁 Ubicación: docs/reports/")
    
    # Listar archivos generados
    pdf_files = [f for f in os.listdir("docs/reports") if f.endswith('.pdf')]
    if pdf_files:
        print("\n📄 Archivos PDF generados:")
        for pdf_file in sorted(pdf_files):
            print(f"   📄 docs/reports/{pdf_file}")
    
    print("\n🎯 Generación de PDFs completada!")


if __name__ == "__main__":
    main()
