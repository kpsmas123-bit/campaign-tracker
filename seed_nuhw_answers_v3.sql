-- Seed NUHW v3 draft answers into questionnaire_answers
-- Run in Supabase SQL Editor (bypasses RLS)
-- Replaces seed_nuhw_answers.sql (v2-2)

INSERT INTO questionnaire_answers (org_slug, question_id, topic, answer_text)
VALUES

  ('nuhw', 'b1', 'background_bio',
   $body$I have not held elected office before. This is my first time running for elected office.$body$),

  ('nuhw', 'b2', 'background_bio',
   $body$I coordinate the Safe Pathways to School volunteer program for Berkeley High School. I co-facilitate a Bay Resistance Pod for the 94702 zip code. I am the volunteer registrar for a summer music and arts camp, where I also founded the mediation team for conflict resolution.$body$),

  ('nuhw', 'b3', 'background_bio',
   $body$I was born and raised in Berkeley, California, by my single mom (also a Berkeley native), who worked as an elementary school secretary for Berkeley Unified. My (absentee) father was a professor in UC Berkeley's Department of Music. I attended Berkeley Public Schools through 6th grade, and attended high school in Oakland. I moved to Pennsylvania for college, where I was an urban studies major at Bryn Mawr College. My first career out of college was as a gardener, horticulturist, and eventually a garden educator. It was in that capacity that I worked for Berkeley Unified from 2009-2015. For the 2013-14 school year, I was the AFT Local 6192 Berkeley Council of Classified Employees Organizer, on a grant from the California Federation of Teachers. In 2014, I returned to school for a master's in counseling psychology, and I have been in private practice as a child and adolescent therapist since 2020.$body$),

  ('nuhw', 'b4', 'labor_solidarity',
   $body$I am currently self-employed, and ineligible for union membership, but I was a member of AFT Local 6192, the Berkeley Council of Classified Employees, when I worked for the Berkeley Unified School District. I was a Site Representative for Thousand Oaks Elementary, and was the Union Organizer for the 2013-2014 school year.$body$),

  ('nuhw', 'b5', 'endorsements',
   $body$I am endorsed by Jennifer Shanoski, Berkeley School Director; Soli Alpert, Berkeley Rent Board President; (more coming)$body$),

  ('nuhw', 'b6', 'campaign_plan',
   $body$I have raised over $2000 since launching my ActBlue page on July 5th, and intend to raise at least the $8667 I need to reach my maximum public financing matching for the City of Berkeley, for a total of $60,000.$body$),

  ('nuhw', 'b7', 'campaign_plan',
   $body$I have not conducted any polling.$body$),

  ('nuhw', 's21', 'why_running',
   $body$I am running for office to protect Berkeley's progressive values, and build for Berkeley's future. I am a therapist for our community's children and young adults, and before that I was a garden educator and proud union member. When my coworkers faced layoffs, I took on the fight as full-time organizer with AFT Local 6192, the Berkeley Council of Classified Employees.

Now I am running as a candidate who can cut through the noise and unite rather than divide my district. Too often we're told we have to choose between a functioning city government and our progressive values, and I am running because I reject the premise of that argument. I am both pro-housing and pro-tenant. I believe in investing in public safety while rejecting surveillance and militarization. And I believe we can provide basic city services and compassion to homeowners, tenants, and our unhoused community without conflict. I have decades of relationships within the City that prove I am a community-driven, results-oriented organizer.$body$),

  ('nuhw', 's22', 'why_running',
   $body$I want to focus on livability - increasing affordability, improving city services, preserving educational and cultural excellence, focusing on public safety that doesn't jeopardize civil liberties.$body$),

  ('nuhw', 's23', 'endorsement_ask',
   $body$Coming from a union household, as a former union member and organizer, my theory of political power is grounded in the work of organized labor. I am seeking the NUHW endorsement not simply to get elected, but to begin a relationship of co-governance and collaboration.

As a mental health professional who has witnessed the impact of our mental health crisis, I stood with Kaiser Nurse Practitioners when they rallied for patient care. I want to continue to learn from and build solidarity with your membership so that when elected, I can amplify your work and bring your proposals into city hall.

NUHW could be incredibly supportive with field and volunteer operations. We would love the opportunity to reach out directly to your Berkeley members and win their support as voters, volunteers, or donors.$body$),

  ('nuhw', 's24', 'endorsement_ask',
   $body$I participate in Berkeley's Sanctuary City Taskforce, and am a member of the Friends of Ohlone Park. I am also a member of the Brass Liberation Orchestra, which provides musical support for aligned protests and street actions.$body$),

  ('nuhw', 's3a', 'labor_solidarity',
   $body$All nine boxes checked.$body$),

  ('nuhw', 's3b', 'labor_solidarity',
   $body$As a member of Brass Liberation Orchestra, I have provided musical support for many labor actions, including the Richmond Teacher's Union last spring, and the Kaiser Nurse Practitioners in January. I have also met with local electeds, like Assemblymember Buffy Wicks, to advocate for NUHW priorities, like CalCare/Medicare for All.$body$),

  ('nuhw', 's4a', 'labor_law',
   $body$All four marked Yes: card-check neutrality, equal access, ban on captive-audience meetings, short election period.$body$),

  ('nuhw', 's5a', 'healthcare_standards',
   $body$While our recent city budget cut some of Berkeley's most important public health programs, including our Mobile Crisis Team, we must protect what remains and center our workers in every decision going forward.

Berkeley is one of the few cities in California that is its own behavioral health jurisdiction, receiving state Behavioral Health Services Act funding directly rather than through the county, about $10 million a year from July 2026 through June 2029. The City is finishing its first Three-Year Integrated Plan under the new BHSA for fiscal years 2027 through 2029, which the next Council will vote on, and that funding is separate from the general fund shortfall driving the recent cuts. The draft plan proposes to expand substance use disorder services, increase peer support and wellness services, and strengthen support for transition-age youth. I would work to keep those investments anchored in care that residents can actually reach.

I would also seek out new funding sources and deeper collaboration with the county, and work closely with our county supervisor, Nikki Fortunato Bas, to keep our programs coordinated rather than duplicative.$body$),

  ('nuhw', 's5b', 'disease_protection',
   $body$California already has the nation's only standard protecting health workers from airborne disease, the Cal/OSHA Aerosol Transmissible Diseases standard, and it was written with labor's support. The gap is usually enforcement and speed, not the rules on paper. Because Berkeley is its own public health jurisdiction, our health officer can act on an airborne threat directly rather than waiting on the county, and I would make sure we use that authority to move quickly and hold covered employers, including shelters and clinics, to that standard. At the city level, I would also protect and strengthen our local Paid Sick Leave Ordinance so that no health or care worker, including part-time and contracted staff, is ever forced to choose between a paycheck and their patients' safety. And I would use the city's own role as an employer and purchaser to require respiratory protection and maintain a stockpile of NIOSH-certified respirators, so frontline workers are never rationed protection again.$body$),

  ('nuhw', 's6a', 'voting_rights',
   $body$I am grateful to live in a community with strong election protections, and I would work to ensure those protections stay intact. I would fight for the continued availability of universal absentee ballots, accessible early voting sites, abundant ballot drop-off locations (with attention to equitable distribution of said sites), and the availability of ballots and voter information guides in multiple languages. I also supported the expansion of voting rights down to age 16 for school board elections, and I support extending school board voting to non-citizen parents, who are among the most directly affected stakeholders in our schools.$body$),

  ('nuhw', 's7a', 'behavioral_health',
   $body$As a mental health clinician myself, I understand the importance of health care parity that treats behavioral health access as just as essential as all other kinds of health care, and I believe health care access is a human right. I worked on the Berkeley vs. Big Soda campaign back in 2014, which provided a funding source for nutrition education and health access for low-income communities in Berkeley.$body$),

  ('nuhw', 's8a', 'single_payer',
   $body$Yes, I strongly support single payer healthcare, and have met with Buffy Wicks' office to advocate for such.$body$),

  ('nuhw', 's8b', 'single_payer',
   $body$I would support a Berkeley council resolution backing CalCare and the unified-financing work the state began under SB 770, and I would keep meeting directly with our state delegation, as I already have with Assemblymember Wicks' office, alongside NUHW and the Healthy California NOW coalition.$body$)

ON CONFLICT (org_slug, question_id) DO UPDATE SET
  answer_text = EXCLUDED.answer_text,
  topic = EXCLUDED.topic;
