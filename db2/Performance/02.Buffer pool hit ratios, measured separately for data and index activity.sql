with mgb_delta ( 
    MEMBER,
    BP_NAME,
    POOL_DATA_L_READS,
    POOL_DATA_P_READS,
    POOL_TEMP_DATA_L_READS,
    POOL_TEMP_DATA_P_READS,
    POOL_ASYNC_DATA_READS,
    POOL_INDEX_L_READS,
    POOL_INDEX_P_READS,
    POOL_TEMP_INDEX_L_READS,
    POOL_TEMP_INDEX_P_READS,
    POOL_ASYNC_INDEX_READS )
as (
    select
        mgb.MEMBER,
        mgb.BP_NAME,
        mgb.POOL_DATA_L_READS
            - mgb_base.POOL_DATA_L_READS,
        mgb.POOL_DATA_P_READS
            - mgb_base.POOL_DATA_P_READS,
        mgb.POOL_TEMP_DATA_L_READS
            - mgb_base.POOL_TEMP_DATA_L_READS,
        mgb.POOL_TEMP_DATA_P_READS
            - mgb_base.POOL_TEMP_DATA_P_READS,
        mgb.POOL_ASYNC_DATA_READS
            - mgb_base.POOL_ASYNC_DATA_READS,
        mgb.POOL_INDEX_L_READS
            - mgb_base.POOL_INDEX_L_READS,
        mgb.POOL_INDEX_P_READS
            - mgb_base.POOL_INDEX_P_READS,
        mgb.POOL_TEMP_INDEX_L_READS
            - mgb_base.POOL_TEMP_INDEX_L_READS,
        mgb.POOL_TEMP_INDEX_P_READS
            - mgb_base.POOL_TEMP_INDEX_P_READS,
        mgb.POOL_ASYNC_INDEX_READS
            - mgb_base.POOL_ASYNC_INDEX_READS
    from
        table(MON_GET_BUFFERPOOL(null,-2)) as mgb,
        session.mgb_baseline as mgb_base
    where
        mgb.member = mgb_base.member and
        mgb.bp_name = mgb_base.bp_name )
select
    MEMBER,
    case when sum(b.POOL_DATA_L_READS + b.POOL_TEMP_DATA_L_READS) < 1000
        then null
        else 100 * sum(b.POOL_DATA_L_READS + b.POOL_TEMP_DATA_L_READS
            - (b.POOL_DATA_P_READS + b.POOL_TEMP_DATA_P_READS - b.POOL_ASYNC_DATA_READS))
            / decimal(sum(b.POOL_DATA_L_READS + b.POOL_TEMP_DATA_L_READS))
    end as DATA_BP_HR,
    case when sum(b.POOL_INDEX_L_READS + b.POOL_TEMP_INDEX_L_READS) < 1000
        then null
        else 100 * sum(b.POOL_INDEX_L_READS + b.POOL_TEMP_INDEX_L_READS 
            - (b.POOL_INDEX_P_READS + b.POOL_TEMP_INDEX_P_READS - b.POOL_ASYNC_INDEX_READS))
            / decimal(sum(b.POOL_INDEX_L_READS + b.POOL_TEMP_INDEX_L_READS))
    end as INDEX_BP_HR from mgb_delta as b
group by MEMBER;