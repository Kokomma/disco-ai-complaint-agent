-- ============================================================
-- NSERC AI Complaint Agent — Supabase Schema
-- Project: AI-001 | Author: Ella
-- Run this in: supabase.com → SQL Editor → New Query → Run
-- ============================================================

CREATE TABLE IF NOT EXISTS complaint_tickets (
    id                  BIGSERIAL PRIMARY KEY,
    ticket_id           VARCHAR(20) UNIQUE NOT NULL,
    customer_phone      VARCHAR(30) NOT NULL,
    message             TEXT NOT NULL,
    category            VARCHAR(40) NOT NULL,
    category_label      VARCHAR(60),
    priority            VARCHAR(10) CHECK (priority IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    sla_hours           INT,
    ai_summary          TEXT,
    ai_response         TEXT,
    sentiment           VARCHAR(20),
    disco_assigned      VARCHAR(60),
    status              VARCHAR(20) DEFAULT 'OPEN'
                            CHECK (status IN ('OPEN','IN_PROGRESS','ESCALATED','RESOLVED','CLOSED')),
    assigned_to         VARCHAR(80),
    ops_notes           TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at on every change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_updated_at
    BEFORE UPDATE ON complaint_tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes for fast ops dashboard queries
CREATE INDEX IF NOT EXISTS idx_tickets_status     ON complaint_tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority   ON complaint_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_disco      ON complaint_tickets(disco_assigned);
CREATE INDEX IF NOT EXISTS idx_tickets_created    ON complaint_tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_phone      ON complaint_tickets(customer_phone);

-- SLA breach monitoring view
CREATE OR REPLACE VIEW vw_sla_status AS
SELECT
    ticket_id,
    customer_phone,
    category_label,
    priority,
    disco_assigned,
    status,
    sentiment,
    created_at,
    sla_hours,
    ROUND(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600, 1)
        AS hours_open,
    ROUND(sla_hours - EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600, 1)
        AS hours_remaining,
    CASE
        WHEN EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 > sla_hours
            THEN 'BREACHED'
        WHEN EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 > sla_hours * 0.8
            THEN 'AT_RISK'
        ELSE 'ON_TRACK'
    END AS sla_status
FROM complaint_tickets
WHERE status NOT IN ('RESOLVED', 'CLOSED');

-- Daily volume summary view
CREATE OR REPLACE VIEW vw_daily_summary AS
SELECT
    DATE(created_at)    AS complaint_date,
    disco_assigned,
    category_label,
    priority,
    COUNT(*)            AS total_tickets,
    COUNT(*) FILTER (WHERE status = 'RESOLVED')  AS resolved,
    COUNT(*) FILTER (WHERE status = 'ESCALATED') AS escalated,
    COUNT(*) FILTER (WHERE sentiment IN ('frustrated','angry')) AS negative_sentiment
FROM complaint_tickets
GROUP BY DATE(created_at), disco_assigned, category_label, priority
ORDER BY complaint_date DESC;

-- Row Level Security
ALTER TABLE complaint_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON complaint_tickets
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "authenticated_read" ON complaint_tickets
    FOR SELECT USING (auth.role() = 'authenticated');

-- Demo seed data
INSERT INTO complaint_tickets
    (ticket_id, customer_phone, message, category, category_label,
     priority, sla_hours, ai_summary, ai_response, sentiment,
     disco_assigned, status)
VALUES
    ('TKT-DEMO0001', 'whatsapp:+2348012345001',
     'My light don go since yesterday evening. No power at all for our whole street.',
     'outage_report', 'Power Outage', 'CRITICAL', 4,
     'Customer reports complete loss of power to entire street since yesterday evening.',
     'We don receive your complaint! Ticket TKT-DEMO0001 don open. Our team dey check the outage and we go restore light within 4 hours.',
     'frustrated', 'Ikeja DisCo', 'IN_PROGRESS'),

    ('TKT-DEMO0002', 'whatsapp:+2348023456002',
     'My electricity bill this month is N45,000 but I was not home for 2 weeks!',
     'high_bill', 'Estimated Billing', 'MEDIUM', 72,
     'Customer disputes high bill for a month they were absent, alleging estimated reading.',
     'Thank you for reaching out. Your ticket TKT-DEMO0002 has been logged. A meter reader will visit within 48 hours to verify and adjust if needed.',
     'frustrated', 'Abuja DisCo', 'OPEN'),

    ('TKT-DEMO0003', 'whatsapp:+2348034567003',
     'Our transformer at the junction is sparking and making loud noise. Very dangerous.',
     'transformer_fault', 'Transformer / Infrastructure', 'HIGH', 8,
     'Safety-critical: community transformer sparking — potential public hazard.',
     'This is being treated as an emergency (Ticket TKT-DEMO0003). Please keep residents away from the transformer. Our crew is dispatched — ETA 2 hours.',
     'urgent', 'Abuja DisCo', 'ESCALATED')
ON CONFLICT (ticket_id) DO NOTHING;
