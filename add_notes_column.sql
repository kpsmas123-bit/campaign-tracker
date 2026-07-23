-- Add notes column to questionnaire_answers
-- Run in Supabase SQL Editor

ALTER TABLE questionnaire_answers ADD COLUMN IF NOT EXISTS notes text DEFAULT '';
