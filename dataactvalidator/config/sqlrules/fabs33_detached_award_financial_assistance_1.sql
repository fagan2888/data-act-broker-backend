-- PeriodOfPerformanceCurrentEndDate is an optional field, but when provided, must follow YYYYMMDD format
CREATE OR REPLACE function pg_temp.is_date(str text) returns boolean AS $$
BEGIN
  perform CAST(str AS DATE);
  return TRUE;
EXCEPTION WHEN others THEN
  return FALSE;
END;
$$ LANGUAGE plpgsql;

SELECT
    row_number,
    period_of_performance_curr,
    afa_generated_unique AS "uniqueid_afa_generated_unique"
FROM detached_award_financial_assistance
WHERE submission_id = {0}
    AND COALESCE(period_of_performance_curr, '') <> ''
    AND CASE WHEN pg_temp.is_date(COALESCE(period_of_performance_curr, '0'))
            THEN period_of_performance_curr !~ '\d\d\d\d\d\d\d\d'
            ELSE TRUE
        END
    AND UPPER(COALESCE(correction_delete_indicatr, '')) <> 'D';
