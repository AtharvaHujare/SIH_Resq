import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Layers, Maximize2, Minimize2, ShieldAlert, MapPin, Home, ShieldCheck, Navigation } from 'lucide-react';
import { api } from '../../services/api';
import { VULNERABLE_HABITATIONS, CANDIDATE_RELOCATION_SITES, RED_ZONES } from '../../data/mockData';

export default function GisMapViewer({
  district = null,
  onSelectHabitation,
  onSelectSite,
  selectedFeature,
  isExpanded = false,
  onToggleExpand,
  activeRoute = null,
  onClearRoute = null,
  isAnalyzing = false,
  pendingCity = null,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef({
    redZones: null,
    safeZones: null,
    habitations: null,
    relocationSites: null,
    route: null,
  });

  // Layer Visibility State - strictly the required default layers
  const [layersVisible, setLayersVisible] = useState({
    redZones: true,
    safeZones: true,
    habitations: true,
    relocationSites: true,
  });

  // Initialize Leaflet Map (runs once on mount - instance preserved)
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter = [26.19, 91.75]; // Guwahati default
    const initialZoom = 12;

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: initialZoom,
      zoomControl: true,
      attributionControl: false,
    });

    mapInstanceRef.current = map;

    // Public OpenStreetMap base map tile provider (Preserved)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    // Create Persistent Layer Groups
    const redZoneGroup = L.layerGroup().addTo(map);
    const safeZoneGroup = L.layerGroup().addTo(map);
    const habitationGroup = L.layerGroup().addTo(map);
    const relocationGroup = L.layerGroup().addTo(map);
    const routeGroup = L.layerGroup().addTo(map);

    layersRef.current = {
      redZones: redZoneGroup,
      safeZones: safeZoneGroup,
      habitations: habitationGroup,
      relocationSites: relocationGroup,
      route: routeGroup,
    };

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Immediately clear stale previous-city overlays and pan to new city upon city selection
  useEffect(() => {
    if (pendingCity || isAnalyzing) {
      const { redZones, safeZones, habitations, relocationSites, route } = layersRef.current;
      if (redZones) redZones.clearLayers();
      if (safeZones) safeZones.clearLayers();
      if (habitations) habitations.clearLayers();
      if (relocationSites) relocationSites.clearLayers();
      if (route) route.clearLayers();

      const map = mapInstanceRef.current;
      if (map) {
        const target = (pendingCity || district || 'guwahati').toLowerCase();
        if (target.includes('pune')) {
          map.setView([18.07, 73.55], 11);
        } else if (target.includes('raigad')) {
          map.setView([18.12, 73.45], 11);
        } else {
          map.setView([26.19, 91.75], 11);
        }
      }
    }
  }, [pendingCity, isAnalyzing]);

  // Fetch & Populate Dynamic Layers based on analyzed city
  useEffect(() => {
    let isMounted = true;

    async function loadMapData() {
      const map = mapInstanceRef.current;
      if (!map || isAnalyzing || pendingCity) return;

      const { redZones, safeZones, habitations, relocationSites, route } = layersRef.current;

      // Cleanly remove old layers before adding new ones
      if (redZones) redZones.clearLayers();
      if (safeZones) safeZones.clearLayers();
      if (habitations) habitations.clearLayers();
      if (relocationSites) relocationSites.clearLayers();
      if (route) route.clearLayers();

      const cityKey = (district || 'guwahati').toLowerCase().trim();

      try {
        // Fetch GIS data for analyzed city (cached in api.js)
        const [redZonesData, safeZonesData, habsData, sitesData] = await Promise.all([
          api.getRedZones(district),
          api.getSafeZones(district),
          api.getHabitations({ district }),
          api.getRelocationSites({ district }),
        ]);

        if (!isMounted || !mapInstanceRef.current) return;

        const allBoundingCoords = [];

        // 4. Render Hazard / Red Zones (RED)
        if (redZones) {
          let zonesToRender = redZonesData && redZonesData.length > 0 ? redZonesData : [];
          if (zonesToRender.length === 0) {
            // Fallback filter by district
            zonesToRender = RED_ZONES.filter((rz) =>
              rz.district.toLowerCase().includes(cityKey.includes('pune') ? 'pune' : cityKey.includes('raigad') ? 'raigad' : 'guwahati')
            );
          }

          zonesToRender.forEach((rz) => {
            if (!rz.coordinates || rz.coordinates.length === 0) return;

            // Collect bounding coords
            rz.coordinates.forEach((pt) => {
              allBoundingCoords.push([pt[0], pt[1]]);
            });

            const polygon = L.polygon(rz.coordinates, {
              color: '#dc2626',
              weight: 2.5,
              fillColor: '#ef4444',
              fillOpacity: 0.28,
              dashArray: '5, 5',
            });

            polygon.bindTooltip(`<strong>RED: Hazard / Red Zone</strong><br/>${rz.name}<br/>Hazard: ${rz.hazardType}`, { sticky: true });

            polygon.bindPopup(`
              <div class="map-popup-card">
                <div class="map-popup-header">
                  <span class="map-popup-title">${rz.name}</span>
                  <span class="badge badge-critical">${rz.riskLevel || 'Critical'}</span>
                </div>
                <div style="font-size: 0.76rem; color: #475569;">${rz.hazardType}</div>
                <div class="map-popup-stats">
                  <div>Area: <strong>${rz.areaSqKm} km²</strong></div>
                  <div>Safety Buffer: <strong>${rz.bufferMarginM}m</strong></div>
                  <div>Exposed Pop: <strong>${(rz.exposedPopulation || 0).toLocaleString()}</strong></div>
                  <div>Trigger: <strong style="color: #b91c1c;">${rz.primaryTrigger || 'Hazard Model'}</strong></div>
                </div>
              </div>
            `);
            redZones.addLayer(polygon);
          });
        }

        // 5. Render Dynamically Calculated Safe Zones (GREEN)
        // Visually distinct from ordinary OSM land/forest with high-contrast emerald borders & opacity
        if (safeZones) {
          if (safeZonesData && safeZonesData.features && safeZonesData.features.length > 0) {
            safeZonesData.features.forEach((feat) => {
              const geom = feat.geometry;
              const props = feat.properties || {};

              if (geom && geom.type === 'Polygon' && geom.coordinates && geom.coordinates[0]) {
                // GeoJSON coordinates are [lon, lat] -> convert to Leaflet [lat, lon]
                const latLngs = geom.coordinates[0].map((c) => {
                  allBoundingCoords.push([c[1], c[0]]);
                  return [c[1], c[0]];
                });

                const polygon = L.polygon(latLngs, {
                  color: '#059669', // Bold emerald / dark jade border
                  weight: 3.5,
                  opacity: 1.0,
                  fillColor: '#10b981', // Vibrant emerald fill
                  fillOpacity: 0.42, // Rich contrast against base OSM tiles
                  dashArray: '5, 5',
                });

                polygon.bindTooltip(
                  `<strong>GREEN: Dynamically Calculated Safe Zone</strong><br/>${props.name || 'Candidate Safe Zone'}<br/>Capacity: ${(props.estimatedCapacity || 0).toLocaleString()} residents • 0% Red-Zone Overlap`,
                  { sticky: true }
                );

                polygon.bindPopup(`
                  <div class="map-popup-card">
                    <div class="map-popup-header">
                      <span class="map-popup-title" style="color: #059669;">${props.name || 'Candidate Safe Zone'}</span>
                      <span class="badge" style="background: #dcfce7; color: #15803d; border: 1px solid #86efac; font-weight: 700;">Safe Green Zone</span>
                    </div>
                    <div style="font-size: 0.76rem; color: #475569;">${props.district} • ${props.usableAreaAcres || 0} acres</div>
                    <div class="map-popup-stats">
                      <div>Feasible Cap: <strong>${(props.estimatedCapacity || 0).toLocaleString()}</strong></div>
                      <div>Slope: <strong>${props.slopeDegree || 0}° (Flat)</strong></div>
                      <div>Red-Zone Margin: <strong>${props.nearestHazardDistanceM ? Math.round(props.nearestHazardDistanceM / 1000) : 2} km</strong></div>
                      <div>Bottleneck: <strong style="color: #059669;">${props.limitingFactor || 'Land'}</strong></div>
                    </div>
                    <div style="font-size: 0.72rem; color: #64748b; margin-top: 6px; font-style: italic;">
                      ${props.derivationCriteria || 'Deterministic GIS Multi-Criteria Exclusion'}
                    </div>
                  </div>
                `);
                safeZones.addLayer(polygon);
              }
            });
          }
        }

        // 6. Render Vulnerable Habitations (BLUE)
        if (habitations) {
          let habsToRender = habsData && habsData.length > 0 ? habsData : [];
          if (habsToRender.length === 0) {
            habsToRender = VULNERABLE_HABITATIONS.filter((h) =>
              h.district.toLowerCase().includes(cityKey.includes('pune') ? 'pune' : cityKey.includes('raigad') ? 'raigad' : 'guwahati')
            );
          }

          habsToRender.forEach((h) => {
            if (!h.coordinates || h.coordinates.length < 2) return;
            allBoundingCoords.push([h.coordinates[0], h.coordinates[1]]);

            // BLUE Vulnerable Habitation Marker
            const marker = L.circleMarker(h.coordinates, {
              radius: 7,
              fillColor: '#2563eb', // Clean vibrant blue
              color: '#ffffff',
              weight: 2.5,
              opacity: 1,
              fillOpacity: 0.95,
            });

            marker.bindTooltip(`<strong>BLUE: Vulnerable Habitation</strong><br/>${h.name} (${h.riskTier})<br/>Risk Score: ${h.riskScore}/100`, { sticky: true });

            marker.bindPopup(`
              <div class="map-popup-card">
                <div class="map-popup-header">
                  <span class="map-popup-title">${h.name}</span>
                  <span class="badge badge-${(h.riskTier || 'moderate').toLowerCase()}">${h.riskTier}</span>
                </div>
                <div style="font-size: 0.76rem; color: #64748b;">${h.district} • Pop: <strong>${(h.population || 0).toLocaleString()}</strong></div>
                <div style="font-size: 0.74rem; color: #0f172a; margin: 3px 0;">Threat: ${h.dominantHazards || 'Multi-Hazard'}</div>
                <div style="font-size: 0.72rem; color: #475569;">Risk Score: <strong style="color: #2563eb;">${h.riskScore}/100</strong></div>
                ${onSelectHabitation ? `<button id="inspect-hab-${h.id}" class="map-popup-action-btn">Inspect & Select for Safe Route</button>` : ''}
              </div>
            `);

            marker.on('popupopen', () => {
              const btn = document.getElementById(`inspect-hab-${h.id}`);
              if (btn && onSelectHabitation) {
                btn.onclick = () => onSelectHabitation(h);
              }
            });

            habitations.addLayer(marker);
          });
        }

        // 7. Render Candidate Relocation Sites (GREEN MARKER)
        if (relocationSites) {
          let sitesToRender = sitesData && sitesData.length > 0 ? sitesData : [];
          if (sitesToRender.length === 0) {
            sitesToRender = CANDIDATE_RELOCATION_SITES.filter((s) =>
              s.district.toLowerCase().includes(cityKey.includes('pune') ? 'pune' : cityKey.includes('raigad') ? 'raigad' : 'guwahati')
            );
          }

          sitesToRender.forEach((site) => {
            if (!site.coordinates || site.coordinates.length < 2) return;
            allBoundingCoords.push([site.coordinates[0], site.coordinates[1]]);

            // GREEN MARKER for Candidate Relocation Site
            const marker = L.circleMarker(site.coordinates, {
              radius: 9,
              fillColor: '#15803d', // Dark Forest Green
              color: '#ffffff',
              weight: 3,
              opacity: 1,
              fillOpacity: 0.95,
            });

            marker.bindTooltip(
              `<strong>GREEN MARKER: Candidate Relocation Site</strong><br/>${site.name}<br/>Suitability: ${site.suitabilityScore}% • Capacity: ${(site.estimatedCapacity || 0).toLocaleString()}`,
              { sticky: true }
            );

            marker.bindPopup(`
              <div class="map-popup-card">
                <div class="map-popup-header">
                  <span class="map-popup-title">${site.name}</span>
                  <span class="badge badge-safe">${site.suitabilityScore}% Suitable</span>
                </div>
                <div style="font-size: 0.76rem; color: #475569;">Safe Relocation Zone (${site.usableAreaAcres || 0} acres)</div>
                <div class="map-popup-stats">
                  <div>Capacity: <strong>${(site.estimatedCapacity || 0).toLocaleString()}</strong></div>
                  <div>Slope: <strong>${site.slopeDegree}° (Flat)</strong></div>
                  <div>Safe Dist: <strong>${site.distanceFromRedZoneKm} km</strong></div>
                  <div>Status: <strong>${site.capacityStatus || 'Optimal'}</strong></div>
                </div>
                ${onSelectSite ? `<button id="inspect-site-${site.id}" class="map-popup-action-btn" style="background: #15803d;">Set as Destination Safe Haven</button>` : ''}
              </div>
            `);

            marker.on('popupopen', () => {
              const btn = document.getElementById(`inspect-site-${site.id}`);
              if (btn && onSelectSite) {
                btn.onclick = () => onSelectSite(site);
              }
            });

            relocationSites.addLayer(marker);
          });
        }

        // 8. TIGHT BOUNDS FITTING (Do NOT show whole of India; fit city features tightly)
        // If an active route is present, skip fitting city bounds so the route bounds stay framed
        if (!activeRoute && allBoundingCoords.length > 0) {
          const bounds = L.latLngBounds(allBoundingCoords);
          map.fitBounds(bounds, {
            padding: [45, 45],
            maxZoom: 13,
            animate: true,
          });
        } else if (!activeRoute) {
          // Fallback tightly centered on active city
          if (cityKey.includes('pune')) {
            map.setView([18.07, 73.55], 12);
          } else if (cityKey.includes('raigad')) {
            map.setView([18.12, 73.45], 11);
          } else {
            map.setView([26.19, 91.75], 12);
          }
        }

      } catch (err) {
        console.warn('Failed to load dynamic GIS layers, using baseline:', err);
      }
    }

    loadMapData();
    return () => {
      isMounted = false;
    };
  }, [district]);

  // Synchronize layer visibility toggles with map instance
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const { redZones, safeZones, habitations, relocationSites } = layersRef.current;

    if (redZones) {
      if (layersVisible.redZones && !map.hasLayer(redZones)) map.addLayer(redZones);
      else if (!layersVisible.redZones && map.hasLayer(redZones)) map.removeLayer(redZones);
    }
    if (safeZones) {
      if (layersVisible.safeZones && !map.hasLayer(safeZones)) map.addLayer(safeZones);
      else if (!layersVisible.safeZones && map.hasLayer(safeZones)) map.removeLayer(safeZones);
    }
    if (habitations) {
      if (layersVisible.habitations && !map.hasLayer(habitations)) map.addLayer(habitations);
      else if (!layersVisible.habitations && map.hasLayer(habitations)) map.removeLayer(habitations);
    }
    if (relocationSites) {
      if (layersVisible.relocationSites && !map.hasLayer(relocationSites)) map.addLayer(relocationSites);
      else if (!layersVisible.relocationSites && map.hasLayer(relocationSites)) map.removeLayer(relocationSites);
    }
  }, [layersVisible]);

  // Center on selected feature if provided
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedFeature || !selectedFeature.coordinates) return;

    map.flyTo(selectedFeature.coordinates, 13, { duration: 1.2 });
  }, [selectedFeature]);

  // Render Real OSRM Road Evacuation Route Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    const { route } = layersRef.current;
    if (!map || !route) return;

    route.clearLayers();

    if (!activeRoute || !activeRoute.geometry || !activeRoute.geometry.coordinates) {
      return;
    }

    // OSRM coordinates are [lon, lat] -> convert to Leaflet [lat, lon]
    const routeCoords = activeRoute.geometry.coordinates.map((c) => [c[1], c[0]]);
    if (routeCoords.length === 0) return;

    // High-visibility road route styling (contrast casing + vibrant core)
    // 1. Casing / background outline
    const casingLine = L.polyline(routeCoords, {
      color: '#1e1b4b',
      weight: 8,
      opacity: 0.65,
      lineCap: 'round',
      lineJoin: 'round',
    });
    route.addLayer(casingLine);

    // 2. Core route line (electric indigo / purple-blue)
    const coreLine = L.polyline(routeCoords, {
      color: '#6366f1',
      weight: 5,
      opacity: 0.98,
      lineCap: 'round',
      lineJoin: 'round',
    });
    coreLine.bindTooltip(
      `<strong>🚗 OSRM Road Evacuation Route</strong><br/>Distance: <strong>${activeRoute.distanceKm} km</strong><br/>Estimated Drive: <strong>${activeRoute.durationMinutes} min</strong>`,
      { sticky: true }
    );
    route.addLayer(coreLine);

    // 3. Origin Marker (Critical Habitation)
    if (activeRoute.origin) {
      const originMarker = L.circleMarker([activeRoute.origin.lat, activeRoute.origin.lon], {
        radius: 10,
        fillColor: '#dc2626',
        color: '#ffffff',
        weight: 3,
        opacity: 1,
        fillOpacity: 1,
      });
      originMarker.bindTooltip(
        `<strong>📍 Evacuation Origin</strong><br/>${activeRoute.originName || 'Critical Habitation'}`,
        { permanent: true, direction: 'top', offset: [0, -10] }
      );
      route.addLayer(originMarker);
    }

    // 4. Destination Marker (Safe Relocation Haven)
    if (activeRoute.destination) {
      const destMarker = L.circleMarker([activeRoute.destination.lat, activeRoute.destination.lon], {
        radius: 12,
        fillColor: '#10b981',
        color: '#ffffff',
        weight: 3.5,
        opacity: 1,
        fillOpacity: 1,
      });
      destMarker.bindTooltip(
        `<strong>🏁 Safe Relocation Haven</strong><br/>${activeRoute.destinationName || 'Recommended Safe Site'}`,
        { permanent: true, direction: 'top', offset: [0, -12] }
      );
      route.addLayer(destMarker);
    }

    // 5. Automatically fit map bounds tightly to the route
    const routeBounds = L.latLngBounds(routeCoords);
    map.fitBounds(routeBounds, { padding: [60, 60], maxZoom: 14, animate: true });
  }, [activeRoute]);

  const toggleLayer = (key) => {
    setLayersVisible((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className={`gis-map-container ${isExpanded ? 'expanded' : ''}`}>
      <div ref={mapContainerRef} className="leaflet-map-element" />

      {/* Floating Active Route Telemetry Banner */}
      {activeRoute && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            left: '14px',
            zIndex: 500,
            background: 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(8px)',
            border: '2px solid #6366f1',
            borderRadius: '10px',
            padding: '10px 16px',
            boxShadow: '0 4px 16px rgba(99, 102, 241, 0.28)',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            maxWidth: 'calc(100% - 28px)',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: '#e0e7ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#4f46e5',
              }}
            >
              <Navigation size={18} />
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e1b4b' }}>
                Safe Road Evacuation Route: {activeRoute.originName || 'Origin'} &rarr; {activeRoute.destinationName || 'Safe Haven'}
              </div>
              <div style={{ fontSize: '0.73rem', color: '#64748b' }}>
                Engine: <strong>OSRM / OpenStreetMap</strong> • Road Network: <strong>All-Weather Paved Route</strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '1px solid #cbd5e1', paddingLeft: '14px' }}>
            <div>
              <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Distance</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#4338ca' }}>
                {activeRoute.distanceKm} km
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Est. Travel Time</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#059669' }}>
                {activeRoute.durationMinutes} min
              </div>
            </div>
          </div>

          {onClearRoute && (
            <button
              onClick={onClearRoute}
              style={{
                marginLeft: 'auto',
                background: '#f1f5f9',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#475569',
                cursor: 'pointer',
              }}
            >
              Clear Route
            </button>
          )}
        </div>
      )}

      {/* Floating Layer Control Panel */}
      <div className="map-layer-panel">
        <div className="layer-panel-header">
          <div className="layer-panel-title">
            <Layers size={14} color="var(--gis-blue)" />
            <span>Map Layers</span>
          </div>
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              style={{ color: '#64748b' }}
              title={isExpanded ? 'Collapse Map' : 'Expand Map'}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
        </div>

        <div className="layer-toggle-list">
          <label className="layer-toggle-item">
            <div className="layer-label-group">
              <span className="layer-swatch" style={{ background: 'rgba(239, 68, 68, 0.35)', border: '2px dashed #dc2626' }} />
              <span>Multi-Hazard Red Zones</span>
            </div>
            <input
              type="checkbox"
              className="custom-checkbox"
              checked={layersVisible.redZones}
              onChange={() => toggleLayer('redZones')}
            />
          </label>

          <label className="layer-toggle-item">
            <div className="layer-label-group">
              <span className="layer-swatch" style={{ background: 'rgba(16, 185, 129, 0.45)', border: '2px dashed #059669' }} />
              <span>Dynamic Safe Green Zones</span>
            </div>
            <input
              type="checkbox"
              className="custom-checkbox"
              checked={layersVisible.safeZones}
              onChange={() => toggleLayer('safeZones')}
            />
          </label>

          <label className="layer-toggle-item">
            <div className="layer-label-group">
              <span className="layer-swatch" style={{ background: '#2563eb', border: '1px solid #ffffff', borderRadius: '50%' }} />
              <span>Vulnerable Habitations</span>
            </div>
            <input
              type="checkbox"
              className="custom-checkbox"
              checked={layersVisible.habitations}
              onChange={() => toggleLayer('habitations')}
            />
          </label>

          <label className="layer-toggle-item">
            <div className="layer-label-group">
              <span className="layer-swatch" style={{ background: '#15803d', border: '2px solid #ffffff', borderRadius: '50%' }} />
              <span>Candidate Relocation Sites</span>
            </div>
            <input
              type="checkbox"
              className="custom-checkbox"
              checked={layersVisible.relocationSites}
              onChange={() => toggleLayer('relocationSites')}
            />
          </label>
        </div>
      </div>

      {/* Floating Status / Preparing Analysis Banner */}
      {(isAnalyzing || pendingCity) && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            zIndex: 500,
            background: 'rgba(255, 255, 255, 0.96)',
            backdropFilter: 'blur(6px)',
            border: '1.5px solid #2563eb',
            borderRadius: '8px',
            padding: '8px 14px',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.18)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: '#1e3a8a',
          }}
        >
          <div
            style={{
              width: '12px',
              height: '12px',
              border: '2px solid #bfdbfe',
              borderTopColor: '#2563eb',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}
          />
          <span>{isAnalyzing ? `Computing GIS risk & safe zones for ${district}...` : `Selected: ${pendingCity} • Click 'Analyze City'`}</span>
        </div>
      )}

      {/* Floating Map Legend (Strictly Configured to System Guidelines) */}
      <div className="map-legend-panel">
        <div className="legend-title">GIS Spatial Decision Legend</div>
        <div className="legend-items">
          <div className="legend-item">
            <span
              style={{
                display: 'inline-block',
                width: '14px',
                height: '14px',
                background: 'rgba(239, 68, 68, 0.3)',
                border: '2px dashed #dc2626',
                borderRadius: '3px',
              }}
            />
            <span><strong>RED =</strong> Hazard / Red Zone</span>
          </div>

          <div className="legend-item">
            <span
              style={{
                display: 'inline-block',
                width: '14px',
                height: '14px',
                background: 'rgba(16, 185, 129, 0.45)',
                border: '2px dashed #059669',
                borderRadius: '3px',
              }}
            />
            <span><strong>GREEN =</strong> Dynamically Calculated Safe Zone</span>
          </div>

          <div className="legend-item">
            <span
              style={{
                display: 'inline-block',
                width: '12px',
                height: '12px',
                background: '#2563eb',
                border: '2px solid #ffffff',
                borderRadius: '50%',
                boxShadow: '0 0 0 1px #1d4ed8',
              }}
            />
            <span><strong>BLUE =</strong> Vulnerable Habitation</span>
          </div>

          <div className="legend-item">
            <span
              style={{
                display: 'inline-block',
                width: '14px',
                height: '14px',
                background: '#15803d',
                border: '2px solid #ffffff',
                borderRadius: '50%',
                boxShadow: '0 0 0 1px #166534',
              }}
            />
            <span><strong>GREEN MARKER =</strong> Candidate Relocation Site</span>
          </div>

          <div className="legend-item">
            <span
              style={{
                display: 'inline-block',
                width: '18px',
                height: '4px',
                background: '#6366f1',
                borderRadius: '2px',
                boxShadow: '0 0 0 1px #1e1b4b',
              }}
            />
            <span><strong>INDIGO =</strong> Road Evacuation Route</span>
          </div>
        </div>
      </div>
    </div>
  );
}
