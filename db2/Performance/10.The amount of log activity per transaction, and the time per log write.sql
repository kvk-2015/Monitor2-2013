with mgw_delta (
    MEMBER,
    TOTAL_APP_COMMITS )
as (
select
    mgw.MEMBER,
    sum( mgw.TOTAL_APP_COMMITS
        - mgw_baseline.TOTAL_APP_COMMITS )
from
    table(MON_GET_WORKLOAD(null,-2)) as mgw,
    session.mgw_baseline as mgw_baseline
where
    mgw.MEMBER = mgw_baseline.MEMBER and
    mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID
group by mgw.MEMBER ),
mgtl_delta (
    MEMBER,
    LOG_WRITES,
    LOG_WRITE_TIME )
as (
select
    mgtl.MEMBER,
    mgtl.LOG_WRITES - mgtl_baseline.LOG_WRITES,
    mgtl.LOG_WRITE_TIME - mgtl_baseline.LOG_WRITE_TIME
from
    table(MON_GET_TRANSACTION_LOG(-2)) as mgtl,
    session.mgtl_baseline as mgtl_baseline
where
    mgtl.MEMBER = mgtl_baseline.MEMBER )
select
    w.MEMBER,
    case when w.TOTAL_APP_COMMITS < 1000
        then null
        else 1000 * tl.LOG_WRITES / decimal(w.TOTAL_APP_COMMITS)
    end as LOG_WR_PER_1000_TX,
    case when w.TOTAL_APP_COMMITS < 1000
        then null
        else 1000 * tl.LOG_WRITE_TIME / decimal(w.TOTAL_APP_COMMITS)
    end as LOG_WR_TIME_PER_1000_TX,
    case when tl.LOG_WRITES < 1000
        then null
        else tl.LOG_WRITE_TIME / decimal(tl.LOG_WRITES)
    end as TIME_PER_LOG_WR
from
    mgw_delta as w,
    mgtl_delta as tl
where
    w.MEMBER = tl.MEMBER;