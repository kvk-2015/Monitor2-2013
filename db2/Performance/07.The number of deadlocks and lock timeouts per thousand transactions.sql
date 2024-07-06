with mgw_delta (
    MEMBER,
    DEADLOCKS,
    LOCK_TIMEOUTS,
    TOTAL_APP_COMMITS )
as ( 
select
    mgw.MEMBER,
    sum( mgw.DEADLOCKS
        - mgw_baseline.DEADLOCKS ),
    sum( mgw.LOCK_TIMEOUTS
        - mgw_baseline.LOCK_TIMEOUTS ),
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
        else 1000 * (w.DEADLOCKS + w.LOCK_TIMEOUTS) / decimal(w.TOTAL_APP_COMMITS)
    end as DL_AND_LOCK_TMO_PER_1000_TX
from mgw_delta as w;