"""Render Chat_Transcript.md → Chat_Transcript.pdf via reportlab.
Keeps it simple: paragraphs + headings + monospace blocks. No HTML pipeline."""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Preformatted, PageBreak, Table, TableStyle)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register a Cyrillic-capable font
import os
candidates = [
    r'C:\Windows\Fonts\arial.ttf',
    r'C:\Windows\Fonts\segoeui.ttf',
    r'C:\Windows\Fonts\calibri.ttf',
]
mono_candidates = [
    r'C:\Windows\Fonts\consola.ttf',
    r'C:\Windows\Fonts\cour.ttf',
]
font_path = next((p for p in candidates if os.path.exists(p)), None)
mono_path = next((p for p in mono_candidates if os.path.exists(p)), None)
assert font_path and mono_path, 'No suitable Windows font found'
pdfmetrics.registerFont(TTFont('Body',  font_path))
pdfmetrics.registerFont(TTFont('Mono',  mono_path))

styles = getSampleStyleSheet()
body  = ParagraphStyle('body', parent=styles['BodyText'], fontName='Body',
                       fontSize=10.5, leading=14, alignment=TA_LEFT,
                       spaceAfter=6)
h1    = ParagraphStyle('h1', parent=styles['Heading1'], fontName='Body',
                       fontSize=18, leading=22, spaceAfter=12, spaceBefore=8)
h2    = ParagraphStyle('h2', parent=styles['Heading2'], fontName='Body',
                       fontSize=14, leading=18, spaceAfter=8, spaceBefore=12,
                       textColor=colors.HexColor('#222266'))
h3    = ParagraphStyle('h3', parent=styles['Heading3'], fontName='Body',
                       fontSize=12, leading=15, spaceAfter=6, spaceBefore=8)
mono_style = ParagraphStyle('mono', parent=body, fontName='Mono',
                            fontSize=9, leading=11, leftIndent=10,
                            backColor=colors.HexColor('#f4f4f4'),
                            borderPadding=4)

def md_inline(s: str) -> str:
    """Convert minimal inline markdown to reportlab markup."""
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`(.+?)`', r'<font name="Mono">\1</font>', s)
    # Markdown links: [text](url)
    s = re.sub(r'\[(.+?)\]\((.+?)\)',
               r'<link href="\2"><font color="#1155cc">\1</font></link>', s)
    return s

src = open(r'C:/Vega HW/Chat_Transcript.md', 'r', encoding='utf-8').read()
lines = src.splitlines()

flow = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('# '):
        flow.append(Paragraph(md_inline(line[2:]), h1))
    elif line.startswith('## '):
        flow.append(Paragraph(md_inline(line[3:]), h2))
    elif line.startswith('### '):
        flow.append(Paragraph(md_inline(line[4:]), h3))
    elif line.strip() == '---':
        flow.append(Spacer(1, 6))
    elif line.startswith('|') and '|' in line[1:]:
        # Markdown table — collect block
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            cells = [c.strip() for c in lines[i].strip('|').split('|')]
            rows.append(cells)
            i += 1
        # drop separator row (---)
        rows = [r for r in rows if not all(set(c) <= set('-: ') for c in r)]
        if rows:
            t = Table([[Paragraph(md_inline(c), body) for c in r] for r in rows],
                      hAlign='LEFT', colWidths=[None]*len(rows[0]))
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eef')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 6))
        continue
    elif line.strip() == '':
        flow.append(Spacer(1, 4))
    elif line.startswith('- ') or line.startswith('* '):
        flow.append(Paragraph('• ' + md_inline(line[2:]), body))
    elif re.match(r'^\d+\.\s', line):
        flow.append(Paragraph(md_inline(line), body))
    else:
        flow.append(Paragraph(md_inline(line), body))
    i += 1

doc = SimpleDocTemplate(r'C:/Vega HW/Chat_Transcript.pdf', pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=1.5*cm, bottomMargin=1.5*cm,
                        title='HW8 Chat Transcript')
doc.build(flow)
print('Wrote C:/Vega HW/Chat_Transcript.pdf')
