with mgb_delta (
    MEMBER,
    POOL_DATA_P_READS,
    POOL_TEMP_DATA_P_READS,
    POOL_INDEX_P_READS,
    POOL_TEMP_INDEX_P_READS,
    POOL_DATA_WRITES,
    POOL_INDEX_WRITES )
as (
select 
    mgb.MEMBER, 
    sum( mgb.POOL_DATA_P_READS
        - mgb_baseline.POOL_DATA_P_READS ),
    sum( mgb.POOL_TEMP_DATA_P_READS
        - mgb_baseline.POOL_TEMP_DATA_P_READS ),
    sum( mgb.POOL_INDEX_P_READS
        - mgb_baseline.POOL_INDEX_P_READS ),
    sum( mgb.POOL_TEMP_INDEX_P_READS
        - mgb_baseline.POOL_TEMP_INDEX_P_READS ),
    sum( mgb.POOL_DATA_WRITES
        - mgb_baseline.POOL_DATA_WRITES ),
    sum( mgb.POOL_INDEX_WRITES
        - mgb_baseline.POOL_INDEX_WRITES )
from
    table(MON_GET_BUFFERPOOL(null,-2)) as mgb,
    session.mgb_baseline as mgb_baseline
where
    mgb.MEMBER = mgb_baseline.MEMBER and
    mgb.BP_NAME = mgb_baseline.BP_NAME
group by mgb.MEMBER ),
mgw_delta (
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
group by mgw.MEMBER)
select
    b.MEMBER,
    case when w.TOTAL_APP_COMMITS < 1000
        then null
        else ( b.POOL_DATA_P_READS + b.POOL_INDEX_P_READS + b.POOL_TEMP_DATA_P_READS + b.POOL_TEMP_INDEX_P_READS )
            / decimal(w.TOTAL_APP_COMMITS)
    end as BP_PHYS_RD_PER_TX,
    case when w.TOTAL_APP_COMMITS < 1000
        then NULL
        else (b.POOL_DATA_WRITES + b.POOL_INDEX_WRITES)
            / decimal(w.TOTAL_APP_COMMITS)
    end as BP_PHYS_WR_PER_TX
from
    mgb_delta as b,
    mgw_delta as w
where b.MEMBER = w.MEMBER;