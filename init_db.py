from app.db.database import init_db

def main():
    print("Creating database tables...")
    init_db()
    print("Database tables created successfully!")

if __name__ == "__main__":
    main()
