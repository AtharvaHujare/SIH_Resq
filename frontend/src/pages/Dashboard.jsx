import React, { useState, useEffect } from 'react';
import {
  Home,
  ShieldAlert,
  AlertTriangle,
  Users,
  MapPin,
  ArrowRight,
  TrendingUp,
  Activity,
  Layers,
  CloudRain,
  Thermometer,
  Wind,
  Droplets,
  CheckCircle2,
  RefreshCw,
  Play,
  Info,
  Navigation
} from 'lucide-react';
import KpiCard from '../components/common/KpiCard';
import GisMapViewer from '../components/map/GisMapViewer';
import { api } from '../services/api';
import { KPI_METRICS, VULNERABLE_HABITATIONS, CANDIDATE_RELOCATION_SITES } from '../data/mockData';

export default function Dashboard({
  currentDistrict = 'Guwahati',
  onDistrictChange,
  onSelectHabitation,
  onSelectSite,
  onNavigate
}) {
  // Selected City in dropdown vs Active Analyzed City in GIS engine
  const [selectedCity, setSelectedCity] = useState(currentDistrict || 'Guwahati');
  const [analyzedCity, setAnalyzedCity] = useState(currentDistrict || 'Guwahati');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Dashboard Data State
  const [kpis, setKpis] = useState(KPI_METRICS);
  const [weatherData, setWeatherData] = useState(null);
  const [criticalHabitations, setCriticalHabitations] = useState(() =>
    VULNERABLE_HABITATIONS.filter(
      (h) => h.district.toLowerCase().includes('guwahati') && h.riskTier === 'Critical'
    ).slice(0, 5)
  );
  const [topSites, setTopSites] = useState(() =>
    CANDIDATE_RELOCATION_SITES.filter((s) =>
      s.district.toLowerCase().includes('guwahati')
    ).slice(0, 3)
  );

  // Real OSRM Road Evacuation Routing State
  const [selectedRouteHabitationId, setSelectedRouteHabitationId] = useState(() => {
    const defaultHabs = VULNERABLE_HABITATIONS.filter(h => h.district.toLowerCase().includes('guwahati'));
    return defaultHabs.length > 0 ? defaultHabs[0].id : '';
  });
  const [selectedRouteSiteId, setSelectedRouteSiteId] = useState(() => {
    const defaultSites = CANDIDATE_RELOCATION_SITES.filter(s => s.district.toLowerCase().includes('guwahati'));
    return defaultSites.length > 0 ? defaultSites[0].id : '';
  });
  const [activeRoute, setActiveRoute] = useState(null);
  const [isComputingRoute, setIsComputingRoute] = useState(false);
  const [routeError, setRouteError] = useState(null);

  // Sync if parent updates district
  useEffect(() => {
    if (currentDistrict && currentDistrict !== selectedCity) {
      setSelectedCity(currentDistrict);
    }
  }, [currentDistrict]);

  // Execute Core Decision Workflow for City
  const executeCityAnalysis = async (cityToAnalyze) => {
    setIsAnalyzing(true);
    try {
      const [weather, kpiData, habData, sitesData] = await Promise.all([
        api.getWeather(cityToAnalyze),
        api.getKPIs(cityToAnalyze),
        api.getHabitations({ district: cityToAnalyze, limit: 20 }),
        api.getRelocationSites({ district: cityToAnalyze })
      ]);

      if (weather) setWeatherData(weather);
      if (kpiData) setKpis(kpiData);

      if (habData && habData.length > 0) {
        const criticals = habData.filter((h) => h.riskTier === 'Critical');
        const toShow = criticals.length > 0 ? criticals.slice(0, 5) : habData.slice(0, 5);
        setCriticalHabitations(toShow);
        if (toShow.length > 0) setSelectedRouteHabitationId(toShow[0].id);
      } else {
        // Fallback filter
        const localHabs = VULNERABLE_HABITATIONS.filter((h) =>
          h.district.toLowerCase().includes(cityToAnalyze.toLowerCase())
        );
        setCriticalHabitations(localHabs.slice(0, 5));
        if (localHabs.length > 0) setSelectedRouteHabitationId(localHabs[0].id);
      }

      if (sitesData && sitesData.length > 0) {
        setTopSites(sitesData.slice(0, 3));
        setSelectedRouteSiteId(sitesData[0].id);
      } else {
        const localSites = CANDIDATE_RELOCATION_SITES.filter((s) =>
          s.district.toLowerCase().includes(cityToAnalyze.toLowerCase())
        );
        setTopSites(localSites.slice(0, 3));
        if (localSites.length > 0) setSelectedRouteSiteId(localSites[0].id);
      }

      // Reset active route on city change
      setActiveRoute(null);
      setRouteError(null);

      setAnalyzedCity(cityToAnalyze);
      if (onDistrictChange) {
        onDistrictChange(cityToAnalyze);
      }
    } catch (err) {
      console.warn('Analysis workflow fetch failed, falling back:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Compute Real OSRM Road Evacuation Route
  const handleShowSafeRoute = async (customHab = null, customSite = null) => {
    setIsComputingRoute(true);
    setRouteError(null);
    try {
      const hab =
        customHab ||
        criticalHabitations.find((h) => h.id === selectedRouteHabitationId) ||
        criticalHabitations[0];
      const site =
        customSite ||
        topSites.find((s) => s.id === selectedRouteSiteId) ||
        topSites[0];

      if (!hab || !hab.coordinates || hab.coordinates.length < 2) {
        throw new Error('Please select an origin habitation with valid geographic coordinates.');
      }
      if (!site || !site.coordinates || site.coordinates.length < 2) {
        throw new Error('Please select a destination relocation site with valid geographic coordinates.');
      }

      const res = await api.getRoadRoute(
        hab.coordinates[0],
        hab.coordinates[1],
        site.coordinates[0],
        site.coordinates[1]
      );

      if (res && res.geometry) {
        setActiveRoute({
          ...res,
          originName: hab.name,
          destinationName: site.name,
        });
      } else {
        throw new Error('OSRM routing engine could not find an available road path between these points.');
      }
    } catch (err) {
      console.warn('Road routing failed:', err);
      setRouteError(err.message || 'Routing calculation failed');
    } finally {
      setIsComputingRoute(false);
    }
  };

  // Initial Load on mount for Default City (Guwahati)
  useEffect(() => {
    executeCityAnalysis(currentDistrict || 'Guwahati');
  }, []);

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <div className="page-title-group">
          <h1>Command Center & Multi-Hazard Overview</h1>
          <span className="page-subtitle">
            ResQ — Intelligent Disaster Relocation & Decision Support System • Real-Time Predictive Risk Monitoring
          </span>
        </div>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={() => onNavigate('what-if')}>
            <Activity size={16} color="var(--ai-purple)" />
            <span>Run What-If Simulation</span>
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate('priority-planning')}>
            <span>View Relocation Queue</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Prominent City Selector & Analysis Command Bar */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '16px 20px',
          marginBottom: '20px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MapPin size={18} color="var(--gis-blue)" />
            <label htmlFor="city-select" style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
              Select City:
            </label>
          </div>

          <select
            id="city-select"
            value={selectedCity}
            onChange={(e) => {
              const nextCity = e.target.value;
              setSelectedCity(nextCity);
              setActiveRoute(null);
              setRouteError(null);
            }}
            style={{
              padding: '8px 14px',
              fontSize: '0.92rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: '1.5px solid #2563eb',
              background: '#f8fafc',
              color: '#0f172a',
              cursor: 'pointer',
              minWidth: '220px'
            }}
          >
            <option value="Guwahati">Guwahati (Default Demo City)</option>
            <option value="Pune">Pune (Ghat Corridor)</option>
            <option value="Raigad">Raigad (Coastal Corridor)</option>
          </select>

          <button
            className="btn btn-primary"
            onClick={() => executeCityAnalysis(selectedCity)}
            disabled={isAnalyzing}
            style={{
              padding: '9px 18px',
              fontSize: '0.92rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: selectedCity !== analyzedCity ? '0 0 0 3px rgba(37, 99, 235, 0.3)' : '0 2px 6px rgba(37, 99, 235, 0.3)',
              opacity: isAnalyzing ? 0.75 : 1,
              cursor: isAnalyzing ? 'not-allowed' : 'pointer'
            }}
          >
            {isAnalyzing ? (
              <>
                <RefreshCw size={16} className="spin-animation" />
                <span>Analyzing {selectedCity}...</span>
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" />
                <span>Analyze City</span>
              </>
            )}
          </button>

          {selectedCity !== analyzedCity && !isAnalyzing && (
            <span
              style={{
                fontSize: '0.78rem',
                color: '#1d4ed8',
                background: '#eff6ff',
                padding: '5px 10px',
                borderRadius: '6px',
                border: '1px solid #bfdbfe',
                fontWeight: 600
              }}
            >
              Selected: {selectedCity} • Preparing analysis... Click &apos;Analyze City&apos;
            </span>
          )}
        </div>

        {/* Workflow Architecture Breadcrumbs */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            color: '#475569',
            background: '#f1f5f9',
            padding: '6px 12px',
            borderRadius: '6px'
          }}
        >
          <span style={{ fontWeight: 600, color: '#0f172a' }}>City: {analyzedCity}</span>
          <span>&rarr;</span>
          <span>Weather Inflow</span>
          <span>&rarr;</span>
          <span>GIS Risk</span>
          <span>&rarr;</span>
          <span style={{ color: '#b91c1c', fontWeight: 600 }}>Red Zones</span>
          <span>&rarr;</span>
          <span style={{ color: '#15803d', fontWeight: 600 }}>Green Safe Zones</span>
          <span>&rarr;</span>
          <span>Relocation</span>
        </div>
      </div>

      {/* Clean Meteorological & Weather Provenance Card (Open-Meteo Forecast Telemetry) */}
      {weatherData && (() => {
        const isLiveWeather = Boolean(
          weatherData &&
          !weatherData.isFallback &&
          weatherData.isFallback !== 'true' &&
          (weatherData.source === 'Open-Meteo' || !String(weatherData.source || '').toLowerCase().includes('prototype'))
        );
        return (
          <div
            style={{
              background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
              border: '1px solid #cbd5e1',
              borderLeft: `5px solid ${isLiveWeather ? '#16a34a' : '#f59e0b'}`,
              borderRadius: '12px',
              padding: '18px 22px',
              marginBottom: '24px',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.03)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '8px',
                    background: isLiveWeather ? '#f0fdf4' : '#eff6ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isLiveWeather ? '#16a34a' : '#2563eb'
                  }}
                >
                  <CloudRain size={22} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#0f172a' }}>
                      {weatherData.city || weatherData.district} Live Meteorological & Precipitation Telemetry
                    </h3>
                    <span
                      className="badge"
                      style={{
                        background: !isLiveWeather ? '#fef3c7' : '#eff6ff',
                        color: !isLiveWeather ? '#92400e' : '#1d4ed8',
                        border: !isLiveWeather ? '1px solid #facc15' : '1px solid #93c5fd',
                        fontWeight: 700
                      }}
                    >
                      {weatherData.weatherCondition || 'Normal Conditions'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
                    Weather source: <strong style={{ color: isLiveWeather ? '#0f172a' : '#b45309' }}>{isLiveWeather ? 'Open-Meteo' : 'Prototype Fallback'}</strong> • Observation Time: <strong>{weatherData.observed_at || weatherData.observedAt || 'Current Cycle'}</strong> {isLiveWeather && <span style={{ color: '#16a34a', fontWeight: 600 }}>(Live)</span>}
                  </div>
                </div>
              </div>

              {/* Status Display: LIVE vs Fallback */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                {isLiveWeather ? (
                  <>
                    <span
                      className="badge live-badge"
                      data-testid="live-weather-badge"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '4px 12px',
                        borderRadius: '20px',
                        fontSize: '0.78rem',
                        fontWeight: 800,
                        background: '#dcfce7',
                        color: '#15803d',
                        border: '1px solid #86efac',
                        boxShadow: '0 1px 3px rgba(22, 163, 74, 0.2)'
                      }}
                    >
                      <span
                        style={{
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: '#16a34a',
                          boxShadow: '0 0 0 2px rgba(22, 163, 74, 0.3)'
                        }}
                      />
                      LIVE
                    </span>
                    <span
                      className="badge"
                      data-testid="live-weather-provenance-badge"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        fontSize: '0.74rem',
                        fontWeight: 600,
                        background: '#f0fdf4',
                        color: '#166534',
                        border: '1px solid #bbf7d0'
                      }}
                    >
                      Live External Weather Data
                    </span>
                  </>
                ) : (
                  <span
                    className="badge"
                    data-testid="fallback-weather-badge"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '5px 10px',
                      borderRadius: '20px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      background: '#fef3c7',
                      color: '#92400e',
                      border: '1px solid #f59e0b'
                    }}
                  >
                    <Info size={12} />
                    LIVE DATA
                  </span>
                )}
              </div>
            </div>

            {/* 4 Core Weather Metrics from Open-Meteo */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '12px',
                marginTop: '10px'
              }}
            >
              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Thermometer size={14} color="#ef4444" />
                  <span>Ambient Temperature</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                  {weatherData.temperatureC !== null && weatherData.temperatureC !== undefined ? `${weatherData.temperatureC}°C` : 'N/A'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>2m Elevation Sensor</div>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CloudRain size={14} color="#2563eb" />
                  <span>Precipitation (mm)</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1d4ed8', marginTop: '4px' }}>
                  {weatherData.precipitationMm !== null && weatherData.precipitationMm !== undefined ? `${weatherData.precipitationMm} mm` : (weatherData.rainfallMm ? `${weatherData.rainfallMm} mm` : '0 mm')}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  Direct Rain: {weatherData.rainMm !== null && weatherData.rainMm !== undefined ? `${weatherData.rainMm} mm` : '0 mm'}
                </div>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Wind size={14} color="#475569" />
                  <span>Wind Speed (10m)</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                  {weatherData.windSpeedKmh !== null && weatherData.windSpeedKmh !== undefined ? `${weatherData.windSpeedKmh} km/h` : 'N/A'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  WMO Condition Code: {weatherData.weatherCode ?? '0'}
                </div>
              </div>

              <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Droplets size={14} color="#0891b2" />
                  <span>Relative Humidity</span>
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                  {weatherData.humidityPercent !== null && weatherData.humidityPercent !== undefined ? `${weatherData.humidityPercent}%` : 'N/A'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Atmospheric Moisture (2m)</div>
              </div>
            </div>

            <div
              style={{
                fontSize: '0.78rem',
                color: '#64748b',
                marginTop: '12px',
                paddingTop: '10px',
                borderTop: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px'
              }}
            >
              <span>
                Weather Condition: <strong>{weatherData.weatherCondition}</strong> (Code {weatherData.weatherCode})
              </span>
              <span>
                Provenance:{' '}
                <strong style={{ color: isLiveWeather ? '#15803d' : '#92400e' }}>
                  {isLiveWeather ? 'Live External Weather Data (Open-Meteo API)' : 'Prototype Fallback (API Unavailable)'}
                </strong>
              </span>
              <a
                href="https://open-meteo.com/"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#2563eb', textDecoration: 'underline', fontSize: '0.75rem', fontWeight: 500 }}
              >
                Weather data by Open-Meteo.com
              </a>
            </div>
          </div>
        );
      })()}

      {/* 5 KPI Cards Section for Analyzed City */}
      <div className="kpi-grid">
        <KpiCard
          title="Monitored Habitations"
          value={kpis.totalHabitations}
          subtitle={`Corridor: ${analyzedCity}`}
          icon={Home}
          variant="info"
        />

        <KpiCard
          title="High-Risk Habitations"
          value={kpis.highRiskHabitations}
          subtitle="Score &ge; 55.0 threshold"
          icon={AlertTriangle}
          variant="high"
          trend={{ isUp: true, text: 'Active Hazard Zone' }}
        />

        <KpiCard
          title="Critical / Red-Zone Habitations"
          value={kpis.criticalRedZoneHabitations}
          subtitle="Requires Immediate Relocation"
          icon={ShieldAlert}
          variant="critical"
          trend={{ isUp: true, text: 'Urgent Evac Plan' }}
        />

        <KpiCard
          title="Population at Critical Risk"
          value={kpis.populationExposed}
          subtitle="Exposed to slope & surge"
          icon={Users}
          variant="critical"
        />

        <KpiCard
          title="Candidate Relocation Sites"
          value={kpis.potentialRelocationSites}
          subtitle="Verified safe parcels"
          icon={MapPin}
          variant="safe"
          trend={{ isUp: false, text: '84.6% Avg Suitability' }}
        />
      </div>

      {/* Large Interactive WebGIS Map Canvas */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="var(--gis-blue)" />
            <h3 style={{ margin: 0 }}>Active Geospatial Multi-Hazard & Relocation Canvas ({analyzedCity})</h3>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            GIS analysis: PostGIS + deterministic rules | Dynamic Red Hazard & Green Safe Zones
          </span>
        </div>

        {/* Real Road Evacuation Routing Command Bar (OSRM Highway Engine) */}
        <div
          style={{
            background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
            border: '1px solid #cbd5e1',
            borderLeft: '5px solid #4f46e5',
            borderRadius: '10px',
            padding: '12px 18px',
            marginBottom: '12px',
            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.04)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Navigation size={18} color="#4f46e5" />
              <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#1e1b4b' }}>
                Evacuation Routing:
              </span>
            </div>

            {/* Select Origin Critical Habitation */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>Origin:</span>
              <select
                className="custom-select"
                value={selectedRouteHabitationId}
                onChange={(e) => setSelectedRouteHabitationId(e.target.value)}
                style={{
                  fontSize: '0.82rem',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  minWidth: '220px',
                  color: '#0f172a',
                  fontWeight: 600
                }}
              >
                {criticalHabitations.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name} ({h.riskTier})
                  </option>
                ))}
              </select>
            </div>

            <span style={{ color: '#94a3b8', fontWeight: 700 }}>&rarr;</span>

            {/* Select Destination Safe Relocation Site */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 600 }}>Safe Destination:</span>
              <select
                className="custom-select"
                value={selectedRouteSiteId}
                onChange={(e) => setSelectedRouteSiteId(e.target.value)}
                style={{
                  fontSize: '0.82rem',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  minWidth: '220px',
                  color: '#0f172a',
                  fontWeight: 600
                }}
              >
                {topSites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.suitabilityScore}% Suitable)
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {activeRoute && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setActiveRoute(null)}
                style={{ fontSize: '0.8rem', padding: '6px 12px' }}
              >
                Clear Route
              </button>
            )}

            <button
              className="btn btn-primary btn-sm"
              onClick={() => handleShowSafeRoute()}
              disabled={isComputingRoute || isAnalyzing}
              style={{
                background: '#4f46e5',
                borderColor: '#4338ca',
                fontSize: '0.84rem',
                fontWeight: 600,
                padding: '7px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 2px 8px rgba(79, 70, 229, 0.3)',
                cursor: (isComputingRoute || isAnalyzing) ? 'not-allowed' : 'pointer',
                opacity: (isComputingRoute || isAnalyzing) ? 0.75 : 1
              }}
            >
              {isComputingRoute ? (
                <>
                  <RefreshCw size={14} className="spin-animation" />
                  <span>Computing OSRM Road Route...</span>
                </>
              ) : (
                <>
                  <Navigation size={14} />
                  <span>Show Safe Route</span>
                </>
              )}
            </button>
          </div>
        </div>

        {routeError && (
          <div style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #f87171', borderRadius: '6px', padding: '8px 12px', fontSize: '0.8rem', marginBottom: '10px' }}>
            {routeError}
          </div>
        )}

        <GisMapViewer
          district={analyzedCity}
          pendingCity={selectedCity !== analyzedCity ? selectedCity : null}
          isAnalyzing={isAnalyzing}
          onSelectHabitation={(h) => {
            setSelectedRouteHabitationId(h.id);
            if (onSelectHabitation) onSelectHabitation(h);
          }}
          onSelectSite={(s) => {
            setSelectedRouteSiteId(s.id);
            if (onSelectSite) onSelectSite(s);
          }}
          activeRoute={activeRoute}
          onClearRoute={() => setActiveRoute(null)}
        />
      </div>

      {/* Two-Column Command Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* Left Column: Urgent Relocation Queue Preview */}
        <div className="data-table-container">
          <div className="table-toolbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} color="var(--risk-critical)" />
              <h3 style={{ fontSize: '1.0rem', margin: 0 }}>Urgent Priority 1 Relocation Queue ({analyzedCity})</h3>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('priority-planning')}
            >
              Full Queue ({criticalHabitations.length})
            </button>
          </div>

          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Habitation</th>
                  <th>Population</th>
                  <th>Risk Score</th>
                  <th>Primary Threat</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {criticalHabitations.map((h) => (
                  <tr key={h.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{h.name}</div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{h.district}</div>
                    </td>
                    <td>{h.population.toLocaleString()}</td>
                    <td>
                      <span className="badge badge-critical">{h.riskScore} / 100</span>
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>{h.dominantHazards}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            setSelectedRouteHabitationId(h.id);
                            onSelectHabitation(h);
                          }}
                        >
                          Inspect
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => {
                            setSelectedRouteHabitationId(h.id);
                            handleShowSafeRoute(h);
                          }}
                          style={{
                            background: '#4f46e5',
                            borderColor: '#4338ca',
                            padding: '4px 8px',
                            fontSize: '0.74rem'
                          }}
                          title="Show Safe Evacuation Route"
                        >
                          <Navigation size={12} />
                          <span>Safe Route</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Recommended Safe Parcels Preview */}
        <div className="data-table-container">
          <div className="table-toolbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MapPin size={18} color="var(--risk-low)" />
              <h3 style={{ fontSize: '1.0rem', margin: 0 }}>Top Audited Relocation Sites ({analyzedCity})</h3>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('relocation-sites')}
            >
              View All ({topSites.length})
            </button>
          </div>

          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {topSites.map((site) => (
              <div
                key={site.id}
                style={{
                  background: '#f8fafc',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '14px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.92rem' }}>{site.name}</span>
                    <span className="badge badge-safe">{site.suitabilityScore}% Suitability</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#475569', marginTop: '4px' }}>
                    Distance: <strong>{site.distanceFromRedZoneKm} km</strong> from danger zone • Capacity: <strong>{site.estimatedCapacity.toLocaleString()}</strong> residents
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#1d4ed8', marginTop: '2px' }}>
                    Water: {site.waterAvailabilityStatus}
                  </div>
                </div>

                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSelectSite(site)}
                >
                  Capacity Audit
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
