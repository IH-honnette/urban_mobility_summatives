#!/usr/bin/env python3
"""
Database setup script for Urban Mobility Data Explorer
This script processes raw data, cleans it, and inserts it into normalized PostgreSQL tables,
then starts the Flask application.
"""

import os
import sys
import subprocess
import pandas as pd
from dotenv import load_dotenv
from database import init_db, get_db_connection
from data_processor import DataProcessor

CLEANED_CSV = 'cleaned_dataset.csv'

def drop_and_recreate_tables():
    """Drop existing tables and recreate with new normalized schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        print("🗑️ Dropping existing tables...")
        # Drop tables in reverse order to handle foreign key constraints
        cursor.execute("DROP TABLE IF EXISTS trips CASCADE")
        cursor.execute("DROP TABLE IF EXISTS zones CASCADE")
        cursor.execute("DROP TABLE IF EXISTS vendors CASCADE")
        conn.commit()
        print("✅ Existing tables dropped successfully")
        
        # Recreate tables with new schema
        print("📊 Creating new normalized tables...")
        init_db()
        print("✅ New tables created successfully")
        
    except Exception as e:
        print(f"❌ Error recreating tables: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def clear_existing_data():
    """Clear existing data from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM trips")
        cursor.execute("DELETE FROM zones")
        cursor.execute("DELETE FROM vendors")
        conn.commit()
        print("✅ Existing data cleared successfully")
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def insert_cleaned_csv(path: str, batch_size: int = 100) -> int:
    """Insert records from cleaned CSV into the normalized database in batches.
    Note: Processing is limited to 1000 records for performance."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cleaned CSV not found at: {path}. Run clean_data.py first.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    total_inserted = 0
    
    try:
        # Read only first 1000 records for performance
        df = pd.read_csv(path, nrows=1000)
        print(f"📊 Processing {len(df)} records (limited to 1000 for performance)")
        
        # Insert vendors first
        unique_vendors = df['vendor_id'].dropna().unique()
        for vendor_id in unique_vendors:
            vendor_name = f"Vendor_{int(vendor_id)}"
            cursor.execute("""
                INSERT INTO vendors (vendor_id, vendor_name)
                VALUES (%s, %s)
                ON CONFLICT (vendor_id) DO NOTHING
            """, (int(vendor_id), vendor_name))
        conn.commit()
        print(f"✅ Inserted {len(unique_vendors)} vendors")
        
        # Insert zones
        all_zones = set()
        all_zones.update(df['pickup_zone'].dropna().unique())
        all_zones.update(df['dropoff_zone'].dropna().unique())
        
        for zone_name in all_zones:
            zone_trips = df[(df['pickup_zone'] == zone_name) | (df['dropoff_zone'] == zone_name)]
            avg_lat = float(zone_trips[['pickup_latitude', 'dropoff_latitude']].values.mean())
            avg_lon = float(zone_trips[['pickup_longitude', 'dropoff_longitude']].values.mean())
            trip_count = int(len(zone_trips))
            
            cursor.execute("""
                INSERT INTO zones (zone_name, latitude, longitude, trip_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_name) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    trip_count = EXCLUDED.trip_count
            """, (str(zone_name), avg_lat, avg_lon, trip_count))
        conn.commit()
        print(f"✅ Inserted {len(all_zones)} zones")
        
        # Insert trips with foreign key references
        for _, row in df.iterrows():
            # Get zone IDs
            pickup_zone_id = None
            dropoff_zone_id = None
            
            if pd.notna(row['pickup_zone']):
                cursor.execute("SELECT id FROM zones WHERE zone_name = %s", (row['pickup_zone'],))
                result = cursor.fetchone()
                if result:
                    pickup_zone_id = result[0]
            
            if pd.notna(row['dropoff_zone']):
                cursor.execute("SELECT id FROM zones WHERE zone_name = %s", (row['dropoff_zone'],))
                result = cursor.fetchone()
                if result:
                    dropoff_zone_id = result[0]
            
            # Convert numpy types to native Python types
            def convert_value(val):
                if pd.isna(val):
                    return None
                if hasattr(val, 'item'):  # numpy scalar
                    return val.item()
                return val
            
            # Insert trip
            cursor.execute("""
                INSERT INTO trips (
                    id, vendor_id, pickup_datetime, dropoff_datetime,
                    passenger_count, pickup_longitude, pickup_latitude,
                    dropoff_longitude, dropoff_latitude, store_and_fwd_flag,
                    trip_duration, trip_distance_km, trip_speed_kmh,
                    fare_amount, fare_per_km, pickup_zone_id, dropoff_zone_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                str(row['id']), convert_value(row['vendor_id']), 
                convert_value(row['pickup_datetime']), convert_value(row['dropoff_datetime']),
                convert_value(row['passenger_count']), convert_value(row['pickup_longitude']), 
                convert_value(row['pickup_latitude']), convert_value(row['dropoff_longitude']), 
                convert_value(row['dropoff_latitude']), convert_value(row['store_and_fwd_flag']),
                convert_value(row['trip_duration']), convert_value(row['trip_distance_km']), 
                convert_value(row['trip_speed_kmh']), convert_value(row['fare_amount']), 
                convert_value(row['fare_per_km']), pickup_zone_id, dropoff_zone_id
            ))
            
            total_inserted += 1
            if total_inserted % 100 == 0:
                print(f"✅ Inserted {total_inserted} trips...")
        
        conn.commit()
        print(f"✅ Finished inserting {total_inserted} trips")
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    
    return total_inserted

