-- Add status tracking columns to jobs table if they don't exist
ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'active' WHERE NOT EXISTS (
    SELECT 1 FROM pragma_table_info('jobs') WHERE name = 'status'
);

ALTER TABLE jobs ADD COLUMN last_seen TEXT WHERE NOT EXISTS (
    SELECT 1 FROM pragma_table_info('jobs') WHERE name = 'last_seen'
);

ALTER TABLE jobs ADD COLUMN missed_scrapes INTEGER DEFAULT 0 WHERE NOT EXISTS (
    SELECT 1 FROM pragma_table_info('jobs') WHERE name = 'missed_scrapes'
);

-- Create job status history table if it doesn't exist
CREATE TABLE IF NOT EXISTS job_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

-- Create index on job_id in status history table if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_status_history_job_id ON job_status_history (job_id);

-- Create index on status in jobs table if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);

-- Initialize last_seen for existing jobs if needed
UPDATE jobs SET last_seen = created_at WHERE last_seen IS NULL;

-- Add entries to status history for existing jobs that don't have entries yet
INSERT INTO job_status_history (job_id, status, changed_at, reason)
SELECT id, 'active', created_at, 'Initial migration'
FROM jobs
WHERE id NOT IN (SELECT job_id FROM job_status_history);