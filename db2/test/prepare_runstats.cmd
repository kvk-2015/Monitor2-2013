db2 -x "select 'runstats on table',substr(rtrim(tabschema)||'.'||rtrim(tabname),1,50),' and indexes all;'from syscat.tables where type = 'T' " > runstats.out