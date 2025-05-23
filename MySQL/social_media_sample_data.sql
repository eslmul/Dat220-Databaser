-- social_media_sample_data.sql
-- Sample data for social media platform database

-- Clear existing data (if any)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE INNLEGG_TAGGER;
TRUNCATE TABLE MELDINGER;
TRUNCATE TABLE FØLGER;
TRUNCATE TABLE REAKSJONER;
TRUNCATE TABLE KOMMENTARER;
TRUNCATE TABLE INNLEGG;
TRUNCATE TABLE TAGGER;
TRUNCATE TABLE BRUKERE;
SET FOREIGN_KEY_CHECKS = 1;

-- Insert sample BRUKERE (Users)
INSERT INTO BRUKERE (brukernavn, epost, passord_hash, profilbilde, bio, registrerings_dato, fødselsdato, status) VALUES
('johansen94', 'erik.johansen@example.com', 'hash1234567890', 'profil1.jpg', 'Fotograf og friluftsentusiast fra Bergen.', '2023-01-15', '1994-05-20', 'aktiv'),
('mariaberg', 'maria.berg@example.com', 'hash2345678901', 'profil2.jpg', 'Journalist og bokelsker.', '2023-02-10', '1990-08-12', 'aktiv'),
('olekristian', 'ole.kristian@example.com', 'hash3456789012', 'profil3.jpg', 'Programmerer og teknologientusiast.', '2023-01-05', '1992-11-30', 'aktiv'),
('annesofi', 'anne.sofi@example.com', 'hash4567890123', 'profil4.jpg', 'Lærer og hobbybaker fra Trondheim.', '2023-03-20', '1988-07-15', 'aktiv'),
('pernillen', 'pernille.n@example.com', 'hash5678901234', 'profil5.jpg', 'Digital markedsfører og yogainstruktør.', '2023-02-28', '1995-04-05', 'aktiv'),
('magnush', 'magnus.h@example.com', 'hash6789012345', 'profil6.jpg', 'Ingeniør og fotballentusiast.', '2023-04-10', '1991-09-25', 'aktiv'),
('karianne', 'karianne@example.com', 'hash7890123456', 'profil7.jpg', 'Grafisk designer med passion for kunst.', '2023-03-15', '1993-12-08', 'aktiv'),
('anderskr', 'anders.kr@example.com', 'hash8901234567', 'profil8.jpg', 'Historiestudent og frivillig.', '2023-05-05', '1997-06-18', 'aktiv'),
('linelise', 'lin.elise@example.com', 'hash9012345678', 'profil9.jpg', 'Sykepleier og reiseglad.', '2023-04-20', '1989-03-22', 'aktiv'),
('torhild', 'tor.hild@example.com', 'hash0123456789', 'profil10.jpg', 'Musiker og vinterbader.', '2023-05-25', '1990-10-14', 'aktiv'),
('martingm', 'martin.gm@example.com', 'hash1122334455', 'profil11.jpg', 'Arkitekt med interesse for bærekraft.', '2023-06-01', '1986-02-28', 'aktiv'),
('jensten', 'jens.ten@example.com', 'hash6677889900', 'profil12.jpg', 'Kokk og matblogger.', '2023-06-15', '1994-08-05', 'aktiv');

-- Insert sample TAGGER (Tags)
INSERT INTO TAGGER (navn, beskrivelse) VALUES
('natur', 'Bilder og innlegg om naturen'),
('mat', 'Matoppskrifter og matopplevelser'),
('teknologi', 'Alt om teknologi og digitale trender'),
('reise', 'Reiseopplevelser og reisetips'),
('trening', 'Treningsrutiner og fitness'),
('musikk', 'Musikkanbefalinger og konsertopplevelser'),
('kunst', 'Kunst og kreative uttrykk'),
('litteratur', 'Bøker og leseopplevelser'),
('film', 'Filmanmeldelser og filmanbefalinger'),
('utdanning', 'Temaer relatert til skole og læring'),
('jobb', 'Arbeidslivet og karrieretips'),
('familie', 'Familie og hverdagsliv');

-- Insert sample INNLEGG (Posts)
INSERT INTO INNLEGG (innhold, opprettet_dato, synlighet, bruker_id) VALUES
('Fantastisk solnedgang fra fjellturen i dag! #natur #fjelltur', '2023-07-01 18:45:00', 'offentlig', 1),
('Ny oppskrift på hjemmelaget pasta med sesongbaserte råvarer. Deilig sommermat!', '2023-07-02 12:30:00', 'offentlig', 12),
('Har nettopp lært meg grunnleggende Python-programmering. Fascinerende!', '2023-07-03 09:15:00', 'offentlig', 3),
('På vei til Roma! Noen tips til hva jeg bør se?', '2023-07-04 16:20:00', 'offentlig', 9),
('Min nye treningsrutine har gitt gode resultater. Deler gjerne erfaringer.', '2023-07-05 07:45:00', 'offentlig', 5),
('Var på konsert med favorittbandet mitt i går. Helt utrolig opplevelse!', '2023-07-06 10:10:00', 'offentlig', 10),
('Besøkte en fascinerende kunstutstilling i helgen. Anbefales!', '2023-07-07 14:25:00', 'offentlig', 7),
('Har nettopp lest en fantastisk roman. Noen andre som har lest "Havet" av Jon Sorensen?', '2023-07-08 20:30:00', 'offentlig', 2),
('Så den nye sci-fi filmen i går. Imponerende effekter!', '2023-07-09 19:05:00', 'offentlig', 6),
('Første dag i ny jobb! Spent på hva framtiden bringer.', '2023-07-10 08:50:00', 'offentlig', 11),
('Familietur til hytta. Barna koser seg med fiske og bading.', '2023-07-11 15:40:00', 'venner', 4),
('Tenker på å ta et nytt kurs i markedsføring. Noen anbefalinger?', '2023-07-12 11:15:00', 'offentlig', 5),
('Tester ut nytt kamera. Her er noen av de første bildene.', '2023-07-13 13:20:00', 'offentlig', 1),
('Endelig ferdig med eksamen! Nå venter sommerferie.', '2023-07-14 16:55:00', 'offentlig', 8);

