with sdb_delta (
    SELECT_SQL_STMTS,
    UID_SQL_STMTS,
    COMMIT_SQL_STMTS )
as (
select
    sum( sdb.SELECT_SQL_STMTS
        - sdb_baseline.SELECT_SQL_STMTS),
    sum( sdb.UID_SQL_STMTS
        - sdb_baseline.UID_SQL_STMTS),
    sum( sdb.COMMIT_SQL_STMTS
        - sdb_baseline.COMMIT_SQL_STMTS)
from
    sysibmadm.snapdb as sdb,
    session.sdb_baseline as sdb_baseline )
select
    SELECT_SQL_STMTS,
    UID_SQL_STMTS,
    COMMIT_SQL_STMTS
from sdb_delta;