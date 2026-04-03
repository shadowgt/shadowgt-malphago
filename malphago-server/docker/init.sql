-- Initial seed data for tracks
INSERT INTO track (id, code, name, name_en) VALUES
    (1, 'S', '서울', 'Seoul'),
    (2, 'B', '부산', 'Busan'),
    (3, 'J', '제주', 'Jeju')
ON CONFLICT DO NOTHING;
