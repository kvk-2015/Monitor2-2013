with sdb_delta (
    COMMIT_SQL_STMTS,
    LOG_WRITE_TIME_S,
    LOG_WRITE_TIME_NS,
    LOG_WRITES )
as (
select
    sdb.COMMIT_SQL_STMTS - sdb_baseline.COMMIT_SQL_STMTS,
    sdb.LOG_WRITE_TIME_S - sdb_baseline.LOG_WRITE_TIME_S,
    sdb.LOG_WRITE_TIME_NS - sdb_baseline.LOG_WRITE_TIME_NS,
    sdb.LOG_WRITES - sdb_baseline.LOG_WRITES
from
    SYSIBMADM.SNAPDB as sdb,
    session.sdb_baseline as sdb_baseline )
select
    case when sdb.COMMIT_SQL_STMTS < 1000
        then null
        else 1000 * sdb.LOG_WRITES / decimal(sdb.COMMIT_SQL_STMTS)
    end as LOG_WR_PER_1000_TX,
    case when sdb.COMMIT_SQL_STMTS < 1000
        then null
        else 1000 * (1000 * sdb.LOG_WRITE_TIME_S + sdb.LOG_WRITE_TIME_NS / 1000000.0)
            / decimal(sdb.COMMIT_SQL_STMTS)
    end as LOG_WR_TIME_PER_1000_TX,
    case when sdb.LOG_WRITES < 1000
        then null
        else (1000 * sdb.LOG_WRITE_TIME_S + sdb.LOG_WRITE_TIME_NS / 1000000.0)
            / decimal(sdb.LOG_WRITES)
    end as TIME_PER_LOG_WR
from sdb_delta as sdb;