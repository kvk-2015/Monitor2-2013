db2 -x "select 'drop table',substr(rtrim(tabschema)||'.'||rtrim(tabname),1,50),';'from syscat.tables where type = 'T' and tabname like 'EXPLAIN_%%'" > delete.out
db2 -x "select 'drop table',substr(rtrim(tabschema)||'.'||rtrim(tabname),1,50),';'from syscat.tables where type = 'T' and tabname like 'ADVISE_%%'" >> delete.out
db2 -x "select 'drop table',substr(rtrim(tabschema)||'.'||rtrim(tabname),1,50),';'from syscat.tables where type = 'T' and tabname like 'OBJECT_METRICS'" >> delete.out
echo drop function explain_get_msgs; >> delete.out