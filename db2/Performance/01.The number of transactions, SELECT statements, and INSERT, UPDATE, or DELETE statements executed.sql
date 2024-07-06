with 
mgw_delta ( 
    MEMBER,
    SELECT_SQL_STMTS,
    UID_SQL_STMTS,
    TOTAL_APP_COMMITS )
as (
    select
        mgw.MEMBER,
        sum( mgw.SELECT_SQL_STMTS
            - mgw_baseline.SELECT_SQL_STMTS),
        sum( mgw.UID_SQL_STMTS
            - mgw_baseline.UID_SQL_STMTS),
        sum( mgw.TOTAL_APP_COMMITS 
            - mgw_baseline.TOTAL_APP_COMMITS)
    from
        table(MON_GET_WORKLOAD(null,-2)) as mgw,
        session.mgw_baseline as mgw_baseline
    where
        mgw.MEMBER = mgw_baseline.MEMBER and
        mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID
    group by mgw.MEMBER )
select
    MEMBER,
    SELECT_SQL_STMTS,
    UID_SQL_STMTS,
    TOTAL_APP_COMMITS
from mgw_delta;