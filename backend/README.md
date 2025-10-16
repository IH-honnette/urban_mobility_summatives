# Urban Mobility Data Explorer - Backend

This is the Flask backend for the Urban Mobility Data Explorer application. It processes NYC taxi trip data and provides REST API endpoints for data visualization.


## Features

- **Data Processing**: Cleans and processes raw NYC taxi trip data
- **Normalized Database**: Well-structured relational database with separate tables for vendors, trips, and zones
- **Derived Features**: Calculates trip speed, fare per km, and zone-based analysis
- **PostgreSQL Integration**: Stores processed data in normalized tables with foreign key relationships
- **REST API**: Provides endpoints for frontend data consumption
- **Data Validation**: Handles missing values, outliers, and invalid records

## Setup Instructions

### 1. Install Dependencies

Make sure to add the the train.csv file to the backend directory.

```bash
cd backend
pip install -r requirements.txt
```

### 2. Database Configuration

Create a `.env` file in the backend directory with your PostgreSQL connection:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/urban_mobility_db
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3. Initialize Database and Process Data

#### Option A: Complete Setup (Recommended)
```bash
python setup.py
```

This will:
- Create normalized database tables (vendors, zones, trips)
- Process the data from `train.csv` file
- Clean and validate data
- Calculate derived features
- Load data into normalized PostgreSQL tables with foreign key relationships

### 4. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:5003`

## API Endpoints

### Core Statistics & Overview
- `GET /api/stats` - Comprehensive urban mobility statistics
  - Returns: Overview metrics, vendor distribution, peak hours analysis
  - Includes: Total trips, average speeds, fare efficiency, market share

## Data Processing

The system processes the first 5000 records from the raw CSV data and:

1. **Cleans Data**:
   - Removes duplicates
   - Handles missing values
   - Validates coordinates (NYC bounds)
   - Filters invalid trip durations
   - Removes outlier passenger counts

2. **Calculates Derived Features**:
   - **Trip Distance**: Using Haversine formula
   - **Trip Speed**: Distance/time calculation
   - **Fare Amount**: Based on distance and duration
   - **Fare per KM**: Cost efficiency metric
   - **Zones**: Grid-based pickup/dropoff zones

3. **Normalized Database Insertion**:
   - Inserts unique vendors into vendors table
   - Creates zones with average coordinates and trip counts
   - Inserts trips with foreign key references to vendors and zones
   - Maintains referential integrity

4. **Data Validation**:
   - Logs excluded records
   - Validates realistic speeds (<200 km/h, >1 km/h)
   - Ensures data integrity

## Database Schema

The database uses a normalized structure with three main tables:

### Vendors Table
- Primary key: `id` (auto-increment)
- Unique vendor_id and vendor_name
- References trips via foreign key

### Zones Table
- Primary key: `id` (auto-increment)
- Unique zone_name with coordinates
- Trip count statistics
- Referenced by trips table for pickup/dropoff zones

### Trips Table
- Primary key: `id` (trip identifier)
- Foreign keys: `vendor_id` → vendors, `pickup_zone_id` → zones, `dropoff_zone_id` → zones
- Trip details: pickup/dropoff times, locations, duration
- Derived features: distance, speed, fare calculations
- Indexes on: datetime, location, duration, fare, vendor, zones

## Error Handling

- Comprehensive logging for data processing
- Database connection error handling
- API error responses with appropriate HTTP status codes
- Excluded records are logged for transparency

## Troubleshooting

### Database Schema Issues
If you encounter schema-related errors (e.g., "column does not exist"):
```bash
# Drop and recreate tables with new schema
python setup.py
# Choose option 1: Drop and recreate tables
```

### Data Processing Issues
If data cleaning fails:
```bash
# Clean data separately first
python clean_data.py
# Then run setup
python setup.py
```

### Common Issues
- **"DATABASE_URL not found"**: Create `.env` file with PostgreSQL connection string
- **"train.csv not found"**: Ensure raw data file is in backend directory
- **"Port already in use"**: Change port in `app.py` or kill existing process
- **"Permission denied"**: Ensure PostgreSQL user has CREATE/DROP privileges
