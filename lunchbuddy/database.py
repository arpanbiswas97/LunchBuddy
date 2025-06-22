"""Database operations for LunchBuddy bot."""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import User, DietaryPreference, WeekDay, LunchOverride
from .config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.connection_string = settings.database_url
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        dietary_preference VARCHAR(10) NOT NULL,
                        preferred_days TEXT[] NOT NULL,
                        is_enrolled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create lunch_overrides table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS lunch_overrides (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        override_date DATE NOT NULL,
                        override_choice BOOLEAN NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, override_date)
                    )
                """)
                
                conn.commit()
                logger.info("Database tables initialized successfully")
    
    def add_user(self, user: User) -> bool:
        """Add a new user to the database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (telegram_id, full_name, email, dietary_preference, preferred_days)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (telegram_id) 
                        DO UPDATE SET 
                            full_name = EXCLUDED.full_name,
                            email = EXCLUDED.email,
                            dietary_preference = EXCLUDED.dietary_preference,
                            preferred_days = EXCLUDED.preferred_days,
                            is_enrolled = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        user.telegram_id,
                        user.full_name,
                        user.email,
                        user.dietary_preference.value,
                        [day.value for day in user.preferred_days]
                    ))
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def remove_user(self, telegram_id: int) -> bool:
        """Remove a user from enrollment."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET is_enrolled = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = %s
                    """, (telegram_id,))
                    
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM users WHERE telegram_id = %s AND is_enrolled = TRUE
                    """, (telegram_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return User(
                            telegram_id=row['telegram_id'],
                            full_name=row['full_name'],
                            email=row['email'],
                            dietary_preference=DietaryPreference(row['dietary_preference']),
                            preferred_days=[WeekDay(day) for day in row['preferred_days']],
                            is_enrolled=row['is_enrolled'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        )
                    return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_enrolled_users(self) -> List[User]:
        """Get all enrolled users."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM users WHERE is_enrolled = TRUE
                    """)
                    
                    users = []
                    for row in cursor.fetchall():
                        users.append(User(
                            telegram_id=row['telegram_id'],
                            full_name=row['full_name'],
                            email=row['email'],
                            dietary_preference=DietaryPreference(row['dietary_preference']),
                            preferred_days=[WeekDay(day) for day in row['preferred_days']],
                            is_enrolled=row['is_enrolled'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        ))
                    return users
        except Exception as e:
            logger.error(f"Error getting enrolled users: {e}")
            return []
    
    def add_lunch_override(self, telegram_id: int, override_date: date, override_choice: bool) -> bool:
        """Add a lunch override for a specific date."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First get the user ID
                    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
                    user_row = cursor.fetchone()
                    if not user_row:
                        return False
                    
                    user_id = user_row[0]
                    
                    cursor.execute("""
                        INSERT INTO lunch_overrides (user_id, override_date, override_choice)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, override_date) 
                        DO UPDATE SET override_choice = EXCLUDED.override_choice
                    """, (user_id, override_date, override_choice))
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error adding lunch override: {e}")
            return False
    
    def get_lunch_override(self, telegram_id: int, override_date: date) -> Optional[bool]:
        """Get lunch override for a specific date."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT lo.override_choice 
                        FROM lunch_overrides lo
                        JOIN users u ON lo.user_id = u.id
                        WHERE u.telegram_id = %s AND lo.override_date = %s
                    """, (telegram_id, override_date))
                    
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting lunch override: {e}")
            return None


# Global database manager instance
db_manager = DatabaseManager() 