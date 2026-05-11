-- Minimal hand-written seed — use seed_demo.py for the full 40-user demo dataset.
-- Run with: sqlite3 data/places.db < data/seed.sql

INSERT INTO booking_policies (name, max_advance_days, max_booking_duration_hours,
  auto_release_enabled, auto_release_threshold_mins, check_in_required,
  approval_required, gdpr_data_retention_days)
VALUES
  ('Standard',        30, 9, 1, 30, 1, 0, 365),
  ('Executive Floor', 60, 9, 0, 60, 1, 1, 730);

INSERT INTO buildings (name, address, building_lat, building_lng) VALUES
  ('London',    '1 Canada Square, Canary Wharf, London E14 5AB', '51.5074', '-0.1278'),
  ('Leeds',     '1 Whitehall Road, Leeds LS1 4HR',               '53.8008', '-1.5491'),
  ('Edinburgh', '1 Festival Square, Edinburgh EH3 9SR',          '55.9533', '-3.1883');

INSERT INTO floors (building_id, number, name) VALUES
  (1, 0, 'Ground'), (1, 1, 'First'),
  (2, 0, 'Ground'), (2, 1, 'First'),
  (3, 0, 'Ground'), (3, 1, 'First');

-- London Ground sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (1, 'Window Bank',        'Window Bank'),
  (1, 'Quiet Zone',         'Quiet Zone'),
  (1, 'Collaboration Zone', 'Collaboration Zone'),
  (1, 'Core Desk Area',     'Core Desk Area');

-- London First sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (2, 'Window Bank',        'Window Bank'),
  (2, 'Quiet Zone',         'Quiet Zone'),
  (2, 'Collaboration Zone', 'Collaboration Zone'),
  (2, 'Core Desk Area',     'Core Desk Area');

-- Leeds Ground sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (3, 'Window Bank',        'Window Bank'),
  (3, 'Quiet Zone',         'Quiet Zone'),
  (3, 'Collaboration Zone', 'Collaboration Zone'),
  (3, 'Core Desk Area',     'Core Desk Area');

-- Leeds First sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (4, 'Window Bank',        'Window Bank'),
  (4, 'Quiet Zone',         'Quiet Zone'),
  (4, 'Collaboration Zone', 'Collaboration Zone'),
  (4, 'Core Desk Area',     'Core Desk Area');

-- Edinburgh Ground sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (5, 'Window Bank',        'Window Bank'),
  (5, 'Quiet Zone',         'Quiet Zone'),
  (5, 'Collaboration Zone', 'Collaboration Zone'),
  (5, 'Core Desk Area',     'Core Desk Area');

-- Edinburgh First sections
INSERT INTO sections (floor_id, name, zone_label) VALUES
  (6, 'Window Bank',        'Window Bank'),
  (6, 'Quiet Zone',         'Quiet Zone'),
  (6, 'Collaboration Zone', 'Collaboration Zone'),
  (6, 'Core Desk Area',     'Core Desk Area');

-- London Ground desks (section_ids 1–4)
INSERT INTO desks (section_id, label, is_active, desk_mode, is_window_seat, has_docking_station) VALUES
  (1, 'LGW-01', 1, 'reservable', 1, 1), (1, 'LGW-02', 1, 'reservable', 1, 1),
  (1, 'LGW-03', 1, 'reservable', 1, 1), (1, 'LGW-04', 1, 'reservable', 1, 1),
  (1, 'LGW-05', 1, 'reservable', 1, 0);

INSERT INTO desks (section_id, label, is_active, desk_mode, has_standing_desk, has_dual_monitors, has_docking_station) VALUES
  (2, 'LGQ-01', 1, 'reservable', 1, 1, 1), (2, 'LGQ-02', 1, 'reservable', 1, 1, 1),
  (2, 'LGQ-03', 1, 'reservable', 1, 0, 1), (2, 'LGQ-04', 1, 'reservable', 0, 1, 1),
  (2, 'LGQ-05', 1, 'reservable', 1, 1, 0);

INSERT INTO desks (section_id, label, is_active, desk_mode, has_dual_monitors, has_docking_station) VALUES
  (3, 'LGC-01', 1, 'reservable', 1, 1), (3, 'LGC-02', 1, 'reservable', 1, 1),
  (3, 'LGC-03', 1, 'reservable', 1, 0), (3, 'LGC-04', 1, 'reservable', 0, 1),
  (3, 'LGC-05', 1, 'reservable', 1, 1);

INSERT INTO desks (section_id, label, is_active, desk_mode) VALUES
  (4, 'LGD-01', 1, 'reservable'), (4, 'LGD-02', 1, 'reservable'),
  (4, 'LGD-03', 1, 'reservable'), (4, 'LGD-04', 1, 'reservable'),
  (4, 'LGD-05', 1, 'reservable'), (4, 'LGD-06', 1, 'reservable'),
  (4, 'LGD-07', 1, 'reservable'), (4, 'LGD-08', 1, 'reservable');

-- Meeting rooms
INSERT INTO rooms (floor_id, name, capacity, is_active) VALUES
  (1, 'Boardroom Ground',      12, 1),
  (1, 'Huddle Ground A',        4, 1),
  (1, 'Meeting Room Ground 1',  8, 1),
  (2, 'Boardroom First',       12, 1),
  (2, 'Huddle First A',         4, 1),
  (2, 'Meeting Room First 1',   8, 1);

INSERT INTO users (email, display_name, is_admin, employment_type, home_building_id,
  workplan_visibility, onboarding_completed, booking_window_days, ai_autonomy_level)
VALUES
  ('alice@thebank.com',    'Alice Smith',      0, 'permanent', 1, 'team', 1, 14, 'book_with_confirm'),
  ('bob@thebank.com',      'Bob Jones',        0, 'permanent', 2, 'team', 1, 14, 'book_with_confirm'),
  ('carol@thebank.com',    'Carol White',      0, 'permanent', 3, 'team', 1, 14, 'suggest_only'),
  ('admin@thebank.com',    'Facilities Admin', 1, 'permanent', 1, 'org',  1, 60, 'book_with_confirm');
