with mgw_delta (
    MEMBER,
    ROWS_READ,
    ROWS_RETURNED )
as (
    select
        mgw.MEMBER,
        sum( mgw.ROWS_READ
            - mgw_baseline.ROWS_READ ),
        sum( mgw.ROWS_RETURNED
            - mgw_baseline.ROWS_RETURNED )
from
    table(MON_GET_WORKLOAD(null,-2)) as mgw,
    session.mgw_baseline as mgw_baseline
where
    mgw.MEMBER = mgw_baseline.MEMBER and
    mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID
group by mgw.MEMBER )
select
    w.MEMBER,
    case when ROWS_RETURNED < 1000
        then null
        else ROWS_READ / decimal(ROWS_RETURNED)
    end as ROWS_READ_PER_ROWS_RET
from mgw_delta as w;