def clean_and_process_data():
    """Clean and process raw data using DataProcessor"""
    print("🧹 Cleaning and processing raw data...")
    processor = DataProcessor()
    
    # Clean data and save to CSV (limited to 1000 records)
    total_cleaned = processor.clean_all_data_and_save(max_records=1000)
    print(f"✅ Data cleaning completed! {total_cleaned} records processed and saved to {CLEANED_CSV}")
    
    return total_cleaned

def main():
    print("🚀 Urban Mobility Data Explorer - Complete Setup & Run App")
    print("=" * 60)
    
    load_dotenv()
    if not os.getenv('DATABASE_URL'):
        print("❌ Error: DATABASE_URL not found in .env file")
        print("Please create backend/.env with your PostgreSQL connection string.")
        sys.exit(1)
    
    # Step 1: Handle database schema
    print("\n📊 Database Schema Management")
    print("-" * 30)
    
    schema_choice = input("Choose database setup option:\n1. Drop and recreate tables (recommended for new schema)\n2. Keep existing tables and clear data\n3. Keep existing data\n\nEnter choice (1-3): ").strip()
    
    if schema_choice == '1':
        drop_and_recreate_tables()
    elif schema_choice == '2':
        # Ensure tables exist with new schema
        print("📊 Initializing database tables...")
        init_db()
        print("✅ Database tables are ready")
        clear_existing_data()
    else:
        # Just ensure tables exist
        print("📊 Initializing database tables...")
        init_db()
        print("✅ Database tables are ready")
    
    # Step 2: Handle data processing
    print("\n📁 Data Processing")
    print("-" * 20)
    
    if os.path.exists(CLEANED_CSV):
        print(f"📁 Found existing cleaned CSV: {CLEANED_CSV}")
        use_existing = input("Use existing cleaned data? (y/N): ").strip().lower()
        if use_existing not in ['y', 'yes']:
            clean_and_process_data()
    else:
        print(f"📁 No cleaned CSV found. Processing raw data...")
        clean_and_process_data()
    
    # Step 3: Insert data into database
    print("\n📥 Database Import")
    print("-" * 20)
    print("📊 Note: Processing limited to 1000 records for performance")
    
    inserted = insert_cleaned_csv(CLEANED_CSV, batch_size=100)
    print(f"✅ Finished inserting {inserted} records into normalized database")
    
    # Step 4: Start Flask app
    print("\n🚀 Starting Flask app on http://localhost:5003 ...")
    print("📊 Dashboard will be available at: http://localhost:8000")
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down.")

if __name__ == "__main__":
    main()
