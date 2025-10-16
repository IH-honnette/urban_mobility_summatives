import pandas as pd
import numpy as np
from datetime import datetime
import logging
from database import get_db_connection, check_data_exists
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.csv_file = 'train.csv'
        self.cleaned_file = 'cleaned_dataset.csv'
        self.excluded_records = []
        
    def load_data(self, max_records=5000):
        """Load data from CSV file - limited to 5000 records for performance"""
        try:
            logger.info(f"Loading data from {self.csv_file} (limited to {max_records} records)")
            # Read only the first 5000 records for performance
            df = pd.read_csv(self.csv_file, nrows=max_records)
            logger.info(f"Loaded {len(df)} records")
            return df
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def load_cleaned_data(self, max_records=5000):
        """Load data from cleaned CSV file - limited to 5000 records for performance"""
        try:
            logger.info(f"Loading cleaned data from {self.cleaned_file} (limited to {max_records} records)")
            df = pd.read_csv(self.cleaned_file, nrows=max_records)
            logger.info(f"Loaded {len(df)} cleaned records")
            return df
        except Exception as e:
            logger.error(f"Error loading cleaned data: {e}")
            raise
    
    def clean_data(self, df):
        """Clean and process the data"""
        logger.info("Starting data cleaning process")
        original_count = len(df)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['id'])
        logger.info(f"Removed {original_count - len(df)} duplicate records")
        
        # Handle missing values
        df = df.dropna(subset=['pickup_datetime', 'dropoff_datetime', 'pickup_latitude', 
                              'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude'])
        
        # Convert datetime columns
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
        df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'])
        
        # Remove invalid datetime records
        invalid_datetime = df['dropoff_datetime'] <= df['pickup_datetime']
        self.excluded_records.extend(df[invalid_datetime]['id'].tolist())
        df = df[~invalid_datetime]
        
        # Remove records with invalid coordinates (outside NYC area)
        nyc_bounds = {
            'lat_min': 40.4774, 'lat_max': 40.9176,
            'lon_min': -74.2591, 'lon_max': -73.7004
        }
        
        invalid_coords = (
            (df['pickup_latitude'] < nyc_bounds['lat_min']) | 
            (df['pickup_latitude'] > nyc_bounds['lat_max']) |
            (df['pickup_longitude'] < nyc_bounds['lon_min']) | 
            (df['pickup_longitude'] > nyc_bounds['lon_max']) |
            (df['dropoff_latitude'] < nyc_bounds['lat_min']) | 
            (df['dropoff_latitude'] > nyc_bounds['lat_max']) |
            (df['dropoff_longitude'] < nyc_bounds['lon_min']) | 
            (df['dropoff_longitude'] > nyc_bounds['lon_max'])
        )
        
        self.excluded_records.extend(df[invalid_coords]['id'].tolist())
        df = df[~invalid_coords]
        
        # Remove outliers in trip duration (trips longer than 6 hours or shorter than 1 minute)
        invalid_duration = (df['trip_duration'] > 21600) | (df['trip_duration'] < 60)
        self.excluded_records.extend(df[invalid_duration]['id'].tolist())
        df = df[~invalid_duration]
        
        # Remove outliers in passenger count
        invalid_passengers = (df['passenger_count'] < 1) | (df['passenger_count'] > 6)
        self.excluded_records.extend(df[invalid_passengers]['id'].tolist())
        df = df[~invalid_passengers]
        
        logger.info(f"Cleaned data: {len(df)} records remaining from {original_count}")
        logger.info(f"Excluded {len(self.excluded_records)} records")
        
        return df
    
    def calculate_derived_features(self, df):
        """Calculate derived features"""
        logger.info("Calculating derived features")
        
        # Create a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Calculate trip distance using Haversine formula
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in kilometers
            lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            return R * c
        
        df['trip_distance_km'] = haversine_distance(
            df['pickup_latitude'], df['pickup_longitude'],
            df['dropoff_latitude'], df['dropoff_longitude']
        )
        
        # Calculate trip speed (km/h)
        df['trip_speed_kmh'] = df['trip_distance_km'] / (df['trip_duration'] / 3600)
        
        # Remove unrealistic speeds (>200 km/h or <1 km/h)
        invalid_speed = (df['trip_speed_kmh'] > 200) | (df['trip_speed_kmh'] < 1)
        self.excluded_records.extend(df[invalid_speed]['id'].tolist())
        df = df[~invalid_speed]
        
        # Calculate fare amount (simplified fare calculation)
        base_fare = 2.50
        per_km_rate = 1.50
        per_minute_rate = 0.50
        
        df['fare_amount'] = (
            base_fare + 
            (df['trip_distance_km'] * per_km_rate) + 
            (df['trip_duration'] / 60 * per_minute_rate)
        ).round(2)
        
        # Calculate fare per kilometer
        df['fare_per_km'] = (df['fare_amount'] / df['trip_distance_km']).round(2)
        
        # Create pickup and dropoff zones (simplified grid-based zones)
        df['pickup_zone'] = self.create_zones(df['pickup_latitude'], df['pickup_longitude'])
        df['dropoff_zone'] = self.create_zones(df['dropoff_latitude'], df['dropoff_longitude'])
        
        logger.info("Derived features calculated successfully")
        return df
    
    def create_zones(self, latitudes, longitudes):
        """Create simplified zones based on coordinates"""
        # Create a grid-based zone system
        lat_bins = pd.cut(latitudes, bins=20, labels=False)
        lon_bins = pd.cut(longitudes, bins=20, labels=False)
        return [f"Zone_{lat}_{lon}" for lat, lon in zip(lat_bins, lon_bins)]
    
    def clean_all_data_and_save(self, max_records=5000):
        """Clean all data and save to cleaned_dataset.csv - limited to 5000 records for performance"""
        try:
            logger.info("Starting comprehensive data cleaning process...")
            
            # Load data (limited to 5000 records)
            df = self.load_data(max_records)
            original_count = len(df)
            logger.info(f"Starting with {original_count} records")
            
            # Clean data
            df = self.clean_data(df)
            
            # Calculate derived features
            df = self.calculate_derived_features(df)
            
            # Save cleaned data to CSV
            df.to_csv(self.cleaned_file, index=False)
            
            final_count = len(df)
            excluded_count = len(self.excluded_records)
            
            logger.info(f"Data cleaning completed!")
            logger.info(f"Original records: {original_count}")
            logger.info(f"Cleaned records: {final_count}")
            logger.info(f"Excluded records: {excluded_count}")
            logger.info(f"Cleaned data saved to: {self.cleaned_file}")
            
            # Save excluded records log
            if self.excluded_records:
                with open('excluded_records.txt', 'w') as f:
                    f.write('\n'.join(self.excluded_records))
                logger.info("Excluded records saved to excluded_records.txt")
            
            return final_count
            
        except Exception as e:
            logger.error(f"Error in data cleaning: {e}")
            raise
    
    def save_to_database(self, df):
        """Save processed data to normalized database tables"""
        conn = None
        cursor = None
        
        try:
            logger.info("Saving data to normalized database tables")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # First, insert vendors
            self.insert_vendors(cursor, conn, df)
            
            # Then, insert zones
            self.insert_zones(cursor, conn, df)
            
            # Finally, insert trips with foreign key references
            self.insert_trips(cursor, conn, df)
            
            logger.info(f"Successfully saved {len(df)} records to normalized database")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def insert_vendors(self, cursor, conn, df):
        """Insert unique vendors into vendors table"""
        logger.info("Inserting vendors...")
        
        # Get unique vendors
        unique_vendors = df['vendor_id'].dropna().unique()
        
        for vendor_id in unique_vendors:
            vendor_name = f"Vendor_{vendor_id}"  # Simple naming convention
            
            cursor.execute("""
                INSERT INTO vendors (vendor_id, vendor_name)
                VALUES (%s, %s)
                ON CONFLICT (vendor_id) DO NOTHING
            """, (vendor_id, vendor_name))
        
        conn.commit()
        logger.info(f"Inserted {len(unique_vendors)} vendors")
    
    def insert_zones(self, cursor, conn, df):
        """Insert unique zones into zones table"""
        logger.info("Inserting zones...")
        
        # Get unique pickup and dropoff zones
        all_zones = set()
        all_zones.update(df['pickup_zone'].dropna().unique())
        all_zones.update(df['dropoff_zone'].dropna().unique())
        
        for zone_name in all_zones:
            # Calculate average coordinates for this zone
            zone_trips = df[(df['pickup_zone'] == zone_name) | (df['dropoff_zone'] == zone_name)]
            avg_lat = zone_trips[['pickup_latitude', 'dropoff_latitude']].values.mean()
            avg_lon = zone_trips[['pickup_longitude', 'dropoff_longitude']].values.mean()
            trip_count = len(zone_trips)
            
            cursor.execute("""
                INSERT INTO zones (zone_name, latitude, longitude, trip_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (zone_name) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    trip_count = EXCLUDED.trip_count
            """, (zone_name, avg_lat, avg_lon, trip_count))
        
        conn.commit()
        logger.info(f"Inserted {len(all_zones)} zones")
    
    def insert_trips(self, cursor, conn, df):
        """Insert trips with foreign key references to vendors and zones"""
        logger.info("Inserting trips...")
        
        # Prepare data for insertion
        columns = [
            'id', 'vendor_id', 'pickup_datetime', 'dropoff_datetime',
            'passenger_count', 'pickup_longitude', 'pickup_latitude',
            'dropoff_longitude', 'dropoff_latitude', 'store_and_fwd_flag',
            'trip_duration', 'trip_distance_km', 'trip_speed_kmh',
            'fare_amount', 'fare_per_km'
        ]
        
        # Insert data in smaller batches
        batch_size = 100  # Smaller batch size for normalized data
        total_inserted = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                # Get zone IDs for foreign key references
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
                
                # Insert trip with foreign key references
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
                    row['id'], row['vendor_id'], row['pickup_datetime'], row['dropoff_datetime'],
                    row['passenger_count'], row['pickup_longitude'], row['pickup_latitude'],
                    row['dropoff_longitude'], row['dropoff_latitude'], row['store_and_fwd_flag'],
                    row['trip_duration'], row['trip_distance_km'], row['trip_speed_kmh'],
                    row['fare_amount'], row['fare_per_km'], pickup_zone_id, dropoff_zone_id
                ))
            
            conn.commit()
            total_inserted += len(batch)
            logger.info(f"Inserted {total_inserted} trips")
    
    
    def process_data_if_needed(self):
        """Process data only if it hasn't been processed yet"""
        if not check_data_exists():
            logger.info("No data found in database. Starting data processing...")
            
            # Check if cleaned data exists
            if os.path.exists(self.cleaned_file):
                logger.info(f"Found cleaned data file: {self.cleaned_file}")
                df = self.load_cleaned_data()
                self.save_to_database(df)
                logger.info(f"Loaded {len(df)} records from cleaned data")
            else:
                logger.info("No cleaned data found. Starting data cleaning...")
                df = self.load_data()
                df = self.clean_data(df)
                df = self.calculate_derived_features(df)
                self.save_to_database(df)
                
                # Log excluded records
                logger.info(f"Excluded records: {len(self.excluded_records)}")
                if self.excluded_records:
                    with open('excluded_records.txt', 'w') as f:
                        f.write('\n'.join(self.excluded_records))
                    logger.info("Excluded records saved to excluded_records.txt")
        else:
            logger.info("Data already exists in database. Skipping processing.")
    
    def clean_data_only(self, max_records=5000):
        """Clean data and save to CSV without database insertion - limited to 5000 records for performance"""
        print("🧹 Data Cleaning Mode")
        print("=" * 30)
        print("This will clean the raw data and save it to cleaned_dataset.csv")
        print(f"Processing limited to {max_records} records for performance.")
        print("You can then inspect the cleaned data before database insertion.")
        
        response = input("Continue with data cleaning? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Data cleaning cancelled.")
            return 0
        
        total_cleaned = self.clean_all_data_and_save(max_records)
        print(f"\n🎉 Data cleaning completed!")
        print(f"📁 Cleaned data saved to: {self.cleaned_file}")
        print(f"📊 Total records cleaned: {total_cleaned}")
        print(f"📝 Excluded records: {len(self.excluded_records)}")
        
        return total_cleaned
    
    def process_data_interactive(self, batch_size=100):
        """Process data in interactive batches using cleaned data"""
        print(f"\n🔄 Starting interactive data processing...")
        
        # Check if cleaned data exists
        if not os.path.exists(self.cleaned_file):
            print("📊 No cleaned data found. Starting data cleaning process...")
            response = input("This will clean ALL data and may take a while. Continue? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ Data cleaning cancelled.")
                return 0
            
            # Clean all data and save to CSV
            total_cleaned = self.clean_all_data_and_save()
            print(f"✅ Data cleaning completed! {total_cleaned} records cleaned and saved.")
        
        print(f"📊 Loading from cleaned data: {self.cleaned_file}")
        print(f"📊 Processing {batch_size} records at a time")
        print("Press 'q' to quit, 'a' to process all remaining, or Enter to continue")
        
        total_processed = 0
        batch_number = 1
        
        while True:
            print(f"\n--- Batch {batch_number} ---")
            
            # Load batch from cleaned data
            start_record = total_processed
            end_record = start_record + batch_size
            
            print(f"Loading records {start_record + 1} to {end_record}...")
            df = self.load_cleaned_data(max_records=end_record)
            
            if len(df) <= start_record:
                print("✅ No more data to process!")
                break
                
            # Get only the new batch
            df = df.iloc[start_record:]
            if len(df) == 0:
                print("✅ No more data to process!")
                break
            
            print(f"Inserting {len(df)} records into database...")
            
            # Save batch to database (data is already cleaned)
            self.save_to_database(df)
            total_processed += len(df)
            
            print(f"✅ Batch {batch_number} completed! Total processed: {total_processed}")
            
            # Ask user what to do next
            response = input(f"\nProcess next batch? (Enter=continue, 'a'=all remaining, 'q'=quit): ").strip().lower()
            
            if response == 'q':
                print(f"\n🛑 Processing stopped by user. Total processed: {total_processed}")
                break
            elif response == 'a':
                print(f"\n🚀 Processing all remaining data...")
                # Process remaining data in larger batches
                remaining_df = self.load_cleaned_data()
                if len(remaining_df) > total_processed:
                    remaining_df = remaining_df.iloc[total_processed:]
                    self.save_to_database(remaining_df)
                    total_processed += len(remaining_df)
                print(f"✅ All data processed! Total records: {total_processed}")
                break
            
            batch_number += 1
        
        return total_processed
