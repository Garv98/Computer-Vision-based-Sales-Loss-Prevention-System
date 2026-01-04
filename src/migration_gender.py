import psycopg2

def migrate():
    try:
        conn = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="diptanshu",
            dbname="salesloss"
        )
        cur = conn.cursor()
        
        # Check if column exists first to avoid error
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='tracking' AND column_name='gender';")
        if not cur.fetchone():
            print("Adding gender column...")
            cur.execute("ALTER TABLE tracking ADD COLUMN gender VARCHAR(50) DEFAULT 'Unknown';")
            conn.commit()
            print("Column 'gender' added successfully.")
        else:
            print("Column 'gender' already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
