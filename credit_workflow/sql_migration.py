"""
A manual SQL migration script to fix the limit_type field conversion issue.
This script should be run directly with Python after stopping your Django app.

Usage:
    uv run python sql_migration.py
"""

import psycopg
import json
from decimal import Decimal

# Custom JSON encoder for decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

def main():
    # Connect to your database - adjust these settings to match your Django settings
    # You can find these in your settings.py file
    conn = psycopg.connect(
        dbname="your_db_name",  # Replace with your actual database name
        user="your_db_user",    # Replace with your actual database user
        password="your_db_password",  # Replace with your actual database password
        host="localhost"
    )
    
    # Turn on autocommit for DDL operations
    conn.autocommit = True
    
    try:
        # Create a cursor
        with conn.cursor() as cur:
            # 1. First, create the limit_type table if it doesn't exist
            cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_workflow_limittype (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) NOT NULL,
                description TEXT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
            """)
            
            print("Created LimitType table")
            
            # 2. Insert standard limit types
            limit_types = [
                ("TRADING_PRE_SETTLEMENT", "Trading (Pre-Settlement)"),
                ("TRADING_SETTLEMENT", "Trading (Settlement)"),
                ("NOSTRO_PRIMARY", "Nostro (Primary)"),
                ("METAL_LEASE", "Metal Lease"),
                ("TRS", "Total Return Swap (TRS)"),
                ("IM", "Initial Margin (IM)"),
                ("VM", "Variation Margin (VM)"),
                ("SBLC", "Standby Letter of Credit (SBLC)"),
                ("RWA", "Risk-Weighted Assets (RWA)"),
                ("NPL", "Non-Performing Loans (NPL)"),
                ("MLRO", "MLRO Financial Crime Risk"),
                ("IOSCO", "IOSCO"),
                ("VAR", "Value at Risk (VAR)"),
                ("RWR", "Right-Way Risk (RWR)"),
                ("HWWR", "High-Wrong-Way Risk (HWWR)"),
                ("ACCELERATION", "Acceleration"),
            ]
            
            for code, name in limit_types:
                try:
                    # Check if the limit type already exists
                    cur.execute("SELECT id FROM credit_workflow_limittype WHERE code = %s", (code,))
                    if cur.fetchone() is None:
                        # Insert the limit type with current timestamp
                        cur.execute("""
                        INSERT INTO credit_workflow_limittype 
                            (name, code, description, created_at, updated_at) 
                        VALUES 
                            (%s, %s, NULL, NOW(), NOW())
                        """, (name, code))
                        print(f"Added LimitType: {name}")
                except Exception as e:
                    print(f"Error adding limit type {code}: {e}")
            
            # 3. Find any additional limit types from existing data
            cur.execute("SELECT DISTINCT limit_type FROM credit_workflow_creditlimit")
            existing_types = [row[0] for row in cur.fetchall() if row[0]]
            
            for code in existing_types:
                try:
                    # Check if the limit type already exists
                    cur.execute("SELECT id FROM credit_workflow_limittype WHERE code = %s", (code,))
                    if cur.fetchone() is None:
                        # Truncate if too long
                        safe_code = code[:50] if len(code) > 50 else code
                        
                        # Insert the limit type with current timestamp
                        cur.execute("""
                        INSERT INTO credit_workflow_limittype 
                            (name, code, description, created_at, updated_at) 
                        VALUES 
                            (%s, %s, NULL, NOW(), NOW())
                        """, (safe_code, safe_code))
                        print(f"Added custom LimitType: {safe_code}")
                except Exception as e:
                    print(f"Error adding custom limit type {code}: {e}")
            
            # 4. Add a new column for the foreign key
            try:
                cur.execute("""
                ALTER TABLE credit_workflow_creditlimit 
                ADD COLUMN limit_type_fk BIGINT NULL
                """)
                print("Added limit_type_fk column")
            except Exception as e:
                print(f"Error adding limit_type_fk column (might already exist): {e}")
            
            # 5. Update the new column with the correct foreign key values
            cur.execute("SELECT id, code FROM credit_workflow_limittype")
            limit_type_map = {row[1]: row[0] for row in cur.fetchall()}
            
            cur.execute("SELECT id, limit_type FROM credit_workflow_creditlimit")
            for row in cur.fetchall():
                credit_limit_id, limit_type_code = row
                if limit_type_code in limit_type_map:
                    try:
                        cur.execute("""
                        UPDATE credit_workflow_creditlimit 
                        SET limit_type_fk = %s
                        WHERE id = %s
                        """, (limit_type_map[limit_type_code], credit_limit_id))
                        print(f"Updated credit limit ID {credit_limit_id} with limit type {limit_type_code}")
                    except Exception as e:
                        print(f"Error updating credit limit {credit_limit_id}: {e}")
            
            # 6. Make the foreign key column NOT NULL and add constraint
            try:
                cur.execute("""
                ALTER TABLE credit_workflow_creditlimit 
                ALTER COLUMN limit_type_fk SET NOT NULL,
                ADD CONSTRAINT fk_credit_limit_limit_type 
                FOREIGN KEY (limit_type_fk) 
                REFERENCES credit_workflow_limittype (id) ON DELETE PROTECT
                """)
                print("Added NOT NULL constraint and foreign key")
            except Exception as e:
                print(f"Error setting NOT NULL constraint: {e}")
            
            # 7. Drop the old column
            try:
                cur.execute("""
                ALTER TABLE credit_workflow_creditlimit 
                DROP COLUMN limit_type
                """)
                print("Dropped old limit_type column")
            except Exception as e:
                print(f"Error dropping old column: {e}")
            
            # 8. Rename the new column to the original name
            try:
                cur.execute("""
                ALTER TABLE credit_workflow_creditlimit 
                RENAME COLUMN limit_type_fk TO limit_type
                """)
                print("Renamed limit_type_fk to limit_type")
            except Exception as e:
                print(f"Error renaming column: {e}")
            
            # 9. Update Django's migration record to mark our migration as applied
            try:
                cur.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('credit_workflow', '0010_fix_limit_type', NOW())
                """)
                print("Updated Django migrations table")
            except Exception as e:
                print(f"Error updating migrations table: {e}")
            
        print("\nSQL migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting manual SQL migration for limit_type field...")
    main()
