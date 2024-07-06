drop table session.mgb_baseline;
declare global temporary table mgb_baseline as (select *
from table(mon_get_bufferpool(null,-2))) with no data on commit preserve rows;
insert into session.mgb_baseline select * from table(mon_get_bufferpool(null,-2));
--
drop table session.mgw_baseline;
declare global temporary table mgw_baseline as (select *
from table(mon_get_workload(null,-2))) with no data on commit preserve rows;
insert into session.mgw_baseline select * from table(mon_get_workload(null,-2));
-- prior to 10.5
drop table session.sdb_baseline;
declare global temporary table sdb_baseline as (select *
from sysibmadm.snapdb) with no data on commit preserve rows;
insert into session.sdb_baseline select * from sysibmadm.snapdb;
--
drop table session.mgtl_baseline;
declare global temporary table mgtl_baseline as (select *
from table(MON_GET_TRANSACTION_LOG(-2))) with no data on commit preserve rows;
insert into session.mgtl_baseline select * from table(MON_GET_TRANSACTION_LOG(-2));
--
drop table session.mgtbsp_baseline;
declare global temporary table mgtbsp_baseline as (select *
from table(MON_GET_TABLESPACE(null,-2))) with no data on commit preserve rows;
insert into session.mgtbsp_baseline select * from table(MON_GET_TABLESPACE(null,-2));
