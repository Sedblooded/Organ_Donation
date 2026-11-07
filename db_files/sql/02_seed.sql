-- =====================================================================
-- Mock data (all names, hospitals, IDs and phone numbers are fictional)
-- Insert order respects FKs and triggers: organs and waitlist rows go in
-- as 'available' / 'active', then the TRANSPLANT inserts flip them to
-- 'transplanted' / 'fulfilled' through the C9 trigger.
-- =====================================================================
BEGIN;

INSERT INTO pincode_area VALUES
 ('600003','Chennai','Tamil Nadu'),
 ('600020','Chennai','Tamil Nadu'),
 ('600042','Chennai','Tamil Nadu'),
 ('641001','Coimbatore','Tamil Nadu'),
 ('625001','Madurai','Tamil Nadu'),
 ('560001','Bengaluru','Karnataka'),
 ('695001','Thiruvananthapuram','Kerala'),
 ('500001','Hyderabad','Telangana'),
 ('400001','Mumbai','Maharashtra'),
 ('110001','New Delhi','Delhi');

INSERT INTO hospital (hosp_id, reg_id, name, facility_type, street, pincode, contact) VALUES
 (1,'HOSP-TN-001','Coastal Care Transplant Institute','transplant_centre','12 Beach Road','600020','9000000001'),
 (2,'HOSP-TN-002','Meenakshi Regional Medical Centre','transplant_centre','45 West Veli Street','625001','9000000002'),
 (3,'HOSP-KA-001','Garden City Multispeciality Hospital','transplant_centre','8 Residency Road','560001','9000000003'),
 (4,'HOSP-TN-003','Kovai General Hospital','general','101 Avinashi Road','641001','9000000004'),
 (5,'HOSP-DL-001','Capital Organ & Research Centre','transplant_centre','3 Barakhamba Road','110001','9000000005'),
 (6,'HOSP-MH-001','Harbour City Hospital','general','27 Nariman Point','400001','9000000006');

INSERT INTO specialization (spec_id, spec_name) VALUES
 (1,'Transplant Surgery'),(2,'Nephrology'),(3,'Hepatology'),(4,'Cardiology'),
 (5,'Pulmonology'),(6,'Critical Care'),(7,'Anaesthesiology');

INSERT INTO doctor (doctor_id, med_bar_id, general_id, name, contact) VALUES
 (1,'TNMC-10231','DOC-0001','Dr. Arvind Raman','9000000101'),
 (2,'TNMC-10377','DOC-0002','Dr. Lakshmi Narayanan','9000000102'),
 (3,'TNMC-11452','DOC-0003','Dr. Priya Subramanian','9000000103'),
 (4,'DMC-20518','DOC-0004','Dr. Rohan Mehta','9000000104'),
 (5,'KMC-30664','DOC-0005','Dr. Kavita Rao','9000000105'),
 (6,'TNMC-11890','DOC-0006','Dr. Imran Sheikh','9000000106'),
 (7,'TNMC-12045','DOC-0007','Dr. Meera Iyer','9000000107'),
 (8,'KMC-30921','DOC-0008','Dr. Suresh Babu','9000000108');

INSERT INTO doctor_spec VALUES
 (1,1),(1,7),(2,2),(2,1),(3,3),(3,1),(4,1),(5,4),(5,1),(6,2),(6,1),(7,6),(8,5),(8,1);

INSERT INTO doctor_hospital VALUES
 (1,1,'Senior Consultant','2015-04-01'),(1,4,'Visiting Surgeon','2019-01-15'),
 (2,1,'Head of Nephrology','2012-08-20'),
 (3,2,'Senior Hepatologist','2016-06-10'),
 (4,5,'Chief Transplant Surgeon','2010-02-01'),
 (5,3,'Cardiac Transplant Lead','2014-09-12'),
 (6,2,'Consultant Nephrologist','2018-03-05'),
 (7,1,'Intensivist','2017-11-01'),(7,4,'Visiting Intensivist','2020-05-18'),
 (8,3,'Pulmonary Transplant Lead','2013-07-22');

