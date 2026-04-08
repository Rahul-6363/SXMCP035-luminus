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
    quantity                  INT,
    status                    VARCHAR(20)     DEFAULT 'Active',
    PRIMARY KEY (id)
);
