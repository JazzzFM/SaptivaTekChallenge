#!/usr/bin/env python3
"""
Generador de reportes PDF usando pypandoc y weasyprint como alternativas.
"""

import os
from datetime import datetime

try:
    import pypandoc
    HAS_PYPANDOC = True
except ImportError:
    HAS_PYPANDOC = False

try:
    from weasyprint import CSS, HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


def generate_pdf_with_pypandoc(markdown_file: str, output_file: str):
    """Genera PDF usando pypandoc."""
    try:
        # Configuración para pypandoc
        extra_args = [
            '--toc',
            '--toc-depth=3',
            '--highlight-style=github',
            '--variable=geometry:margin=1in',
            '--variable=fontsize=11pt'
        ]
        
        pypandoc.convert_file(
            markdown_file, 
            'pdf', 
            outputfile=output_file,
            extra_args=extra_args
        )
        
        return True
    except Exception as e:
        print(f"Error con pypandoc: {e}")
        return False


def generate_pdf_with_weasyprint(html_file: str, output_file: str):
    """Genera PDF usando weasyprint desde HTML."""
    try:
        # CSS personalizado para mejor formatting
        css_content = """
        @page {
            margin: 1in;
            @top-center {
                content: "Microservicio de Prompts - Documentación";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Página " counter(page);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        
        h1, h2, h3, h4 { 
            color: #2c3e50; 
            page-break-after: avoid;
        }
        
        h1 { 
            border-bottom: 3px solid #3498db; 
            padding-bottom: 10px; 
            page-break-before: always;
        }
        
        h2 { 
            border-bottom: 1px solid #bdc3c7; 
            padding-bottom: 5px; 
        }
        
        code {
            background: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 9pt;
        }
        
        pre {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
            font-size: 9pt;
            page-break-inside: avoid;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            page-break-inside: avoid;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            font-size: 9pt;
        }
        
        th { 
            background-color: #f2f2f2; 
            font-weight: bold;
        }
        
        .status-pass { color: #27ae60; font-weight: bold; }
        .status-warn { color: #f39c12; font-weight: bold; }
        .status-fail { color: #e74c3c; font-weight: bold; }
        
        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 15px 0;
            background: #f8f9fa;
            padding: 15px;
            page-break-inside: avoid;
        }
        """
        
        css = CSS(string=css_content)
        HTML(filename=html_file).write_pdf(output_file, stylesheets=[css])
        return True
        
    except Exception as e:
        print(f"Error con weasyprint: {e}")
        return False


def create_comprehensive_report():
    """Crea un reporte PDF comprehensivo."""
    
    print("📄 Generando reporte PDF comprehensivo...")
    
    # Leer todos los documentos markdown
    docs = []
    
    # Resumen ejecutivo
    try:
        with open("docs/EXECUTIVE_SUMMARY.md", 'r', encoding='utf-8') as f:
            docs.append(("# Resumen Ejecutivo\n\n", f.read()))
    except FileNotFoundError:
        pass
    
    # Documentación técnica
    try:
        with open("docs/TECHNICAL_DOCUMENTATION.md", 'r', encoding='utf-8') as f:
            docs.append(("\\newpage\n# Documentación Técnica\n\n", f.read()))
    except FileNotFoundError:
        pass
    
    # Reporte de testing
    try:
        with open("docs/TEST_REPORT.md", 'r', encoding='utf-8') as f:
            docs.append(("\\newpage\n# Reporte de Testing\n\n", f.read()))
    except FileNotFoundError:
        pass
    
    if not docs:
        print("❌ No se encontraron documentos para generar PDF")
        return False
    
    # Crear documento combinado
    combined_content = f"""---
title: "Documentación Completa - Microservicio de Prompts"
subtitle: "SaptivaTekChallenge"
author: "Sistema de Documentación Automatizado"
date: "{datetime.now().strftime('%Y-%m-%d')}"
geometry: margin=1in
fontsize: 11pt
documentclass: article
toc: true
toc-depth: 3
highlight-style: github
---

"""
    
    for title, content in docs:
        combined_content += title + content + "\n\n"
    
    # Guardar documento combinado
    combined_file = "docs/reports/COMPREHENSIVE_REPORT.md"
    with open(combined_file, 'w', encoding='utf-8') as f:
        f.write(combined_content)
    
    output_pdf = "docs/reports/COMPREHENSIVE_REPORT.pdf"
    
    # Intentar generar PDF
    if HAS_PYPANDOC:
        print("🔄 Intentando generar PDF con pypandoc...")
        if generate_pdf_with_pypandoc(combined_file, output_pdf):
            print(f"✅ PDF generado con pypandoc: {output_pdf}")
            return True
    
    if HAS_WEASYPRINT:
        print("🔄 Intentando generar PDF con weasyprint...")
        # Primero necesitamos generar HTML
        html_file = "docs/reports/COMPREHENSIVE_REPORT.html"
        if generate_html_from_markdown(combined_file, html_file):
            if generate_pdf_with_weasyprint(html_file, output_pdf):
                print(f"✅ PDF generado con weasyprint: {output_pdf}")
                return True
    
    print("❌ No se pudo generar PDF - librerías no disponibles")
    print("💡 Sugerencia: Los reportes HTML están disponibles en docs/reports/")
    return False


