CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    client1_name TEXT NOT NULL,
    client1_dob TEXT,
    client1_ssn_last4 TEXT,
    client1_salary REAL DEFAULT 0,

    client2_name TEXT,
    client2_dob TEXT,
    client2_ssn_last4 TEXT,
    client2_salary REAL DEFAULT 0,

    monthly_outflow REAL DEFAULT 0,
    insurance_deductibles_total REAL DEFAULT 0,
    account_floor REAL DEFAULT 1000
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    category TEXT NOT NULL,          -- retirement | non_retirement | trust | liability
    owner TEXT,                       -- client1 | client2 | joint  (null for trust/liability)
    account_type TEXT NOT NULL,       -- 'IRA', 'Roth IRA', '401K', 'Wells Fargo Checking', etc.
    account_number_last4 TEXT,
    sacs_role TEXT,                   -- inflow | outflow | private_reserve | investment | null
    property_address TEXT,            -- trust only
    interest_rate REAL,               -- liability only

    -- cache of last entered values
    last_balance REAL,
    last_cash_balance REAL,
    last_value_date TEXT,

    sort_order INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_accounts_client ON accounts(client_id);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_date TEXT NOT NULL,
    snapshot_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_client ON reports(client_id);
