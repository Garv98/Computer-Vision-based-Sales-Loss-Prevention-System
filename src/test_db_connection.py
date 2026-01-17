import psycopg2

# Update these if your credentials are different
conn = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="Garv@gr897",
    dbname="salesloss"
)

cur = conn.cursor()

try:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cur.fetchall()
    print("Tables in 'salesloss':")
    for t in tables:
        print("-", t[0])
    
    cur.execute("SELECT COUNT(*) FROM camera;")
    count = cur.fetchone()[0]
    print(f"\nNumber of cameras in 'camera' table: {count}")
except Exception as e:
    print("Error:", e)
finally:
    cur.close()
    conn.close()