-- Insert sample KOMMENTARER (Comments)
INSERT INTO KOMMENTARER (innhold, opprettet_dato, innlegg_id, bruker_id, forelder_kommentar_id) VALUES
('Nydelig bilde! Hvor er dette tatt?', '2023-07-01 19:10:00', 1, 2, NULL),
('Ser fantastisk ut! Må prøve denne oppskriften.', '2023-07-02 13:05:00', 2, 4, NULL),
('Python er et flott språk å starte med. Prøv å lage et lite prosjekt!', '2023-07-03 10:30:00', 3, 6, NULL),
('Colosseum er et must! Og ikke glem å besøke Trastevere for god mat.', '2023-07-04 16:45:00', 4, 7, NULL),
('Hvilken treningsrutine følger du?', '2023-07-05 08:20:00', 5, 8, NULL),
('Hvilket band var det?', '2023-07-06 10:35:00', 6, 9, NULL),
('Det var i Hardanger. Takk!', '2023-07-01 20:00:00', 1, 1, 1),
('Jeg følger et program med fokus på styrketrening 3 ganger i uken.', '2023-07-05 09:15:00', 5, 5, 5),
('Kan du dele oppskriften?', '2023-07-02 14:10:00', 2, 5, 2),
('Arctic Monkeys. De var helt fantastiske live!', '2023-07-06 11:05:00', 6, 10, 6),
('Kunstutstillingen var virkelig inspirerende!', '2023-07-07 15:00:00', 7, 11, NULL),
('Jeg har lest den! En av årets beste bøker etter min mening.', '2023-07-08 21:20:00', 8, 12, NULL),
('Hvilken sci-fi film var det?', '2023-07-09 19:30:00', 9, 3, NULL),
('Gratulerer med ny jobb! Hva skal du jobbe med?', '2023-07-10 09:15:00', 10, 1, NULL);

-- Insert sample REAKSJONER (Reactions)
INSERT INTO REAKSJONER (reaksjon_type, opprettet_dato, bruker_id, innlegg_id, kommentar_id) VALUES
('like', '2023-07-01 19:05:00', 2, 1, NULL),
('love', '2023-07-01 19:30:00', 3, 1, NULL),
('like', '2023-07-02 13:10:00', 5, 2, NULL),
('like', '2023-07-02 13:45:00', 6, 2, NULL),
('like', '2023-07-03 10:20:00', 4, 3, NULL),
('like', '2023-07-03 11:00:00', 5, 3, NULL),
('like', '2023-07-04 17:00:00', 8, 4, NULL),
('like', '2023-07-05 08:30:00', 9, 5, NULL),
('love', '2023-07-06 10:40:00', 11, 6, NULL),
('like', '2023-07-07 14:50:00', 12, 7, NULL),
('like', '2023-07-08 21:00:00', 1, 8, NULL),
('like', '2023-07-09 19:20:00', 2, 9, NULL),
('like', '2023-07-10 09:10:00', 3, 10, NULL),
('like', '2023-07-11 16:00:00', 5, 11, NULL),
('like', '2023-07-01 19:15:00', 4, NULL, 1),
('like', '2023-07-02 14:00:00', 7, NULL, 2);

-- Insert sample FØLGER (Follows)
INSERT INTO FØLGER (følger_id, følger_bruker_id, opprettet_dato, status) VALUES
(1, 2, '2023-07-01 10:00:00', 'aktiv'),
(1, 3, '2023-07-02 11:30:00', 'aktiv'),
(2, 1, '2023-07-01 12:15:00', 'aktiv'),
(2, 4, '2023-07-03 14:45:00', 'aktiv'),
(3, 6, '2023-07-04 09:20:00', 'aktiv'),
(4, 5, '2023-07-05 16:30:00', 'aktiv'),
(5, 7, '2023-07-06 13:10:00', 'aktiv'),
(6, 8, '2023-07-07 10:25:00', 'aktiv'),
(7, 9, '2023-07-08 15:40:00', 'aktiv'),
(8, 10, '2023-07-09 11:55:00', 'aktiv'),
(9, 11, '2023-07-10 14:20:00', 'aktiv'),
(10, 12, '2023-07-11 09:45:00', 'aktiv'),
(11, 1, '2023-07-12 13:30:00', 'aktiv'),
(12, 2, '2023-07-13 10:15:00', 'aktiv');



-- Insert sample INNLEGG_TAGGER (Post-Tags)
INSERT INTO INNLEGG_TAGGER (innlegg_id, tag_id) VALUES
(1, 1),  -- natur
(2, 2),  -- mat
(3, 3),  -- teknologi
(4, 4),  -- reise
(5, 5),  -- trening
(6, 6),  -- musikk
(7, 7),  -- kunst
(8, 8),  -- litteratur
(9, 9),  -- film
(10, 11), -- jobb
(11, 12), -- familie
(12, 10), -- utdanning
(13, 1),  -- natur (for kameratestbilde)
(13, 7),  -- kunst (for kameratestbilde)
(14, 10); -- utdanning (for eksamen-innlegget)