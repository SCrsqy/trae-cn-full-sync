-- =====================================================
-- 数据版本化与审计表设计
-- 支持数据追溯、回滚、多源一致性校验
-- =====================================================

-- 1. 审计日志表(替代直接UPDATE/DELETE)
CREATE TABLE IF NOT EXISTS lottery_data_audit (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(10) NOT NULL,  -- 'AM' or 'HK'
    issue_number VARCHAR(20) NOT NULL,
    operation VARCHAR(10) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    data_snapshot JSONB NOT NULL,    -- 完整数据快照
    change_reason VARCHAR(255),       -- 变更原因
    source_verified BOOLEAN DEFAULT FALSE,  -- 是否通过多源校验
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT CURRENT_USER
);

-- 审计表索引
CREATE INDEX idx_audit_source_issue ON lottery_data_audit(source_id, issue_number);
CREATE INDEX idx_audit_created_at ON lottery_data_audit(created_at);
CREATE INDEX idx_audit_operation ON lottery_data_audit(operation);

-- 2. 多源校验记录表
CREATE TABLE IF NOT EXISTS source_verification (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(10) NOT NULL,
    issue_number VARCHAR(20) NOT NULL,
    source_name VARCHAR(50) NOT NULL,  -- 'primary', 'backup1', 'backup2'
    raw_data JSONB NOT NULL,           -- 原始爬取数据
    fetch_status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'timeout'
    error_message TEXT,
    fetched_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_id, issue_number, source_name)
);

CREATE INDEX idx_verification_issue ON source_verification(source_id, issue_number);

-- 3. 数据一致性状态表
CREATE TABLE IF NOT EXISTS data_consistency (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(10) NOT NULL,
    issue_number VARCHAR(20) NOT NULL,
    consistency_status VARCHAR(20) NOT NULL,  -- 'consistent', 'inconsistent', 'pending_review'
    discrepancy_details JSONB,  -- 具体差异描述
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consistency_status ON data_consistency(consistency_status);

-- 4. 触发器函数: 自动记录审计日志
CREATE OR REPLACE FUNCTION fn_lottery_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- 记录INSERT操作
    IF TG_OP = 'INSERT' THEN
        INSERT INTO lottery_data_audit (source_id, issue_number, operation, data_snapshot)
        VALUES (NEW.source_id, NEW.issue_number, 'INSERT', to_jsonb(NEW));
        RETURN NEW;

    -- 记录UPDATE操作(保留旧值)
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO lottery_data_audit (source_id, issue_number, operation, data_snapshot, change_reason)
        VALUES (OLD.source_id, OLD.issue_number, 'UPDATE', to_jsonb(OLD), 
                'Updated at ' || NOW() || ' from ' || COALESCE(OLD.numbers::text, 'null') || ' to ' || COALESCE(NEW.numbers::text, 'null'));
        RETURN NEW;

    -- 记录DELETE操作
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO lottery_data_audit (source_id, issue_number, operation, data_snapshot)
        VALUES (OLD.source_id, OLD.issue_number, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 5. 视图: 当前有效数据(只读)
CREATE OR REPLACE VIEW v_current_lottery_data AS
WITH latest_records AS (
    SELECT DISTINCT ON (source_id, issue_number)
           source_id, issue_number, data_snapshot->>'issue_number' as issue_num,
           data_snapshot
    FROM lottery_data_audit
    WHERE operation != 'DELETE'
    ORDER BY source_id, issue_number, created_at DESC
)
SELECT 
    (data_snapshot->>'source_id')::VARCHAR as source_id,
    (data_snapshot->>'issue_number')::VARCHAR as issue_number,
    (data_snapshot->>'draw_date')::DATE as draw_date,
    (data_snapshot->>'numbers')::INTEGER[] as numbers,
    (data_snapshot->>'zodiacs')::VARCHAR[] as zodiacs,
    (data_snapshot->>'lunar_zodiac_year')::VARCHAR as lunar_zodiac_year
FROM latest_records;

-- 6. 物化视图: 准确率统计(定期刷新)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_accuracy_stats AS
SELECT 
    source_id,
    DATE_TRUNC('day', created_at) as stat_date,
    COUNT(*) as total_predictions,
    AVG(hit_rate_top6) as avg_hit_rate_top6,
    AVG(hit_rate_triple4) as avg_hit_rate_triple4,
    AVG(hit_rate_top12) as avg_hit_rate_top12,
    AVG(accuracy_rate) as avg_accuracy_rate,
    MAX(accuracy_rate) as best_accuracy,
    MIN(accuracy_rate) as worst_accuracy
FROM predictions_am
GROUP BY source_id, DATE_TRUNC('day', created_at)
UNION ALL
SELECT 
    source_id,
    DATE_TRUNC('day', created_at) as stat_date,
    COUNT(*) as total_predictions,
    AVG(hit_rate_top6) as avg_hit_rate_top6,
    AVG(hit_rate_triple4) as avg_hit_rate_triple4,
    AVG(hit_rate_top12) as avg_hit_rate_top12,
    AVG(accuracy_rate) as avg_accuracy_rate,
    MAX(accuracy_rate) as best_accuracy,
    MIN(accuracy_rate) as worst_accuracy
FROM predictions_hk
GROUP BY source_id, DATE_TRUNC('day', created_at);

CREATE UNIQUE INDEX idx_mv_accuracy ON mv_accuracy_stats(source_id, stat_date);

-- 7. 刷新物化视图的函数
CREATE OR REPLACE FUNCTION refresh_accuracy_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_accuracy_stats;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE lottery_data_audit IS '数据变更审计日志，支持追溯和回滚';
COMMENT ON TABLE source_verification IS '多源数据校验记录';
COMMENT ON TABLE data_consistency IS '数据一致性状态追踪';