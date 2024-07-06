--db2 update db cfg using logfilsiz 16384
db2 SET INTEGRITY FOR IPPON.VOLTAGE OFF
db2 ALTER TABLE IPPON.VOLTAGE ADD COLUMN AVR SMALLINT NOT NULL GENERATED ALWAYS AS ( NVL2(NULLIF(INPUT_VOLTAGE, 0), MAX(0, SIGN(ABS(OUTPUT_VOLTAGE - INPUT_VOLTAGE) - 9)), 0) )
db2 SET INTEGRITY FOR IPPON.VOLTAGE IMMEDIATE CHECKED FORCE GENERATED
REORG TABLE IPPON.VOLTAGE
RUNSTATS ON TABLE IPPON.VOLTAGE