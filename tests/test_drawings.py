# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import pikepdf as q
import pymupdf as fitz
import pytest
from pdfprep.fixtures import drawing_pdf
from pdfprep.engine import prepare, review, render_and_compare, brightspace_check
from pdfprep.saving import save_one

@pytest.mark.parametrize('variant', ['vector', 'nested', 'scanned', 'nested-marked'])
def test_drafting_variants_preserve_individual_pages(tmp_path, variant):
    src=drawing_pdf(tmp_path/'drawing.pdf',nested=variant.startswith('nested'),scanned=variant=='scanned')
    if variant=='nested-marked':
        with q.open(src) as pdf:
            form=next(iter(pdf.pages[0].Resources.XObject.values()))
            form.write(b'/Artifact BMC\n'+form.read_bytes()+b'\nEMC')
            temp=tmp_path/'marked.pdf'; pdf.save(temp)
        temp.replace(src)
    r=prepare(src,tmp_path/'work')
    assert r['page_count']==2
    assert r['brightspace']['status']=='PDF format checks passed'
    assert not r['brightspace']['live_upload_tested']
    assert all(p['source_render_sha256']==p['prepared_render_sha256'] and p['page_boxes_preserved'] for p in r['pages'])
    if variant=='vector':
        figures=[e for e in r['elements'] if e['kind']=='figure']
        assert len(figures)==2
        assert all(e['mcid']==-1 for e in figures)
        missing=review(r,{'reviewed':['graphics:1','figures:1']})
        assert not any(i['reviewed'] for i in missing['issues'] if i['id'] in ('graphics:1','figures:1'))
        description='Isometric view of a rectangular block, 60 by 40 by 30 mm. A through hole is shown on the top face.\n\nUnits are millimeters; verify hidden edges and dimensions with the instructor.'
        edited=review(r,{'elements':[dict(e,alt=description) for e in figures], 'reviewed':['graphics:1','figures:1']})
        assert all(e['alt']==description for e in edited['elements'] if e['kind']=='figure')
        assert all(i['reviewed'] for i in edited['issues'] if i['id'] in ('graphics:1','figures:1'))
        with q.open(edited['output']) as pdf:
            assert pdf.pages[0].obj.UserUnit==2
            numbers=pdf.Root.StructTreeRoot.ParentTree.Nums
            f=next(o for o in pdf.objects if isinstance(o,q.Dictionary) and str(o.get('/S',''))=='/Figure')
            assert isinstance(f.K,q.Array) and len(f.K)>5
            assert all(numbers[1][int(k)].objgen==f.objgen for k in f.K)
        with q.open(src) as before, q.open(edited['output']) as after:
            for a,b in zip(before.pages,after.pages):
                stripped=[o for o in q.parse_content_stream(b) if str(o.operator) not in ('BDC','EMC')]
                assert q.unparse_content_stream(q.parse_content_stream(a))==q.unparse_content_stream(stripped)
        output=tmp_path/'saved'; output.mkdir()
        saved,report=save_one(edited,output)
        assert brightspace_check(saved)['status']=='PDF format checks passed'
        assert 'Brightspace file compatibility' in Path(report).read_text()
    elif variant=='nested':
        assert any(i['kind']=='nested_drawing' and i['reviewable'] for i in r['issues'])
        assert not any(i['kind']=='structure' for i in r['issues'])
        figures=[e for e in r['elements'] if e['kind']=='figure']
        assert len(figures)==2
        changed=review(r,{'elements':[dict(e,alt='Nested isometric drawing of the block, including its dimensions and hidden edges.') for e in figures]})
        assert all(e['alt'] for e in changed['elements'] if e['kind']=='figure')
        assert all(f['clause'] in ('5','7.21.3.2') for f in changed['validator'].get('failures',[]))
    elif variant=='nested-marked':
        assert any(i['kind']=='structure' and not i['reviewable'] for i in r['issues'])
        assert r['status']=='Review needed — draft'
    else:
        assert any(i['kind']=='ocr' for i in r['issues'])

