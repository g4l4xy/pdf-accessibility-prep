# Copyright (c) 2026 Eathan Huber
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Real MCID/ParentTree editing. Existing structures are never replaced automatically."""
from __future__ import annotations
import pikepdf as q
from pikepdf import Name as N, Dictionary as D, Array as A


def ins(operands, op):
    return q.ContentStreamInstruction(operands, q.Operator(op))



def has_semantic_marking(ops):
    """Preserve balanced optional-content layer wrappers; don't nest source MCIDs."""
    depth = 0
    for op in ops:
        name = str(op.operator)
        if name in ('BMC', 'INLINE IMAGE'): return True
        if name == 'BDC':
            if len(op.operands) != 2 or str(op.operands[0]) != '/OC': return True
            if isinstance(op.operands[1], D) and '/MCID' in op.operands[1]: return True
            depth += 1
        elif name == 'EMC':
            if depth == 0: return True
            depth -= 1
    return depth != 0


def build(pdf, page_text, issue):
    root = pdf.make_indirect(D(Type=N.StructTreeRoot, K=A()))
    doc = pdf.make_indirect(D(Type=N.StructElem, S=N.Document, P=root, K=A()))
    root.K.append(doc)
    nums = A()
    model = []
    for page_no, page in enumerate(pdf.pages):
        ops = list(q.parse_content_stream(page))
        # Existing marked content may already have semantic associations.
        # Keep these streams untouched instead of nesting invalid MCIDs.
        if has_semantic_marking(ops):
            issue('structure', page_no + 1, 'This page has existing marked content or inline images. Repair its structure in the source document or a specialist PDF editor.', False)
            continue
        xobjs = page.Resources.get('/XObject', D())
        # An untagged Form invocation can be one Figure; its original nested
        # streams stay intact. Reject pre-existing semantic associations, cycles,
        # unknown XObjects and excessive recursion rather than rewriting them.
        budget = [20000]
        def safe_artwork(name, resources, ancestors=()):
            obj = resources.get('/XObject', D()).get(name)
            if obj is None: return False
            subtype = str(obj.get('/Subtype', ''))
            if subtype == '/Image': return True
            if subtype != '/Form' or len(ancestors) >= 32 or obj.objgen in ancestors:
                return False
            if '/StructParents' in obj or '/StructParent' in obj: return False
            nested_ops = list(q.parse_content_stream(obj))
            budget[0] -= len(nested_ops)
            if budget[0] < 0: return False
            if has_semantic_marking(nested_ops):
                return False
            nested_resources = obj.get('/Resources', resources)
            return all(safe_artwork(v.operands[0], nested_resources, ancestors + (obj.objgen,))
                       for v in nested_ops if str(v.operator) == 'Do')
        if any(not safe_artwork(o.operands[0], page.Resources) for o in ops if str(o.operator) == 'Do'):
            issue('structure', page_no + 1, 'This page has nested artwork with existing marked content, unknown resources, or complex recursive structure. Its reading structure needs a specialist PDF editor.', False)
            continue
        nested = any(str(o.operator) == 'Do' and str(xobjs.get(o.operands[0], D()).get('/Subtype', '')) == '/Form' for o in ops)
        if nested:
            issue('nested_drawing', page_no + 1, 'Nested CAD artwork is preserved as a Figure. Its description must include the entire drawing, all meaningful labels and dimensions, units, view direction, features and relationships. Text inside that Figure does not have separate reading-order tags. Have the instructor verify the explanation.', True)
        parent = pdf.make_indirect(D(Type=N.StructElem, S=N.Sect, P=doc, K=A()))
        doc.K.append(parent)
        page.obj.StructParents = page_no
        page.obj.Tabs = N.S
        parents = A()
        output = []
        index = 0
        # One page-level Figure references all vector painting MCIDs. Text labels
        # retain their own tags; geometry stays in the original vector operators.
        vector = None
        paints = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'sh'}
        for op in ops:
            operator = str(op.operator)
            if operator in paints:
                if vector is None:
                    vector = pdf.make_indirect(D(Type=N.StructElem, S=N.Figure, P=parent,
                                                 Pg=page.obj, K=A()))
                    parent.K.append(vector)
                    model.append({'page': page_no + 1, 'mcid': -1, 'role': 'Figure',
                                  'kind': 'figure', 'object': list(vector.objgen),
                                  'label': 'Drawing / vector graphics on this page', 'alt': ''})
                vector.K.append(index); parents.append(vector)
                output += [ins([N.Figure, D(MCID=index)], 'BDC'), op, ins([], 'EMC')]
                index += 1
                continue
            kind = 'text' if operator in ('Tj', 'TJ', "'", '"') else (
                'figure' if operator == 'Do' else None)
            if kind:
                role = 'P' if kind == 'text' else 'Figure'
                element = pdf.make_indirect(D(Type=N.StructElem, S=N('/' + role), P=parent,
                                              Pg=page.obj, K=index))
                parent.K.append(element); parents.append(element)
                output += [ins([N('/' + role), D(MCID=index)], 'BDC'), op, ins([], 'EMC')]
                entry = {'page': page_no + 1, 'mcid': index, 'role': role, 'kind': kind,
                         'object': list(element.objgen), 'label': f'{role} {index + 1}', 'alt': ''}
                model.append(entry)
                index += 1
            else:
                output.append(op)
        page.Contents = pdf.make_stream(q.unparse_content_stream(output))
        nums.extend([page_no, parents])
        texts = [m for m in model if m['page'] == page_no + 1 and m['kind'] == 'text']
        lines = page_text[page_no]
        # Only attach a preview label when mapping is unambiguous; never use it
        # to replace the source glyphs or imply complex layout was understood.
        if len(texts) == len(lines):
            for entry, line in zip(texts, lines):
                entry['label'] = line[:200]
        if index:
            issue('reading', page_no + 1, 'Check the numbered content items against this page. Set heading roles and correct the reading order where needed.', True)
        if any(m['page'] == page_no + 1 and m['kind'] == 'figure' for m in model):
            issue('figures', page_no + 1, 'Describe each meaningful image or drawing. For isometric drawings explain the object, view direction, geometry, dimensions and units, holes, hidden lines, and the learning task. A vector Figure groups the graphics on that page. Do not mark technical drawings decorative.', True)
        if not index and page_text[page_no]:
            issue('structure', page_no + 1, 'Text could not be associated with page content. Remediate using the source document.', False)
    root.ParentTree = pdf.make_indirect(D(Nums=nums))
    root.ParentTreeNextKey = len(pdf.pages)
    pdf.Root.StructTreeRoot = root
    pdf.Root.MarkInfo = D(Marked=True)
    return model


