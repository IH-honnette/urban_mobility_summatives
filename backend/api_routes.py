from flask import Blueprint, jsonify, request
from database import get_db_connection
import logging
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get comprehensive urban mobility statistics and insights"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get basic statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trips,
                AVG(trip_speed_kmh) as avg_speed,
                AVG(fare_per_km) as avg_fare_per_km,
                AVG(trip_duration) as avg_duration,
                AVG(trip_distance_km) as avg_distance,
                AVG(fare_amount) as avg_fare,
                MIN(pickup_datetime) as earliest_trip,
                MAX(pickup_datetime) as latest_trip
            FROM trips t
        """)
        
        stats = cursor.fetchone()
        
        # Get vendor distribution
        cursor.execute("""
            SELECT v.vendor_name, COUNT(t.id) as trip_count
            FROM vendors v
            LEFT JOIN trips t ON v.vendor_id = t.vendor_id
            GROUP BY v.vendor_id, v.vendor_name
            ORDER BY trip_count DESC
        """)
        
        vendor_stats = []
        for row in cursor.fetchall():
            vendor_stats.append({
                'vendor_name': row[0],
                'trip_count': int(row[1]),
                'market_share': round((row[1] / stats[0]) * 100, 2) if stats[0] > 0 else 0
            })
        
        # Get peak hours analysis
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM pickup_datetime) as hour,
                COUNT(*) as trip_count,
                AVG(trip_speed_kmh) as avg_speed,
                AVG(fare_amount) as avg_fare
            FROM trips
            GROUP BY EXTRACT(HOUR FROM pickup_datetime)
            ORDER BY trip_count DESC
            LIMIT 5
        """)
        
        peak_hours = []
        for row in cursor.fetchall():
            peak_hours.append({
                'hour': int(row[0]),
                'trip_count': int(row[1]),
                'avg_speed_kmh': round(float(row[2]), 2),
                'avg_fare': round(float(row[3]), 2)
            })
        
        return jsonify({
            'overview': {
                'total_trips': int(stats[0]),
                'avg_speed_kmh': round(float(stats[1]), 2),
                'avg_fare_per_km': round(float(stats[2]), 2),
                'avg_duration_minutes': round(float(stats[3]) / 60, 2),
                'avg_distance_km': round(float(stats[4]), 2),
                'avg_fare': round(float(stats[5]), 2),
                'data_period': {
                    'earliest_trip': stats[6].isoformat() if stats[6] else None,
                    'latest_trip': stats[7].isoformat() if stats[7] else None
                }
            },
            'vendor_distribution': vendor_stats,
            'peak_hours': peak_hours
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/trips', methods=['GET'])
def get_trips():
    """Get trips with filters, pagination and sorting - using normalized tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get query parameters
        start_date = request.args.get('start', '')
        end_date = request.args.get('end', '')
        min_fare = float(request.args.get('min_fare', '0'))

        # Additional filters
        min_dist = request.args.get('min_distance_km')
        max_dist = request.args.get('max_distance_km')
        passenger_min = request.args.get('passenger_min')
        passenger_max = request.args.get('passenger_max')
        pickup_zone = request.args.get('pickup_zone')

        # Pagination
        page = int(request.args.get('page', '1'))
        page_size = int(request.args.get('page_size', '50'))
        page = 1 if page < 1 else page
        page_size = 1 if page_size < 1 else min(page_size, 500)
        offset = (page - 1) * page_size

        # Sorting
        sort_by = request.args.get('sort_by', 'pickup_datetime')
        sort_dir = request.args.get('sort_dir', 'desc').lower()
        allowed_sorts = {
            'pickup_datetime', 'fare_amount', 'trip_distance_km',
            'trip_duration', 'trip_speed_kmh'
        }
        if sort_by not in allowed_sorts:
            sort_by = 'pickup_datetime'
        sort_dir = 'DESC' if sort_dir != 'asc' else 'ASC'
        
        # Build dynamic WHERE clauses
        where_clauses = ["t.fare_amount >= %s"]
        params = [min_fare]
        
        if start_date:
            where_clauses.append("t.pickup_datetime >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("t.pickup_datetime <= %s")
            params.append(end_date)

        if min_dist is not None:
            where_clauses.append("t.trip_distance_km >= %s")
            params.append(float(min_dist))
        if max_dist is not None:
            where_clauses.append("t.trip_distance_km <= %s")
            params.append(float(max_dist))
        if passenger_min is not None:
            where_clauses.append("t.passenger_count >= %s")
            params.append(int(passenger_min))
        if passenger_max is not None:
            where_clauses.append("t.passenger_count <= %s")
            params.append(int(passenger_max))
        if pickup_zone:
            where_clauses.append("pz.zone_name = %s")
            params.append(pickup_zone)

        where_sql = " AND ".join(where_clauses)

        # Total count for pagination
        count_sql = f"""
            SELECT COUNT(*) 
            FROM trips t
            LEFT JOIN zones pz ON t.pickup_zone_id = pz.id
            LEFT JOIN zones dz ON t.dropoff_zone_id = dz.id
            WHERE {where_sql}
        """
        cursor.execute(count_sql, tuple(params))
        total = cursor.fetchone()[0]

        # Page query with joins to get zone names
        query = f"""
            SELECT 
                t.id, t.pickup_datetime, t.dropoff_datetime,
                t.pickup_latitude, t.pickup_longitude,
                t.dropoff_latitude, t.dropoff_longitude,
                t.trip_duration, t.trip_distance_km,
                t.trip_speed_kmh, t.fare_amount, t.fare_per_km,
                t.passenger_count, pz.zone_name as pickup_zone, dz.zone_name as dropoff_zone,
                v.vendor_name
            FROM trips t
            LEFT JOIN zones pz ON t.pickup_zone_id = pz.id
            LEFT JOIN zones dz ON t.dropoff_zone_id = dz.id
            LEFT JOIN vendors v ON t.vendor_id = v.vendor_id
            WHERE {where_sql}
            ORDER BY t.{sort_by} {sort_dir}
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, tuple(params + [page_size, offset]))
        
        trips = []
        for row in cursor.fetchall():
            trips.append({
                'id': row[0],
                'pickup_datetime': row[1].isoformat() if row[1] else None,
                'dropoff_datetime': row[2].isoformat() if row[2] else None,
                'pickup_latitude': float(row[3]),
                'pickup_longitude': float(row[4]),
                'dropoff_latitude': float(row[5]),
                'dropoff_longitude': float(row[6]),
                'trip_duration': int(row[7]),
                'trip_distance_km': float(row[8]),
                'trip_speed_kmh': float(row[9]),
                'fare_amount': float(row[10]),
                'fare_per_km': float(row[11]),
                'passenger_count': int(row[12]),
                'pickup_zone': row[13],
                'dropoff_zone': row[14],
                'vendor_name': row[15]
            })
        
        return jsonify({
            'data': trips,
            'total': int(total),
            'page': page,
            'page_size': page_size
        })
        
    except Exception as e:
        logger.error(f"Error getting trips: {e}")
        return jsonify({'error': 'Failed to get trips'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/zones', methods=['GET'])
def get_all_zones():
    """Get all zones for filtering"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id,
                zone_name,
                latitude,
                longitude
            FROM zones
            ORDER BY zone_name
        """)
        
        zones = []
        for row in cursor.fetchall():
            zones.append({
                'id': int(row[0]),
                'zone_name': row[1],
                'latitude': float(row[2]),
                'longitude': float(row[3])
            })
        
        return jsonify(zones)
        
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return jsonify({'error': 'Failed to get zones'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/busiest-zones', methods=['GET'])
def get_busiest_zones():
    """Get busiest pickup zones - using normalized tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                pz.zone_name,
                pz.latitude as lat,
                pz.longitude as lon,
                COUNT(t.id) as count
            FROM trips t
            JOIN zones pz ON t.pickup_zone_id = pz.id
            GROUP BY pz.id, pz.zone_name, pz.latitude, pz.longitude
            ORDER BY count DESC
            LIMIT 20
        """)
        
        zones = []
        for row in cursor.fetchall():
            zones.append({
                'zone': row[0],
                'lat': float(row[1]),
                'lon': float(row[2]),
                'count': int(row[3])
            })
        
        return jsonify(zones)
        
    except Exception as e:
        logger.error(f"Error getting busiest zones: {e}")
        return jsonify({'error': 'Failed to get busiest zones'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/all-zones-with-counts', methods=['GET'])
def get_all_zones_with_counts():
    """Get all zones with their trip counts for map visualization"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                pz.id,
                pz.zone_name,
                pz.latitude as lat,
                pz.longitude as lon,
                COUNT(t.id) as count
            FROM zones pz
            LEFT JOIN trips t ON pz.id = t.pickup_zone_id
            GROUP BY pz.id, pz.zone_name, pz.latitude, pz.longitude
            ORDER BY count DESC, pz.zone_name
        """)
        
        zones = []
        for row in cursor.fetchall():
            zones.append({
                'id': int(row[0]),
                'zone': row[1],
                'lat': float(row[2]),
                'lon': float(row[3]),
                'count': int(row[4])
            })
        
        return jsonify(zones)
        
    except Exception as e:
        logger.error(f"Error getting all zones with counts: {e}")
        return jsonify({'error': 'Failed to get all zones with counts'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/hourly-distribution', methods=['GET'])
def get_hourly_distribution():
    """Get trip distribution by hour"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        start_date = request.args.get('start', '2016-01-01')
        end_date = request.args.get('end', '2016-12-31')
        
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM pickup_datetime) as hour,
                COUNT(*) as count
            FROM trips
            WHERE pickup_datetime >= %s 
            AND pickup_datetime <= %s
            GROUP BY EXTRACT(HOUR FROM pickup_datetime)
            ORDER BY hour
        """, (start_date, end_date))
        
        hourly_data = [0] * 24
        for row in cursor.fetchall():
            hour = int(row[0])
            count = int(row[1])
            hourly_data[hour] = count
        
        return jsonify(hourly_data)
        
    except Exception as e:
        logger.error(f"Error getting hourly distribution: {e}")
        return jsonify({'error': 'Failed to get hourly distribution'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/fare-analysis', methods=['GET'])
def get_fare_analysis():
    """Get comprehensive fare analysis with urban mobility insights"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        start_date = request.args.get('start', '2016-01-01')
        end_date = request.args.get('end', '2016-12-31')
        limit = int(request.args.get('limit', '1000'))
        
        # Get fare efficiency analysis
        cursor.execute("""
            SELECT 
                AVG(fare_per_km) as avg_fare_per_km,
                MIN(fare_per_km) as min_fare_per_km,
                MAX(fare_per_km) as max_fare_per_km,
                STDDEV(fare_per_km) as fare_per_km_stddev,
                AVG(fare_amount) as avg_fare_amount,
                AVG(trip_distance_km) as avg_distance,
                AVG(trip_duration) as avg_duration
            FROM trips
            WHERE pickup_datetime >= %s 
            AND pickup_datetime <= %s
        """, (start_date, end_date))
        
        fare_stats = cursor.fetchone()
        
        # Get fare distribution by distance ranges
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN trip_distance_km < 2 THEN 'Short (<2km)'
                    WHEN trip_distance_km < 5 THEN 'Medium (2-5km)'
                    WHEN trip_distance_km < 10 THEN 'Long (5-10km)'
                    ELSE 'Very Long (>10km)'
                END as distance_category,
                COUNT(*) as trip_count,
                AVG(fare_amount) as avg_fare,
                AVG(fare_per_km) as avg_fare_per_km,
                AVG(trip_speed_kmh) as avg_speed
            FROM trips
            WHERE pickup_datetime >= %s 
            AND pickup_datetime <= %s
            GROUP BY distance_category
            ORDER BY AVG(trip_distance_km)
        """, (start_date, end_date))
        
        fare_by_distance = []
        for row in cursor.fetchall():
            fare_by_distance.append({
                'distance_category': row[0],
                'trip_count': int(row[1]),
                'avg_fare': round(float(row[2]), 2),
                'avg_fare_per_km': round(float(row[3]), 2),
                'avg_speed_kmh': round(float(row[4]), 2)
            })
        
        # Get sample data for scatter plot
        cursor.execute("""
            SELECT 
                fare_amount,
                trip_distance_km,
                trip_duration,
                trip_speed_kmh,
                fare_per_km
            FROM trips
            WHERE pickup_datetime >= %s 
            AND pickup_datetime <= %s
            ORDER BY pickup_datetime DESC
            LIMIT %s
        """, (start_date, end_date, limit))
        
        sample_data = []
        for row in cursor.fetchall():
            sample_data.append({
                'fare_amount': float(row[0]),
                'trip_distance_km': float(row[1]),
                'trip_duration': int(row[2]),
                'trip_speed_kmh': float(row[3]),
                'fare_per_km': float(row[4])
            })
        
        return jsonify({
            'fare_statistics': {
                'avg_fare_per_km': round(float(fare_stats[0]), 2),
                'min_fare_per_km': round(float(fare_stats[1]), 2),
                'max_fare_per_km': round(float(fare_stats[2]), 2),
                'fare_per_km_stddev': round(float(fare_stats[3]), 2),
                'avg_fare_amount': round(float(fare_stats[4]), 2),
                'avg_distance_km': round(float(fare_stats[5]), 2),
                'avg_duration_minutes': round(float(fare_stats[6]) / 60, 2)
            },
            'fare_by_distance': fare_by_distance,
            'sample_data': sample_data
        })
        
    except Exception as e:
        logger.error(f"Error getting fare analysis: {e}")
        return jsonify({'error': 'Failed to get fare analysis'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/mobility-insights', methods=['GET'])
def get_mobility_insights():
    """Get comprehensive urban mobility insights and patterns"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get speed analysis by time of day
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM pickup_datetime) as hour,
                COUNT(*) as trip_count,
                AVG(trip_speed_kmh) as avg_speed,
                AVG(trip_distance_km) as avg_distance,
                AVG(fare_per_km) as avg_fare_per_km
            FROM trips
            GROUP BY EXTRACT(HOUR FROM pickup_datetime)
            ORDER BY hour
        """)
        
        hourly_patterns = []
        for row in cursor.fetchall():
            hourly_patterns.append({
                'hour': int(row[0]),
                'trip_count': int(row[1]),
                'avg_speed_kmh': round(float(row[2]), 2),
                'avg_distance_km': round(float(row[3]), 2),
                'avg_fare_per_km': round(float(row[4]), 2)
            })
        
        # Get efficiency metrics
        cursor.execute("""
            SELECT 
                AVG(trip_speed_kmh) as overall_avg_speed,
                AVG(fare_per_km) as overall_avg_fare_per_km,
                COUNT(CASE WHEN trip_speed_kmh > 30 THEN 1 END) as fast_trips,
                COUNT(CASE WHEN trip_speed_kmh < 10 THEN 1 END) as slow_trips,
                COUNT(*) as total_trips
            FROM trips
        """)
        
        efficiency_stats = cursor.fetchone()
        
        # Get zone efficiency analysis
        cursor.execute("""
            SELECT 
                pz.zone_name as pickup_zone,
                COUNT(*) as trip_count,
                AVG(trip_speed_kmh) as avg_speed,
                AVG(fare_per_km) as avg_fare_per_km,
                AVG(trip_distance_km) as avg_distance
            FROM trips t
            JOIN zones pz ON t.pickup_zone_id = pz.id
            GROUP BY pz.id, pz.zone_name
            HAVING COUNT(*) >= 5
            ORDER BY AVG(trip_speed_kmh) DESC
            LIMIT 10
        """)
        
        efficient_zones = []
        for row in cursor.fetchall():
            efficient_zones.append({
                'zone_name': row[0],
                'trip_count': int(row[1]),
                'avg_speed_kmh': round(float(row[2]), 2),
                'avg_fare_per_km': round(float(row[3]), 2),
                'avg_distance_km': round(float(row[4]), 2)
            })
        
        return jsonify({
            'hourly_patterns': hourly_patterns,
            'efficiency_metrics': {
                'overall_avg_speed_kmh': round(float(efficiency_stats[0]), 2),
                'overall_avg_fare_per_km': round(float(efficiency_stats[1]), 2),
                'fast_trips_count': int(efficiency_stats[2]),
                'slow_trips_count': int(efficiency_stats[3]),
                'total_trips': int(efficiency_stats[4]),
                'fast_trips_percentage': round((efficiency_stats[2] / efficiency_stats[4]) * 100, 2),
                'slow_trips_percentage': round((efficiency_stats[3] / efficiency_stats[4]) * 100, 2)
            },
            'most_efficient_zones': efficient_zones
        })
        
    except Exception as e:
        logger.error(f"Error getting mobility insights: {e}")
        return jsonify({'error': 'Failed to get mobility insights'}), 500
    finally:
        cursor.close()
        conn.close()

@api_bp.route('/vendor-performance', methods=['GET'])
def get_vendor_performance():
    """Get vendor performance analysis and comparison"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                v.vendor_name,
                COUNT(t.id) as total_trips,
                AVG(t.trip_speed_kmh) as avg_speed,
                AVG(t.fare_per_km) as avg_fare_per_km,
                AVG(t.trip_distance_km) as avg_distance,
                AVG(t.trip_duration) as avg_duration,
                AVG(t.fare_amount) as avg_fare_amount,
                MIN(t.pickup_datetime) as first_trip,
                MAX(t.pickup_datetime) as last_trip
            FROM vendors v
            LEFT JOIN trips t ON v.vendor_id = t.vendor_id
            GROUP BY v.vendor_id, v.vendor_name
            ORDER BY total_trips DESC
        """)
        
        vendor_performance = []
        for row in cursor.fetchall():
            vendor_performance.append({
                'vendor_name': row[0],
                'total_trips': int(row[1]),
                'avg_speed_kmh': round(float(row[2]), 2),
                'avg_fare_per_km': round(float(row[3]), 2),
                'avg_distance_km': round(float(row[4]), 2),
                'avg_duration_minutes': round(float(row[5]) / 60, 2),
                'avg_fare_amount': round(float(row[6]), 2),
                'operational_period': {
                    'first_trip': row[7].isoformat() if row[7] else None,
                    'last_trip': row[8].isoformat() if row[8] else None
                }
            })
        
        return jsonify({
            'vendor_performance': vendor_performance,
            'insights': {
                'total_vendors': len(vendor_performance),
                'most_active_vendor': vendor_performance[0]['vendor_name'] if vendor_performance else None,
                'fastest_vendor': max(vendor_performance, key=lambda x: x['avg_speed_kmh'])['vendor_name'] if vendor_performance else None,
                'most_efficient_vendor': min(vendor_performance, key=lambda x: x['avg_fare_per_km'])['vendor_name'] if vendor_performance else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting vendor performance: {e}")
        return jsonify({'error': 'Failed to get vendor performance'}), 500
    finally:
        cursor.close()
        conn.close()

