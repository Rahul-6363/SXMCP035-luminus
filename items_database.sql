CREATE DATABASE mrp_db;

USE mrp_db;

CREATE TABLE items (
    id                        INT             NOT NULL AUTO_INCREMENT,
    code                      VARCHAR(50)     NOT NULL UNIQUE,
    description               VARCHAR(255)    NOT NULL,
    part_grade                VARCHAR(50),
    component_classification  VARCHAR(100),
    revision                  VARCHAR(20),
    msl_level                 VARCHAR(20),
    category                  VARCHAR(100),
    uom                       VARCHAR(20),
    standard_cost             DECIMAL(18, 4),
    lead_time                 INT,
    mrp_type                  VARCHAR(50),
    status                    VARCHAR(20)     DEFAULT 'Active',
    PRIMARY KEY (id)
);

INSERT INTO items (code, description, part_grade, component_classification, revision, msl_level, category, uom, standard_cost, quantity, mrp_type, status) VALUES
('ITM-001', 'Resistor 10K Ohm 0402',         'A', 'Passive',   'A', '1',   'Resistor',   'PCS', 0.0050,  7, 10, 'Active'),
('ITM-002', 'Capacitor 100nF 0603',           'A', 'Passive',   'A', '2',   'Capacitor',  'PCS', 0.0080,  7,  20, 'Active'),
('ITM-003', 'IC Microcontroller STM32F103',   'A', 'Active',    'B', '3',   'IC',         'PCS', 2.5000,  21, 15, 'Active'),
('ITM-004', 'LED Red 0805',                   'B', 'Active',    'A', '1',   'LED',        'PCS', 0.0150,  14, 12, 'Active'),
('ITM-005', 'Crystal 16MHz SMD',              'A', 'Passive',   'A', '2a',  'Crystal',    'PCS', 0.3500,  14, 17, 'Active'),
('ITM-006', 'Connector USB Type-C',           'A', 'Mechanical','B', '4',   'Connector',  'PCS', 0.8500,  30, 19, 'Active'),
('ITM-007', 'PCB FR4 2-Layer',                'A', 'PCB',       'C', 'N/A', 'PCB',        'PCS', 3.2000,  15, 25, 'Active'),
('ITM-008', 'Inductor 10uH 0805',             'A', 'Passive',   'A', '1',   'Inductor',   'PCS', 0.0450,  10, 28, 'Active'),
('ITM-009', 'Transistor NPN SOT-23',          'A', 'Active',    'A', '1',   'Transistor', 'PCS', 0.0300,  10, 12, 'Active'),
('ITM-010', 'Voltage Regulator 3.3V SOT-223', 'A', 'Active',    'B', '2',   'IC',         'PCS', 0.4500,  21, 18, 'Inactive');
