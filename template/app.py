from flask import Flask, render_template, jsonify
import os

import mysql.connector

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_default_secret_key')


db_config = {
    "host": "107.180.1.16",
    "port": 3306,
    "user": "cis440springA2025team3",
    "password": "cis440springA2025team3",
    "database": "cis440springA2025team3"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')


@app.route("/test_connection", methods=["GET"])
def test_connection():
    try:
        con = get_db_connection()
        cursor = con.cursor()
        cursor.execute("SELECT * FROM test")
        cursor.fetchall()
        cursor.close()
        con.close()
        return jsonify({"message": "Success!"})
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"})



if __name__ == '__main__':
    app.run(debug=True)