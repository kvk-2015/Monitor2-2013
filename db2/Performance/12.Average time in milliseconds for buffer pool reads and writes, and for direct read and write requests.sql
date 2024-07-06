with mgtbsp_delta (
    MEMBER,
    TBSP_NAME,
    POOL_DATA_P_READS, POOL_TEMP_DATA_P_READS,
    POOL_XDA_P_READS, POOL_TEMP_XDA_P_READS,
    POOL_INDEX_P_READS, POOL_TEMP_INDEX_P_READS,
    POOL_READ_TIME, POOL_DATA_WRITES, POOL_XDA_WRITES,
    POOL_INDEX_WRITES, POOL_WRITE_TIME,
    DIRECT_READ_REQS, DIRECT_READ_TIME,
    DIRECT_WRITE_REQS, DIRECT_WRITE_TIME )
as (
select 
    mgtbsp.MEMBER,
    substr(mgtbsp.TBSP_NAME,1,20),
    sum(mgtbsp.POOL_DATA_P_READS 
        - mgtbsp_baseline.POOL_DATA_P_READS),
    sum(mgtbsp.POOL_TEMP_DATA_P_READS
        - mgtbsp_baseline.POOL_TEMP_DATA_P_READS),
    sum(mgtbsp.POOL_XDA_P_READS
        - mgtbsp_baseline.POOL_XDA_P_READS),
    sum(mgtbsp.POOL_TEMP_XDA_P_READS
        - mgtbsp_baseline.POOL_TEMP_XDA_P_READS),
    sum(mgtbsp.POOL_INDEX_P_READS
        - mgtbsp_baseline.POOL_INDEX_P_READS),
    sum(mgtbsp.POOL_TEMP_INDEX_P_READS
        - mgtbsp_baseline.POOL_TEMP_INDEX_P_READS),
    sum(mgtbsp.POOL_READ_TIME
        - mgtbsp_baseline.POOL_READ_TIME),
    sum(mgtbsp.POOL_DATA_WRITES
        - mgtbsp_baseline.POOL_DATA_WRITES),
    sum(mgtbsp.POOL_XDA_WRITES
        - mgtbsp_baseline.POOL_XDA_WRITES),
    sum(mgtbsp.POOL_INDEX_WRITES
        - mgtbsp_baseline.POOL_INDEX_WRITES),
    sum(mgtbsp.POOL_WRITE_TIME
        - mgtbsp_baseline.POOL_WRITE_TIME),
    sum(mgtbsp.DIRECT_READ_REQS
        - mgtbsp_baseline.DIRECT_READ_REQS),
    sum(mgtbsp.DIRECT_READ_TIME
        - mgtbsp_baseline.DIRECT_READ_TIME),
    sum(mgtbsp.DIRECT_WRITE_REQS
        - mgtbsp_baseline.DIRECT_WRITE_REQS),
    sum(mgtbsp.DIRECT_WRITE_TIME 
        - mgtbsp_baseline.DIRECT_WRITE_TIME)
from
    table(MON_GET_TABLESPACE(null,-2)) as mgtbsp,
    session.mgtbsp_baseline as mgtbsp_baseline
where
    mgtbsp.MEMBER = mgtbsp_baseline.MEMBER and
    mgtbsp.TBSP_NAME = mgtbsp_baseline.TBSP_NAME
group by mgtbsp.MEMBER, mgtbsp.TBSP_NAME )
select
    m.MEMBER,
    m.TBSP_NAME,
    case when m.POOL_DATA_P_READS + m.POOL_TEMP_DATA_P_READS + m.POOL_XDA_P_READS + m.POOL_TEMP_XDA_P_READS
            + m.POOL_INDEX_P_READS + m.POOL_TEMP_INDEX_P_READS > 100 
        then decimal(m.POOL_READ_TIME) / ( m.POOL_DATA_P_READS + m.POOL_TEMP_DATA_P_READS + m.POOL_XDA_P_READS
            + m.POOL_TEMP_XDA_P_READS + m.POOL_INDEX_P_READS + m.POOL_TEMP_INDEX_P_READS)
        else null
    end as MS_PER_POOL_READ,
    case when m.POOL_DATA_WRITES + m.POOL_XDA_WRITES + m.POOL_INDEX_WRITES > 100
        then decimal(m.POOL_WRITE_TIME) /(m.POOL_DATA_WRITES + m.POOL_XDA_WRITES + m.POOL_INDEX_WRITES)
        else null
    end as MS_PER_POOL_WRITE,
    case when m.DIRECT_READ_REQS > 100
        then decimal(m.DIRECT_READ_TIME) / m.DIRECT_READ_REQS
        else null
    end as MS_PER_DIRECT_READ_REQ,
    case when m.DIRECT_WRITE_REQS > 100
        then decimal(m.DIRECT_WRITE_TIME) / m.DIRECT_WRITE_REQS
        else null
    end as MS_PER_DIRECT_WRITE_REQ
from mgtbsp_delta as m;