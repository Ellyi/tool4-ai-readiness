import psycopg2

# Railway DATABASE_URL (public connection)
DATABASE_URL = "postgresql://postgres:dlkbpbLyksIHtZfLEicctAxjUncNTotr@metro.proxy.rlwy.net:14980/railway"

print("Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("Reading schema.sql...")
with open('schema.sql', 'r') as f:
    schema = f.read()

print("Creating tables...")
cursor.execute(schema)

conn.commit()
cursor.close()
conn.close()

print("✅ Tables created successfully!")
print("✅ readiness_assessments")
print("✅ readiness_patterns")
print("✅ readiness_insights")