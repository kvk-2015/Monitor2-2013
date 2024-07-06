with mgw_delta (
    MEMBER,
    PKG_CACHE_INSERTS,
    TOTAL_COMPILE_TIME,
    TOTAL_RQST_TIME,
    TOTAL_APP_COMMITS )
as (
select
    mgw.MEMBER,
    sum( mgw.PKG_CACHE_INSERTS
        - mgw_baseline.PKG_CACHE_INSERTS ),
    sum( mgw.TOTAL_COMPILE_TIME
        - mgw_baseline.TOTAL_COMPILE_TIME ),
    sum( mgw.TOTAL_RQST_TIME
        - mgw_baseline.TOTAL_RQST_TIME ),
    sum( mgw.TOTAL_APP_COMMITS
        - mgw_baseline.TOTAL_APP_COMMITS )
from
    table(MON_GET_WORKLOAD(null,-2)) as mgw,
    session.mgw_baseline as mgw_baseline
where
    mgw.MEMBER = mgw_baseline.MEMBER and
    mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID
group by mgw.MEMBER )
select
    w.MEMBER,
    case when w.TOTAL_APP_COMMITS < 1000
        then null
        else 1000 * w.PKG_CACHE_INSERTS / decimal(w.TOTAL_APP_COMMITS)
    end as PKG_CACHE_INS_PER_1000_TX,
    case when w.TOTAL_RQST_TIME < 1000
        then null
        else 100.0 * (w.TOTAL_COMPILE_TIME / decimal(w.TOTAL_RQST_TIME))
    end as PCT_COMPILE_TIME
from mgw_delta as w;