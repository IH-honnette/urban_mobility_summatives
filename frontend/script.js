class UrbanMobilityDashboard {
  constructor() {
    this.apiBase = 'http://localhost:5003/api';
    this.currentSection = 'overview';
    this.currentPage = 1;
    this.pageSize = 50;
    this.charts = {};
    this.zonesMap = null;
    this.data = {};
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadInitialData();
  }

  setupEventListeners() {
    document.querySelectorAll('.menu-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const section = e.currentTarget.dataset.section;
        this.switchSection(section);
      });
    });

    document.getElementById('sidebar-toggle').addEventListener('click', () => {
      document.querySelector('.sidebar').classList.toggle('collapsed');
      document.querySelector('.main-content').classList.toggle('expanded');
    });

    document.getElementById('refresh-btn').addEventListener('click', () => {
      this.refreshData();
    });

    document.getElementById('apply-filters').addEventListener('click', () => {
      this.currentPage = 1;
      this.loadTripsData();
    });

    document.getElementById('reset-filters').addEventListener('click', () => {
      this.resetFilters();
    });

    this.setupPaginationListeners();
  }

  switchSection(section) {
    document.querySelectorAll('.menu-item').forEach(item => {
      item.classList.remove('active');
    });
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    document.querySelectorAll('.content-section').forEach(section => {
      section.classList.remove('active');
    });
    document.getElementById(`${section}-section`).classList.add('active');

    this.currentSection = section;

    this.loadSectionData(section);
  }

  async loadInitialData() {
    this.showLoading();
    try {
      await Promise.all([
        this.loadStatsData(),
        this.loadMobilityInsights(),
        this.loadFareAnalysis(),
        this.loadVendorPerformance(),
        this.loadBusiestZones(),
        this.loadZones()
      ]);
      this.hideLoading();
    } catch (error) {
      console.error('Error loading initial data:', error);
      this.showError('Failed to load data. Please check if the backend is running.');
    }
  }

  async loadSectionData(section) {
    switch (section) {
      case 'overview':
        await this.loadStatsData();
        break;
      case 'mobility':
        await this.loadMobilityInsights();
        break;
      case 'fare-analysis':
        await this.loadFareAnalysis();
        break;
      case 'vendor-performance':
        await this.loadVendorPerformance();
        break;
      case 'zones':
        await this.loadBusiestZones();
        break;
      case 'trips':
        await Promise.all([
          this.loadZones(),
          this.loadTripsData()
        ]);
        break;
    }
  }

  async loadStatsData() {
    try {
      const response = await fetch(`${this.apiBase}/stats`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      console.log('Stats data received:', data);
      
      this.data.stats = data;
      this.updateOverviewMetrics(data);
      this.renderVendorChart(data.vendor_distribution);
      this.renderPeakHours(data.peak_hours);
      this.renderKeyInsights(data);
    } catch (error) {
      console.error('Error loading stats:', error);
      this.showError('Failed to load statistics data');
    }
  }

  async loadMobilityInsights() {
    try {
      const response = await fetch(`${this.apiBase}/mobility-insights`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      
      console.log('Mobility insights data received:', data);
      
      this.data.mobility = data;
      this.renderSpeedHourlyChart(data.hourly_patterns);
      this.renderEfficiencyChart(data.efficiency_metrics);
      this.updateEfficiencyMetrics(data.efficiency_metrics);
      this.renderEfficientZones(data.most_efficient_zones);
    } catch (error) {
      console.error('Error loading mobility insights:', error);
      this.showError('Failed to load mobility insights');
    }
  }

  async loadFareAnalysis() {
    try {
      const response = await fetch(`${this.apiBase}/fare-analysis`);
      const data = await response.json();
      
      this.data.fare = data;
      this.renderFareDistanceChart(data.sample_data);
      this.renderFareCategoryChart(data.fare_by_distance);
      this.renderFareStatistics(data.fare_statistics);
    } catch (error) {
      console.error('Error loading fare analysis:', error);
    }
  }

  async loadVendorPerformance() {
    try {
      const response = await fetch(`${this.apiBase}/vendor-performance`);
      const data = await response.json();
      
      this.data.vendors = data;
      this.renderVendorPerformance(data.vendor_performance);
    } catch (error) {
      console.error('Error loading vendor performance:', error);
    }
  }

  async loadBusiestZones() {
    try {
      const allZonesResponse = await fetch(`${this.apiBase}/all-zones-with-counts`);
      if (!allZonesResponse.ok) {
        throw new Error(`HTTP error! status: ${allZonesResponse.status}`);
      }
      const allZonesData = await allZonesResponse.json();
      
      const busiestZonesResponse = await fetch(`${this.apiBase}/busiest-zones`);
      if (!busiestZonesResponse.ok) {
        throw new Error(`HTTP error! status: ${busiestZonesResponse.status}`);
      }
      const busiestZonesData = await busiestZonesResponse.json();
      
      console.log('All zones data received:', allZonesData);
      console.log('Busiest zones data received:', busiestZonesData);
      
      this.data.allZones = allZonesData;
      this.data.zones = busiestZonesData;
      this.renderZonesMap(allZonesData);
      this.renderBusiestZones(busiestZonesData);
    } catch (error) {
      console.error('Error loading zones:', error);
      this.showError('Failed to load zone data');
    }
  }

  async loadZones() {
    try {
      const response = await fetch(`${this.apiBase}/zones`);
      const data = await response.json();
      
      this.data.allZones = data;
      this.populateZoneDropdown(data);
    } catch (error) {
      console.error('Error loading zones:', error);
    }
  }

  populateZoneDropdown(zones) {
    const dropdown = document.getElementById('pickup-zone');
    if (!dropdown) return;

    // Clear existing options except the first one
    dropdown.innerHTML = '<option value="">All Zones</option>';
    
    // Add zone options
    zones.forEach(zone => {
      const option = document.createElement('option');
      option.value = zone.zone_name;
      option.textContent = zone.zone_name;
      dropdown.appendChild(option);
    });
  }

  async loadTripsData() {
    try {
      const params = this.buildTripsParams();
      const response = await fetch(`${this.apiBase}/trips?${params}`);
      const data = await response.json();
      
      this.data.trips = data;
      this.renderTripsTable(data);
      this.updatePagination(data);
    } catch (error) {
      console.error('Error loading trips:', error);
    }
  }

  buildTripsParams() {
    const params = new URLSearchParams();
    
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const fareAmount = document.getElementById('fare-amount').value;
    const distance = document.getElementById('distance').value;
    const passengers = document.getElementById('passengers').value;
    const pickupZone = document.getElementById('pickup-zone').value;
    const sortBy = document.getElementById('sort-by').value;
    const sortDir = document.getElementById('sort-dir').value;
    
    if (startDate) params.append('start', startDate);
    if (endDate) params.append('end', endDate);
    if (fareAmount) params.append('min_fare', fareAmount);
    if (distance) params.append('min_distance_km', distance);
    if (passengers) params.append('passenger_min', passengers);
    if (pickupZone) params.append('pickup_zone', pickupZone);
    
    params.append('page', this.currentPage);
    params.append('page_size', this.pageSize);
    params.append('sort_by', sortBy);
    params.append('sort_dir', sortDir);
    
    return params.toString();
  }

  updateOverviewMetrics(data) {
    if (!data || !data.overview) {
      console.error('No overview data available');
      return;
    }
    
    const overview = data.overview;
    
    const totalTripsEl = document.getElementById('total-trips');
    const avgSpeedEl = document.getElementById('avg-speed');
    const avgFarePerKmEl = document.getElementById('avg-fare-per-km');
    const avgDurationEl = document.getElementById('avg-duration');
    
    if (totalTripsEl) totalTripsEl.textContent = (overview.total_trips || 0).toLocaleString();
    if (avgSpeedEl) avgSpeedEl.textContent = `${overview.avg_speed_kmh || 0} km/h`;
    if (avgFarePerKmEl) avgFarePerKmEl.textContent = `$${overview.avg_fare_per_km || 0}`;
    if (avgDurationEl) avgDurationEl.textContent = `${overview.avg_duration_minutes || 0} min`;
  }

  renderVendorChart(vendorData) {
    const ctx = document.getElementById('vendorChart');
    if (!ctx) return;

    if (this.charts.vendor) {
      this.charts.vendor.destroy();
    }

    if (!vendorData || vendorData.length === 0) {
      ctx.parentElement.innerHTML = '<p>No vendor data available</p>';
      return;
    }

    this.charts.vendor = new Chart(ctx, {
      type: 'doughnut',
    data: { 
        labels: vendorData.map(v => v.vendor_name || 'Unknown'),
      datasets: [{  
          data: vendorData.map(v => v.trip_count || 0),
          backgroundColor: [
            '#00f0ff',
            '#ffd700',
            '#ff6b6b',
            '#00ff88',
            '#4488ff'
          ],
          borderWidth: 2,
          borderColor: '#1a1a1a'
      }] 
    },
    options: { 
      responsive: true, 
      maintainAspectRatio: false, 
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#b0b0b0',
              font: { size: 12 }
            }
          }
      } 
    }
  });
}

  renderPeakHours(peakHours) {
    const container = document.getElementById('peak-hours');
    if (!container) return;

    container.innerHTML = '';
    if (!peakHours || peakHours.length === 0) {
      container.innerHTML = '<p>No peak hours data available</p>';
      return;
    }

    peakHours.slice(0, 5).forEach((hour, index) => {
      const item = document.createElement('div');
      item.className = 'peak-hour-item';
      item.innerHTML = `
        <span class="peak-hour-time">${hour.hour}:00</span>
        <span class="peak-hour-count">${hour.trip_count} trips</span>
      `;
      container.appendChild(item);
    });
  }

  renderKeyInsights(data) {
    const container = document.getElementById('key-insights');
    if (!container) return;

    const insights = [
      {
        icon: 'fas fa-clock',
        text: `Peak hour is ${data.peak_hours[0]?.hour || 'N/A'}:00 with ${data.peak_hours[0]?.trip_count || 0} trips`
      },
      {
        icon: 'fas fa-building',
        text: `${data.vendor_distribution[0]?.vendor_name || 'N/A'} leads with ${data.vendor_distribution[0]?.market_share || 0}% market share`
      },
      {
        icon: 'fas fa-tachometer-alt',
        text: `Average speed is ${data.overview.avg_speed_kmh} km/h across all trips`
      },
      {
        icon: 'fas fa-dollar-sign',
        text: `Average fare per km is $${data.overview.avg_fare_per_km}`
      }
    ];

    container.innerHTML = '';
    insights.forEach(insight => {
      const item = document.createElement('div');
      item.className = 'insight-item';
      item.innerHTML = `
        <i class="${insight.icon}"></i>
        <span>${insight.text}</span>
      `;
      container.appendChild(item);
    });
  }

  renderSpeedHourlyChart(hourlyPatterns) {
    const ctx = document.getElementById('speedHourlyChart');
  if (!ctx) return;
  
    if (this.charts.speedHourly) {
      this.charts.speedHourly.destroy();
    }

    if (!hourlyPatterns || hourlyPatterns.length === 0) {
      ctx.parentElement.innerHTML = '<p>No hourly speed data available</p>';
      return;
    }

    this.charts.speedHourly = new Chart(ctx, {
      type: 'line',
    data: {
        labels: hourlyPatterns.map(h => `${h.hour}:00`),
      datasets: [{
          label: 'Average Speed (km/h)',
          data: hourlyPatterns.map(h => h.avg_speed_kmh),
          borderColor: '#00f0ff',
          backgroundColor: 'rgba(0, 240, 255, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#b0b0b0' }
          }
        },
      scales: {
        x: { 
          grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#b0b0b0' }
        },
        y: { 
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#b0b0b0' }
        }
      }
    }
  });
}

  renderEfficiencyChart(efficiencyMetrics) {
    const ctx = document.getElementById('efficiencyChart');
  if (!ctx) return;
  
    if (this.charts.efficiency) {
      this.charts.efficiency.destroy();
    }

    this.charts.efficiency = new Chart(ctx, {
      type: 'bar',
    data: {
        labels: ['Fast Trips', 'Slow Trips', 'Normal Trips'],
      datasets: [{
          data: [
            efficiencyMetrics.fast_trips_count,
            efficiencyMetrics.slow_trips_count,
            efficiencyMetrics.total_trips - efficiencyMetrics.fast_trips_count - efficiencyMetrics.slow_trips_count
          ],
          backgroundColor: ['#00ff88', '#ff6b6b', '#00f0ff'],
          borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#b0b0b0' }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#b0b0b0' }
          }
        }
      }
    });
  }

  updateEfficiencyMetrics(metrics) {
    document.getElementById('fast-trips').textContent = metrics.fast_trips_count.toLocaleString();
    document.getElementById('fast-trips-pct').textContent = `${metrics.fast_trips_percentage}%`;
    document.getElementById('slow-trips').textContent = metrics.slow_trips_count.toLocaleString();
    document.getElementById('slow-trips-pct').textContent = `${metrics.slow_trips_percentage}%`;
  }

  renderEfficientZones(zones) {
    const container = document.getElementById('efficient-zones');
    if (!container) return;

    container.innerHTML = '';
    zones.forEach(zone => {
      const item = document.createElement('div');
      item.className = 'efficient-zone-item';
      item.innerHTML = `
        <div class="zone-name">${zone.zone_name}</div>
        <div class="zone-metrics">
          <span>Speed: ${zone.avg_speed_kmh} km/h</span>
          <span>Fare: $${zone.avg_fare_per_km}/km</span>
          <span>Trips: ${zone.trip_count}</span>
        </div>
      `;
      container.appendChild(item);
    });
  }

  renderFareDistanceChart(sampleData) {
    const ctx = document.getElementById('fareDistanceChart');
  if (!ctx) return;
  
    if (this.charts.fareDistance) {
      this.charts.fareDistance.destroy();
    }

    this.charts.fareDistance = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
          label: 'Fare vs Distance',
          data: sampleData.map(d => ({
            x: d.trip_distance_km,
            y: d.fare_amount
          })),
          backgroundColor: 'rgba(255, 215, 0, 0.6)',
          borderColor: '#ffd700',
          borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { 
          labels: { color: '#b0b0b0' }
        }
      },
      scales: {
        x: {
            title: {
              display: true,
              text: 'Distance (km)',
              color: '#b0b0b0'
            },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#b0b0b0' }
        },
        y: {
            title: {
              display: true,
              text: 'Fare ($)',
              color: '#b0b0b0'
            },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#b0b0b0' }
        }
      }
    }
  });
}

  renderFareCategoryChart(fareByDistance) {
    const ctx = document.getElementById('fareCategoryChart');
    if (!ctx) return;

    if (this.charts.fareCategory) {
      this.charts.fareCategory.destroy();
    }

    this.charts.fareCategory = new Chart(ctx, {
      type: 'bar',
    data: { 
        labels: fareByDistance.map(c => c.distance_category),
      datasets: [{ 
          label: 'Average Fare ($)',
          data: fareByDistance.map(c => c.avg_fare),
          backgroundColor: '#00f0ff',
          borderColor: '#00d4e6',
          borderWidth: 1
      }] 
    },
    options: {
      responsive: true, 
      maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#b0b0b0' }
          }
        },
      scales: {
        x: { 
          grid: { color: 'rgba(255,255,255,0.05)' }, 
          ticks: { color: '#b0b0b0' } 
        },
        y: { 
          grid: { color: 'rgba(255,255,255,0.05)' }, 
          ticks: { color: '#b0b0b0' } 
        }
      }
    }
  });
}

  renderFareStatistics(stats) {
    const container = document.getElementById('fare-stats');
    if (!container) return;

    const statItems = [
      { label: 'Avg Fare/KM', value: `$${stats.avg_fare_per_km}` },
      { label: 'Min Fare/KM', value: `$${stats.min_fare_per_km}` },
      { label: 'Max Fare/KM', value: `$${stats.max_fare_per_km}` },
      { label: 'Avg Fare', value: `$${stats.avg_fare_amount}` },
      { label: 'Avg Distance', value: `${stats.avg_distance_km} km` },
      { label: 'Avg Duration', value: `${stats.avg_duration_minutes} min` }
    ];

    container.innerHTML = '';
    statItems.forEach(stat => {
      const item = document.createElement('div');
      item.className = 'stat-item';
      item.innerHTML = `
        <div class="stat-value">${stat.value}</div>
        <div class="stat-label">${stat.label}</div>
      `;
      container.appendChild(item);
    });
  }

  renderVendorPerformance(vendorData) {
    const container = document.getElementById('vendor-performance-grid');
    if (!container) return;

    container.innerHTML = '';
    vendorData.forEach((vendor, index) => {
      const card = document.createElement('div');
      card.className = 'vendor-card';
      card.innerHTML = `
        <div class="vendor-header">
          <div class="vendor-name">${vendor.vendor_name}</div>
          <div class="vendor-rank">#${index + 1}</div>
        </div>
        <div class="vendor-metrics">
          <div class="vendor-metric">
            <div class="vendor-metric-value">${vendor.total_trips}</div>
            <div class="vendor-metric-label">Total Trips</div>
          </div>
          <div class="vendor-metric">
            <div class="vendor-metric-value">${vendor.avg_speed_kmh} km/h</div>
            <div class="vendor-metric-label">Avg Speed</div>
          </div>
          <div class="vendor-metric">
            <div class="vendor-metric-value">$${vendor.avg_fare_per_km}</div>
            <div class="vendor-metric-label">Fare/KM</div>
          </div>
          <div class="vendor-metric">
            <div class="vendor-metric-value">${vendor.avg_duration_minutes} min</div>
            <div class="vendor-metric-label">Avg Duration</div>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  renderZonesMap(zones) {
    const mapContainer = document.getElementById('zones-map');
    if (!mapContainer) {
      console.error('Map container not found');
      return;
    }
    
    console.log('Rendering zones map with data:', zones);
    
    // Clear existing map
    if (this.zonesMap) {
      this.zonesMap.remove();
    }
    
    // Initialize map centered on NYC
    this.zonesMap = L.map('zones-map').setView([40.7128, -74.0060], 11);
    
    // Add dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(this.zonesMap);
    
    // Sort zones by trip count to determine busiest zones
    const sortedZones = [...zones].sort((a, b) => b.count - a.count);
    const busiestZones = sortedZones.slice(0, 20); // Top 20 busiest zones
    
    // Add zone markers with different styles
    zones.forEach((zone, index) => {
      const isBusiest = busiestZones.some(bz => bz.id === zone.id);
      const rank = sortedZones.findIndex(z => z.id === zone.id) + 1;
      
      // Different styling for busiest vs other zones
      const markerStyle = isBusiest ? {
        radius: Math.max(12, Math.min(25, zone.count / 30)), // Larger for busiest
        fillColor: this.getZoneColor(rank - 1),
        color: '#fff',
        weight: 3,
        opacity: 1,
        fillOpacity: 0.9
      } : {
        radius: Math.max(6, Math.min(12, zone.count / 100)), // Smaller for others
        fillColor: '#666666',
        color: '#999999',
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.6
      };
      
      const marker = L.circleMarker([zone.lat, zone.lon], markerStyle).addTo(this.zonesMap);
      
      // Different popup content based on zone type
      const popupContent = isBusiest ? `
        <div style="color: white; font-family: Inter, sans-serif;">
          <h4 style="margin: 0 0 8px 0; color: #00f0ff;">🔥 ${zone.zone}</h4>
          <p style="margin: 4px 0;"><strong>Trip Count:</strong> ${zone.count.toLocaleString()}</p>
          <p style="margin: 4px 0;"><strong>Coordinates:</strong><br>
          Lat: ${zone.lat.toFixed(4)}<br>
          Lon: ${zone.lon.toFixed(4)}</p>
          <p style="margin: 4px 0; font-size: 0.9em; color: #ffd700;">
           Rank: #${rank} busiest zone</p>
        </div>
      ` : `
        <div style="color: white; font-family: Inter, sans-serif;">
          <h4 style="margin: 0 0 8px 0; color: #b0b0b0;">📍 ${zone.zone}</h4>
          <p style="margin: 4px 0;"><strong>Trip Count:</strong> ${zone.count.toLocaleString()}</p>
          <p style="margin: 4px 0;"><strong>Coordinates:</strong><br>
          Lat: ${zone.lat.toFixed(4)}<br>
          Lon: ${zone.lon.toFixed(4)}</p>
          <p style="margin: 4px 0; font-size: 0.9em; color: #808080;">
          Rank: #${rank} overall</p>
        </div>
      `;
      
      marker.bindPopup(popupContent);
    });
    
    // Add legend
    this.addMapLegend();
    
    console.log('Map rendered successfully with', zones.length, 'zones');
  }

  addMapLegend() {
    const legend = L.control({position: 'bottomright'});
    
    legend.onAdd = function(map) {
      const div = L.DomUtil.create('div', 'map-legend');
      div.style.cssText = `
        background: rgba(30, 30, 30, 0.9);
        padding: 12px;
        border-radius: 8px;
        color: white;
        font-family: Inter, sans-serif;
        font-size: 12px;
        border: 1px solid #444;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      `;
      
      div.innerHTML = `
        <div style="margin-bottom: 8px; font-weight: 600; color: #00f0ff;">Zone Types</div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: #00f0ff; border-radius: 50%; margin-right: 8px; border: 2px solid white;"></div>
          <span>🔥 Busiest Zones (Top 20)</span>
        </div>
        <div style="display: flex; align-items: center;">
          <div style="width: 8px; height: 8px; background: #666; border-radius: 50%; margin-right: 8px; border: 1px solid #999;"></div>
          <span>📍 Other Zones</span>
        </div>
        <div style="margin-top: 8px; font-size: 10px; color: #b0b0b0;">
          Marker size indicates trip volume
        </div>
      `;
      
      return div;
    };
    
    legend.addTo(this.zonesMap);
  }

  renderBusiestZones(zones) {
    const container = document.getElementById('busiest-zones');
    if (!container) return;

    container.innerHTML = '';
    zones.slice(0, 10).forEach((zone, index) => {
      const item = document.createElement('div');
      item.className = 'zone-item';
      item.innerHTML = `
        <div class="zone-info">
          <div class="zone-name">${zone.zone}</div>
          <div class="zone-coords">${zone.lat.toFixed(3)}, ${zone.lon.toFixed(3)}</div>
        </div>
        <div class="zone-count">${zone.count.toLocaleString()}</div>
      `;
      container.appendChild(item);
    });
  }

  renderTripsTable(data) {
    const tbody = document.getElementById('trips-tbody');
    const tableInfo = document.getElementById('table-info');
    
    if (!tbody) return;

    tbody.innerHTML = '';
    
    if (data.data && data.data.length > 0) {
      data.data.forEach(trip => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td><span class="trip-id">${trip.id}</span></td>
          <td>${new Date(trip.pickup_datetime).toLocaleString()}</td>
          <td>${Number(trip.trip_distance_km).toFixed(2)} km</td>
          <td>${(trip.trip_duration / 60).toFixed(1)} min</td>
          <td>${Number(trip.trip_speed_kmh).toFixed(1)} km/h</td>
          <td>$${Number(trip.fare_amount).toFixed(2)}</td>
          <td>${trip.passenger_count}</td>
          <td>
            <span class="zone-badge">${trip.pickup_zone || 'N/A'}</span>
            <span class="zone-badge">${trip.dropoff_zone || 'N/A'}</span>
          </td>
          <td>${trip.vendor_name || 'N/A'}</td>
          <td>
            <button class="btn-small" onclick="dashboard.showTripDetails('${trip.id}')">View</button>
          </td>
        `;
        tbody.appendChild(row);
      });
    } else {
      const row = document.createElement('tr');
      row.innerHTML = '<td colspan="10" style="text-align: center; color: #b0b0b0;">No trips found</td>';
      tbody.appendChild(row);
    }

    if (tableInfo) {
      const totalPages = Math.ceil(data.total / this.pageSize);
      tableInfo.textContent = `Page ${data.page} of ${totalPages} • ${data.total.toLocaleString()} total trips`;
    }
  }

  updatePagination(data) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;

    const totalPages = Math.ceil(data.total / this.pageSize);
    
    pagination.innerHTML = `
      <div class="pagination-controls">
        <button class="btn-secondary" ${this.currentPage <= 1 ? 'disabled' : ''} onclick="dashboard.goToPage(1)">
          <i class="fas fa-angle-double-left"></i> First
        </button>
        <button class="btn-secondary" ${this.currentPage <= 1 ? 'disabled' : ''} onclick="dashboard.goToPage(${this.currentPage - 1})">
          <i class="fas fa-angle-left"></i> Prev
        </button>
      </div>
      
      <div class="pagination-info">
        Page ${data.page} of ${totalPages} • ${data.total.toLocaleString()} trips
      </div>
      
      <div class="page-jump">
        <span>Go to:</span>
        <input type="number" id="jump-to-page" min="1" max="${totalPages}" placeholder="Page">
        <button class="btn-secondary" onclick="dashboard.jumpToPage()">Go</button>
      </div>
      
      <div class="pagination-controls">
        <button class="btn-secondary" ${this.currentPage >= totalPages ? 'disabled' : ''} onclick="dashboard.goToPage(${this.currentPage + 1})">
          Next <i class="fas fa-angle-right"></i>
        </button>
        <button class="btn-secondary" ${this.currentPage >= totalPages ? 'disabled' : ''} onclick="dashboard.goToPage(${totalPages})">
          Last <i class="fas fa-angle-double-right"></i>
        </button>
      </div>
    `;
  }

  setupPaginationListeners() {
    // This will be called when pagination is rendered
  }

  goToPage(page) {
    this.currentPage = page;
    this.loadTripsData();
  }

  jumpToPage() {
    const input = document.getElementById('jump-to-page');
    const page = parseInt(input.value);
    if (page && page > 0) {
      this.goToPage(page);
    }
  }

  resetFilters() {
    document.getElementById('start-date').value = '';
    document.getElementById('end-date').value = '';
    document.getElementById('fare-amount').value = '';
    document.getElementById('distance').value = '';
    document.getElementById('passengers').value = '';
    document.getElementById('pickup-zone').value = '';
    document.getElementById('sort-by').value = 'pickup_datetime';
    document.getElementById('sort-dir').value = 'desc';
    document.getElementById('page-size').value = '50';
    
    this.currentPage = 1;
    this.loadTripsData();
  }

  showTripDetails(tripId) {
    const trip = this.data.trips?.data?.find(t => t.id === tripId);
    if (trip) {
      alert(`Trip Details:\n\nID: ${trip.id}\nPickup: ${new Date(trip.pickup_datetime).toLocaleString()}\nDropoff: ${new Date(trip.dropoff_datetime).toLocaleString()}\nDistance: ${trip.trip_distance_km} km\nDuration: ${(trip.trip_duration / 60).toFixed(1)} min\nSpeed: ${trip.trip_speed_kmh} km/h\nFare: $${trip.fare_amount}\nPassengers: ${trip.passenger_count}\nPickup Zone: ${trip.pickup_zone}\nDropoff Zone: ${trip.dropoff_zone}\nVendor: ${trip.vendor_name}`);
    }
  }

  getZoneColor(index) {
  const colors = [
    '#ff4444', '#ffaa00', '#ffd700', '#00ff88', 
    '#00f0ff', '#4488ff', '#ff68ff', '#88ff88'
  ];
  return colors[index % colors.length];
}

  showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
  }

  hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
  }

  showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '20px';
    errorDiv.style.right = '20px';
    errorDiv.style.zIndex = '10000';
    errorDiv.style.maxWidth = '400px';
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }

  async refreshData() {
    this.showLoading();
    try {
      await this.loadInitialData();
      this.hideLoading();
    } catch (error) {
      console.error('Error refreshing data:', error);
      this.showError('Failed to refresh data');
      this.hideLoading();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.dashboard = new UrbanMobilityDashboard();
});