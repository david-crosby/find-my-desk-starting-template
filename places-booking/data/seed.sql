-- Demo seed data — load with: sqlite3 data/places.db < data/seed.sql

INSERT INTO locations (name, address) VALUES
  ('HQ',               '1 Main Street, London'),
  ('Satellite Office', '42 High Road, Manchester');

INSERT INTO floors (location_id, number, name) VALUES
  (1, 0, 'Ground'),
  (1, 1, 'First'),
  (2, 0, 'Ground');

INSERT INTO desks (floor_id, label, is_active) VALUES
  (1, 'G-01', 1), (1, 'G-02', 1), (1, 'G-03', 1), (1, 'G-04', 1), (1, 'G-05', 1),
  (2, 'F-01', 1), (2, 'F-02', 1), (2, 'F-03', 1),
  (3, 'S-01', 1), (3, 'S-02', 1);

INSERT INTO rooms (floor_id, name, capacity, is_active) VALUES
  (1, 'Boardroom',     12, 1),
  (1, 'Huddle A',       4, 1),
  (2, 'Training Room', 20, 1),
  (2, 'Huddle B',       4, 1),
  (3, 'Meeting Room 1', 6, 1);

INSERT INTO users (email, display_name, is_admin) VALUES
  ('alice@example.com',    'Alice Smith',      0),
  ('bob@example.com',      'Bob Jones',        0),
  ('carol@example.com',    'Carol White',      0),
  ('admin@example.com',    'Facilities Admin', 1);
