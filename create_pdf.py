#!/usr/bin/env python3
"""
Simple Markdown to PDF converter using built-in libraries
"""
import sys

try:
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'SVG Shape Detection Pipeline - Changes Log', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

        def chapter_title(self, title):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(2)

        def chapter_body(self, body):
            self.set_font('Arial', '', 11)
            self.multi_cell(0, 6, body)
            self.ln()

    # Read markdown file
    with open('CHANGES_LOG.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Create PDF
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Process content - simple markdown parsing
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('# '):
            # Skip first header (already in header)
            if i > 0:
                pdf.chapter_title(line[2:])
        elif line.startswith('## '):
            pdf.chapter_title(line[3:])
        elif line.startswith('### '):
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, line[4:], 0, 1, 'L')
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, line[2:-2], 0, 1, 'L')
        elif line.startswith('```'):
            # Code block
            pdf.set_font('Courier', '', 9)
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                pdf.cell(0, 5, lines[i], 0, 1, 'L')
                i += 1
        elif line.startswith('|'):
            # Table row
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 6, line, 0, 1, 'L')
        elif line.startswith('-') or line.startswith('*'):
            # List item
            pdf.set_font('Arial', '', 11)
            pdf.cell(10, 6, '')
            pdf.multi_cell(0, 6, '• ' + line[2:])
        elif line:
            # Normal text
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, line)

        i += 1

    # Save PDF
    pdf.output('CHANGES_LOG.pdf')
    print("✓ PDF created successfully: CHANGES_LOG.pdf")

except ImportError:
    print("ERROR: fpdf module not found. Trying alternative method...")
    sys.exit(1)
