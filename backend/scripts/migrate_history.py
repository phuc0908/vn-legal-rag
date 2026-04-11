"""Migration: add view_history table"""
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "3307")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456789"),
    "database": os.getenv("DB_NAME", "law"),
    "charset":  "utf8mb4",
}

def run():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS view_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                mapc VARCHAR(200) NOT NULL,
                chimuc VARCHAR(50),
                ten VARCHAR(1000),
                vbqppl VARCHAR(500),
                chude_id VARCHAR(50),
                chude_ten VARCHAR(500),
                demuc_id VARCHAR(50),
                demuc_ten VARCHAR(500),
                chuong_id VARCHAR(200),
                chuong_ten VARCHAR(500),
                chuong_chimuc VARCHAR(50),
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_dieu (user_id, mapc),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            conn.commit()
            print("OK: view_history table created.")
    finally:
        conn.close()

if __name__ == "__main__":
    run()
