#!/usr/bin/env python3
"""Fill a blank org questionnaire PDF from the editor's saved answers.

Usage:
    python3 questionnaires/fill_pdf.py <blank.pdf> <answers.json> <out.pdf> [--org wfp]

answers.json is keyed by question number:

    {"16": {"choice": ["Yes"], "text": "Costa-Hawkins is the reason..."},
     "25": {"choice": ["Youth 0-18", "Seniors 65+"]}}

Checkbox targets come from the `choices` block in questionnaires/data/<org>.json,
which records each option's PDF field name and export value. Those were read off
the blank form rather than guessed, so a form revision requires re-deriving them
(see the field-dump in the commit that added this file) instead of editing by hand.

Radio groups need /V on the parent field AND /AS on the selected kid widget.
Setting only /V leaves the box visually unticked in most viewers.
"""
import json, sys, argparse
from pypdf import PdfWriter
from pypdf.generic import NameObject


def load_choice_map(org_json):
    """question number -> {'type', 'pdf_field', 'choices': [{label, pdf, pdf_field?}]}"""
    doc = json.load(open(org_json, encoding='utf-8'))
    out = {}
    for q in doc['questions']:
        if not q.get('choices'):
            continue
        num = q['id'].rsplit('_q', 1)[-1]
        out[num] = {
            'type': q.get('choice_type', 'single'),
            'pdf_field': q.get('pdf_field'),
            'choices': q['choices'],
        }
    return out


def _field_name(obj):
    """Walk up to whichever node carries /T."""
    node = obj
    while node is not None:
        if node.get('/T'):
            return str(node.get('/T'))
        node = node.get('/Parent')
    return None


def set_button(writer, field_name, on_state):
    """Tick a radio kid or a checkbox, setting both /V and /AS.

    This form stores some checkboxes TWICE — once as a page annotation and
    again as a separate object under /AcroForm/Fields, with different object
    numbers. Writing only the page copy leaves get_fields() and some viewers
    reading a stale /V, so both locations are updated. Radio groups are not
    affected, since their parent field is the /Fields entry itself.

    Returns True if any widget was found and set.
    """
    hit = False

    # 1. Page annotations — carry the visible /AS appearance state
    for page in writer.pages:
        for annot in (page.get('/Annots') or []):
            o = annot.get_object()
            if o.get('/Subtype') != '/Widget' or _field_name(o) != field_name:
                continue
            ap = o.get('/AP')
            states = [str(k) for k in ap['/N'].keys()] if ap and '/N' in ap else []
            parent = o.get('/Parent')
            target = parent.get_object() if parent else o
            if on_state in states:
                target[NameObject('/V')] = NameObject(on_state)
                o[NameObject('/AS')] = NameObject(on_state)
                hit = True
            elif states:
                # Sibling kid of the selected one — force it off
                o[NameObject('/AS')] = NameObject('/Off')

    # 2. /AcroForm/Fields entries — what get_fields() and many viewers read
    root = writer._root_object
    if '/AcroForm' in root and '/Fields' in root['/AcroForm']:
        stack = list(root['/AcroForm']['/Fields'])
        while stack:
            fo = stack.pop().get_object()
            if '/Kids' in fo:
                stack.extend(fo['/Kids'])
            if str(fo.get('/T') or '') != field_name:
                continue
            # Only write when this field genuinely offers the state, either on
            # itself (checkbox) or on one of its kids (radio group). Setting /V
            # on any field that merely has kids corrupts unrelated questions.
            ap = fo.get('/AP')
            own = [str(k) for k in ap['/N'].keys()] if ap and '/N' in ap else []
            kid_states = []
            for kid in (fo.get('/Kids') or []):
                kap = kid.get_object().get('/AP')
                if kap and '/N' in kap:
                    kid_states += [str(k) for k in kap['/N'].keys()]
            if on_state in own:
                fo[NameObject('/V')] = NameObject(on_state)
                fo[NameObject('/AS')] = NameObject(on_state)
                hit = True
            elif on_state in kid_states:
                fo[NameObject('/V')] = NameObject(on_state)
                hit = True

    return hit


def main():
    p = argparse.ArgumentParser()
    p.add_argument('blank_pdf')
    p.add_argument('answers_json')
    p.add_argument('out_pdf')
    p.add_argument('--org', default='wfp')
    p.add_argument('--data-dir', default='questionnaires/data')
    a = p.parse_args()

    cmap = load_choice_map(f'{a.data_dir}/{a.org}.json')
    answers = json.load(open(a.answers_json, encoding='utf-8'))

    # clone_from, not append(): append() rebuilds /AcroForm and silently drops
    # most fields — on this form it kept 25 of 81, losing every standalone
    # checkbox. clone_from preserves the full field tree.
    writer = PdfWriter(clone_from=a.blank_pdf)

    ticked = skipped = 0
    for num, entry in sorted(answers.items(), key=lambda kv: int(kv[0])):
        selected = entry.get('choice') or []
        if not selected:
            continue
        spec = cmap.get(str(num))
        if not spec:
            print(f'  Q{num}: no checkbox on this form — skipped')
            skipped += 1
            continue
        for label in selected:
            choice = next((c for c in spec['choices'] if c['label'] == label), None)
            if not choice:
                print(f'  Q{num}: unknown option {label!r} — skipped')
                skipped += 1
                continue
            field = choice.get('pdf_field') or spec.get('pdf_field')
            if set_button(writer, field, choice['pdf']):
                print(f'  Q{num}: {label} -> {choice["pdf"]}')
                ticked += 1
            else:
                print(f'  Q{num}: field {field!r} not found — skipped')
                skipped += 1

    # Show field values without needing the viewer to regenerate appearances
    if '/AcroForm' in writer._root_object:
        writer._root_object['/AcroForm'][NameObject('/NeedAppearances')] = \
            __import__('pypdf').generic.BooleanObject(True)

    with open(a.out_pdf, 'wb') as f:
        writer.write(f)
    print(f'\nWrote {a.out_pdf} — {ticked} ticked, {skipped} skipped')
    if skipped:
        sys.exit(1)


if __name__ == '__main__':
    main()
