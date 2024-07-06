db2 select sec_log_used_top, tot_log_used_top, sec_logs_allocated from table(MON_GET_TRANSACTION_LOG(-2))
