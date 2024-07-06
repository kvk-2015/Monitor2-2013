with mgw_delta (
    MEMBER,
    TOTAL_APP_COMMITS )
as (
select
    mgw.MEMBER,
    mgw.TOTAL_APP_COMMITS - mgw_baseline.TOTAL_APP_COMMITS
from
    table(MON_GET_WORKLOAD(null,-2)) as mgw,
    session.mgw_baseline as mgw_baseline
where
    mgw.MEMBER = mgw_baseline.MEMBER and
    mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID ),
mgb_delta (
    MEMBER,
    POOL_DRTY_PG_STEAL_CLNS )
as (
select
    mgb.MEMBER,
    mgb.POOL_DRTY_PG_STEAL_CLNS - mgb_baseline.POOL_DRTY_PG_STEAL_CLNS
from
    table(MON_GET_BUFFERPOOL(null,-2)) as mgb,
    session.mgb_baseline as mgb_baseline
where
    mgb.MEMBER = mgb_baseline.MEMBER and
    mgb.BP_NAME = mgb_baseline.BP_NAME )
select
    w.MEMBER,
    case when sum(w.TOTAL_APP_COMMITS) < 1000
        then null
        else 1000 * sum(b.POOL_DRTY_PG_STEAL_CLNS) / decimal(sum(w.TOTAL_APP_COMMITS))
    end as DRTY_STEAL_PER_1000_TX
from
    mgw_delta as w,
    mgb_delta as b
where
    w.MEMBER = b.MEMBER
group by w.MEMBER;