@pytest.mark.parametrize('mutation', ['scale','line'])
def test_drawing_changes_are_rejected(tmp_path, mutation):
    src=drawing_pdf(tmp_path/'source.pdf'); changed=tmp_path/'changed.pdf'
    if mutation=='scale':
        with q.open(src) as pdf:
            pdf.pages[0].obj.UserUnit=1; pdf.save(changed)
    else:
        with fitz.open(src) as pdf:
            pdf[0].draw_line((10,10),(400,500),width=.1); pdf.save(changed)
    with pytest.raises(ValueError,match='changed'):
        render_and_compare(src,changed,tmp_path)

def test_multiline_drawing_editor(qtbot=None):
    # No pytest-qt dependency: drive the existing same-window Qt controls.
    from PySide6.QtWidgets import QApplication
    from pdfprep.app import Window
    app=QApplication.instance() or QApplication([])
    window=Window()
    window.load_elements([{'page':1,'mcid':-1,'role':'Figure','kind':'figure','object':[10,0],'label':'Drawing','alt':''}])
    window.elements.setCurrentCell(0,3)
    window.description_editor.setPlainText('Object and view.\nDimensions and units.')
    assert window.current_elements()[0]['alt']=='Object and view.\nDimensions and units.'
    assert not window.elements.cellWidget(0,4).isEnabled()
    window.close()

@pytest.mark.parametrize('nested', [False, True])
def test_drawing_associations_with_independent_validator(tmp_path, nested):
    # A positive validation fixture, not an app-generated conformance assertion.
    # This generator uses glyph IDs as CIDs, so its font mapping is known.
    from pdfprep.validation import validate
    src=drawing_pdf(tmp_path/'drawing.pdf',nested=nested)
    r=prepare(src,tmp_path/'work')
    r=review(r,{'elements':[dict(e,alt='Isometric practice block. Dimensions and all drawing features are described here for this structural test fixture.') for e in r['elements'] if e['kind']=='figure']})
    positive=tmp_path/'structural-fixture.pdf'
    with q.open(r['output']) as pdf:
        for obj in pdf.objects:
            if isinstance(obj,q.Dictionary) and str(obj.get('/Subtype',''))=='/CIDFontType2':
                obj.CIDToGIDMap=q.Name.Identity
        with pdf.open_metadata(set_pikepdf_as_editor=False,update_docinfo=False) as meta:
            meta.register_xml_namespace('http://www.aiim.org/pdfua/ns/id/','pdfuaid')
            meta['pdfuaid:part']='1'
        pdf.save(positive,force_version='1.7')
    result=validate(positive,tmp_path/'validation.xml')
    assert result['status']=='passed',result


@pytest.mark.parametrize('nested', [False, True])
def test_cad_optional_content_layers_preserved(tmp_path, nested):
    src=drawing_pdf(tmp_path/'layers.pdf',nested=nested)
    with q.open(src) as pdf:
        layer=pdf.make_indirect(q.Dictionary(Type=q.Name.OCG,Name='Dimension layer'))
        pdf.Root.OCProperties=q.Dictionary(OCGs=q.Array([layer]),D=q.Dictionary(BaseState=q.Name.ON,Order=q.Array([layer])))
        if nested:
            target=next(iter(pdf.pages[0].Resources.XObject.values()))
            if '/Resources' not in target: target.Resources=q.Dictionary()
            target.Resources.Properties=q.Dictionary(Layer=layer)
            target.write(b'/OC /Layer BDC\n'+target.read_bytes()+b'\nEMC')
        else:
            page=pdf.pages[0]
            page.Resources.Properties=q.Dictionary(Layer=layer)
            page.Contents=pdf.make_stream(b'/OC /Layer BDC\n'+q.unparse_content_stream(q.parse_content_stream(page))+b'\nEMC')
        staged=tmp_path/'staged.pdf'; pdf.save(staged)
    staged.replace(src)
    r=prepare(src,tmp_path/'work')
    assert not any(i['kind']=='structure' for i in r['issues'])
    assert any(i['kind']=='layers' for i in r['issues'])
    assert len([e for e in r['elements'] if e['kind']=='figure'])==2
    with q.open(r['output']) as pdf:
        assert str(pdf.Root.OCProperties.OCGs[0].Name)=='Dimension layer'
        assert str(pdf.Root.OCProperties.D.BaseState)=='/ON'
