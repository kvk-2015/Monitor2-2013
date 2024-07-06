with mgw_delta (
    MEMBER,
    TOTAL_APP_COMMITS,
    LOCK_WAIT_TIME,
    LOCK_ESCALS )
as (
    select
        mgw.MEMBER,
        sum( mgw.TOTAL_APP_COMMITS
            - mgw_baseline.TOTAL_APP_COMMITS ),
        sum( mgw.LOCK_WAIT_TIME
            - mgw_baseline.LOCK_WAIT_TIME ),
        sum( mgw.LOCK_ESCALS
            - mgw_baseline.LOCK_ESCALS )
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
        else 1000 * w.LOCK_WAIT_TIME / decimal(w.TOTAL_APP_COMMITS)
    end as LOCK_WAIT_TIME_PER_1000_TX,
    case when w.TOTAL_APP_COMMITS < 1000
        then null
        else 1000 * w.LOCK_ESCALS / decimal(w.TOTAL_APP_COMMITS)
    end as LOCK_ESCALS_PER_1000_TX
from mgw_delta as w;