-- ---------- patients 1-19 (1-9 donors, 10-19 recipients) -------------
INSERT INTO patient (patient_id,name,dob,gender,blood_group,street,pincode,notes,hosp_id) VALUES
 (1,'Rajesh Kumar','1975-04-12','M','O+','14 Gandhi Nagar','600020','Healthy, non-smoker',1),
 (2,'Anita Desai','1988-09-23','F','A+','22 Lake View Road','560001','Healthy, volunteer living donor',3),
 (3,'Mohammed Faizal','1992-01-30','M','B+','8 Anna Salai','625001','Brain-stem death after road accident',2),
 (4,'Sunita Reddy','1980-06-05','F','O-','5 Banjara Hills','500001','Brain-stem death, cerebral haemorrhage',3),
 (5,'Karthik Venkatesh','1999-11-18','M','AB+','31 Velachery Main Road','600042','Brain-stem death, head injury',1),
 (6,'Deepa Nair','1985-03-09','F','A-','12 MG Road','695001','Registered living donor',4),
 (7,'Vikram Singh','1971-12-02','M','B-','77 Connaught Place','110001','Brain-stem death, stroke',5),
 (8,'Joseph Thomas','1994-07-14','M','O+','3 Marine Drive','400001','Enquired about living donation',6),
 (9,'Latha Pillai','1982-02-27','F','AB-','19 Pallavaram Road','600003','Deceased donor, case file closed',1),
 (10,'Suresh Kumar','1968-08-21','M','A+','40 TTK Road','600020','Chronic liver disease',2),
 (11,'Lakshmi Priya','1979-05-16','F','O+','9 Mount Road','600003','End-stage renal disease',1),
 (12,'Arjun Mehta','1990-10-03','M','B+','66 Brigade Road','560001','Dilated cardiomyopathy',3),
 (13,'Fatima Begum','1983-01-11','F','AB+','21 Charminar Road','500001','Acute-on-chronic liver failure',5),
 (14,'Ramesh Gowda','1972-04-25','M','O-','48 Jayanagar','560001','End-stage COPD',3),
 (15,'Neha Sharma','1995-12-19','F','A+','17 Karol Bagh','110001','Chronic kidney disease stage 5',1),
 (16,'Gopal Krishnan','1960-06-30','M','B+','2 Race Course Road','641001','End-stage renal disease',2),
 (17,'Shalini Menon','1987-09-08','F','AB-','55 Panampilly Nagar','695001','End-stage renal disease, corneal scarring',1),
 (18,'Prakash Rao','1975-03-14','M','O+','13 Peelamedu','641001','Chronic kidney disease stage 5',4),
 (19,'Divya Bhatt','2001-08-07','F','A-','28 Bandra West','400001','Chronic kidney disease, hereditary',1);

INSERT INTO donor (patient_id,donor_type,alive_status,consent_status,medical_notes) VALUES
 (1,'living','alive','given','Cleared for kidney donation'),
 (2,'living','alive','given','Cleared for partial liver donation'),
 (3,'deceased','deceased','given','Family consent obtained'),
 (4,'deceased','deceased','given','Family consent obtained'),
 (5,'deceased','deceased','given','Family consent obtained'),
 (6,'living','alive','given','Registered, no donation scheduled yet'),
 (7,'deceased','deceased','given','Family consent obtained'),
 (8,'living','alive','pending','Evaluation pending, consent not yet given'),
 (9,'deceased','deceased','given','Family consent obtained');

INSERT INTO recipient (patient_id,urgency_level,medical_notes) VALUES
 (10,1,'MELD score high'),(11,2,'On dialysis 3 years'),(12,1,'Status 1A cardiac'),
 (13,1,'Fulminant hepatic failure'),(14,2,'Oxygen dependent'),(15,3,'On dialysis 8 months'),
 (16,3,'On dialysis 2 years'),(17,2,'Dual listing, kidney and cornea'),(18,2,'On dialysis 14 months'),
 (19,3,'Pre-emptive listing');

-- ---------- organ types ---------------------------------------------
INSERT INTO organ_type (organ_type_id, organ_name, viability_hours, living_donation_allowed) VALUES
 (1,'Kidney',36,TRUE),(2,'Liver',12,TRUE),(3,'Heart',4,FALSE),
 (4,'Lung',6,FALSE),(5,'Pancreas',12,FALSE),(6,'Cornea',NULL,FALSE);

-- ---------- organs ---------------------------------------------------
-- historical ones (will be transplanted below)
INSERT INTO organ (organ_id,organ_type_id,donor_id,full_or_part,harvest_datetime,status,description) VALUES
 (1,1,1,'full','2026-06-12 08:00+05:30','available','Left kidney, living donor'),
 (2,2,2,'part','2026-07-03 07:00+05:30','available','Right lobe, living donor'),
 (3,3,3,'full','2026-08-20 08:10+05:30','available','Heart, deceased donor'),
 (4,1,3,'full','2026-08-20 08:30+05:30','available','Kidney, deceased donor'),
 (5,4,4,'full','2026-09-14 06:00+05:30','available','Lung, deceased donor');
