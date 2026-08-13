-- Export submitted questionnaires for the Drive archive.
--
-- Run in the Supabase SQL Editor, then copy the single cell of output and save
-- it as export.json. Feed that to export_pdf.py.
--
-- Only organisations in the Done group are included, and only rows that
-- actually carry text — blank drafts are not part of the record.

select json_build_object(
  'status', (
    select coalesce(json_agg(to_jsonb(s)), '[]'::json)
    from questionnaire_status s
    where s.status = 'finished'
  ),
  'answers', (
    select coalesce(json_agg(json_build_object(
             'org_slug',    a.org_slug,
             'question_id', a.question_id,
             'answer_text', a.answer_text,
             'approved',    a.approved
           )), '[]'::json)
    from questionnaire_answers a
    where a.org_slug in (select org_slug from questionnaire_status where status = 'finished')
      and coalesce(a.answer_text, '') <> ''
  )
) as export;

-- If the answers array comes back empty but the status array does not, the
-- questionnaires are marked Done without any saved answers — check the tracker
-- before assuming the export failed.
