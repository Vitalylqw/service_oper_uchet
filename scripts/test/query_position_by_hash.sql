-- Запрос позиции по hash_key из таблицы read_positions
-- hash_key = f555c1114bebd7aa85d2a9c46def52d3

-- Основной запрос
SELECT 
    id,
    deal_id,
    deal_key,
    position_number,
    hash_key,
    product_name,
    supplier_name,
    pickup_date,
    quantity,
    purchase_price_amount,
    sale_price_amount,
    revenue_amount,
    margin_amount,
    cost_amount,
    client_name,
    period_month,
    period_year,
    created_at,
    updated_at,
    version
FROM read_positions 
WHERE hash_key = 'f555c1114bebd7aa85d2a9c46def52d3';

-- Дополнительный запрос: поиск всех позиций той же сделки
SELECT 
    position_number,
    hash_key,
    product_name,
    supplier_name,
    revenue_amount,
    margin_amount
FROM read_positions 
WHERE deal_id = (
    SELECT deal_id 
    FROM read_positions 
    WHERE hash_key = 'f555c1114bebd7aa85d2a9c46def52d3'
    LIMIT 1
)
ORDER BY position_number;

-- Проверка уникальности hash_key
SELECT 
    hash_key,
    COUNT(*) as count
FROM read_positions 
WHERE hash_key = 'f555c1114bebd7aa85d2a9c46def52d3'
GROUP BY hash_key;

-- Статистика по таблице (для контекста)
SELECT 
    COUNT(*) as total_positions,
    COUNT(DISTINCT deal_id) as total_deals,
    COUNT(DISTINCT hash_key) as unique_hashes
FROM read_positions;

-- Поиск похожих hash_key (если нужный не найден)
SELECT hash_key, product_name, client_name
FROM read_positions 
LIMIT 10;