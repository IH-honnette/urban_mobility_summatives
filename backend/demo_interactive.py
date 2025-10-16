#!/usr/bin/env python3
"""
Demo script showing interactive data processing
"""

from data_processor import DataProcessor

def demo_interactive_processing():
    """Demo the interactive processing with a small batch"""
    print("🎯 Interactive Data Processing Demo")
    print("=" * 40)
    print("This demo will process just 50 records to show how it works.")
    print("In the real setup, you can process 100 records at a time.")
    
    processor = DataProcessor()
    
    # Process a small demo batch
    total_processed = processor.process_data_interactive(batch_size=50)
    
    print(f"\n🎉 Demo completed! Processed {total_processed} records.")
    print("You can now run the full setup with: python3 setup.py")

if __name__ == "__main__":
    demo_interactive_processing()
