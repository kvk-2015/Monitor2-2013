with mgw_delta (
    MEMBER,
    TOTAL_APP_COMMITS,
    TOTAL_SECTION_SORT_TIME,
    TOTAL_SORTS,
    SORT_OVERFLOWS )
as (
    select
        mgw.MEMBER,
        sum( mgw.TOTAL_APP_COMMITS
            - mgw_baseline.TOTAL_APP_COMMITS ),
        sum( mgw.TOTAL_SECTION_SORT_TIME
            - mgw_baseline.TOTAL_SECTION_SORT_TIME ),
        sum( mgw.TOTAL_SORTS
            - mgw_baseline.TOTAL_SORTS ),
        sum( mgw.SORT_OVERFLOWS
            - mgw_baseline.SORT_OVERFLOWS )
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
        else w.TOTAL_SECTION_SORT_TIME / decimal(w.TOTAL_APP_COMMITS)
    end as SORT_TIME_PER_TX,
    w.TOTAL_SORTS,
    w.SORT_OVERFLOWS
from mgw_delta as w;