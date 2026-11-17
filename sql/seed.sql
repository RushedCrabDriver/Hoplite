-- Fictional sample data. Run after schema.sql (and view.sql).
-- All Assignment 1 business rules hold in this data (see README, "Business rules").

INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1,  'Arman',   'Armanov',    'arman.armanov@example.com',    'Nazarbayev University',        'Kazakhstan', '+77010000001'),
 (2,  'Amina',   'Aminova',    'amina.aminova@example.com',    'Astana IT University',         'Kazakhstan', '+77010000002'),
 (3,  'Dana',    'Bekova',     'dana.bekova@example.com',      'Nazarbayev University',        'Kazakhstan', '+77010000003'),
 (4,  'Timur',   'Sadykov',    'timur.sadykov@example.com',    'KBTU',                         'Kazakhstan', '+77010000004'),
 (5,  'Laura',   'Schmidt',    'laura.schmidt@example.com',    'TU Berlin',                    'Germany',    '+4930000005'),
 (6,  'Marco',   'Rossi',      'marco.rossi@example.com',      'Politecnico di Milano',        'Italy',      '+3902000006'),
 (7,  'Aliya',   'Kassymova',  'aliya.kassymova@example.com',  'Satbayev University',          'Kazakhstan', '+77010000007'),
 (8,  'John',    'Miller',     'john.miller@example.com',      'University of Toronto',        'Canada',     '+14160000008'),
 (9,  'Yerlan',  'Ospanov',    'yerlan.ospanov@example.com',   'Al-Farabi KazNU',              'Kazakhstan', '+77010000009'),
 (10, 'Sofia',   'Garcia',     'sofia.garcia@example.com',     'Universidad de Madrid',        'Spain',      '+3491000010'),
 (11, 'Wei',     'Chen',       'wei.chen@example.com',         'Tsinghua University',          'China',      '+8610000011'),
 (12, 'Madina',  'Tulegenova', 'madina.tulegenova@example.com','Nazarbayev University',        'Kazakhstan', '+77010000012');

-- Authors: 1, 2, 3, 7, 8, 9, 11  (author-only: 2, 7, 8, 11)
INSERT INTO author (author_id, orcid) VALUES
 (1, '0000-0001-1111-0001'), (2, '0000-0001-1111-0002'), (3, NULL),
 (7, '0000-0001-1111-0007'), (8, NULL), (9, '0000-0001-1111-0009'), (11, '0000-0001-1111-0011');

INSERT INTO author_research_area (author_id, area_label) VALUES
 (1, 'Machine Learning'), (1, 'Distributed Systems'),
 (2, 'Machine Learning'),
 (3, 'Databases'), (3, 'Data Engineering'),
 (7, 'Databases'),
 (8, 'Graph Analytics'),
 (9, 'Distributed Systems'),
 (11, 'Machine Learning'), (11, 'Data Engineering');

-- Reviewers: 1, 3, 4, 5, 6, 9, 10, 12  (reviewer-only: 4, 5, 6, 10, 12; both roles: 1, 3, 9)
INSERT INTO reviewer (reviewer_id, years_experience) VALUES
 (1, 2), (3, 6), (4, 5), (5, 8), (6, 10), (9, 3), (10, 4), (12, 1);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 (1, 'Databases'), (1, 'Machine Learning'),
 (3, 'Machine Learning'),
 (4, 'Databases'), (4, 'Query Optimization'),
 (5, 'Databases'), (5, 'Distributed Databases'), (5, 'Information Retrieval'),
 (6, 'Machine Learning'), (6, 'Databases'),
 (9, 'Software Engineering'),
 (10, 'Databases'),
 (12, 'Databases');

INSERT INTO conference (conference_id, name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Central Asian Conference on Data Systems', 'CADS 2026',
     'Data management, machine learning and information retrieval.', 'Astana', 'Kazakhstan',
     '2026-06-15', '2026-06-17', '2026-02-15', '2026-04-15'),
 (2, 'European Symposium on Machine Learning Systems', 'EMLS 2026',
     'Systems for training and serving machine learning models.', 'Berlin', 'Germany',
     '2026-09-09', '2026-09-11', '2026-04-01', '2026-06-01'),
 (3, 'Kazakhstan Software Engineering Workshop', 'KSEW 2026',
     'Software testing and verification.', 'Almaty', 'Kazakhstan',
     '2026-12-01', '2026-12-02', '2026-09-01', '2026-10-15');

INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Nazarbayev University'), (1, 'Astana IT University'),
 (2, 'TU Berlin'),
 (3, 'Al-Farabi KazNU'), (3, 'KBTU');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
 (1, 1), (1, 3), (1, 4), (1, 5), (1, 6), (1, 12),
 (2, 3), (2, 5), (2, 6), (2, 9), (2, 10),
 (3, 9), (3, 10);

