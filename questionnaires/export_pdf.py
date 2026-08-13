"""Render submitted questionnaires as PDFs for the Drive archive.

The answers live in Supabase behind RLS, not in this repo, so this script does
not talk to the database. It takes an export blob produced by the SQL in
export_answers.sql and joins it against the question text in data/*.json.

Only organisations whose status is 'finished' are rendered — the point of the
archive is a record of what was actually submitted, not a snapshot of drafts.

    python3 export_pdf.py <export.json> <outdir>

The export blob contains campaign answers. Keep it out of the repo.
"""
import json
import os
import re
import sys

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer, KeepTogether)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')

INK = colors.HexColor('#1A1A18')
MUTED = colors.HexColor('#6E6E6C')
FAINT = colors.HexColor('#A8A8AC')
RULE = colors.HexColor('#E6E6E2')

S = {
    'title': ParagraphStyle('title', fontName='Times-Roman', fontSize=19,
                            leading=23, textColor=INK, spaceAfter=3),
    'sub': ParagraphStyle('sub', fontName='Helvetica', fontSize=9.5,
                          leading=13, textColor=MUTED, spaceAfter=1),
    'meta': ParagraphStyle('meta', fontName='Helvetica', fontSize=8,
                           leading=11, textColor=FAINT, spaceAfter=0),
    'section': ParagraphStyle('section', fontName='Helvetica-Bold', fontSize=8,
                              leading=11, textColor=MUTED, spaceBefore=20,
                              spaceAfter=8, borderPadding=0),
    'q': ParagraphStyle('q', fontName='Helvetica-Bold', fontSize=10,
                        leading=14, textColor=INK, spaceBefore=11, spaceAfter=4),
    'a': ParagraphStyle('a', fontName='Helvetica', fontSize=10, leading=15,
                        textColor=INK, alignment=TA_LEFT, spaceAfter=3),
    'choice': ParagraphStyle('choice', fontName='Helvetica', fontSize=10,
                             leading=15, textColor=INK, leftIndent=12,
                             spaceAfter=1),
    'blank': ParagraphStyle('blank', fontName='Helvetica-Oblique', fontSize=9.5,
                            leading=14, textColor=FAINT, spaceAfter=3),
    'note': ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.5,
                           leading=12, textColor=MUTED, spaceAfter=6),
    'contact': ParagraphStyle('contact', fontName='Helvetica', fontSize=9.5,
                              leading=14, textColor=INK, spaceAfter=1),
}


def esc(s):
    """Escape for reportlab's mini-markup and convert newlines to breaks."""
    s = (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\n{2,}', '<br/><br/>', s)
    return s.replace('\n', '<br/>')


def draw_furniture(canvas, doc):
    """Rule and page number in the footer; nothing in the header after page 1."""
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.9 * inch, 0.72 * inch, letter[0] - 0.9 * inch, 0.72 * inch)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(FAINT)
    canvas.drawString(0.9 * inch, 0.55 * inch, doc.footer_left)
    canvas.drawRightString(letter[0] - 0.9 * inch, 0.55 * inch,
                           'Page %d' % canvas.getPageNumber())
    canvas.restoreState()


def build(org_data, answers, status_row, out_path):
    """One PDF for one organisation. Returns the number of answered questions."""
    doc = BaseDocTemplate(out_path, pagesize=letter,
                          leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                          topMargin=0.85 * inch, bottomMargin=0.95 * inch,
                          title='%s — Candidate Questionnaire' % org_data['org'],
                          author=org_data.get('candidate', ''))
    doc.footer_left = '%s  ·  %s' % (org_data['org'], org_data.get('candidate', ''))
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')
    doc.addPageTemplates([PageTemplate(id='p', frames=[frame],
                                       onPage=draw_furniture)])

    story = [
        Paragraph(esc(org_data['org']), S['title']),
        Paragraph('Candidate Questionnaire &middot; %s' % esc(org_data.get('cycle', '')),
                  S['sub']),
        Paragraph(esc(org_data.get('candidate', '')), S['sub']),
        Spacer(1, 10),
    ]

    st = status_row or {}
    submitted = st.get('submitted_at') or st.get('updated_at') or ''
    if submitted:
        label = 'Submitted' if st.get('submitted_at') else 'Marked done'
        story.append(Paragraph('%s %s' % (label, esc(str(submitted)[:10])), S['meta']))
    story.append(Spacer(1, 6))

    contact = [f for f in org_data.get('contact_fields', []) if (f.get('v') or '').strip()]
    if contact:
        story.append(Paragraph('CANDIDATE INFORMATION', S['section']))
        for f in contact:
            story.append(Paragraph(
                '<font color="#6E6E6C">%s:</font> %s' % (esc(f['label']), esc(f['v'])),
                S['contact']))

    answered = 0
    seen_section = None
    for q in org_data.get('questions', []):
        qid = q['id']
        text = (answers.get(qid) or '').strip()
        picks = [c for c in (answers.get('__c__' + qid) or '').split('\n') if c.strip()]
        if not text and not picks:
            continue
        answered += 1

        # The question stem, any section header above it and the checkbox picks
        # stay on one page together — a question stranded at the foot of a page
        # with its answer overleaf is the one break that misreads badly.
        head = []
        sec = q.get('section') or ''
        if sec and sec != seen_section:
            seen_section = sec
            head.append(Paragraph(esc(sec.upper()), S['section']))
            if q.get('section_note'):
                head.append(Paragraph(esc(q['section_note']), S['note']))
        head.append(Paragraph(esc(q['question']), S['q']))
        for c in picks:
            head.append(Paragraph('&#9632;&nbsp; %s' % esc(c.strip()), S['choice']))
        story.append(KeepTogether(head))
        if text:
            story.append(Paragraph(esc(text), S['a']))

    doc.build(story)
    return answered


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    export = json.load(open(sys.argv[1]))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    status = {r['org_slug']: r for r in export.get('status', [])}
    by_org = {}
    for r in export.get('answers', []):
        by_org.setdefault(r['org_slug'], {})[r['question_id']] = r.get('answer_text') or ''

    finished = sorted(s for s, r in status.items() if r.get('status') == 'finished')
    if not finished:
        sys.exit('No questionnaires are marked Done. Nothing to archive.')

    made = []
    for slug in finished:
        path = os.path.join(DATA, slug + '.json')
        if not os.path.exists(path):
            print('  ! %s marked Done but has no data file — skipped' % slug)
            continue
        org_data = json.load(open(path))
        name = re.sub(r'[^\w\- ]+', '', org_data['org']).strip()
        out = os.path.join(outdir, '%s — Questionnaire (Daria Wrubel D1).pdf' % name)
        n = build(org_data, by_org.get(slug, {}), status.get(slug), out)
        total = len(org_data.get('questions', []))
        made.append((slug, out, n, total))
        print('  %-6s %2d/%-2d answered  ->  %s' % (slug, n, total, os.path.basename(out)))

    print('\n%d PDF(s) in %s' % (len(made), outdir))


if __name__ == '__main__':
    main()
