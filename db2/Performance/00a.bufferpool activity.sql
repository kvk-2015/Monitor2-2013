-- Set up a common table expression (‘with clause’) 
-- to calculate deltas for each table function we reference 
with mgb_delta
    (
    MEMBER,
    BP_NAME,
    bp_cur_buffsz,
    POOL_DATA_L_READS,
    POOL_DATA_P_READS )
as (
    select
        mgb.MEMBER,
        substr(mgb.BP_NAME,1,20) as BP_NAME,
        mgb.bp_cur_buffsz,
        mgb.POOL_DATA_L_READS - mgb_baseline.POOL_DATA_L_READS,
        mgb.POOL_DATA_P_READS - mgb_baseline.POOL_DATA_P_READS
    from
        table(MON_GET_BUFFERPOOL(null,-2)) as mgb,
        session.mgb_baseline as mgb_baseline
    where
        mgb.MEMBER = mgb_baseline.MEMBER and
        mgb.BP_NAME = mgb_baseline.BP_NAME )
-- Then pick out the values we need from our 
-- ‘mgb_delta’ common table expression
select 
    MEMBER,
    BP_NAME,
    bp_cur_buffsz,
    POOL_DATA_L_READS,
    POOL_DATA_P_READS
from
    mgb_delta;