-- Track 3 and track 6 are empty; conference 3 has no papers.
INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Data Management',          'Storage, indexing and query processing.',  'Databases',              4),
 (2, 1, 'Applied Machine Learning', 'Applications of machine learning.',        'Machine Learning',       3),
 (3, 1, 'Information Retrieval',    'Search and ranking.',                      'Information Retrieval',  5),
 (4, 2, 'ML Systems',               'Infrastructure for ML workloads.',         'Machine Learning',       6),
 (5, 2, 'Data Engineering',         'Pipelines and data platforms.',            'Data Engineering',       5),
 (6, 3, 'Software Testing',         'Testing techniques and tools.',            'Software Engineering',   9);

-- Session 3 (Astana) and session 5 (Berlin) are empty.
INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Query Processing',      '2026-06-16', '10:00', '11:30', 'Hall A',     4),
 (2, 1, 'Learning Systems',      '2026-06-16', '13:00', '14:30', 'Hall B',     5),
 (3, 1, 'Late-Breaking Results', '2026-06-17', '09:00', '10:00', 'Room 101',   12),
 (4, 2, 'ML Infrastructure',     '2026-09-10', '11:00', '12:30', 'Room Spree', 6),
 (5, 2, 'Open Discussion',       '2026-09-11', '15:00', '16:00', 'Room Havel', 9);

INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1,  1, 'Adaptive Indexing for Hybrid Workloads',
         'We present an adaptive indexing technique that reorganizes data incrementally for mixed OLTP and OLAP workloads.',
         '2026-02-01', 'accepted', 1),
 (2,  1, 'Cost Models for Learned Query Optimizers',
         'We study how Machine Learning cost models behave inside relational query optimizers.',
         '2026-02-05', 'accepted', 1),
 (3,  2, 'Federated Learning on Edge Devices',
         'A machine learning framework for training models across resource-constrained edge devices.',
         '2026-02-10', 'accepted', 2),
 (4,  2, 'Explainable Credit Scoring',
         'Interpretable models for credit risk assessment using gradient boosting.',
         '2026-02-11', 'accepted', NULL),
 (5,  1, 'Benchmarking Graph Databases',
         'An empirical comparison of graph database engines on traversal-heavy workloads.',
         '2026-02-12', 'rejected', NULL),
 (6,  2, 'Sentiment Analysis of Kazakh Social Media',
         'A dataset and baseline models for sentiment classification of Kazakh-language posts.',
         '2026-02-13', 'withdrawn', NULL),
 (7,  1, 'Compressed Bitmap Indexes Revisited',
         'We revisit bitmap index compression schemes on modern hardware.',
         '2026-02-14', 'withdrawn', NULL),
 (8,  4, 'Scheduling GPU Clusters for Deep Learning Training',
         'A scheduler that improves utilization of shared GPU clusters for MACHINE LEARNING jobs.',
         '2026-03-20', 'accepted', 4),
 (9,  4, 'Compression of Large Language Models',
         'Quantization and pruning strategies for deploying large language models.',
         '2026-03-25', 'under review', NULL),
 (10, 5, 'Streaming ETL Pipelines at Scale',
         'Design of exactly-once streaming ETL pipelines.',
         '2026-03-28', 'submitted', NULL),
 (11, 5, 'Lakehouse Metadata Management',
         'Scalable metadata services for lakehouse table formats.',
         '2026-03-29', 'rejected', NULL),
 (12, 2, 'Few-Shot Topic Modeling',
         'Topic discovery with very few labeled documents.',
         '2026-02-15', 'withdrawn', NULL);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
 (1, 'indexing'), (1, 'HTAP'),
 (2, 'query optimization'), (2, 'cost models'),
 (3, 'federated learning'), (3, 'edge computing'),
 (4, 'explainability'), (4, 'credit scoring'),
 (5, 'graph databases'), (5, 'benchmarking'),
 (6, 'sentiment analysis'), (6, 'NLP'),
 (7, 'bitmap indexes'),
 (8, 'GPU scheduling'), (8, 'deep learning'),
 (9, 'LLM'), (9, 'quantization'),
 (10, 'streaming'), (10, 'ETL'),
 (11, 'lakehouse'), (11, 'metadata'),
 (12, 'topic modeling');

-- Exactly one corresponding author per paper. Amina (2) is corresponding author of withdrawn
-- papers 6 and 7, and a non-corresponding co-author of withdrawn paper 12.
INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 3, 1, TRUE),  (1, 7, 2, FALSE),
 (2, 7, 1, TRUE),  (2, 11, 2, FALSE),
 (3, 1, 1, TRUE),  (3, 2, 2, FALSE),
 (4, 11, 1, TRUE), (4, 8, 2, FALSE),
 (5, 8, 1, TRUE),
 (6, 2, 1, TRUE),  (6, 7, 2, FALSE),
 (7, 2, 1, TRUE),
 (8, 9, 1, TRUE),  (8, 3, 2, FALSE),
 (9, 1, 1, TRUE),
 (10, 11, 1, TRUE), (10, 9, 2, FALSE),
 (11, 3, 1, TRUE),
 (12, 7, 1, TRUE), (12, 2, 2, FALSE);

