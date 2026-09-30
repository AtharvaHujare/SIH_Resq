// ==============================================================================
// Frontend Service Layer - SIH 2026 PS ID 191
// Seamless API Integration with Resilient Fallback to Mock Data
// Backend Base URL: http://127.0.0.1:8000/api/v1
// ==============================================================================

import {
  KPI_METRICS,
  DISTRICT_PROFILES,
  VULNERABLE_HABITATIONS,
  CANDIDATE_RELOCATION_SITES,
  RED_ZONES,
  RECENT_SYSTEM_ALERTS,
  RISK_ANALYTICS_DATA
} from '../data/mockData';

const BASE_URL = 'http://127.0.0.1:8000/api/v1';
const REQUEST_TIMEOUT_MS = 5000;
const apiCache = new Map();
const DEFAULT_TTL_MS = 120000; // 2 minutes

/**
 * Robust fetch wrapper with in-memory caching, timeout, status checking, and automatic fallback.
 */
async function fetchWithFallback(endpoint, options = {}, fallbackData, customTtl = null) {
  const method = (options.method || 'GET').toUpperCase();
  const url = `${BASE_URL}${endpoint}`;
  const ttl = customTtl !== null ? customTtl : DEFAULT_TTL_MS;
  const isWeatherEndpoint = endpoint.startsWith('/weather');

  // Serve from in-memory cache for GET requests (excluding weather to ensure 100% fresh telemetry on Analyze City)
  if (method === 'GET' && !isWeatherEndpoint && customTtl !== 0) {
    const cached = apiCache.get(url);
    if (cached && Date.now() - cached.timestamp < cached.ttl) {
      return cached.data;
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.warn(`[API Warning] ${method} ${url} responded with HTTP ${response.status}. Using fallback.`);
      return typeof fallbackData === 'function' ? fallbackData() : fallbackData;
    }

    const data = await response.json();
    if (method === 'GET' && !isWeatherEndpoint && customTtl !== 0) {
      apiCache.set(url, { data, timestamp: Date.now(), ttl });
    }
    return data;
  } catch (err) {
    clearTimeout(timeoutId);
    console.warn(`[API Network Fallback] Request to ${endpoint} failed (${err.name}: ${err.message}). Using local fallback.`);
    return typeof fallbackData === 'function' ? fallbackData() : fallbackData;
  }
}

