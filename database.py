import sqlite3
from datetime import date, datetime, timedelta
from config import DB_NAME

def db_exec(q, p=(), fetch=False, commit=False):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(q, p)
    if commit: conn.commit()
    r = cur.fetchall() if fetch else None
    conn.close()
    return r

def init_db():
    db_exec("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, total_answers INTEGER DEFAULT 0, correct_answers INTEGER DEFAULT 0, current_streak INTEGER DEFAULT 0, best_streak INTEGER DEFAULT 0, mode TEXT DEFAULT 'all', status TEXT DEFAULT 'free', vip_until TEXT, referrer_id INTEGER DEFAULT 0, referrals_count INTEGER DEFAULT 0, referral_activated INTEGER DEFAULT 0)", commit=True)
    db_exec("CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, message TEXT, reply TEXT DEFAULT '', status TEXT DEFAULT 'open', created_at TEXT)", commit=True)
    db_exec("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, level TEXT DEFAULT 'moderator')", commit=True)

def get_user(uid):
    r = db_exec("SELECT * FROM users WHERE user_id=?", (uid,), fetch=True)
    if not r:
        db_exec("INSERT INTO users (user_id) VALUES (?)", (uid,), commit=True)
        return {'total_answers': 0, 'correct_answers': 0, 'current_streak': 0, 'best_streak': 0, 'mode': 'all', 'status': 'free', 'vip_until': None, 'referrer_id': 0, 'referrals_count': 0, 'referral_activated': 0}
    cols = ['user_id', 'username', 'total_answers', 'correct_answers', 'current_streak', 'best_streak', 'mode', 'status', 'vip_until', 'referrer_id', 'referrals_count', 'referral_activated']
    return dict(zip(cols, r[0]))

def update_stats(uid, correct):
    if correct:
        db_exec("UPDATE users SET total_answers = total_answers + 1, correct_answers = correct_answers + 1, current_streak = current_streak + 1, best_streak = MAX(best_streak, current_streak + 1) WHERE user_id=?", (uid,), commit=True)
    else:
        db_exec("UPDATE users SET total_answers = total_answers + 1, current_streak = 0 WHERE user_id=?", (uid,), commit=True)

def set_mode(uid, mode):
    db_exec("UPDATE users SET mode=? WHERE user_id=?", (mode, uid), commit=True)

def set_vip(uid, days=30):
    until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    db_exec("UPDATE users SET status='vip', vip_until=? WHERE user_id=?", (until, uid), commit=True)

def check_vip(uid):
    u = get_user(uid)
    if u['status'] == 'vip' and u['vip_until'] and str(date.today()) <= u['vip_until']:
        return True
    if u['status'] == 'vip':
        db_exec("UPDATE users SET status='free' WHERE user_id=?", (uid,), commit=True)
    return False

def add_support(uid, username, message):
    db_exec("INSERT INTO support (user_id, username, message, status, created_at) VALUES (?,?,?,'open',datetime('now'))", (uid, username, message), commit=True)
    r = db_exec("SELECT last_insert_rowid()", fetch=True)
    return r[0][0] if r else 0

def get_open_tickets():
    return db_exec("SELECT id, user_id, username, message, created_at FROM support WHERE status='open' ORDER BY id DESC LIMIT 10", fetch=True)

def reply_ticket(tid, reply):
    db_exec("UPDATE support SET reply=?, status='closed' WHERE id=?", (reply, tid), commit=True)

def is_admin(uid):
    from config import OWNER_ID
    if uid == OWNER_ID: return 'owner'
    r = db_exec("SELECT level FROM admins WHERE user_id=?", (uid,), fetch=True)
    return r[0][0] if r else None

def add_admin(uid, level='moderator'):
    db_exec("INSERT OR REPLACE INTO admins (user_id, level) VALUES (?,?)", (uid, level), commit=True)

def remove_admin(uid):
    db_exec("DELETE FROM admins WHERE user_id=?", (uid,), commit=True)

def get_stats():
    total = db_exec("SELECT COUNT(*) FROM users", fetch=True)[0][0]
    vip = db_exec("SELECT COUNT(*) FROM users WHERE status='vip'", fetch=True)[0][0]
    tickets = db_exec("SELECT COUNT(*) FROM support WHERE status='open'", fetch=True)[0][0]
    return {'total_users': total, 'vip_users': vip, 'open_tickets': tickets}

def activate_referral(uid, rid):
    u = get_user(uid)
    if not u.get('referrer_id') and not u.get('referral_activated'):
        db_exec("UPDATE users SET referrer_id=?, referral_activated=1 WHERE user_id=?", (rid, uid), commit=True)
        db_exec("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id=?", (rid,), commit=True)
        set_vip(uid, days=2)
        return True
    return False
