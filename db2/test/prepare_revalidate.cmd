db2 -x "select 'CALL SYSPROC.ADMIN_REVALIDATE_DB_OBJECTS(''function'',',''''||rtrim(objectschema)||''', '''||rtrim(objectname)||''');'from syscat.invalidobjects where objecttype = 'F'" > revalidate.out
db2 -x "select 'CALL SYSPROC.ADMIN_REVALIDATE_DB_OBJECTS(''view'',',''''||rtrim(objectschema)||''', '''||rtrim(objectname)||''');'from syscat.invalidobjects where objecttype = 'V'" >> revalidate.out