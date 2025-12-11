-- Инициализация базы данных для тикетов и логов

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Для полнотекстового поиска

-- Таблица тикетов
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    theme VARCHAR(100) NOT NULL,
    ticket_type VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    system_service VARCHAR(255),
    reasoning TEXT,
    support_line INTEGER NOT NULL CHECK (support_line IN (1, 2, 3)),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rag_answer TEXT,
    conversation_history JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolution TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    tags JSONB,
    assigned_to VARCHAR(255),
    escalation_reason TEXT,
    user_satisfaction VARCHAR(50)
);

-- Таблица логов
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    logger_name VARCHAR(255),
    message TEXT NOT NULL,
    module VARCHAR(255),
    function_name VARCHAR(255),
    line_number INTEGER,
    user_id BIGINT,
    ticket_id INTEGER REFERENCES tickets(id),
    extra_data JSONB,
    traceback TEXT
);

-- Индексы для тикетов
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_support_line ON tickets(support_line);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_number ON tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_tickets_theme ON tickets(theme);
CREATE INDEX IF NOT EXISTS idx_tickets_conversation_history ON tickets USING GIN(conversation_history);
CREATE INDEX IF NOT EXISTS idx_tickets_tags ON tickets USING GIN(tags);

-- Индексы для логов
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_ticket_id ON logs(ticket_id);
CREATE INDEX IF NOT EXISTS idx_logs_logger_name ON logs(logger_name);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Представление для статистики тикетов
CREATE OR REPLACE VIEW ticket_stats AS
SELECT 
    support_line,
    status,
    priority,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_hours
FROM tickets
GROUP BY support_line, status, priority;

-- Функция для получения статистики очереди
CREATE OR REPLACE FUNCTION get_queue_stats()
RETURNS TABLE (
    line INTEGER,
    pending_count BIGINT,
    in_progress_count BIGINT,
    resolved_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.support_line as line,
        COUNT(*) FILTER (WHERE t.status IN ('Новое', 'В работе')) as pending_count,
        COUNT(*) FILTER (WHERE t.status = 'В работе') as in_progress_count,
        COUNT(*) FILTER (WHERE t.status IN ('Решено', 'Закрыто')) as resolved_count
    FROM tickets t
    GROUP BY t.support_line;
END;
$$ LANGUAGE plpgsql;
