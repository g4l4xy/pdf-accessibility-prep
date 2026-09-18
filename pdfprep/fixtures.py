# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import pymupdf as fitz
import pikepdf as q
from pdfprep.validation import resources
from pdfprep import structure


def text_pdf(path, pages=1, label='Document', columns=False, graphics=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as doc:
        for i in range(pages):
            p = doc.new_page(width=612, height=792)
            p.insert_text((50, 65), f'{label} - page {i + 1} of {pages}', fontsize=18,
                          fontname='Noto', fontfile=str(resources() / 'NotoSans-Regular.ttf'))
            p.insert_text((50, 110), f'Unique page marker: {label}/{i + 1}', fontsize=11,
                          fontname='Noto', fontfile=str(resources() / 'NotoSans-Regular.ttf'))
            if columns:
                p.insert_text((50, 160), 'Left column first.\nLeft column second.', fontname='Noto', fontsize=10)
                p.insert_text((320, 160), 'Right column first.\nRight column second.', fontname='Noto', fontsize=10)
            if graphics:
                p.draw_rect(fitz.Rect(50, 220, 500, 360)); p.draw_line((50, 260), (500, 260)); p.draw_line((220, 220), (220, 360))
                p.insert_text((60, 245), 'Header A', fontname='Noto'); p.insert_text((230, 245), 'Header B', fontname='Noto')
                p.insert_text((60, 285), 'Value 1', fontname='Noto'); p.insert_text((230, 285), 'Value 2', fontname='Noto')
        doc.save(path)
    return path


def scan_pdf(path, mixed=False, rotated=False):
    source = Path(path).with_suffix('.source.pdf')
    text_pdf(source, label='Scanned worksheet')
    with fitz.open(source) as doc:
        pixels = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_image(page.rect, stream=pixels)
        if rotated: page.set_rotation(90)
        if mixed:
            page = doc.new_page(); page.insert_text((50, 60), 'Mixed document digital page', fontname='Noto', fontfile=str(resources() / 'NotoSans-Regular.ttf'))
        doc.save(path)
    source.unlink(); return Path(path)


def accessible_pdf(path):
    plain = Path(path).with_suffix('.plain.pdf'); text_pdf(plain, label='Accessible example')
    with fitz.open(plain) as doc: lines = [p.get_text().splitlines() for p in doc]
    with q.open(plain) as pdf:
        structure.build(pdf, lines, lambda *args: None)
        pdf.docinfo['/Title'] = 'Accessible example'; pdf.Root.Lang = 'en'
        pdf.Root.ViewerPreferences = q.Dictionary(DisplayDocTitle=True)
        # This fixture generator uses glyph IDs as CIDs; explicitly record that mapping.
        for obj in pdf.objects:
            if isinstance(obj, q.Dictionary) and str(obj.get('/Subtype', '')) == '/CIDFontType2':
                obj.CIDToGIDMap = q.Name.Identity
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta.register_xml_namespace('http://www.aiim.org/pdfua/ns/id/', 'pdfuaid')
            meta['dc:title'] = 'Accessible example'
            meta['pdfuaid:part'] = '1'
        pdf.save(path, force_version='1.7')
    plain.unlink(); return Path(path)


def corpus(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    out = [text_pdf(folder / 'text.pdf'), text_pdf(folder / 'five-pages.pdf', 5),
           text_pdf(folder / 'columns.pdf', columns=True), text_pdf(folder / 'simple-table.pdf', graphics=True),
           scan_pdf(folder / 'scan.pdf'), scan_pdf(folder / 'mixed.pdf', mixed=True),
           scan_pdf(folder / 'rotated.pdf', rotated=True), accessible_pdf(folder / 'already-tagged.pdf')]
    fig = folder / 'figure.pdf'
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (200, 100), 'white'); draw = ImageDraw.Draw(im); draw.rectangle((20, 20, 180, 80), outline='blue', width=4)
    import io
    buf = io.BytesIO(); im.save(buf, format='PNG')
    with fitz.open() as doc:
        p = doc.new_page(); p.insert_image(fitz.Rect(60, 60, 260, 160), stream=buf.getvalue()); doc.save(fig)
    out.append(fig)
    damaged = folder / 'damaged.pdf'; damaged.write_bytes(b'%PDF-1.7\nnot a valid document'); out.append(damaged)
    with q.open(out[0]) as pdf:
        pdf.save(folder / 'encrypted.pdf', encryption=q.Encryption(owner='owner-authorized', user='open-me', R=6))
    out.append(folder / 'encrypted.pdf')
    # Signature-shaped fixture exercises conservative detection, not crypto validation.
    with q.open(out[0]) as pdf:
        sig = pdf.make_indirect(q.Dictionary(Type=q.Name.Sig, ByteRange=q.Array([0, 1, 2, 3]), Contents=q.String(b'not-a-real-signature')))
        field = pdf.make_indirect(q.Dictionary(FT=q.Name.Sig, T='Signature fixture', V=sig))
        pdf.Root.AcroForm = q.Dictionary(Fields=q.Array([field]))
        pdf.save(folder / 'signature-marker.pdf')
    out.append(folder / 'signature-marker.pdf')
    with fitz.open() as doc:
        p = doc.new_page(); w = fitz.Widget(); w.field_name = 'Student name'; w.field_type = fitz.PDF_WIDGET_TYPE_TEXT; w.rect = fitz.Rect(50, 60, 250, 90); p.add_widget(w); doc.save(folder / 'form.pdf')
    out.append(folder / 'form.pdf')
    p = text_pdf(folder / 'technical.pdf', label='Engineering: E = mc2; check notation', graphics=True); out.append(p)
    p = text_pdf(folder / 'complex-table.pdf', label='Merged-cell table needs specialist review', graphics=True); out.append(p)
    return out


def drawing_pdf(path, nested=False, scanned=False):
    """Synthetic drafting sheet; numerical values are fixture data, not inferred CAD."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as source:
        for n in range(2):
            p = source.new_page(width=792, height=612)
            p.insert_text((40, 45), f'ISOMETRIC PRACTICE — SHEET {n + 1}', fontsize=16,
                          fontname='Noto', fontfile=str(resources() / 'NotoSans-Regular.ttf'))
            p.insert_text((40, 565), 'Units: mm | Scale 1:2 | 60 × 40 × 30 | Ø10 THRU | R5 | ±0.1', fontname='Noto', fontsize=11)
            # Isometric projection of a block, with distinct features on page 2.
            a,b,c,d = (210,190),(365,100),(495,175),(340,265)
            e,f,g = (210,340),(340,415),(495,325)
            for start,end in [(a,b),(b,c),(c,d),(d,a),(a,e),(e,f),(f,g),(g,c),(d,f)]:
                p.draw_line(start,end,color=(0,0,0),width=.35 if n==0 else .7)
            p.draw_line((365,100),(365,250),width=.25,dashes='[4 3] 0',color=(.3,.3,.3))
            p.draw_line((365,250),(210,340),width=.25,dashes='[4 3] 0')
            p.draw_oval(fitz.Rect(310,160,365,195),color=(0,0,.6),width=.5)
            p.draw_line((210,455),(340,455),width=.2)
            p.insert_text((270,475), '60 ±0.1',fontname='Noto',fontsize=10)
            p.insert_text((510,295), '30',fontname='Noto',fontsize=10,rotate=90)
            if n: p.draw_rect(fitz.Rect(60,80,145,145),width=.25,fill=(.9,.9,.9)); p.set_rotation(90)
        if nested or scanned:
            with fitz.open() as target:
                for page in source:
                    p=target.new_page(width=page.rect.width,height=page.rect.height)
                    if nested: p.show_pdf_page(p.rect,source,page.number)
                    else: p.insert_image(p.rect,stream=page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png'))
                target.save(path)
        else: source.save(path)
    if not nested and not scanned:
        with q.open(path) as pdf:
            pdf.pages[0].obj.UserUnit=2
            pdf.pages[0].obj.TrimBox=q.Array([5,5,787,607])
            staged=path.with_suffix('.scale.pdf'); pdf.save(staged)
        staged.replace(path)
    return path


def export_defaults_pdf(path):
    """Synthetic source with omitted default glyph map and unnamed layer settings."""
    path = Path(path)
    original = path.with_suffix('.original.pdf')
    drawing_pdf(original)
    with q.open(original) as pdf:
        for obj in pdf.objects:
            if isinstance(obj, q.Dictionary) and str(obj.get('/Subtype', '')) == '/Type0':
                for font in obj.get('/DescendantFonts', []):
                    if '/CIDToGIDMap' in font: del font['/CIDToGIDMap']
        layer = pdf.make_indirect(q.Dictionary(Type=q.Name.OCG, Name='Drawing'))
        pdf.Root.OCProperties = q.Dictionary(OCGs=q.Array([layer]), D=q.Dictionary(Order=q.Array([layer]), OFF=q.Array()))
        pdf.save(path)
    original.unlink()
    return path