def generate_html_from_markdown(markdown_file: str, html_file: str):
    """Convierte markdown a HTML mejorado."""
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Procesar markdown básico a HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentación Completa - Microservicio de Prompts</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
        }}
        
        h1, h2, h3, h4 {{ color: #2c3e50; margin-top: 2em; }}
        h1 {{ border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        
        code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
        
        pre code {{
            background: none;
            padding: 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        th {{ 
            background-color: #f8f9fa; 
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .status-pass {{ color: #27ae60; font-weight: bold; }}
        .status-warn {{ color: #f39c12; font-weight: bold; }}
        .status-fail {{ color: #e74c3c; font-weight: bold; }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding: 15px 20px;
            margin: 20px 0;
            background: #f8f9fa;
            border-radius: 0 4px 4px 0;
        }}
        
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        
        .timestamp {{
            color: #7f8c8d;
            font-style: italic;
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #3498db;
        }}
        
        .header h1 {{
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Documentación Completa</h1>
        <div class="subtitle">Microservicio de Prompts - SaptivaTekChallenge</div>
        <div class="timestamp">Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    
    <div class="content">
        {content.replace('✅', '<span class="status-pass">✅</span>')
                 .replace('⚠️', '<span class="status-warn">⚠️</span>')
                 .replace('❌', '<span class="status-fail">❌</span>')
                 .replace('```', '</code></pre>' if '```' in content else '<pre><code>')
                 .replace('`', '</code>' if '`' in content else '<code>')}
    </div>
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
    except Exception as e:
        print(f"Error generando HTML: {e}")
        return False


def main():
    """Función principal."""
    print("📋 Generador de Reportes PDF - Microservicio de Prompts")
    print("=" * 60)
    
    # Verificar dependencias
    print("🔍 Verificando dependencias...")
    if HAS_PYPANDOC:
        print("✅ pypandoc disponible")
    else:
        print("❌ pypandoc no disponible")
    
    if HAS_WEASYPRINT:
        print("✅ weasyprint disponible")
    else:
        print("❌ weasyprint no disponible")
    
    if not HAS_PYPANDOC and not HAS_WEASYPRINT:
        print("\n⚠️  Sin librerías PDF disponibles")
        print("💡 Instalación sugerida:")
        print("   pip install pypandoc weasyprint")
        print("   o para pypandoc: pip install pypandoc-binary")
        print("\n📄 Los reportes HTML están disponibles en docs/reports/")
        return
    
    # Crear directorios
    os.makedirs("docs/reports", exist_ok=True)
    
    # Generar reporte comprehensivo
    success = create_comprehensive_report()
    
    if success:
        print("\n🎉 ¡Reporte PDF generado exitosamente!")
        print("📍 Ubicación: docs/reports/COMPREHENSIVE_REPORT.pdf")
    else:
        print("\n📄 Reportes HTML disponibles:")
        html_files = [
            "docs/reports/EXECUTIVE_SUMMARY.html",
            "docs/reports/TECHNICAL_DOCUMENTATION.html", 
            "docs/reports/TEST_REPORT.html"
        ]
        for html_file in html_files:
            if os.path.exists(html_file):
                print(f"   📄 {html_file}")


if __name__ == "__main__":
    main()
