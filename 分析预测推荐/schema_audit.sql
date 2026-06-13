-- =====================================================
-- 数据分析与预测平台 - 数据库表结构
-- =====================================================

-- =====================================================
-- 3.1 开奖数据表（澳门）
-- =====================================================
CREATE TABLE IF NOT EXISTS lottery_data_am (
    id BIGSERIAL PRIMARY KEY,
    issue_number VARCHAR(20) NOT NULL UNIQUE,           -- 期号 "163期"
    draw_date DATE NOT NULL,
    draw_date_lunar VARCHAR(30),                        -- 农历日期字符串
    lunar_year INTEGER,                                 -- 农历年份（如2026）
    lunar_zodiac_year VARCHAR(10),                      -- 对应的农历生肖年（如"马"）
    is_first_after_chunjie BOOLEAN DEFAULT FALSE,      -- 是否春节后首期
    numbers INTEGER[] NOT NULL,                         -- 7个号码数组
    zodiacs VARCHAR(10)[] NOT NULL,                    -- 对应生肖数组
    single_count INTEGER,                               -- 奇数个数
    double_count INTEGER,                               -- 偶数个数
    big_count INTEGER,                                  -- 大数个数（≥25）
    small_count INTEGER,                               -- 小数个数（<25）
    interval_distribution JSONB,                        -- 区间分布
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_am_issue ON lottery_data_am(issue_number);
CREATE INDEX IF NOT EXISTS idx_am_draw_date ON lottery_data_am(draw_date);
CREATE INDEX IF NOT EXISTS idx_am_lunar_year ON lottery_data_am(lunar_year);

-- =====================================================
-- 开奖数据表（香港）
-- =====================================================
CREATE TABLE IF NOT EXISTS lottery_data_hk (
    id BIGSERIAL PRIMARY KEY,
    issue_number VARCHAR(20) NOT NULL UNIQUE,           -- 期号 "163期"
    draw_date DATE NOT NULL,
    draw_date_lunar VARCHAR(30),                        -- 农历日期字符串
    lunar_year INTEGER,                                 -- 农历年份（如2026）
    lunar_zodiac_year VARCHAR(10),                      -- 对应的农历生肖年（如"马"）
    is_first_after_chunjie BOOLEAN DEFAULT FALSE,      -- 是否春节后首期
    numbers INTEGER[] NOT NULL,                         -- 7个号码数组
    zodiacs VARCHAR(10)[] NOT NULL,                    -- 对应生肖数组
    single_count INTEGER,                               -- 奇数个数
    double_count INTEGER,                               -- 偶数个数
    big_count INTEGER,                                  -- 大数个数（≥25）
    small_count INTEGER,                               -- 小数个数（<25）
    interval_distribution JSONB,                        -- 区间分布
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hk_issue ON lottery_data_hk(issue_number);
CREATE INDEX IF NOT EXISTS idx_hk_draw_date ON lottery_data_hk(draw_date);
CREATE INDEX IF NOT EXISTS idx_hk_lunar_year ON lottery_data_hk(lunar_year);

-- =====================================================
-- 3.2 预测记录表（澳门）
-- =====================================================
CREATE TABLE IF NOT EXISTS predictions_am (
    id BIGSERIAL PRIMARY KEY,
    issue_number VARCHAR(20) NOT NULL UNIQUE,           -- 预测对应的期号
    predict_date DATE NOT NULL,                         -- 预测生成日期
    top6_zodiacs JSONB,          -- [{"zodiac":"鼠","predicted_accuracy":78.5}, ...]
    triple4_groups JSONB,        -- [{"group":["鼠","龙","猴"],"numbers":[7,19,31,3,15,27,11,23,35]}, ...]
    top12_numbers JSONB,         -- [{"number":31,"zodiac":"鼠","frequency":12}, ...]
    actual_result JSONB,                                -- 实际开奖结果（回填）
    hit_rate_top6 DECIMAL(5,2),                         -- 特肖6只命中率(%)
    hit_rate_triple4 DECIMAL(5,2),                      -- 三肖4组命中率(%)
    hit_rate_top12 DECIMAL(5,2),                        -- 热门12数字命中率(%)
    accuracy_rate DECIMAL(5,2),                         -- 综合加权准确率(%)
    hit_status JSONB,                                   -- 详细命中情况
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_am_issue ON predictions_am(issue_number);
CREATE INDEX IF NOT EXISTS idx_pred_am_date ON predictions_am(predict_date);

-- =====================================================
-- 预测记录表（香港）
-- =====================================================
CREATE TABLE IF NOT EXISTS predictions_hk (
    id BIGSERIAL PRIMARY KEY,
    issue_number VARCHAR(20) NOT NULL UNIQUE,           -- 预测对应的期号
    predict_date DATE NOT NULL,                         -- 预测生成日期
    top6_zodiacs JSONB,          -- [{"zodiac":"鼠","predicted_accuracy":78.5}, ...]
    triple4_groups JSONB,        -- [{"group":["鼠","龙","猴"],"numbers":[7,19,31,3,15,27,11,23,35]}, ...]
    top12_numbers JSONB,         -- [{"number":31,"zodiac":"鼠","frequency":12}, ...]
    actual_result JSONB,                                -- 实际开奖结果（回填）
    hit_rate_top6 DECIMAL(5,2),                         -- 特肖6只命中率(%)
    hit_rate_triple4 DECIMAL(5,2),                      -- 三肖4组命中率(%)
    hit_rate_top12 DECIMAL(5,2),                        -- 热门12数字命中率(%)
    accuracy_rate DECIMAL(5,2),                         -- 综合加权准确率(%)
    hit_status JSONB,                                   -- 详细命中情况
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_hk_issue ON predictions_hk(issue_number);
CREATE INDEX IF NOT EXISTS idx_pred_hk_date ON predictions_hk(predict_date);

-- =====================================================
-- 3.3 准确率统计汇总表
-- =====================================================
CREATE TABLE IF NOT EXISTS accuracy_summary (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(10) NOT NULL,   -- 'AM' or 'HK'
    stat_date DATE NOT NULL,
    avg_accuracy_7d DECIMAL(5,2),
    avg_accuracy_30d DECIMAL(5,2),
    best_issue VARCHAR(20),
    worst_issue VARCHAR(20),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_acc_summary_source_date ON accuracy_summary(source_id, stat_date);

-- =====================================================
-- 审计日志表（数据版本化）
-- =====================================================
CREATE TABLE IF NOT EXISTS data_audit (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,   -- INSERT/UPDATE/DELETE
    record_id BIGINT,
    data_snapshot JSONB,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_table ON data_audit(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_time ON data_audit(valid_from);

-- =====================================================
-- 多源校验表
-- =====================================================
CREATE TABLE IF NOT EXISTS source_validation (
    id BIGSERIAL PRIMARY KEY,
    source_id VARCHAR(10) NOT NULL,
    url VARCHAR(255) NOT NULL,
    response_hash VARCHAR(64),
    record_count INTEGER,
    validation_status VARCHAR(20) DEFAULT 'pending',  -- pending/success/failed
    error_message TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_validation_source ON source_validation(source_id);
CREATE INDEX IF NOT EXISTS idx_validation_status ON source_validation(validation_status);

-- =====================================================
-- 物化视图：统计汇总
-- =====================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS lottery_statistics_am AS
SELECT
    lunar_zodiac_year,
    COUNT(*) as total_issues,
    AVG(single_count) as avg_single_count,
    AVG(double_count) as avg_double_count,
    AVG(big_count) as avg_big_count,
    AVG(small_count) as avg_small_count
FROM lottery_data_am
GROUP BY lunar_zodiac_year;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_am_zodiac ON lottery_statistics_am(lunar_zodiac_year);

CREATE MATERIALIZED VIEW IF NOT EXISTS lottery_statistics_hk AS
SELECT
    lunar_zodiac_year,
    COUNT(*) as total_issues,
    AVG(single_count) as avg_single_count,
    AVG(double_count) as avg_double_count,
    AVG(big_count) as avg_big_count,
    AVG(small_count) as avg_small_count
FROM lottery_data_hk
GROUP BY lunar_zodiac_year;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_hk_zodiac ON lottery_statistics_hk(lunar_zodiac_year);