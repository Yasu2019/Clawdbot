-- READ ONLY ONLY. Never execute write statements.

-- 不良率上位
SELECT TOP 10
    ProductNo,
    LotNo,
    DefectCount,
    InspectionCount,
    CAST(DefectCount AS float) / NULLIF(InspectionCount, 0) AS DefectRate
FROM dbo.QualityResults WITH (NOLOCK)
WHERE InspectionDate BETWEEN @StartDate AND @EndDate
ORDER BY DefectRate DESC;

-- SQL Guardで禁止する語句:
-- UPDATE DELETE INSERT MERGE DROP ALTER TRUNCATE EXEC CREATE
