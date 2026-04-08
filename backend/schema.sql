-- ERP System Schema: Inventory + BOM
-- Run this once against your MySQL MCP database

CREATE DATABASE IF NOT EXISTS MCP;
USE MCP;

-- ---------------------------------------------------------------------------
-- Inventory
-- quantity        = total stock on hand
-- quantity_in_use = blocked by active BOM runs (not available)
-- available       = quantity - quantity_in_use (computed in queries)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    code                     VARCHAR(50)    UNIQUE NOT NULL,
    description              TEXT,
    part_grade               VARCHAR(50),
    component_classification VARCHAR(50),
    revision                 VARCHAR(20),
    msl_level                VARCHAR(20),
    category                 VARCHAR(50),
    uom                      VARCHAR(20)    DEFAULT 'pcs',
    standard_cost            DECIMAL(10,2)  DEFAULT 0.00,
    lead_time                INT            DEFAULT 0,
    quantity                 INT            DEFAULT 0,
    quantity_in_use          INT            DEFAULT 0,
    status                   VARCHAR(20)    DEFAULT 'Active',
    created_at               TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Bill of Materials (header)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bom (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)  UNIQUE NOT NULL,
    description     TEXT,
    output_quantity INT           DEFAULT 1,
    lead_time_days  INT           DEFAULT 14,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- BOM line items — each row = one component required per BOM output unit
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bom_items (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    bom_id       INT         NOT NULL,
    item_code    VARCHAR(50) NOT NULL,
    qty_required INT         NOT NULL DEFAULT 1,
    FOREIGN KEY (bom_id)    REFERENCES bom(id)       ON DELETE CASCADE,
    FOREIGN KEY (item_code) REFERENCES inventory(code) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------------
-- Seed inventory with mock data (safe to re-run — INSERT IGNORE)
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO inventory
    (code, description, part_grade, component_classification, revision, msl_level, category, uom, standard_cost, lead_time, quantity, status)
VALUES
    ('MCU-32F103', '32-bit Microcontroller ARM Cortex',  'Industrial',  'IC',        'Rev B', 'MSL 3', 'Semiconductor', 'pcs',  290.45, 45, 1500, 'Active'),
    ('CAP-0805-10U','10uF 16V Ceramic Capacitor 0805',  'Commercial',  'Passive',   '-',     'MSL 1', 'Capacitor',     'reel', 1250.20,14,   42, 'Active'),
    ('RES-0603-10K','10K Ohm 1% 1/10W Resistor 0603',  'Automotive',  'Passive',   'A.1',   'MSL 1', 'Resistor',      'reel',  650.50,14,  120, 'Active'),
    ('CON-USB-C',  'USB Type-C Receptacle SMD',          'Commercial',  'Connector', 'v2.0',  'MSL 1', 'Connector',     'pcs',   70.85, 21,    8, 'Active'),
    ('PCB-MAIN-01','Main Control Board Bare PCB',        'Custom',      'PCB',       'V1.4',  '-',     'PCB',           'pcs', 1050.40, 28,    3, 'Obsolete'),
    ('PWR-5V-2A',  '5V 2A DC-DC Converter Module',       'Industrial',  'Power',     'Rev A', 'MSL 2', 'Power Supply',  'pcs',  495.90, 30,  340, 'Active');