-- Paper 9 has a version-number gap (1, 3).
INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, 'papers/1/v1.pdf', '2026-02-01 09:00', NULL),
 (1, 2, 'papers/1/v2.pdf', '2026-02-10 14:30', 'Fixed related work section'),
 (1, 3, 'papers/1/v3.pdf', '2026-05-01 18:00', 'Camera-ready version'),
 (2, 1, 'papers/2/v1.pdf', '2026-02-05 10:00', NULL),
 (3, 1, 'papers/3/v1.pdf', '2026-02-10 11:00', NULL),
 (3, 2, 'papers/3/v2.pdf', '2026-05-02 12:00', 'Camera-ready version'),
 (4, 1, 'papers/4/v1.pdf', '2026-02-11 08:15', NULL),
 (5, 1, 'papers/5/v1.pdf', '2026-02-12 16:40', NULL),
 (6, 1, 'papers/6/v1.pdf', '2026-02-13 13:00', NULL),
 (6, 2, 'papers/6/v2.pdf', '2026-02-14 13:00', 'Typo fixes'),
 (7, 1, 'papers/7/v1.pdf', '2026-02-14 09:30', NULL),
 (8, 1, 'papers/8/v1.pdf', '2026-03-20 10:00', NULL),
 (9, 1, 'papers/9/v1.pdf', '2026-03-25 10:00', NULL),
 (9, 3, 'papers/9/v3.pdf', '2026-04-02 10:00', 'Major revision (v2 discarded)'),
 (10, 1, 'papers/10/v1.pdf', '2026-03-28 10:00', NULL),
 (11, 1, 'papers/11/v1.pdf', '2026-03-29 10:00', NULL),
 (12, 1, 'papers/12/v1.pdf', '2026-02-15 10:00', NULL);

-- Review counts per reviewer: 4->5, 5->3, 6->3, 1->2, 12->2, 3->1, 9->1, 10->0 (avg 2.125).
-- No reviewer reviews their own paper; reviewers belong to the paper's conference pool.
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1,  1, 4,  5, 'accept', 'Strong contribution with convincing experiments.', NULL, '2026-04-01'),
 (2,  1, 5,  4, 'accept', 'Good paper; clarify the cost model.', 'Solid accept.', '2026-04-03'),
 (3,  1, 6,  4, 'accept', 'Well written.', NULL, '2026-04-05'),
 (4,  2, 4,  4, 'accept', 'Interesting analysis of learned optimizers.', NULL, '2026-04-02'),
 (5,  2, 12, 3, 'accept', 'Borderline but acceptable.', 'Weak accept.', '2026-04-06'),
 (6,  3, 4,  5, 'accept', 'Excellent system design.', NULL, '2026-04-04'),
 (7,  3, 5,  4, 'accept', 'Good evaluation on real devices.', NULL, '2026-04-07'),
 (8,  5, 4,  2, 'reject', 'Benchmark setup is not representative.', NULL, '2026-04-08'),
 (9,  5, 1,  1, 'reject', 'Results cannot be reproduced.', 'Possible overlap with prior work.', '2026-04-09'),
 (10, 6, 3,  2, 'reject', 'Dataset description is insufficient.', NULL, '2026-04-10'),
 (11, 8, 6,  5, 'accept', 'Impressive utilization gains.', NULL, '2026-05-10'),
 (12, 8, 5,  4, 'accept', 'Practical and well evaluated.', NULL, '2026-05-12'),
 (13, 11, 6, 2, 'reject', 'Limited novelty.', NULL, '2026-05-14'),
 (14, 4, 1,  4, 'accept', 'Useful for practitioners.', NULL, '2026-04-11'),
 (15, 4, 12, 4, 'accept', 'Clear explanations.', NULL, '2026-04-12'),
 (16, 11, 9, 2, 'reject', 'Evaluation is too small.', NULL, '2026-05-15'),
 (17, 7, 4,  1, 'reject', 'Not novel.', NULL, '2026-04-13');

-- Advance identity sequences past the explicit ids.
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),                MAX(user_id))       FROM app_user;
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),        MAX(conference_id)) FROM conference;
SELECT setval(pg_get_serial_sequence('track', 'track_id'),                  MAX(track_id))      FROM track;
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'),   MAX(session_id))    FROM conference_session;
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),                  MAX(paper_id))      FROM paper;
SELECT setval(pg_get_serial_sequence('review', 'review_id'),                MAX(review_id))     FROM review;
