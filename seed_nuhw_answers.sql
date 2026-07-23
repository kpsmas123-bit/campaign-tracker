-- Seed existing NUHW draft answers from v2-2 into questionnaire_answers
-- Run in Supabase SQL Editor (bypasses RLS)

INSERT INTO questionnaire_answers (org_slug, question_id, topic, answer_text)
VALUES
  ('nuhw', 'b1', 'background_bio',
   'I have not held elected office before. This is my first time running for elected office.'),

  ('nuhw', 'b2', 'background_bio',
   'I coordinate the Safe Pathways to School volunteer program for Berkeley High School. I co-facilitate a Bay Resistance Pod for the 94702 zip code. I am the volunteer registrar for a summer music and arts camp, where I also founded the mediation team for conflict resolution.'),

  ('nuhw', 'b3', 'background_bio',
   E'I was born and raised in Berkeley, California, by my single mom (also a Berkeley native), who worked as an elementary school secretary for Berkeley Unified. My (absentee) father was a professor in UC Berkeley\'s Department of Music. I attended Berkeley Public Schools through 6th grade, and attended high school in Oakland. I moved to Pennsylvania for college, where I was an urban studies major at Bryn Mawr College. My first career out of college was as a gardener, horticulturist, and eventually a garden educator. It was in that capacity that I worked for Berkeley Unified from 2009-2015. For the 2013-14 school year, I was the AFT Local 6192 Berkeley Council of Classified Employees Organizer, on a grant from the California Federation of Teachers. In 2014, I returned to school for a master\'s in counseling psychology, and I have been in private practice as a child and adolescent therapist since 2020.'),

  ('nuhw', 'b4', 'labor_solidarity',
   'I am currently self-employed, and ineligible for union membership, but I was a member of AFT Local 6192, the Berkeley Council of Classified Employees, when I worked for the Berkeley Unified School District. I was a Site Representative for Thousand Oaks Elementary, and was the Union Organizer for the 2013-2014 school year.'),

  ('nuhw', 'b5', 'endorsements',
   'I am endorsed by Jennifer Shanoski, Berkeley School Director; Soli Alpert, Berkeley Rent Board President; (more coming)'),

  ('nuhw', 'b6', 'campaign_plan',
   'I have raised over $2000 since launching my ActBlue page on July 5th, and intend to raise at least the $8667 I need to reach my maximum public financing matching for the City of Berkeley, for a total of $60,000.'),

  ('nuhw', 'b7', 'campaign_plan',
   'I have not conducted any polling.'),

  ('nuhw', 's21', 'why_running',
   E'I am running for office to protect Berkeley\'s progressive values, and build for Berkeley\'s future. I am a pro-housing and pro-tenant candidate, and a collaborator and bridge-builder. I have decades of relationships within the City that prove I am a community-driven, results-oriented organizer.'),

  ('nuhw', 's22', 'why_running',
   E'I want to focus on livability - increasing affordability, improving city services, preserving educational and cultural excellence, focusing on public safety that doesn\'t jeopardize civil liberties.'),

  ('nuhw', 's23', 'endorsement_ask',
   'I am a strong supporter of labor, and the power of collective action that unions represent. I would welcome person-power from NUHW - door knocking, phone and text banking, etc.'),

  ('nuhw', 's24', 'why_running',
   E'I participate in Berkeley\'s Sanctuary City Taskforce, and am a member of the Friends of Ohlone Park. I am also a member of the Brass Liberation Orchestra, which provides musical support for aligned protests and street actions.'),

  ('nuhw', 's3a', 'labor_solidarity',
   'All nine boxes checked.'),

  ('nuhw', 's3b', 'labor_solidarity',
   E'As a member of Brass Liberation Orchestra, I have provided musical support for many labor actions, including the Richmond Teacher\'s Union last spring, and the Kaiser Nurse Practitioners in January. I have also met with local electeds, like Assemblymember Buffy Wicks, to advocate for NUHW priorities, like CalCare/Medicare for All.'),

  ('nuhw', 's4a', 'labor_law',
   'All four marked Yes: card-check neutrality, equal access and time, ban on captive-audience meetings, short election period.'),

  ('nuhw', 's5a', 'healthcare_standards',
   E'Berkeley has its own Department of Public Health, and I would fiercely advocate for adequate staffing, bans on contracting out, and strong workplace safety.'),

  ('nuhw', 's6a', 'voting_rights',
   'I am grateful to live in a community with strong election protections, and I would work to ensure those protections stay intact. I would fight for the continued availability of universal absentee ballots, accessible early voting sites, abundance ballot drop-off locations (with attention to equitable distribution of said sites), and the availability of ballots and voter information guides in multiple languages. I also supported the expansion of voting rights down to age 16 for school board elections.'),

  ('nuhw', 's7a', 'behavioral_health',
   'As a mental health clinician myself, I understand the importance of health care parity that treats behavioral health access as just as essential as all other kinds of health care, and I believe health care access is a human right. I worked on the Berkeley vs. Big Soda campaign back in 2014, which provided a funding source for nutrition education and health access for low-income communities in Berkeley.'),

  ('nuhw', 's8a', 'single_payer',
   E'Yes, I strongly support single payer healthcare, and have met with Buffy Wicks\' office to advocate for such.')

ON CONFLICT (org_slug, question_id) DO UPDATE SET
  answer_text = EXCLUDED.answer_text,
  topic = EXCLUDED.topic;