def existing_model(pdf):
    result, seen = [], set()
    def walk(obj, page=None):
        if not isinstance(obj, q.Object):
            return
        if isinstance(obj, A):
            for child in obj:
                walk(child, page)
            return
        if not isinstance(obj, D):
            return
        key = obj.objgen
        if key != (0, 0):
            if key in seen: return
            seen.add(key)
        if len(seen) > 50000:
            raise ValueError('Structure too large')
        pg = obj.get('/Pg')
        if pg is not None:
            page = next((i + 1 for i, p in enumerate(pdf.pages) if p.obj.objgen == pg.objgen), page)
        role = str(obj.get('/S', ''))[1:]
        k = obj.get('/K')
        if role and obj.is_indirect and (isinstance(k, int) or role == 'Figure'):
            result.append({'page': page or 1, 'object': list(key), 'mcid': int(k) if isinstance(k, int) else -1,
                           'kind': 'figure' if role == 'Figure' else 'text', 'role': role,
                           'label': str(obj.get('/ActualText', role)), 'alt': str(obj.get('/Alt', '')),
                           'actual_text': str(obj.ActualText) if '/ActualText' in obj else None})
        if isinstance(k, (D, A)): walk(k, page)
    if '/StructTreeRoot' in pdf.Root:
        walk(pdf.Root.StructTreeRoot)
    return result