-- current inventory (relative to load time so the demo stays "fresh")
INSERT INTO organ (organ_id,organ_type_id,donor_id,full_or_part,harvest_datetime,status,description) VALUES
 (6,2,5,'full', now() - interval '3 hours','available','Liver, AB+ deceased donor'),
 (7,1,5,'full', now() - interval '3 hours','available','Kidney, AB+ deceased donor (no compatible waitlisted recipient)'),
 (8,1,7,'full', now() - interval '2 hours','allocated','Kidney, B- deceased donor, held for recipient 17'),
 (9,6,7,'full', now() - interval '2 hours','available','Cornea, stored in eye bank'),
 (10,5,9,'full',now() - interval '4 days', 'expired','Pancreas, not used within viability window');

-- ---------- waitlist -------------------------------------------------
INSERT INTO waitlist (waitlist_id,recipient_id,organ_type_id,hosp_id,date_added,priority,status) VALUES
 (1,11,1,1,'2026-03-01',2,'active'),
 (2,10,2,2,'2026-04-10',1,'active'),
 (3,12,3,3,'2026-05-02',1,'active'),
 (4,16,1,2,'2025-12-15',3,'active'),
 (5,14,4,3,'2026-06-20',2,'active'),
 (6,17,1,1,'2026-02-11',2,'matched'),   -- holds organ 8
 (7,13,2,5,'2026-10-20',1,'active'),    -- AB+ liver candidate for organ 6
 (8,15,1,1,'2026-02-28',3,'active'),
 (9,19,1,1,'2026-09-05',3,'active'),
 (10,18,1,4,'2026-01-19',2,'active'),
 (11,17,6,6,'2026-08-30',3,'active');

-- ---------- transplants (triggers validate + propagate status) ------
INSERT INTO transplant (transplant_id,organ_id,recipient_id,hosp_id,lead_doctor_id,transplant_date,outcome) VALUES
 (1,1,11,1,2,'2026-06-12 10:30+05:30','successful'),
 (2,2,10,2,3,'2026-07-03 09:30+05:30','successful'),
 (3,3,12,3,5,'2026-08-20 11:30+05:30','complications'),
 (4,4,16,2,6,'2026-08-20 18:45+05:30','successful'),
 (5,5,14,3,8,'2026-09-14 10:15+05:30','pending');

INSERT INTO recovery (transplant_id,doctor_id,checkup_date,status,description) VALUES
 (1,2,'2026-06-19','stable','Creatinine trending down'),
 (1,2,'2026-07-12','improving','Off dialysis'),
 (1,2,'2026-09-12','recovered','Normal graft function'),
 (2,3,'2026-07-10','stable','Liver enzymes normalising'),
 (2,3,'2026-08-03','improving','Regeneration on ultrasound'),
 (2,3,'2026-10-03','stable','Routine 3-month review'),
 (3,5,'2026-08-27','critical','Acute rejection episode, steroids started'),
 (3,5,'2026-09-20','improving','Rejection resolved'),
 (3,5,'2026-10-20','stable','Biopsy clear'),
 (4,6,'2026-08-27','stable','Good urine output'),
 (4,6,'2026-09-20','recovered','Normal graft function'),
 (5,8,'2026-09-21','stable','On ventilator weaning protocol'),
 (5,8,'2026-10-14','improving','Oxygen saturation improving');

-- keep identity counters ahead of the explicit ids used above
SELECT setval(pg_get_serial_sequence('hospital','hosp_id'),           (SELECT max(hosp_id) FROM hospital));
SELECT setval(pg_get_serial_sequence('specialization','spec_id'),     (SELECT max(spec_id) FROM specialization));
SELECT setval(pg_get_serial_sequence('doctor','doctor_id'),           (SELECT max(doctor_id) FROM doctor));
SELECT setval(pg_get_serial_sequence('patient','patient_id'),         (SELECT max(patient_id) FROM patient));
SELECT setval(pg_get_serial_sequence('organ_type','organ_type_id'),   (SELECT max(organ_type_id) FROM organ_type));
SELECT setval(pg_get_serial_sequence('organ','organ_id'),             (SELECT max(organ_id) FROM organ));
SELECT setval(pg_get_serial_sequence('waitlist','waitlist_id'),       (SELECT max(waitlist_id) FROM waitlist));
SELECT setval(pg_get_serial_sequence('transplant','transplant_id'),   (SELECT max(transplant_id) FROM transplant));
SELECT setval(pg_get_serial_sequence('recovery','recovery_id'),       (SELECT max(recovery_id) FROM recovery));

COMMIT;