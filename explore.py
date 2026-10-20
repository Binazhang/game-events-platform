import duckdb

raw = "read_json_auto('data/raw/*.jsonl', union_by_name = TRUE, filename=true)"
print(raw)

print("== How many records for each event_type: ==")
duckdb.sql(f"select event_type, count(*) as n from {raw} group by 1 order by 2 desc").show()
# late events:
duckdb.sql(f"""
    select count(*) as late_events from {raw}
    where cast(event_ts as date)::varchar != regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1)
""")