def apply(pdf, edits):
    """Only edit selected existing elements; no false PDF/UA conformance flag."""
    model = existing_model(pdf)
    lookup = {tuple(m['object']): m for m in model}
    for edit in edits.get('elements', []):
        key = tuple(edit['object'])
        if key not in lookup: raise ValueError('Review no longer matches the prepared copy')
        obj = pdf.get_object(key)
        role = edit.get('role', lookup[key]['role'])
        if role != lookup[key]['role'] and role not in ('P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'Figure', 'TH', 'TD', 'Span', 'LBody'):
            raise ValueError('Unsupported role')
        obj.S = N('/' + role)
        if 'alt' in edit:
            if edit['alt'].strip(): obj.Alt = edit['alt'].strip()
            elif '/Alt' in obj: del obj['/Alt']
        if edit.get('actual_text') is not None:
            obj.ActualText = edit['actual_text']
        if edit.get('decorative'):
            # Convert this exact marked content to Artifact and remove its tree entry.
            pg = pdf.pages[lookup[key]['page'] - 1]
            mcid = lookup[key]['mcid']
            if mcid < 0: raise ValueError('Complex image requires specialist artifact editing')
            ops = list(q.parse_content_stream(pg))
            found = False
            for n, op in enumerate(ops):
                if str(op.operator) == 'BDC' and isinstance(op.operands[1], D) and op.operands[1].get('/MCID') == mcid:
                    ops[n] = ins([N.Artifact], 'BMC'); found = True
            if not found: raise ValueError('Cannot identify image content safely')
            pg.Contents = pdf.make_stream(q.unparse_content_stream(ops))
            parent = obj.P
            parent.K = A([v for v in parent.K if v.objgen != key])
            nums = pdf.Root.StructTreeRoot.ParentTree.get('/Nums')
            if nums is None: raise ValueError('Complex parent tree requires specialist review')
            for n in range(0, len(nums), 2):
                if nums[n] == pg.obj.StructParents: nums[n + 1][mcid] = None
    # Reorder siblings only: preserve parent relationships in pre-existing trees.
    order = edits.get('order', [])
    groups = {}
    for key in order:
        obj = pdf.get_object(tuple(key))
        if tuple(key) in lookup: groups.setdefault(obj.P.objgen, []).append(obj)
    for key, desired in groups.items():
        parent = pdf.get_object(key)
        if not isinstance(parent.K, A): continue
        keys = {o.objgen for o in desired}
        it = iter(desired)
        parent.K = A([next(it) if isinstance(o, D) and o.objgen in keys else o for o in parent.K])
    for table in edits.get('tables', []):
        rows = table['rows']
        objs = [pdf.get_object(tuple(k)) for row in rows for k in row]
        if not objs: continue
        parent = objs[0].P
        if any(o.P.objgen != parent.objgen for o in objs):
            raise ValueError('Table cells must share a section')
        ids = {o.objgen for o in objs}
        if len(ids) != len(objs): raise ValueError('Repeated table cell')
        tab = pdf.make_indirect(D(Type=N.StructElem, S=N.Table, P=parent, K=A()))
        for ri, row in enumerate(rows):
            tr = pdf.make_indirect(D(Type=N.StructElem, S=N.TR, P=tab, K=A()))
            tab.K.append(tr)
            for key in row:
                cell = pdf.get_object(tuple(key)); cell.P = tr
                cell.S = N.TH if ri == 0 else N.TD
                if ri == 0: cell.A = D(O=N.Table, Scope=N.Column)
                tr.K.append(cell)
        children, inserted = A(), False
        for o in parent.K:
            if isinstance(o, D) and o.objgen in ids:
                if not inserted: children.append(tab); inserted = True
            else: children.append(o)
        parent.K = children
    for group in edits.get('lists', []):
        objs = [pdf.get_object(tuple(k)) for k in group]
        if not objs: continue
        parent = objs[0].P
        if any(o.P.objgen != parent.objgen for o in objs): raise ValueError('List items must share a section')
        li_root = pdf.make_indirect(D(Type=N.StructElem, S=N.L, P=parent, K=A()))
        ids = {o.objgen for o in objs}
        for obj in objs:
            li = pdf.make_indirect(D(Type=N.StructElem, S=N.LI, P=li_root, K=A()))
            obj.P = li; obj.S = N.LBody; li.K.append(obj); li_root.K.append(li)
        children, inserted = A(), False
        for obj in parent.K:
            if isinstance(obj, D) and obj.objgen in ids:
                if not inserted: children.append(li_root); inserted = True
            else: children.append(obj)
        parent.K = children
