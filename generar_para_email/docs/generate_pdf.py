#!/usr/bin/env python3
"""
Script para generar PDF del manual de cierres desde Markdown.
Usa reportlab para crear un documento profesional.
"""

import re
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white, grey, lightgrey
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Image
)
from reportlab.pdfgen import canvas
from reportlab.lib import colors


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._pagenum = 0

    def showPage(self):
        self._pagenum += 1
        canvas.Canvas.showPage(self)

    def save(self):
        canvas.Canvas.save(self)


def create_pdf_from_markdown(md_file: Path, pdf_file: Path) -> None:
    """
    Convierte un archivo Markdown a PDF con estilos profesionales.
    
    Args:
        md_file: Ruta al archivo Markdown
        pdf_file: Ruta del archivo PDF a generar
    """
    
    # Leer el archivo Markdown
    content = md_file.read_text(encoding='utf-8')
    
    # Crear documento PDF
    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title="Guía de Cierres Zoo Picasso",
        author="Zoo Picasso",
    )
    
    # Crear estilos personalizados
    styles = getSampleStyleSheet()
    
    # Colores corporativos Zoo Picasso (aproximados)
    PRIMARY_COLOR = HexColor("#1F4E79")  # Azul
    SECONDARY_COLOR = HexColor("#70AD47")  # Verde
    ACCENT_COLOR = HexColor("#FFC000")  # Dorado
    
    # Título del documento
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=white,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        backColor=PRIMARY_COLOR,
        leftIndent=10,
        rightIndent=10,
        topPadding=10,
        bottomPadding=10,
    )
    
    heading1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
    )
    
    heading2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=SECONDARY_COLOR,
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold',
    )
    
    heading3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=PRIMARY_COLOR,
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold',
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        leading=14,
    )
    
    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['BodyText'],
        fontSize=9,
        fontName='Courier',
        leftIndent=20,
        rightIndent=20,
        backColor=lightgrey,
        spaceAfter=6,
        leading=10,
    )
    
    warning_style = ParagraphStyle(
        'CustomWarning',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=HexColor("#FF6B6B"),
        fontName='Helvetica-Bold',
        spaceAfter=6,
    )
    
    # Parsear el Markdown
    story = []
    lines = content.split('\n')
    i = 0
    
    in_code_block = False
    code_block_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar bloques de código
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lines = []
            else:
                # Fin del bloque de código
                if code_block_lines:
                    code_text = '\n'.join(code_block_lines)
                    # Escapar caracteres especiales
                    code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(f"<font face='Courier' size='9'>{code_text}</font>", code_style))
                    story.append(Spacer(1, 0.2*inch))
                in_code_block = False
                code_block_lines = []
            i += 1
            continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # Título (# TÍTULO)
        if line.startswith('# '):
            title_text = line[2:].strip()
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 0.3*inch))
            i += 1
            continue
        
        # Heading 2 (## Heading)
        if line.startswith('## '):
            heading_text = line[3:].strip()
            story.append(Paragraph(heading_text, heading1_style))
            story.append(Spacer(1, 0.15*inch))
            i += 1
            continue
        
        # Heading 3 (### Heading)
        if line.startswith('### '):
            heading_text = line[4:].strip()
            story.append(Paragraph(heading_text, heading2_style))
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue
        
        # Heading 4 (#### Heading)
        if line.startswith('#### '):
            heading_text = line[5:].strip()
            story.append(Paragraph(heading_text, heading3_style))
            story.append(Spacer(1, 0.08*inch))
            i += 1
            continue
        
        # Tabla
        if '|' in line and i + 2 < len(lines):
            # Detectar tabla
            if lines[i+1].strip().startswith('|'):
                table_lines = [line]
                i += 1
                table_lines.append(lines[i])
                i += 1
                
                # Agregar filas hasta que no haya más pipes
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                
                # Procesar tabla
                rows = []
                for tline in table_lines:
                    cells = [cell.strip() for cell in tline.split('|')[1:-1]]
                    rows.append(cells)
                
                if len(rows) > 1:
                    # Saltar la línea separadora
                    rows = [rows[0]] + rows[2:]
                    
                    # Crear tabla
                    table = Table(rows, colWidths=[1.5*inch] * len(rows[0]))
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                        ('TEXTCOLOR', (0, 0), (-1, 0), white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), lightgrey),
                        ('GRID', (0, 0), (-1, -1), 1, black),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#F5F5F5')]),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))
                continue
        
        # Línea separadora (---)
        if line.strip() == '---':
            story.append(Spacer(1, 0.2*inch))
            i += 1
            continue
        
        # Párrafos de advertencia (⚠️)
        if '⚠️' in line or line.strip().startswith('❌'):
            text = line.replace('⚠️', '⚠️ ').replace('❌', '❌ ')
            story.append(Paragraph(text, warning_style))
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue
        
        # Párrafos normales
        if line.strip():
            # Procesar formatos inline
            text = line.strip()
            # Reemplazar **text** con <b>text</b>
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Reemplazar *text* con <i>text</i> (pero no si ya tiene **)
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            # Reemplazar `text` con <font>text</font>
            text = re.sub(r'`([^`]+)`', r'<font face="Courier"><b>\1</b></font>', text)
            
            story.append(Paragraph(text, body_style))
        else:
            story.append(Spacer(1, 0.1*inch))
        
        i += 1
    
    # Agregar salto de página cada cierto número de elementos
    final_story = []
    element_count = 0
    for element in story:
        final_story.append(element)
        element_count += 1
        
        # PageBreak cada ~20 elementos
        if element_count % 25 == 0 and element_count < len(story):
            final_story.append(PageBreak())
    
    # Construir PDF
    doc.build(final_story)
    print(f"✅ PDF generado: {pdf_file}")


if __name__ == "__main__":
    # Paths
    docs_dir = Path(__file__).parent
    md_file = docs_dir / "MANUAL_CIERRES_CLIENTA.md"
    pdf_file = docs_dir / "MANUAL_CIERRES_CLIENTA.pdf"
    
    if not md_file.exists():
        print(f"❌ Archivo no encontrado: {md_file}")
        exit(1)
    
    print(f"📄 Leyendo: {md_file}")
    print(f"📊 Generando PDF...")
    
    try:
        create_pdf_from_markdown(md_file, pdf_file)
        print(f"✅ Listo: {pdf_file}")
        print(f"📦 Tamaño: {pdf_file.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
