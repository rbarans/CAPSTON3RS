# DO NOT RUN UNTIL WE ARE DONE IMPLEMENTING

import mysql.connector

def reset_database():
    try:
        # Establish database connection
        conn = mysql.connector.connect(
            host='107.180.1.16',
            port= 3306,
            user='cis440springA2025team3',
            password='cis440springA2025team3',
            database='cis440springA2025team3'
        )
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        # Disable foreign key checks to prevent constraint errors
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # Delete all data from each table
        for (table,) in tables:
            cursor.execute(f"DELETE FROM `{table}`")
            print(f"Deleted all data from {table}")

        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        # Insert new admin account
        cursor.execute("""
            INSERT INTO User (UserID, Username, Password, Points, IsAdmin, IsActive) 
            VALUES (1, 'admin', '123', 0, 1, 1)
        """)
        print("Admin account created/updated successfully.")

        # Insert status threshold
        cursor.execite("""
            INSERT INTO Status (StatusName, Threshold) 
            Values ('Unlikely', -10), ('Even',0), ('Possible', 1), ('Implemented', 3);
        """)

        # Commit changes and close connection
        conn.commit()
        cursor.close()
        conn.close()
        print("Database reset complete.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")

# Run the function
reset_database()