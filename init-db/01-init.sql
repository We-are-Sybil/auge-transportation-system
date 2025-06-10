-- Basic test table
CREATE TABLE connection_test (
    id SERIAL PRIMARY KEY,
    test_message VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data
INSERT INTO connection_test (test_message) VALUES 
    ('PostgreSQL initialized'),
    ('Ready for SQLAlchemy');

-- Health check function
CREATE OR REPLACE FUNCTION health_check()
RETURNS TABLE(status TEXT, db_name TEXT, connections INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'healthy'::TEXT,
        current_database()::TEXT,
        (SELECT count(*)::INTEGER FROM pg_stat_activity WHERE datname = current_database());
END;
$$ LANGUAGE plpgsql;
