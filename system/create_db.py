import mysql.connector

# Connect to the MySQL database
conn = mysql.connector.connect(
    host= "107.180.1.16",
    port= 3306,
    user= "cis440springA2025team3",
    password= "cis440springA2025team3",
    database= "cis440springA2025team3"
)

cur = conn.cursor()


# Create Employee table
cur.execute('''
    CREATE TABLE IF NOT EXISTS Feedback (
        EmpID INTEGER PRIMARY KEY AUTOINCREMENT,
        FirstName VARCHAR(50) NOT NULL,
        LastName VARCHAR(50) NOT NULL,
        Username VARCHAR(20) NOT NULL,
        Password VARCHAR(20) NOT NULL,
        Points INTEGER
    )
''')




# Commit changes and close the connection
conn.commit()
conn.close()
