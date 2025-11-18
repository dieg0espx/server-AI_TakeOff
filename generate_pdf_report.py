#!/usr/bin/env python3
"""
Convert markdown to styled HTML for PDF printing
"""
import re

# Read markdown
with open('CHANGES_LOG.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Create HTML with CSS styling
html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SVG Shape Detection Pipeline - Changes Log</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            font-size: 2.5em;
        }
        h2 {
            color: #2c3e50;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 40px;
            font-size: 2em;
        }
        h3 {
            color: #34495e;
            margin-top: 30px;
            font-size: 1.5em;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
        }
        pre {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            line-height: 1.4;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        ul, ol {
            margin: 15px 0;
            padding-left: 30px;
        }
        li {
            margin: 8px 0;
        }
        strong {
            color: #2c3e50;
            font-weight: 600;
        }
        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 30px 0;
        }
        .metadata {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        @media print {
            body {
                margin: 0;
                padding: 20px;
            }
            h1, h2 {
                page-break-after: avoid;
            }
            pre, table {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
"""

# Simple markdown to HTML conversion
lines = content.split('\n')
in_code_block = False
in_table = False
html_lines = []

for line in lines:
    # Code blocks
    if line.startswith('```'):
        if in_code_block:
            html_lines.append('</pre>')
            in_code_block = False
        else:
            html_lines.append('<pre>')
            in_code_block = True
        continue

    if in_code_block:
        html_lines.append(line)
        continue

    # Headers
    if line.startswith('# '):
        html_lines.append(f'<h1>{line[2:]}</h1>')
    elif line.startswith('## '):
        html_lines.append(f'<h2>{line[3:]}</h2>')
    elif line.startswith('### '):
        html_lines.append(f'<h3>{line[4:]}</h3>')
    # Tables
    elif line.startswith('|'):
        if not in_table:
            html_lines.append('<table>')
            in_table = True

        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if all(cell.replace('-', '').strip() == '' for cell in cells):
            continue  # Skip separator row

        is_header = html_lines[-1] == '<table>'
        tag = 'th' if is_header else 'td'
        html_lines.append('<tr>')
        for cell in cells:
            html_lines.append(f'<{tag}>{cell}</{tag}>')
        html_lines.append('</tr>')
    else:
        if in_table:
            html_lines.append('</table>')
            in_table = False

        # Horizontal rules
        if line.strip() == '---':
            html_lines.append('<hr>')
        # Lists
        elif line.startswith('- ') or line.startswith('* '):
            if not html_lines or not html_lines[-1].startswith('<ul>'):
                html_lines.append('<ul>')
            html_lines.append(f'<li>{line[2:]}</li>')
            # Check if next line is also a list item
        elif html_lines and html_lines[-1].startswith('<li>'):
            if not (line.startswith('- ') or line.startswith('* ')):
                html_lines.append('</ul>')
        # Bold text
        elif '**' in line:
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f'<p>{line}</p>')
        # Empty lines
        elif not line.strip():
            html_lines.append('<br>')
        # Regular text
        else:
            html_lines.append(f'<p>{line}</p>')

# Close any open tags
if in_table:
    html_lines.append('</table>')

html_content += '\n'.join(html_lines)
html_content += """
</body>
</html>
"""

# Write HTML file
with open('CHANGES_LOG.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("✓ HTML file created: CHANGES_LOG.html")
print("\nTo convert to PDF:")
print("  1. Open CHANGES_LOG.html in your browser")
print("  2. Press Cmd+P (Print)")
print("  3. Select 'Save as PDF' as the destination")
print("\nOpening in default browser...")
