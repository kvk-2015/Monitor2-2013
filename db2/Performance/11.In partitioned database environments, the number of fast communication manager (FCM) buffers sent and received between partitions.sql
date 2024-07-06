with mgw_delta (
    MEMBER,
    FCM_SENDS_TOTAL,
    FCM_RECVS_TOTAL)
as (
select
    mgw.MEMBER,
    sum(mgw.FCM_SENDS_TOTAL
        - mgw_baseline.FCM_SENDS_TOTAL),
    sum(mgw.FCM_RECVS_TOTAL
        - mgw_baseline.FCM_RECVS_TOTAL)
from
    table(MON_GET_WORKLOAD(null,-2)) as mgw,
    session.mgw_baseline as mgw_baseline
where
    mgw.MEMBER = mgw_baseline.MEMBER and
    mgw.WORKLOAD_ID = mgw_baseline.WORKLOAD_ID
group by mgw.MEMBER )
select
    MEMBER,
    FCM_SENDS_TOTAL,
    FCM_RECVS_TOTAL
from mgw_delta as w;