#!/usr/bin/env python3
"""
Data cleaning script for Urban Mobility Data Explorer
This script processes raw NYC taxi data and saves cleaned data to CSV.
"""

import os
import sys
from data_processor import DataProcessor

def main():
    print("🧹 Urban Mobility Data Explorer - Data Cleaning")
    print("=" * 50)
    
    # Check if raw data exists
    if not os.path.exists('train.csv'):
        print("❌ Error: train.csv not found in current directory")
        print("Please ensure train.csv is in the backend directory")
        sys.exit(1)
    
    print("📊 Found train.csv - starting data cleaning process...")
    print("📊 Processing limited to 1000 records for performance")
    
    # Initialize data processor
    processor = DataProcessor()
    
    # Clean data and save to CSV
    total_cleaned = processor.clean_all_data_and_save(max_records=1000)
    
    print(f"\n🎉 Data cleaning completed!")
    print(f"📁 Cleaned data saved to: cleaned_dataset.csv")
    print(f"📊 Total records cleaned: {total_cleaned}")
    print(f"📝 Excluded records: {len(processor.excluded_records)}")
    
    if processor.excluded_records:
        print(f"📄 Excluded records log saved to: excluded_records.txt")
    
    print(f"\n✅ Ready to run setup.py to import data into database")

if __name__ == "__main__":
    main()