export const api = {
  // 0. Real-World Weather & Rainfall Telemetry from Open-Meteo API (Always Fresh, No Stale Cache)
  async getWeather(district = 'Guwahati') {
    const cleanDist = district && district !== 'All' ? district : 'Guwahati';
    return fetchWithFallback(
      `/weather?city=${encodeURIComponent(cleanDist)}&_t=${Date.now()}`,
      { method: 'GET' },
      () => {
        const nowTs = new Date().toISOString().slice(0, 16);
        const fallbacks = {
          guwahati: {
            city: 'Guwahati',
            district: 'Guwahati',
            temperatureC: 28.4,
            precipitationMm: 0.0,
            rainMm: 0.0,
            humidityPercent: 86,
            windSpeedKmh: 18.0,
            weatherCode: 63,
            weatherCondition: 'Moderate Rain',
            observedAt: nowTs,
            observed_at: nowTs,
            source: 'Prototype Baseline',
            provenance: 'Weather unavailable — Prototype / Demo fallback',
            isFallback: true,
            attribution: 'Weather data by Open-Meteo.com'
          },
          pune: {
            city: 'Pune',
            district: 'Pune',
            temperatureC: 24.2,
            precipitationMm: 0.0,
            rainMm: 0.0,
            humidityPercent: 78,
            windSpeedKmh: 22.5,
            weatherCode: 3,
            weatherCondition: 'Overcast',
            observedAt: nowTs,
            observed_at: nowTs,
            source: 'Prototype Baseline',
            provenance: 'Weather unavailable — Prototype / Demo fallback',
            isFallback: true,
            attribution: 'Weather data by Open-Meteo.com'
          },
          raigad: {
            city: 'Raigad',
            district: 'Raigad',
            temperatureC: 26.5,
            precipitationMm: 0.0,
            rainMm: 0.0,
            humidityPercent: 92,
            windSpeedKmh: 26.0,
            weatherCode: 65,
            weatherCondition: 'Heavy Rain',
            observedAt: nowTs,
            observed_at: nowTs,
            source: 'Prototype Baseline',
            provenance: 'Weather unavailable — Prototype / Demo fallback',
            isFallback: true,
            attribution: 'Weather data by Open-Meteo.com'
          }
        };
        const key = cleanDist.toLowerCase().includes('pune') ? 'pune' : cleanDist.toLowerCase().includes('raigad') ? 'raigad' : 'guwahati';
        return fallbacks[key];
      },
      0 // 0 TTL disables caching for weather so each city analysis is 100% fresh
    );
  },

  // 0b. Real-World Road Evacuation Route from OSRM Engine
  async getRoadRoute(fromLat, fromLon, toLat, toLon) {
    const params = new URLSearchParams({
      from_lat: String(fromLat),
      from_lon: String(fromLon),
      to_lat: String(toLat),
      to_lon: String(toLon),
    });
    return fetchWithFallback(
      `/routing/route?${params.toString()}`,
      { method: 'GET' },
      () => ({
        status: 'fallback',
        source: 'OSRM/OpenStreetMap',
        distance_km: 16.93,
        distanceKm: 16.93,
        duration_minutes: 26.0,
        durationMinutes: 26.0,
        geometry: null,
      })
    );
  },

  // 1. Headline KPI Summary Metrics
  async getKPIs(district = null) {
    const query = district && district !== 'All' ? `?district=${encodeURIComponent(district)}` : '';
    return fetchWithFallback(
      `/analytics/kpis${query}`,
      { method: 'GET' },
      () => {
        let metrics = { ...KPI_METRICS };
        if (district && district !== 'All') {
          const habs = VULNERABLE_HABITATIONS.filter(h => h.district.toLowerCase().includes(district.toLowerCase()));
          if (habs.length > 0) {
            metrics.totalHabitations = habs.length;
            metrics.highRiskHabitations = habs.filter(h => h.riskScore >= 55).length;
            metrics.criticalRedZoneHabitations = habs.filter(h => h.riskTier === 'Critical').length;
            metrics.populationExposed = habs.filter(h => h.riskScore >= 55).reduce((acc, h) => acc + h.population, 0);
            metrics.immediateRelocationQueue = habs.filter(h => h.priority === 1).length;
          }
        }
        return metrics;
      }
    );
  },

  // 2. Vulnerable Habitations with Multi-Criteria Filtering
  async getHabitations(filters = {}) {
    const params = new URLSearchParams();
    if (filters.searchQuery) params.append('search', filters.searchQuery);
    if (filters.district && filters.district !== 'All') params.append('district', filters.district);
    if (filters.riskTier && filters.riskTier !== 'All') params.append('risk_tier', filters.riskTier);
    if (filters.priority && filters.priority !== 'All') params.append('priority', filters.priority);
    if (filters.sortBy) params.append('sort_by', filters.sortBy);
    params.append('limit', '100');

    const queryString = params.toString() ? `?${params.toString()}` : '';

    return fetchWithFallback(
      `/habitations${queryString}`,
      { method: 'GET' },
      () => {
        let result = [...VULNERABLE_HABITATIONS];
        if (filters.district && filters.district !== 'All') {
          result = result.filter(h => h.district.toLowerCase().includes(filters.district.toLowerCase()));
        }
        if (filters.riskTier && filters.riskTier !== 'All') {
          result = result.filter(h => h.riskTier.toLowerCase() === filters.riskTier.toLowerCase());
        }
        if (filters.priority && filters.priority !== 'All') {
          result = result.filter(h => String(h.priority) === String(filters.priority));
        }
        if (filters.searchQuery) {
          const q = filters.searchQuery.toLowerCase().trim();
          result = result.filter(h =>
            h.name.toLowerCase().includes(q) ||
            h.district.toLowerCase().includes(q) ||
            h.dominantHazards.toLowerCase().includes(q)
          );
        }
        if (filters.sortBy) {
          if (filters.sortBy === 'riskScore') result.sort((a, b) => b.riskScore - a.riskScore);
          else if (filters.sortBy === 'population') result.sort((a, b) => b.population - a.population);
          else if (filters.sortBy === 'priority') result.sort((a, b) => a.priority - b.priority);
        }
        return result;
      }
    );
  },

  // 3. Habitation by ID
  async getHabitationById(id) {
    return fetchWithFallback(
      `/habitations/${encodeURIComponent(id)}`,
      { method: 'GET' },
      () => {
        const habitation = VULNERABLE_HABITATIONS.find(h => h.id === id);
        if (!habitation) throw new Error(`Habitation ${id} not found`);
        return { ...habitation };
      }
    );
  },

  // 4. Candidate Relocation Sites
  async getRelocationSites(filters = {}) {
    const params = new URLSearchParams();
    if (filters.searchQuery) params.append('search', filters.searchQuery);
    if (filters.district && filters.district !== 'All') params.append('district', filters.district);
    if (filters.minSuitability) params.append('min_suitability', filters.minSuitability);
    if (filters.minCapacity) params.append('min_capacity', filters.minCapacity);

    const queryString = params.toString() ? `?${params.toString()}` : '';

    return fetchWithFallback(
      `/relocation-sites${queryString}`,
      { method: 'GET' },
      () => {
        let result = [...CANDIDATE_RELOCATION_SITES];
        if (filters.district && filters.district !== 'All') {
          result = result.filter(s => s.district.toLowerCase().includes(filters.district.toLowerCase()));
        }
        if (filters.minSuitability) {
          result = result.filter(s => s.suitabilityScore >= Number(filters.minSuitability));
        }
        if (filters.minCapacity) {
          result = result.filter(s => s.estimatedCapacity >= Number(filters.minCapacity));
        }
        if (filters.searchQuery) {
          const q = filters.searchQuery.toLowerCase().trim();
          result = result.filter(s =>
            s.name.toLowerCase().includes(q) ||
            s.district.toLowerCase().includes(q) ||
            s.overallRecommendation.toLowerCase().includes(q)
          );
        }
        return result;
      }
    );
  },

  // 5. Candidate Site by ID
  async getRelocationSiteById(id) {
    return fetchWithFallback(
      `/relocation-sites/${encodeURIComponent(id)}`,
      { method: 'GET' },
      () => {
        const site = CANDIDATE_RELOCATION_SITES.find(s => s.id === id);
        if (!site) throw new Error(`Site ${id} not found`);
        return { ...site };
      }
    );
  },

  // 6. Red Zones Polygons
  async getRedZones(district = null) {
    const query = district && district !== 'All' ? `?district=${encodeURIComponent(district)}` : '';
    return fetchWithFallback(
      `/hazards/red-zones${query}`,
      { method: 'GET' },
      () => [...RED_ZONES]
    );
  },

  // 6b. Dynamic Green / Safe Zones (GeoJSON FeatureCollection)
  async getSafeZones(district = null) {
    const query = district && district !== 'All' ? `?district=${encodeURIComponent(district)}` : '';
    return fetchWithFallback(
      `/hazards/safe-zones${query}`,
      { method: 'GET' },
      () => ({
        type: 'FeatureCollection',
        features: [],
        metadata: {
          totalSafeZones: 0,
          district: district || 'All',
          calculationMode: 'PROTOTYPE_FALLBACK',
          fallbackUsed: true,
          statusMessage: 'Prototype fallback active'
        }
      })
    );
  },

  // 6c. Authoritative Ingestion & Provenance Status
  async getIngestionStatus() {
    return fetchWithFallback(
      '/ingestion/status',
      { method: 'GET' },
      () => ({
        status: 'operational',
        databaseConnected: false,
        dataProvenanceMode: 'IN_MEMORY_PROTOTYPE_FALLBACK',
        summary: { weatherObservationsCount: 0, rainfallObservationsCount: 0, infrastructureFeaturesCount: 0 },
        sources: []
      })
    );
  },

  // 7. District Profiles
  async getDistrictProfiles() {
    return fetchWithFallback(
      '/districts',
      { method: 'GET' },
      () => [...DISTRICT_PROFILES]
    );
  },

  // 8. Early Warning Alerts
  async getRecentAlerts(unreadOnly = false) {
    const query = unreadOnly ? '?unread_only=true' : '';
    return fetchWithFallback(
      `/alerts${query}`,
      { method: 'GET' },
      () => [...RECENT_SYSTEM_ALERTS]
    );
  },

  // 8b. Mark All Alerts Read
  async markAllAlertsRead() {
    return fetchWithFallback(
      '/alerts/mark-all-read',
      { method: 'POST' },
      () => ({ success: true, markedCount: RECENT_SYSTEM_ALERTS.length })
    );
  },

  // 9. Risk Analytics Matrix
  async getRiskAnalytics(district = null) {
    const query = district && district !== 'All' ? `?district=${encodeURIComponent(district)}` : '';
    return fetchWithFallback(
      `/analytics/risk-distribution${query}`,
      { method: 'GET' },
      () => ({ ...RISK_ANALYTICS_DATA })
    );
  },

  // 10. Relocation Priority Queue
  async getPriorityQueue(tierFilter = 'All') {
    const query = tierFilter && tierFilter !== 'All' ? `?tier=${encodeURIComponent(tierFilter)}` : '';
    return fetchWithFallback(
      `/prioritization/queue${query}`,
      { method: 'GET' },
      () => {
        let habitations = [...VULNERABLE_HABITATIONS].sort((a, b) => a.priority - b.priority || b.riskScore - a.riskScore);
        if (tierFilter !== 'All') {
          habitations = habitations.filter(h => String(h.priority) === String(tierFilter));
        }
        return habitations.map(h => {
          const recommendedSite = CANDIDATE_RELOCATION_SITES.find(s => s.id === h.recommendedSiteId);
          return { ...h, recommendedSite };
        });
      }
    );
  },

  // 11. What-If Parametric Policy Simulation
  async simulateWhatIf(params = {}) {
    const {
      targetPopulation = 4000,
      riskThreshold = 75,
      maxDistanceKm = 15,
      minCapacity = 3000
    } = params;

    const body = {
      targetPopulation: Number(targetPopulation),
      riskThreshold: Number(riskThreshold),
      maxDistanceKm: Number(maxDistanceKm),
      minCapacity: Number(minCapacity)
    };

    return fetchWithFallback(
      '/simulation/what-if',
      {
        method: 'POST',
        body: JSON.stringify(body)
      },
      () => {
        const eligibleSites = CANDIDATE_RELOCATION_SITES.filter(site => site.distanceFromRedZoneKm <= maxDistanceKm);
        const highlySuitable = eligibleSites.filter(s => s.suitabilityScore >= 85 && s.estimatedCapacity >= targetPopulation);
        const capacityDeficits = eligibleSites.filter(s => s.estimatedCapacity < targetPopulation);
        const infrastructureNeeds = eligibleSites.filter(s => s.capacityStatus === 'Moderate' || s.capacityStatus === 'Deficit Risk');

        return {
          simulationTimestamp: new Date().toISOString(),
          parametersUsed: { targetPopulation, riskThreshold, maxDistanceKm, minCapacity },
          totalEligibleFound: eligibleSites.length,
          highlySuitableCount: highlySuitable.length,
          capacityDeficitCount: capacityDeficits.length,
          infrastructureImprovementNeededCount: infrastructureNeeds.length,
          topRecommendedSite: highlySuitable[0] || eligibleSites[0] || null,
          evaluatedSites: eligibleSites.map(s => ({
            ...s,
            simulatedHeadroom: s.estimatedCapacity - targetPopulation,
            simulatedUtilizationPercent: Math.round((targetPopulation / s.estimatedCapacity) * 100),
            absorptionFeasibility: s.estimatedCapacity >= targetPopulation ? 'Feasible' : 'Requires Split Relocation'
          }))
        };
      }
    );
  },

  // 12. Unified Search
  async search(query) {
    if (!query) return { habitations: [], sites: [], redZones: [] };
    return fetchWithFallback(
      `/search?q=${encodeURIComponent(query)}`,
      { method: 'GET' },
      () => {
        const q = query.toLowerCase().trim();
        return {
          query,
          habitations: VULNERABLE_HABITATIONS.filter(h =>
            h.name.toLowerCase().includes(q) || h.district.toLowerCase().includes(q) || h.dominantHazards.toLowerCase().includes(q)
          ),
          sites: CANDIDATE_RELOCATION_SITES.filter(s =>
            s.name.toLowerCase().includes(q) || s.district.toLowerCase().includes(q) || s.overallRecommendation.toLowerCase().includes(q)
          ),
          redZones: RED_ZONES.filter(r => r.name.toLowerCase().includes(q) || r.hazardType.toLowerCase().includes(q))
        };
      }
    );
  },

  // 13. Reports Export & PDF Download
  async exportDossier(payload) {
    return fetchWithFallback(
      '/reports/export-dossier',
      {
        method: 'POST',
        body: JSON.stringify(payload)
      },
      () => ({
        report_id: payload.report_template_id || 'REP_01',
        title: `Habitation Relocation Action Dossier`,
        generated_at: new Date().toISOString(),
        reference_code: `SDMA/RELOC/2026/MOCK`,
        status: 'Final Approved Order',
        download_url: `/api/v1/reports/download?habitation_id=${payload.habitation_id || 'HAB_001'}`,
        content_summary: 'Generated statutory dossier preview.'
      })
    );
  },

  getReportDownloadUrl(habitationId = 'HAB_001') {
    return `${BASE_URL}/reports/download?habitation_id=${encodeURIComponent(habitationId)}`;
  }
};
