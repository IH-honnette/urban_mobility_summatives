# Urban Mobility Data Explorer

This is full-stack web application for exploring NYC taxi trip data with interactive visualizations and real-time analytics.


## Project Structure

```
urban-mobility-data-explorer/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── database.py            # Database connection and schema
│   ├── data_processor.py      # Data cleaning and processing
│   ├── api_routes.py          # REST API endpoints
│   ├── setup.py               # Database setup script
│   ├── requirements.txt       # Python dependencies
│   ├── README.md              # Backend documentation
│   ├── env_template.txt       # Environment variables template
│   └── train.csv              # Raw NYC taxi data
├── frontend/
│   ├── index.html             # Main HTML page
│   ├── script.js              # Frontend JavaScript
│   └── style.css              # Styling
└── README.md                  # This file
```

## Report & Video

- **Report**: [REPORT](https://docs.google.com/document/d/1uJmi7nF_PL4kR4iqPt29EzgpdtVLDNhc-ki_y8etvIo/edit?usp=sharing) - Comprehensive report documentation including system architecture, algorithmic implementations, and insights
- **Video**: [VIDEO](./video.mov) - Video demonstration of the application

## Features

### Backend (Flask + PostgreSQL)
- **Data Processing**: Cleans and processes NYC taxi trip records
- **Normalized Database**: Well-structured relational database with vendors, zones, and trips tables
- **Derived Features**: Calculates trip speed, fare per km, and zone analysis
- **Database Design**: Normalized schema with foreign key relationships and proper indexing
- **REST API**: Comprehensive endpoints for data visualization
- **Data Validation**: Handles outliers, missing values, and invalid records

### Frontend (Vanilla JavaScript + Chart.js)
- **Interactive Dashboard**: Real-time data visualization
- **Filtering**: Date range and fare amount filters
- **Charts**: Hourly distribution and fare vs distance analysis
- **Responsive Design**: Modern dark theme with gradient accents

## Quick Start

### 1. Backend Setup

```
git clone https://github.com/IH-honnette/urban_mobility_summatives.git
cd urban-mobility-data-explorer
```

```bash
cd backend

# Install dependencies
pip install -r requirements.txt || pip3 install -r requirements.txt

# Make sure to add the the train.csv file to the backend directory.
# Create .env file (copy from env_template.txt)
# Update DATABASE_URL with your PostgreSQL connection

# Setup database and process data
python setup.py

# Run Flask application
python app.py
```

### 2. Frontend Setup

```bash
cd frontend

# Open index.html in your browser
```

### 3. Access Application

- Backend API: `http://localhost:5003`

## Database Schema

The database uses a normalized structure with three main tables:

### Vendors Table
```sql
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER UNIQUE NOT NULL,
    vendor_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Zones Table
```sql
CREATE TABLE zones (
    id SERIAL PRIMARY KEY,
    zone_name VARCHAR(50) UNIQUE NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    trip_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Trips Table
```sql
CREATE TABLE trips (
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
    trip_distance_km DECIMAL(8, 3),      -- Derived feature
    trip_speed_kmh DECIMAL(6, 2),        -- Derived feature
    fare_amount DECIMAL(8, 2),           -- Derived feature
    fare_per_km DECIMAL(6, 2),          -- Derived feature
    pickup_zone_id INTEGER REFERENCES zones(id),
    dropoff_zone_id INTEGER REFERENCES zones(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/stats` | GET | Comprehensive urban mobility statistics and overview metrics 
| `/api/trips` | GET | Advanced trip filtering, sorting, and pagination | `start`, `end`, `fare_amount`, `distance`, `passengers`, `pickup_zone`, `min_fare`, `max_fare`, `min_distance_km`, `max_distance_km`, `passenger_min`, `passenger_max`, `page`, `page_size`, `sort_by`, `sort_dir` |
| `/api/zones` | GET | All zones 
| `/api/busiest-zones` | GET | Top 20 busiest pickup zones with coordinates 
| `/api/all-zones-with-counts` | GET | All zones with trip counts for map visualization 
| `/api/hourly-distribution` | GET | Trip distribution by hour of day 
| `/api/fare-analysis` | GET | Detailed fare economics and pricing analysis 
| `/api/mobility-insights` | GET | Comprehensive mobility patterns and efficiency metrics 
| `/api/vendor-performance` | GET | Vendor comparison and performance analysis 

## Data Processing 

**Note**: The system processes the first 5000 records from the raw CSV data for optimal performance while maintaining meaningful insights.

### 1. Data Cleaning
- Remove duplicates based on trip ID
- Handle missing values in critical fields
- Validate coordinates within NYC bounds


### 2. Derived Features
- **Trip Distance**: Haversine formula for accurate distance calculation
- **Trip Speed**: Distance/time calculation with validation (<200 km/h, >1 km/h)
- **Fare Amount**: Base fare + distance rate + time rate
- **Fare per KM**: Cost efficiency metric
- **Zones**: Grid-based pickup/dropoff zones for analysis

### 3. Data Validation
- Comprehensive logging of excluded records
- Transparent reporting of data quality issues
- Performance optimization with database indexes

## Technology Stack

### Backend
- **Flask**: Web framework
- **PostgreSQL**: Relational database
- **Pandas**: Data processing
- **NumPy**: Numerical computations
- **psycopg2**: PostgreSQL adapter

### Frontend
- **Vanilla JavaScript**
- **Chart.js**: Data visualization
- **CSS3**: Modern styling with gradients
- **HTML5**: Semantic markup

## Development Notes

### Data Processing
- Processes the data from the raw CSV file
- Normalized database structure with foreign key relationships
- Excluded records are logged for transparency

### Performance
- Database indexes on frequently queried columns
- Chunked data processing for large files
- Efficient API responses with pagination

### Error Handling
- Comprehensive logging throughout the application
- Graceful error handling in API endpoints
- User-friendly error messages in frontend

## Future Enhancements

- Real-time data streaming
- Machine learning predictions
- Geographic mapping integration
- Advanced filtering options
- Data export functionality

### **GROUP MEMBERS**

-Umwari Vanessa
-Ihozo Marie Honnette
-Kwizera Karangwa Laura
