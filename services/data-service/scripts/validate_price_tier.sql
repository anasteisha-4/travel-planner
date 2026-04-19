-- Validate price_tier population coverage

-- Total POI with price_tier assigned
SELECT
    COUNT(*) as total_poi,
    SUM(CASE WHEN price_tier IS NOT NULL THEN 1 ELSE 0 END) as with_price_tier,
    SUM(CASE WHEN price_tier IS NULL THEN 1 ELSE 0 END) as without_price_tier,
    ROUND(100.0 * SUM(CASE WHEN price_tier IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as coverage_percent
FROM poi;

-- Distribution by price_tier
SELECT
    price_tier,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM poi), 2) as percent
FROM poi
GROUP BY price_tier
ORDER BY count DESC;

-- POI with entrance_fee_usd
SELECT
    COUNT(*) as with_fee,
    COUNT(DISTINCT destination_id) as destinations_with_fees,
    MIN(entrance_fee_usd) as min_fee,
    MAX(entrance_fee_usd) as max_fee,
    ROUND(AVG(entrance_fee_usd), 2) as avg_fee
FROM poi
WHERE entrance_fee_usd IS NOT NULL;

-- Distribution by category and price_tier
SELECT
    category,
    price_tier,
    COUNT(*) as count
FROM poi
WHERE price_tier IS NOT NULL
GROUP BY category, price_tier
ORDER BY category, count DESC
LIMIT 20;

-- Sample POI by tier to verify correctness
SELECT name, category, tags, price_tier, entrance_fee_usd FROM poi
WHERE price_tier = 'free'
ORDER BY RANDOM()
LIMIT 5;

SELECT name, category, tags, price_tier, entrance_fee_usd FROM poi
WHERE price_tier = 'budget'
ORDER BY RANDOM()
LIMIT 5;

SELECT name, category, tags, price_tier, entrance_fee_usd FROM poi
WHERE price_tier = 'mid'
ORDER BY RANDOM()
LIMIT 5;
