import psycopg2
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with timeout settings"""
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            connect_timeout=30,  # 30 second connection timeout
            application_name='urban_mobility_app'
        )
        # Set statement timeout to prevent long-running queries
        conn.cursor().execute("SET statement_timeout = '60s'")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize normalized database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Disable statement timeout during schema creation (can be heavy on first run)
        cursor.execute("SET statement_timeout = 0")
        
        # Create vendors table (normalized)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER UNIQUE NOT NULL,
                vendor_name VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create zones table (normalized)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id SERIAL PRIMARY KEY,
                zone_name VARCHAR(50) UNIQUE NOT NULL,
                latitude DECIMAL(10, 7),
                longitude DECIMAL(10, 7),
                trip_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create trips table (normalized with foreign keys)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id VARCHAR(50) PRIMARY KEY,
                vendor_id INTEGER REFERENCES vendors(vendor_id),
                pickup_datetime TIMESTAMP,
                dropoff_datetime TIMESTAMP,
                passenger_count INTEGER,
                pickup_longitude DECIMAL(10, 7),
                pickup_latitude DECIMAL(10, 7),
                dropoff_longitude DECIMAL(10, 7),
                dropoff_latitude DECIMAL(10, 7),
                store_and_fwd_flag CHAR(1),
                trip_duration INTEGER,
                trip_distance_km DECIMAL(8, 3),
                trip_speed_kmh DECIMAL(6, 2),
                fare_amount DECIMAL(8, 2),
                fare_per_km DECIMAL(6, 2),
                pickup_zone_id INTEGER REFERENCES zones(id),
                dropoff_zone_id INTEGER REFERENCES zones(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_pickup_datetime ON trips(pickup_datetime);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_pickup_location ON trips(pickup_latitude, pickup_longitude);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_duration ON trips(trip_duration);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_fare_amount ON trips(fare_amount);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_vendor_id ON trips(vendor_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_pickup_zone ON trips(pickup_zone_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trips_dropoff_zone ON trips(dropoff_zone_id);
        """)
        
        conn.commit()
        logger.info("Normalized database tables initialized successfully")
        
        # Restore a safer default timeout (60s)
        cursor.execute("SET statement_timeout = '60s'")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def check_data_exists():
    """Check if data has been processed and loaded"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM trips")
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"Error checking data existence: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
