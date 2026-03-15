import sqlite3
import bcrypt
from datetime import datetime

password = '123456'
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
now = datetime.now().isoformat()

conn = sqlite3.connect(r'D:\cauc-sep\data\experiments.db')
conn.execute('INSERT INTO users (username, email, password_hash, role, preferences, created_at, updated_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
             ('123456', 'user@cauc-sep.local', password_hash, 'user', '{"theme":"light","language":"zh-CN"}', now, now, 1))
conn.commit()
print('User 123456 created successfully')
conn.close()
