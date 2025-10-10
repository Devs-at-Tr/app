# Database Switching Guide

This project supports multiple database backends: **MySQL**, **PostgreSQL**, and **SQLite**. You can easily switch between them using the `.env` configuration file.

## Current Configuration

**Active Database:** MySQL  
**Database Name:** pf_messenger  
**Host:** localhost:3306

---

## Quick Switch Guide

### Switch to MySQL (Production - Current)

Edit `.env` file:
```env
DB_TYPE=mysql

MYSQL_HOST=localhost
MYSQL_USER=developer
MYSQL_PASSWORD=Tickle@1800
MYSQL_DATABASE=pf_messenger
MYSQL_PORT=3306
```

### Switch to PostgreSQL (Backup)

Edit `.env` file:
```env
DB_TYPE=postgres

POSTGRES_URL=postgresql://ticklegram_user:ticklegram_pass@localhost:5433/ticklegram
```

### Switch to SQLite (Development)

Edit `.env` file:
```env
DB_TYPE=sqlite
```

---

## Database Management

### Current Databases:

| Database | Status | Purpose | Location |
|----------|--------|---------|----------|
| **MySQL** | ✅ Active | Production | `localhost:3306/pf_messenger` |
| **PostgreSQL** | 🔄 Backup | Previous production | `localhost:5433/ticklegram` |
| **SQLite** | 💤 Available | Development fallback | `backend/ticklegram.db` |

### MySQL Database Details:
- **User:** developer
- **Password:** Tickle@1800
- **Database:** pf_messenger
- **Tables Created:** ✅
  - users
  - instagram_accounts
  - chats (with platform support)
  - messages (with platform support)
  - facebook_pages
- **Seeded Data:** ✅
  - 1 Admin user (admin@ticklegram.com / admin123)
  - 2 Agent users
  - 5 Sample Instagram chats

---

## Migration Scripts

### Create MySQL Database
```bash
python create_mysql_db.py
```

### Run MySQL Migration
```bash
python migrate_to_mysql.py
```

### Seed Initial Data
```bash
python seed_data.py
```

---

## After Switching Databases

1. **Restart Backend Server:**
   ```bash
   # Stop current server (Ctrl+C)
   uvicorn server:app --reload --port 8000
   ```

2. **Verify Connection:**
   - Check terminal output for "✓ Connected to [DATABASE] database"

3. **Refresh Frontend:**
   - Reload browser to fetch data from new database

---

## Important Notes

⚠️ **Data Isolation:** Each database is completely separate. Switching databases means accessing different data.

✅ **PostgreSQL Backup:** Your PostgreSQL database with 24 chats (20 Instagram + 4 Facebook) is preserved and can be switched back anytime.

✅ **MySQL Production:** Fresh MySQL database with seed data is ready for production use.

✅ **No Code Changes:** The application code automatically adapts to the selected database type.

---

## Model Compatibility

All models are compatible with MySQL, PostgreSQL, and SQLite:

- ✅ VARCHAR lengths specified for MySQL
- ✅ ENUM types work across all databases
- ✅ UUID primary keys (String(36))
- ✅ Timezone-aware DateTime fields
- ✅ Text fields for long content
- ✅ Foreign key relationships
- ✅ Indexes on frequently queried fields

---

## Troubleshooting

### MySQL Connection Failed
- Ensure XAMPP MySQL is running
- Check credentials in `.env`
- Verify database exists: `python create_mysql_db.py`

### PostgreSQL Connection Failed
- Check if PostgreSQL server is running on port 5433
- Verify POSTGRES_URL in `.env`

### Fallback to SQLite
- If configured database fails, system automatically uses SQLite
- Check terminal output for warnings

---

## Environment Variables Reference

```env
# Database Selection
DB_TYPE=mysql              # Options: mysql, postgres, sqlite

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_USER=developer
MYSQL_PASSWORD=Tickle@1800
MYSQL_DATABASE=pf_messenger
MYSQL_PORT=3306

# PostgreSQL Configuration (Backup)
POSTGRES_URL=postgresql://ticklegram_user:ticklegram_pass@localhost:5433/ticklegram
```

---

## Contact

For any database-related issues or questions, check the application logs or refer to the main README.md.
