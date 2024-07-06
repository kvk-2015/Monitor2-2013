select pid, tid,
       substr(eventtype, 1, 10),
       substr(objtype, 1, 30) as objtype,
       substr(objname_qualifier, 1, 20) as objschema,
       substr(objname, 1, 10) as objname,
       substr(first_eventqualifier, 1, 26) as event1,
       substr(second_eventqualifiertype, 1, 2) as event2_type,
       substr(second_eventqualifier, 1, 20) as event2,
       substr(third_eventqualifiertype, 1, 6) as event3_type,
       substr(third_eventqualifier, 1, 15) as event3,
       substr(eventstate, 1, 20) as eventstate
     from table(sysproc.pd_get_diag_hist 
       ('optstats', 'EX', 'NONE', 
         current_timestamp - 1 year, cast(null as timestamp))) as sl
     order by timestamp(varchar(substr(first_eventqualifier, 1, 26), 26));