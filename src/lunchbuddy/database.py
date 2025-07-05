import logging
from contextlib import contextmanager
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import settings
from .models import Admin, DietaryPreference, User

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
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        dietary_preference VARCHAR(10) NOT NULL,
                        preferred_days TEXT[] NOT NULL,
                        is_enrolled BOOLEAN DEFAULT TRUE,
                        is_verified BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create admin table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admins (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                    )
                """
                )

                conn.commit()
                logger.info("Database tables initialized successfully")

    def add_user(self, user: User) -> bool:
        """Add a new user to the database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (telegram_id, full_name, email, dietary_preference, preferred_days)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (telegram_id)
                        DO UPDATE SET
                            full_name = EXCLUDED.full_name,
                            email = EXCLUDED.email,
                            dietary_preference = EXCLUDED.dietary_preference,
                            preferred_days = EXCLUDED.preferred_days,
                            is_enrolled = TRUE,
                            is_verified = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """,
                        (
                            user.telegram_id,
                            user.full_name,
                            user.email,
                            user.dietary_preference.value,
                            user.preferred_days,
                        ),
                    )

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
                    cursor.execute(
                        """
                        UPDATE users
                        SET is_enrolled = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = %s
                    """,
                        (telegram_id,),
                    )

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
                    cursor.execute(
                        """
                        SELECT * FROM users WHERE telegram_id = %s AND is_enrolled = TRUE AND is_verified = TRUE
                    """,
                        (telegram_id,),
                    )

                    row = cursor.fetchone()
                    if row:
                        return User(
                            telegram_id=row["telegram_id"],
                            full_name=row["full_name"],
                            email=row["email"],
                            dietary_preference=DietaryPreference(
                                row["dietary_preference"]
                            ),
                            preferred_days=row["preferred_days"],
                            is_enrolled=row["is_enrolled"],
                            is_verified=row["is_verified"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
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
                    cursor.execute(
                        """
                        SELECT * FROM users WHERE is_enrolled = TRUE AND is_verified = TRUE
                    """
                    )

                    users = []
                    for row in cursor.fetchall():
                        users.append(
                            User(
                                telegram_id=row["telegram_id"],
                                full_name=row["full_name"],
                                email=row["email"],
                                dietary_preference=DietaryPreference(
                                    row["dietary_preference"]
                                ),
                                preferred_days=row["preferred_days"],
                                is_enrolled=row["is_enrolled"],
                                is_verified=row["is_verified"],
                                created_at=row["created_at"],
                                updated_at=row["updated_at"],
                            )
                        )
                    return users
        except Exception as e:
            logger.error(f"Error getting enrolled users: {e}")
            return []

    def get_admins(self) -> List[Admin]:
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM admins
                    """
                    )

                    users = []
                    for row in cursor.fetchall():
                        users.append(
                            User(
                                telegram_id=row["telegram_id"],
                                full_name=row["full_name"],
                                email=row["email"],
                            )
                        )
                    return users
        except Exception as e:
            logger.error(f"Error getting enrolled users: {e}")
            return []

    def approve_user(self, telegram_id: int) -> bool:
        """Mark a user's enrollment as verified."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET is_verified = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = %s AND is_enrolled = TRUE
                    """,
                        (telegram_id,),
                    )

                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error approving user: {e}")
            return False

    def reject_user(self, telegram_id: int) -> bool:
        """Reject a user's enrollment by marking them as not enrolled and not verified."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET is_enrolled = FALSE, is_verified = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = %s
                    """,
                        (telegram_id,),
                    )

                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error rejecting user: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()
