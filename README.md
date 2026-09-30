# Intelligent GIS-Based Proactive Relocation Decision Support System

[![SIH 2026](https://img.shields.io/badge/SIH-2026-FF6F00.svg?style=flat-square&logo=target)](https://www.sih.gov.in/)
[![Problem Statement](https://img.shields.io/badge/Problem%20Statement-ID%20191-0288D1.svg?style=flat-square)](https://www.sih.gov.in/)
[![Domain](https://img.shields.io/badge/Domain-AI%20%2B%20GIS%20%2B%20Disaster%20Management-00796B.svg?style=flat-square)](#overview)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![PostGIS](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20PostGIS-336791.svg?style=flat-square&logo=postgresql&logoColor=white)](https://postgis.net/)
[![License](https://img.shields.io/badge/License-MIT%20%2F%20SIH%202026-gray.svg?style=flat-square)](#license)

> **A data-driven spatial platform transforming disaster management from reactive post-disaster rescue to proactive, multi-hazard risk assessment and carrying-capacity-audited settlement relocation.**

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [The Proactive Solution](#-the-proactive-solution)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
  - [Compact Architecture Pipeline](#compact-architecture-pipeline)
  - [Processing Workflow](#processing-workflow)
  - [Dual-Mode Data Resilience](#dual-mode-data-resilience)
- [Technology Stack](#-technology-stack)
- [GIS & Mathematical Risk Logic](#-gis--mathematical-risk-logic)
  - [1. Multi-Hazard Composite Risk Engine](#1-multi-hazard-composite-risk-engine)
  - [2. Risk Classification Tiers](#2-risk-classification-tiers)
  - [3. Red Zone Spatial Buffering & Containment](#3-red-zone-spatial-buffering--containment)
  - [4. Relocation Site Suitability (AHP 7-Factor Model)](#4-relocation-site-suitability-ahp-7-factor-model)
  - [5. Carrying Capacity Assessment Model](#5-carrying-capacity-assessment-model)
  - [6. Geodesic & Haversine Distance Metrics](#6-geodesic--haversine-distance-metrics)
- [APIs, Integrations & Data Ingestion](#-apis-integrations--data-ingestion)
  - [Data Provenance: Live vs. Prototype Baseline](#data-provenance-live-vs-prototype-baseline)
  - [External Ingestion & Integration Catalog](#external-ingestion--integration-catalog)
- [Database & PostGIS Architecture](#-database--postgis-architecture)
  - [Entity-Relationship Architecture](#entity-relationship-architecture)
  - [PostGIS Spatial Types & SRID:4326 Policy](#postgis-spatial-types--srid4326-policy)
  - [Coordinate Translation Matrix](#coordinate-translation-matrix)
- [Project Structure](#-project-structure)
- [Setup & Installation](#-setup--installation)
  - [Prerequisites](#prerequisites)
  - [Backend Setup (Python / FastAPI)](#backend-setup-python--fastapi)
  - [Frontend Setup (React / Vite)](#frontend-setup-react--vite)
  - [Database Migrations & Seeding](#database-migrations--seeding)
- [Environment Variables](#-environment-variables)
- [Running the Platform](#-running-the-platform)
  - [Starting the FastAPI Backend](#starting-the-fastapi-backend)
  - [Starting the React WebGIS Dashboard](#starting-the-react-webgis-dashboard)
- [REST API Documentation](#-rest-api-documentation)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Current Data & Prototype Scope](#-current-data--prototype-scope)
- [Future Scope & Scaling Roadmap](#-future-scope--scaling-roadmap)
- [Contributing & License](#-contributing--license)

---

## 🌍 Overview

Disaster management in hazard-prone corridors historically operates under a **reactive paradigm**: emergency teams mobilize *after* an extreme cloudburst, flood, or landslide occurs, rescue survivors, establish makeshift relief camps, and eventually rebuild homes in the very same hazard-exposed valleys.

The **Intelligent GIS-Based Proactive Relocation Decision Support System (PS ID 191)** establishes a systematic, data-driven approach for State and District Disaster Management Authorities (SDMA / DDMA). By coupling geospatial hazard zoning, geomorphological terrain metrics, multi-criteria site suitability analysis, and infrastructure carrying capacity calculations, the platform identifies endangered habitations **months ahead of catastrophic weather seasons** and algorithmically recommends verified, safe relocation parcels.

### Core Philosophy

> *"Don't wait for a disaster to strike. Demarcate high-risk habitations in advance, discover safer relocation parcels, audit their carrying capacity, and generate actionable, phased relocation schedules for administrative authorities."*

---

## ⚠️ Problem Statement

In ecologically fragile regions—such as the Western Ghats, the Himalayan arc, and floodplains—communities experience recurring destruction from cascading natural hazards:

1. **Repetitive Destruction Cycles:** Rebuilding habitations on the same unstable slope or flood margin perpetuates vulnerability with each monsoon season.
2. **Cascading Hazard Isolation:** Heavy precipitation simultaneously triggers flash flooding in valley channels and debris flows on mountain slopes, cutting off single-access roads and stranding entire villages.
3. **Hazard Polygons Without Destination Direction:** Standard disaster maps draw red hazard boundaries but fail to answer the critical governance question: *Where can affected populations be safely relocated without overloading recipient civic infrastructure or triggering secondary hazards?*
4. **Ad-Hoc Relocation Decisions:** Relocating populations without auditing potable water aquifer availability, road access, schools, or primary healthcare capacity creates unviable informal settlements and secondary crises.

---

## 💡 The Proactive Solution

The platform resolves four fundamental governance questions through automated spatial and mathematical modeling:

```text
CONVENTIONAL PARADIGM (Reactive):
Disaster Occurs ──► Destruction ──► Emergency Rescue ──► Relief Camps ──► Rebuild in Hazard Path

PROACTIVE PLATFORM PARADIGM:
Multi-Source Data ──► Multi-Hazard Risk Scoring ──► Red Zone Demarcation ──► Candidate Parcel Discovery ──► Carrying Capacity Audit ──► Phased Relocation
```

| # | Administrative Question | System Resolution Mechanism |
|:---:|---|---|
| **Q1** | **Which geographic areas are strictly unsafe for human settlement?** | Dynamic multi-hazard overlay synthesizing slope steepness ($>30^\circ$), extreme rainfall pore pressure ($>200\text{ mm}$), and historical disaster scars into buffered **Red Zones**. |
| **Q2** | **Which specific habitations are in imminent danger?** | Spatial intersection of georeferenced revenue settlements with Red Zones, incorporating demographic exposure and road cutoff isolation indices. |
| **Q3** | **Where can affected populations be safely and sustainably resettled?** | Spatial exclusion filtering and 7-factor Analytical Hierarchy Process (AHP) scoring across safe terrain, water aquifers, road links, schools, and healthcare. |
| **Q4** | **Can recipient parcels sustain the incoming population?** | Mathematical carrying capacity auditing checking per-capita land, municipal water norms ($135\text{ LPD}$), and hospital bed ratios to prevent secondary humanitarian strain. |

---

## ✨ Key Features

- **🗺️ Interactive WebGIS Command Center:** Built with React 18, Vite, and Leaflet, featuring layer toggles for active Red Zones, vulnerable settlements, candidate relocation sites, and road lifelines.
- **🛡️ Multi-Hazard Red Zone Delineation:** Automated spatial buffering and polygon containment algorithms identifying habitations inside extreme hazard envelopes.
- **📊 Habitation Vulnerability Profiling:** Integrates population volume, household counts, kutcha housing percentages, and road isolation distances.
- **📍 AHP Candidate Site Discovery:** 7-factor Analytical Hierarchy Process evaluating potential recipient parcels for safety, slope stability, accessibility, and utility reach.
- **💧 Carrying Capacity Resource Audit:** Checks per-capita land ($45\text{ m}^2/\text{person}$), daily water supply ($135\text{ LPD}$), and primary healthcare beds against relocated population demands.
- **⏱️ 4-Tier Phased Relocation Queue:** Prioritizes settlements into **Priority 1 (Immediate: 0–6 months)**, **Priority 2 (Short-Term: 6–18 months)**, **Priority 3 (Medium-Term: 18–36 months)**, and **Priority 4 (In-Situ Monitoring)**.
- **🧠 Explainable AI (TreeSHAP Factor Cards):** Decomposes composite risk predictions into transparent, quantifiable environmental and infrastructural contributors for administrative accountability.
- **🧪 Parametric "What-If" Resettlement Sandbox:** Enables planners to simulate variable risk thresholds, maximum haul distances, and land allocation constraints in real time.
- **📄 Statutory Section 38 Dossier Generator:** Produces two-page, gazette-ready administrative relocation briefs and PDF action dossiers via ReportLab under Section 38 of the Disaster Management Act.
- **🌐 Real-World Road Evacuation Routing:** Direct OSRM integration computing actual road network driving paths, distances, and evacuation travel times between hazard zones and safe sites.
- **🌦️ Meteorological Telemetry & Alerts:** Live weather telemetry via Open-Meteo with fallback support and early warning alert management.
- **🔄 Dual-Mode Data Resilience:** Seamlessly runs against hosted Supabase PostgreSQL + PostGIS or automatically falls back to deterministic prototype baseline datasets when offline.

---

## 🏛️ System Architecture

### Compact Architecture Pipeline

```mermaid
flowchart LR
    subgraph S1["External Data"]
        direction TB
        E1["Open-Meteo / IMD"]
        E2["OSRM Routing Engine"]
        E3["OSM Overpass API"]
        E4["ISRO Bhuvan WMS"]
    end

    subgraph S2["Ingestion & Resilience"]
        direction TB
        I1["Ingestion Adapters<br/>(IMD, OSM, Bhuvan)"]
        I2["Dual-Mode Fallback<br/>(Deterministic Baseline Data)"]
    end

    subgraph S3["Persistence Layer"]
        direction TB
        DB[("PostgreSQL 15+ & PostGIS<br/>SRID:4326 • GiST Indexes")]
    end

    subgraph S4["Core Analytical Engines"]
        direction TB
        R1["Multi-Hazard Risk Engine"]
        R2["AHP Suitability Engine"]
        R3["Carrying Capacity Engine"]
        R4["Prioritization Engine"]
        R5["Simulation & ReportLab"]
    end

    subgraph S5["FastAPI Backend Server"]
        direction TB
        A1["REST API Routers (/api/v1)"]
        A2["DataRepository Layer"]
        A3["OpenAPI / Swagger Specs"]
    end

    subgraph S6["WebGIS Frontend Client"]
        direction TB
        U1["React 18 + Vite"]
        U2["Leaflet WebGIS Viewer"]
        U3["Command Center Dashboard"]
    end

    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 <==>|REST / JSON / GeoJSON| S6
```

### Processing Workflow

```text
┌─────────────────────────┐
│ External & Spatial Data │ (Open-Meteo, OSRM, OSM Overpass, Bhuvan, Base Demographics)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ PostGIS Spatial Storage │ (EPSG:4326 Point & Polygon geometries with GiST spatial indexes)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  Multi-Hazard Scoring   │ R = 0.45·Hazard + 0.25·Exposure + 0.30·Vulnerability
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│   Red Zone Buffering    │ Delineate contiguous hazard envelopes (300m safety buffer)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ AHP Parcel Suitability  │ 7-factor weighted scoring for candidate resettlement sites
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Carrying Capacity Check │ Audit land area, potable water (135 LPD), and hospital beds
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Action Prioritization   │ Algorithmic assignment into Priority Tiers (P1 to P4)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ WebGIS Command Center   │ Interactive mapping, What-If simulation sandbox, PDF dossiers
└─────────────────────────┘
```

### Dual-Mode Data Resilience

The platform features an architectural abstraction in `backend/app/db/repository.py`:
- **Database Mode (`USE_DATABASE=True`):** Queries Supabase PostgreSQL with PostGIS geometry types and GiST indexes.
- **Offline / Prototype Mode (`mock_fallback`):** If the database connection drops or credentials are unconfigured, the system transparently serves deterministic baseline datasets (`mock_data.py`), guaranteeing zero downtime during development, network dropouts, or jury evaluations.

---

## 🛠️ Technology Stack

| Layer | Technology | Version | Purpose & Architectural Rationale |
|---|---|---|---|
| **Backend Framework** | **FastAPI** | `>= 0.110.0` | High-throughput asynchronous REST API framework with native OpenAPI generation. |
| **ASGI Web Server** | **Uvicorn** | `>= 0.28.0` | Production ASGI web server with worker clustering and reload capabilities. |
| **Runtime** | **Python** | `3.10+` | Core programming language runtime. |
| **Validation & Settings** | **Pydantic / Settings** | `>= 2.6.0` | Strict type validation, environment configuration, and schema serialization. |
| **ORM & Spatial DB** | **SQLAlchemy / GeoAlchemy2** | `2.0+ / 0.14+` | Declarative relational mapping with PostGIS spatial column integration. |
| **Geospatial Processing** | **Shapely** | `>= 2.0.0` | In-memory computational geometry (buffers, unions, ray-casting containment). |
| **Database** | **PostgreSQL + PostGIS** | `15+` | Spatial database supporting `GEOMETRY(POINT, 4326)` and `GEOMETRY(POLYGON, 4326)`. |
| **Statutory Reporting** | **ReportLab** | `>= 4.2.0` | Programmatic two-page Section 38 administrative relocation dossier PDF generator. |
| **Frontend Framework** | **React.js** | `18.3.1` | Component-driven UI orchestrating interactive state and analytical views. |
| **Frontend Tooling** | **Vite** | `5.4.14` | High-speed frontend build tool and development server. |
| **Web Mapping Engine** | **Leaflet** | `1.9.4` | Lightweight client-side WebGIS rendering raster basemaps, pins, and polygons. |
| **UI Components & Icons** | **Lucide React** | `1.16.0` | Clean, accessible iconography for command center panels. |
| **Styling** | **Vanilla CSS3** | Custom | Responsive glassmorphic dark-mode design system with crisp contrast. |
| **External Routing** | **OSRM API** | `v1 driving` | Turn-by-turn road network routing and distance matrix calculation. |
| **Meteorology Feed** | **Open-Meteo API** | `v1 forecast` | Live meteorological telemetry, WMO weather classification, and temperature metrics. |

---

## 📐 GIS & Mathematical Risk Logic

### 1. Multi-Hazard Composite Risk Engine

Disaster risk formulation adheres to the United Nations Office for Disaster Risk Reduction (UNDRR) paradigm:

$$\text{Risk} = f(\text{Hazard}, \text{Exposure}, \text{Vulnerability})$$

Implemented in `backend/app/services/risk_engine.py`:

$$\mathcal{R}_i = 0.45 \cdot \mathcal{H}_i + 0.25 \cdot \mathcal{E}_i + 0.30 \cdot \mathcal{V}_i$$

Where:
- **Hazard ($\mathcal{H}_i$):** Quantifies physical triggers including terrain slope steepness ($>30^\circ$), 3-day antecedent rainfall ($>200\text{ mm}$ pore-pressure escalation), and historical disaster scars.
- **Exposure ($\mathcal{E}_i$):** Measures human concentration and asset exposure based on total population volume and single-access road isolation distance.
- **Vulnerability ($\mathcal{V}_i$):** Reflects socio-structural susceptibility, specifically the proportion of kutcha (non-engineered mud/thatch) dwellings and travel distance to emergency trauma care.

### 2. Risk Classification Tiers

Continuous scores ($\mathcal{R}_i \in [0, 100]$) are segmented into four administrative intervention tiers:

| Tier | Score Range | Color Code | Administrative Implication & Action Directive |
|---|:---:|:---:|---|
| **Critical (Red Zone)** | $75.0 \le \mathcal{R}_i \le 100.0$ | 🔴 Red | Unacceptable danger to life; gazetted for **Priority 1 Immediate Relocation (0–6 Months)**. |
| **High** | $55.0 \le \mathcal{R}_i < 75.0$ | 🟠 Orange | Severe hazard vulnerability; scheduled for **Priority 2 Short-Term Relocation (6–18 Months)**. |
| **Moderate** | $35.0 \le \mathcal{R}_i < 55.0$ | 🟡 Yellow | Moderate exposure; categorized for **Priority 3 Medium-Term Planned Scheme (18–36 Months)**. |
| **Low** | $0.0 \le \mathcal{R}_i < 35.0$ | 🟢 Green | Defensible terrain; designated for **Priority 4 In-Situ Monitoring** and sensor surveillance. |

### 3. Red Zone Spatial Buffering & Containment

A **Red Zone** represents a geographically bounded polygon where multi-hazard risk exceeds safety thresholds:
1. **Dynamic Safety Buffering:** A default metric buffer ($300\text{ m}$, scalable up to $500\text{ m}$) is applied around active hazard polygons using PostGIS `ST_Buffer` (projected to UTM `EPSG:32643`) or Shapely in-memory dilation to accommodate debris runout margins.
2. **Containment Audit:** Habitation points are evaluated via PostGIS `ST_Within(habitation.geom, red_zone.geom)` or ray-casting algorithms (`geo_utils.point_in_polygon`). Settlements inside buffered envelopes are flagged as candidates for proactive relocation.

### 4. Relocation Site Suitability (AHP 7-Factor Model)

Candidate recipient land parcels are scored using the Analytical Hierarchy Process (AHP) across 7 weighted dimensions in `backend/app/services/suitability_engine.py`:

$$\text{Suitability Score} = \sum_{j=1}^{7} w_j \cdot F_j$$

| Factor ($F_j$) | Weight ($w_j$) | Evaluation Criteria | Ideal Benchmark |
|---|:---:|---|---|
| **Hazard Safety** | `0.25` | Radial distance from active Red Zone hazard boundaries | $> 1,500\text{ m}$ safety margin |
| **Land Suitability** | `0.20` | Gentle terrain gradient minimizing construction risk | Slope $< 8^\circ$ (Max allowable: $15^\circ$) |
| **Water Availability** | `0.15` | Proximity to perennial freshwater aquifers | Meets CPHEEO consumption standard |
| **Road Accessibility** | `0.15` | Distance to all-weather state or national highways | $< 500\text{ m}$ paved access link |
| **Healthcare Access** | `0.10` | Travel distance to Primary Health Centers (PHCs) | $< 5\text{ km}$ ($< 30\text{ min}$ transit) |
| **Education Access** | `0.08` | Proximity to primary and secondary schools | $< 3\text{ km}$ commute corridor |
| **Carrying Capacity** | `0.07` | Extent of contiguous unencumbered public land | Land bank $> 5\text{ acres}$ ($20,000\text{ m}^2$) |

### 5. Carrying Capacity Assessment Model

Relocating an endangered community without auditing municipal carrying capacity risks creating secondary disasters (groundwater depletion, informal squalor, infrastructure collapse). The carrying capacity factor ($\mathcal{C}_k$) evaluates whether candidate parcel $k$ can sustain relocated population $P_{\text{reloc}}$:

$$\mathcal{C}_k = \min \left( \frac{\text{Land Area}_k}{P_{\text{reloc}} \cdot \theta_{\text{land}}}, \frac{\text{Daily Water}_k}{P_{\text{reloc}} \cdot \theta_{\text{water}}}, \frac{\text{Hospital Beds}_k}{P_{\text{reloc}} \cdot \theta_{\text{health}}}, \frac{\text{School Seats}_k}{P_{\text{reloc}} \cdot \theta_{\text{school}}} \right)$$

- **$\theta_{\text{land}}$:** Minimum per-capita spatial norm ($45\text{ m}^2/\text{person}$ inclusive of dwelling, circulation, and green buffers).
- **$\theta_{\text{water}}$:** CPHEEO potable water consumption benchmark ($135\text{ Liters Per Capita per Day}$).
- **$\theta_{\text{health}}$:** Primary healthcare ratio benchmark ($1\text{ bed per } 500\text{ residents}$).
- **Capacity Status:**
  - $\mathcal{C}_k \ge 1.0$: **Optimal** (Approved for resettlement).
  - $0.8 \le \mathcal{C}_k < 1.0$: **Near Capacity** (Requires targeted infrastructure expansion).
  - $\mathcal{C}_k < 0.8$: **Exceeded** (Resettlement rejected or split-allocation plan triggered).

### 6. Geodesic & Haversine Distance Metrics

The backend provides dual distance calculation strategies:
1. **Haversine Great-Circle Formulation (`backend/app/utils/geo_utils.py`):**
   Zero-dependency computation used during real-time parametric simulation:

   $$\Delta\sigma = 2 \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right), \quad d = R \cdot \Delta\sigma \quad (R = 6,371.0\text{ km})$$

2. **Projected PostGIS Metric Queries:**
   Transforms geographic coordinates to UTM Zone 43N (`EPSG:32643`) for high-precision planar distance measurement in meters:
   ```sql
   ST_Distance(ST_Transform(habitation.geom, 32643), ST_Transform(site.geom, 32643))
   ```

---

## 🔌 APIs, Integrations & Data Ingestion

### Data Provenance: Live vs. Prototype Baseline

To ensure transparency and engineering honesty, the repository explicitly delineates live operational integrations from prototype demo baselines:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DATA PROVENANCE MATRIX                            │
├──────────────────────────┬───────────────────────────────────────────────────┤
│ LIVE EXTERNAL FEEDS      │ • Open-Meteo REST API (real-time weather & temps) │
│                          │ • OSRM Routing Engine (live road driving routes)  │
│                          │ • OSM Overpass API (live infrastructure queries)  │
│                          │ • Ingestion Sync Endpoints (/api/v1/ingestion/*)  │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ PROTOTYPE BASELINE DATA  │ • 5 Monitored Districts (Raigad, Pune, etc.)      │
│                          │ • 15 Geocoded Vulnerable Habitations              │
│                          │ • 5 Audited Candidate Relocation Parcels          │
│                          │ • 3 Severe Hazard Red Zone Boundary Polygons      │
│                          │ • Seed Datasets in seed_data.py & mock_data.py    │
└──────────────────────────┴───────────────────────────────────────────────────┘
```

> [!NOTE]
> **Machine Learning Status:** The machine learning folder (`ml/`) contains architecture and pipeline scaffolding for spatial cross-validation and feature extraction. Operational risk scoring currently runs on the verified, deterministic multi-hazard mathematical engine with TreeSHAP factor attribution, ensuring auditability for disaster officials.

### External Ingestion & Integration Catalog

| External Service | Endpoint / Integration | Protocol | Role in Platform | Active Status |
|---|---|:---:|---|:---:|
| **Open-Meteo** | `https://api.open-meteo.com/v1/forecast` | REST / JSON | Live meteorological observations, WMO weather classification, temperature, humidity | 🟢 Live Connected |
| **OSRM Engine** | `https://router.project-osrm.org/route/v1/driving` | REST / JSON | Authoritative turn-by-turn road driving distance, evacuation duration, route geometry | 🟢 Live Connected |
| **OpenStreetMap** | `https://overpass-api.de/api/interpreter` | Overpass QL | Querying hospitals, schools, and road infrastructure within bounding boxes | 🟢 Live Ingestor |
| **ISRO Bhuvan** | `https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms` | OGC WMS | Landslide hazard zonation, flood inundation history, thematic wasteland layers | 🟡 WMS Adapter Configured |
| **IMD Mausam** | `https://mausam.imd.gov.in/api` | REST / JSON | Extreme rainfall trigger thresholds, district precipitation anomaly sync | 🟡 Adapter Configured |

---

## 🗄️ Database & PostGIS Architecture

### Entity-Relationship Architecture

The relational schema is implemented with SQLAlchemy 2.0 and GeoAlchemy2, supporting PostGIS geometries and GiST spatial indexing:

```text
                             ┌─────────────────────────┐
                             │        districts        │
                             ├─────────────────────────┤
                             │ PK id VARCHAR(50)       │
                             │    name VARCHAR(100)    │
                             │    state VARCHAR(100)   │
                             └───────────┬─────────────┘
                                         │ 1:N
                ┌────────────────────────┴────────────────────────┐
                │ 1:N                                             │ 1:N
                ▼                                                 ▼
 ┌─────────────────────────────┐                   ┌─────────────────────────────┐
 │         habitations         │                   │  candidate_relocation_sites │
 ├─────────────────────────────┤                   ├─────────────────────────────┤
 │ PK id VARCHAR(50)           │                   │ PK id VARCHAR(50)           │
 │ FK district_id VARCHAR(50)  │                   │ FK district_id VARCHAR(50)  │
 │ FK recommended_site_id      │◀──────────────────│    name VARCHAR(150)        │
 │    name VARCHAR(150)        │   assigned to     │    suitability_score FLOAT  │
 │    risk_score FLOAT         │                   │    usable_area_sqm FLOAT    │
 │    geom GEOMETRY(POINT,4326)│                   │    geom GEOMETRY(POINT,4326)│
 └──────────────┬──────────────┘                   └─────────────────────────────┘
                │ 1:N
                ▼
 ┌─────────────────────────────┐
 │    habitation_ai_factors    │
 ├─────────────────────────────┤
 │ PK id INTEGER (Auto-Inc)    │
 │ FK habitation_id (CASCADE)  │
 │    factor VARCHAR(150)      │
 │    impact VARCHAR(50)       │
 └─────────────────────────────┘

 ┌─────────────────────────────┐                   ┌─────────────────────────────┐
 │          red_zones          │                   │        system_alerts        │
 ├─────────────────────────────┤                   ├─────────────────────────────┤
 │ PK id VARCHAR(50)           │                   │ PK id VARCHAR(50)           │
 │    name VARCHAR(150)        │                   │    severity VARCHAR(30)     │
 │    hazard_type VARCHAR(100) │                   │    title VARCHAR(200)       │
 │    geom GEOMETRY(POLY,4326) │                   │    read BOOLEAN             │
 └─────────────────────────────┘                   └─────────────────────────────┘
```

### PostGIS Spatial Types & SRID:4326 Policy

All spatial database columns use the **WGS84 (`EPSG:4326`)** coordinate reference system:
- **Settlement Locations:** `GEOMETRY(geometry_type="POINT", srid=4326, spatial_index=True)`
- **Candidate Relocation Parcels:** `GEOMETRY(geometry_type="POINT", srid=4326, spatial_index=True)`
- **Hazard Red Zones:** `GEOMETRY(geometry_type="POLYGON", srid=4326, spatial_index=True)`
- **Spatial Indexing:** Binds Generalized Search Tree (`GIST`) indexes (`USING GIST (geom)`) across all geometry columns to guarantee sub-second spatial queries.

### Coordinate Translation Matrix

The codebase strictly enforces coordinate ordering rules to prevent latitude/longitude transposition errors:

| Layer / Component | Coordinate Format | Example Representation | Reference Implementation |
|---|---|---|---|
| **PostGIS Database** | `POINT(lon, lat)` (WKT) | `POINT(73.4912 18.0645)` | Native PostGIS geometry column |
| **GeoJSON Specification** | `[longitude, latitude]` | `[73.4912, 18.0645]` | `backend/app/utils/geo_utils.py` |
| **Leaflet WebGIS Client** | `[latitude, longitude]` | `[18.0645, 73.4912]` | Serialized in API response coordinates |

---

## 📂 Project Structure

Verified directory tree reflecting the actual repository implementation:

```text
SIH_PROTOTYPE/
├── alembic.ini                              # Alembic migration configuration
├── BACKEND.md                               # In-depth backend architecture and reference guide
├── README.md                                # Master project documentation (this file)
├── .env.example                             # Environment variable template
├── .gitignore                               # Git ignore rules for venv, node_modules, and secrets
│
├── backend/                                 # FastAPI Asynchronous Application Server
│   ├── requirements.txt                     # Backend Python dependencies
│   ├── alembic/                             # Database schema migration environment
│   │   ├── env.py                           # Migration runtime with GeoAlchemy2 support
│   │   └── versions/
│   │       └── 0001_initial_schema.py       # Baseline migration with PostGIS geometries
│   ├── app/                                 # Core backend package
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI factory, CORS, connection pre-warming
│   │   ├── api/v1/                          # REST HTTP routing layer
│   │   │   ├── router.py                    # Master v1 router aggregating all endpoints
│   │   │   └── endpoints/                   # Modular endpoint controllers
│   │   │       ├── alerts.py                # Early warning alerts API
│   │   │       ├── analytics.py             # Disaster management KPIs & risk distribution
│   │   │       ├── districts.py             # Monitored district profiles
│   │   │       ├── habitations.py           # Vulnerable settlements listing and detail
│   │   │       ├── ingestion.py             # External data ingestion and sync endpoints
│   │   │       ├── prioritization.py        # Phased administrative relocation queue
│   │   │       ├── red_zones.py             # Delineated hazard boundary polygons
│   │   │       ├── relocation_sites.py      # Candidate safe parcels catalog
│   │   │       ├── reports.py               # Section 38 dossier metadata & PDF stream
│   │   │       ├── routing.py               # OSRM road evacuation route engine
│   │   │       ├── search.py                # Unified multi-entity search endpoint
│   │   │       ├── simulation.py            # What-If parametric policy sandbox
│   │   │       └── weather.py               # Open-Meteo meteorological telemetry
│   │   ├── core/                            # Configuration & application settings
│   │   │   ├── __init__.py
│   │   │   └── config.py                    # Pydantic BaseSettings, URL validation, and CRS
│   │   ├── db/                              # Persistence and database access
│   │   │   ├── __init__.py
│   │   │   ├── session.py                   # Connection pooling and PostGIS health checks
│   │   │   ├── repository.py                # Dual-mode data access layer (Supabase / Mock)
│   │   │   ├── mock_data.py                 # Deterministic fallback dataset
│   │   │   └── seed_data.py                 # PostGIS spatial database seeding script
│   │   ├── models/                          # Schemas and ORM definitions
│   │   │   ├── __init__.py
│   │   │   ├── orm_models.py                # SQLAlchemy ORM models with PostGIS geometries
│   │   │   └── schemas.py                   # Pydantic request and response schemas
│   │   ├── services/                        # Business logic & scientific calculation engines
│   │   │   ├── __init__.py
│   │   │   ├── adapters/                    # External data source adapters
│   │   │   │   ├── base_adapter.py          # Abstract base adapter interface
│   │   │   │   ├── bhuvan_adapter.py        # ISRO NRSC Bhuvan WMS adapter
│   │   │   │   ├── imd_adapter.py           # IMD Mausam weather adapter
│   │   │   │   └── osm_adapter.py           # OpenStreetMap Overpass infrastructure adapter
│   │   │   ├── capacity_engine.py           # Carrying capacity evaluation engine
│   │   │   ├── gis_engine.py                # Geospatial PostGIS & Shapely operations
│   │   │   ├── ingestion_service.py         # Ingestion orchestration and sync ledger
│   │   │   ├── prioritization_engine.py     # 4-tier action queue ranking algorithm
│   │   │   ├── report_service.py            # Section 38 statutory PDF dossier generator
│   │   │   ├── risk_engine.py               # Multi-hazard composite risk & TreeSHAP scoring
│   │   │   ├── simulation_service.py        # Parametric resettlement sandbox service
│   │   │   └── suitability_engine.py        # 7-factor AHP candidate site scoring engine
│   │   └── utils/                           # Geospatial and formatting helpers
│   │       ├── __init__.py
│   │       └── geo_utils.py                 # Haversine distance, ray-casting, GeoJSON tools
│   └── tests/                               # Backend automated test suite (58+ passing tests)
│       ├── __init__.py
│       ├── test_api_endpoints.py            # REST endpoints, parameter validation, 404 tests
│       ├── test_database.py                 # Connection health, geometry bindings, ORM mapping
│       ├── test_engines.py                  # Unit tests for Risk, Suitability, Capacity engines
│       ├── test_gis_decision_engine.py      # Spatial buffering and safe parcel queries
│       ├── test_ingestion.py                # External data source adapters and sync tests
│       ├── test_routing.py                  # OSRM road evacuation route tests
│       ├── test_supabase_read.py            # Supabase read verification and coordinate tests
│       └── test_weather.py                  # Meteorological engine and weather code tests
│
├── frontend/                                # React 18 / Vite Interactive WebGIS Application
│   ├── index.html                           # HTML single-page entry point with fonts & Leaflet
│   ├── package.json                         # Frontend dependencies (React, Leaflet, Lucide)
│   ├── vite.config.js                       # Vite bundler configuration
│   ├── public/                              # Public static web assets
│   │   └── logo.svg                         # Government emblem SVG logo
│   └── src/                                 # Frontend source code
│       ├── App.jsx                          # Master application shell and layout orchestrator
│       ├── main.jsx                         # React DOM bootstrap entrypoint
│       ├── components/                      # Reusable UI component modules
│       │   ├── common/                      # Shared UI components
│       │   │   ├── GlobalSearchModal.jsx    # Unified Ctrl+K global search modal
│       │   │   └── KpiCard.jsx              # Disaster management headline metric cards
│       │   ├── habitation/                  # Settlement-specific components
│       │   │   └── HabitationDetailModal.jsx# Inspection modal with TreeSHAP XAI breakdown
│       │   ├── layout/                      # Layout components
│       │   │   ├── Navbar.jsx               # Header with district filter & alert center
│       │   │   └── Sidebar.jsx              # Collapsible navigation menu
│       │   ├── map/                         # WebGIS mapping components
│       │   │   └── GisMapViewer.jsx         # Leaflet interactive map canvas with layer toggles
│       │   └── relocation/                  # Relocation parcel components
│       │       └── CarryingCapacityGauge.jsx# Carrying capacity dials & resource audits
│       ├── data/                            # Client-side data
│       │   └── mockData.js                  # Comprehensive client-side fallback dataset
│       ├── pages/                           # 9 Dedicated administrative dashboard views
│       │   ├── Dashboard.jsx                # Command Center & Multi-Hazard Overview
│       │   ├── Habitations.jsx              # Vulnerable Settlements Registry & Profiler
│       │   ├── PriorityPlanning.jsx         # Phased Relocation Planning & Priority Queue
│       │   ├── RedZones.jsx                 # Multi-Hazard Red Zones & Buffer Viewer
│       │   ├── RelocationSites.jsx          # Candidate Safe Parcels Catalog
│       │   ├── Reports.jsx                  # Governance Dossiers & PDF Preview
│       │   ├── RiskAnalysis.jsx             # Risk Distribution & Multi-Hazard Analytics
│       │   ├── SiteSuitability.jsx          # Multi-Criteria AHP Suitability Comparison
│       │   └── WhatIfSimulation.jsx         # Parametric Policy Resettlement Sandbox
│       ├── services/                        # Client-side networking layer
│       │   └── api.js                       # Axios/Fetch client with graceful fallback
│       └── styles/                          # CSS design system
│           ├── index.css                    # Typography, CSS tokens, and resets
│           ├── dashboard.css                # Glassmorphic dashboard and panel styles
│           └── map.css                      # Leaflet map styling and popup overrides
│
├── data/                                    # Local data directories (raw, processed, samples)
├── docs/                                    # Technical architecture blueprints and specifications
├── gis/                                     # Scaffolding for standalone offline GIS pipelines
├── ml/                                      # Scaffolding for offline ML training pipelines
└── scripts/                                 # Operational utility scripts
```

---

## 🚀 Setup & Installation

### Prerequisites

- **Python:** Python 3.10 to 3.14 (`Python 3.14+` tested)
- **Node.js:** Node.js v18.0+ and npm v9.0+ (`Node v20+` recommended)
- **Git:** Git 2.40+ installed
- **Database (Optional):** Hosted Supabase PostgreSQL instance with PostGIS enabled, or a local PostgreSQL 15+ installation with `postgis`. *(If unconfigured, the platform automatically runs in deterministic prototype fallback mode).*

---

### Backend Setup (Python / FastAPI)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/SIH_backend.git
   cd SIH_backend/SIH_PROTOTYPE
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Windows (CMD):
   python -m venv .venv
   .\.venv\Scripts\activate.bat

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r backend/requirements.txt
   ```

---

### Frontend Setup (React / Vite)

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install JavaScript packages:**
   ```bash
   npm install
   ```

3. **Return to the prototype root:**
   ```bash
   cd ..
   ```

---

### Database Migrations & Seeding

*(Optional if using hosted Supabase or local PostgreSQL; skipped if running in fallback mode)*

1. **Apply Alembic spatial schema migrations:**
   ```bash
   alembic upgrade head
   ```

2. **Seed the database with districts, habitations, safe sites, and red zones:**
   ```bash
   python -m backend.app.db.seed_data
   ```

---

## ⚙️ Environment Variables

Create a `.env` file in `SIH_PROTOTYPE/` or in the workspace root based on `.env.example`:

```ini
# Application Configuration
APP_NAME="Intelligent GIS-Based Proactive Relocation DSS API"
APP_ENV=development
APP_DEBUG=true
PORT=8000
HOST=127.0.0.1
API_V1_STR=/api/v1

# CORS Allowed Origins
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Database Connection (Supabase PostgreSQL + PostGIS)
# Leave blank or omit to operate in zero-downtime mock fallback mode
DATABASE_URL=postgresql://postgres:your_password@your-host.supabase.co:5432/postgres
USE_DATABASE=true
DB_FIRST_MODE=true
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_TIMEOUT_SECONDS=10

# Coordinate Reference System (CRS) Settings
DEFAULT_STORAGE_CRS=EPSG:4326
DEFAULT_PROJECTED_CRS=EPSG:32643

# Algorithmic Thresholds
RED_ZONE_RISK_THRESHOLD=75.0
MAX_HABITATION_SLOPE_DEGREE=15.0
MIN_CONTIGUOUS_ACRES_RELOCATION=5.0
PER_CAPITA_LAND_SQM=45.0
PER_CAPITA_WATER_LPD=135.0

# External API Integrations
IMD_API_URL=https://mausam.imd.gov.in/api
OVERPASS_API_URL=https://overpass-api.de/api/interpreter
BHUVAN_WMS_URL=https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms
```

---

## 🏃 Running the Platform

### Starting the FastAPI Backend

From `SIH_PROTOTYPE/` (with your virtual environment activated):

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **API Base URL:** `http://127.0.0.1:8000`
- **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`
- **Liveness Health Check:** `http://127.0.0.1:8000/health`
- **Database / PostGIS Health Check:** `http://127.0.0.1:8000/health/db`

---

### Starting the React WebGIS Dashboard

From `SIH_PROTOTYPE/frontend/`:

```bash
npm run dev
```

- **Web Dashboard URL:** `http://localhost:5173`

---

## 📡 REST API Documentation

The backend provides 17 RESTful HTTP routes under `/api/v1` with automatic OpenAPI schema validation:

| # | Method | Path | Summary | Key Parameters | Response Type |
|:---:|:---:|---|---|---|---|
| **1** | `GET` | `/` | Root service descriptor | None | Service metadata JSON |
| **2** | `GET` | `/health` | API liveness health check | None | `{"status": "healthy", ...}` |
| **3** | `GET` | `/health/db` | Database & PostGIS connection check | None | DB status & PostGIS version JSON |
| **4** | `GET` | `/api/v1/analytics/kpis` | Disaster management headline KPIs | `district` (optional) | `KpiMetricsResponse` |
| **5** | `GET` | `/api/v1/analytics/risk-distribution` | Risk distribution across tiers | None | `RiskDistributionResponse` |
| **6** | `GET` | `/api/v1/districts` | Monitored district administrative profiles | None | `List[DistrictProfile]` |
| **7** | `GET` | `/api/v1/habitations` | Filterable habitations catalog | `search`, `district`, `risk_tier`, `priority` | `List[HabitationResponse]` |
| **8** | `GET` | `/api/v1/habitations/{id}` | Single settlement profile + TreeSHAP XAI | `id` (path string) | `HabitationResponse` (404 if missing) |
| **9** | `GET` | `/api/v1/relocation-sites` | Candidate safe parcels catalog | None | `List[CandidateSiteResponse]` |
| **10** | `GET` | `/api/v1/relocation-sites/{id}` | Candidate parcel profile + AHP metrics | `id` (path string) | `CandidateSiteResponse` (404 if missing) |
| **11** | `GET` | `/api/v1/hazards/red-zones` | Severe hazard boundary polygons | None | `List[RedZoneResponse]` |
| **12** | `GET` | `/api/v1/prioritization/queue` | Phased relocation queue (P1–P4) | None | `List[PriorityQueueItemResponse]` |
| **13** | `POST`| `/api/v1/simulation/what-if` | Parametric resettlement simulation | `SimulationRequest` (population, threshold) | `SimulationResponse` |
| **14** | `GET` | `/api/v1/alerts` | Early warning system alerts | None | `List[AlertResponse]` |
| **15** | `POST`| `/api/v1/alerts/mark-all-read` | Acknowledge active system alerts | None | `{"status": "success", "markedCount": N}` |
| **16** | `GET` | `/api/v1/search` | Unified cross-entity search (Ctrl+K) | `q` (query string) | `SearchResponse` |
| **17** | `POST`| `/api/v1/reports/export-dossier` | Generate relocation dossier metadata | `DossierRequest` | `DossierMetadataResponse` |
| **18** | `GET` | `/api/v1/reports/download` | Binary download of Section 38 PDF | `habitation_id` (optional) | Binary `application/pdf` stream |
| **19** | `GET` | `/api/v1/weather/current` | Live meteorological telemetry | `district`, `city` | `WeatherCurrentResponse` |
| **20** | `GET` | `/api/v1/routing/route` | OSRM road evacuation route | `from_lat`, `from_lon`, `to_lat`, `to_lon` | GeoJSON route geometry & travel time |
| **21** | `GET` | `/api/v1/ingestion/status` | Authoritative data provenance status | None | `IngestionStatusResponse` |
| **22** | `POST`| `/api/v1/ingestion/sync/all` | Trigger multi-source sync | None | Aggregated ingestion results JSON |

---

## 🧪 Testing & Quality Assurance

The backend includes an automated test suite verifying mathematical formulas, API endpoints, PostGIS spatial queries, and routing logic:

```bash
# Run core test suites from SIH_PROTOTYPE/
python -m unittest backend.tests.test_engines backend.tests.test_api_endpoints backend.tests.test_database backend.tests.test_routing backend.tests.test_weather backend.tests.test_gis_decision_engine -v
```

### Test Suite Coverage

| Test Module | Tests | Focus Area | Status |
|---|:---:|---|:---:|
| `test_engines.py` | 17 | Multi-hazard risk math, AHP suitability weights, carrying capacity thresholds, Haversine formulas | 🟢 PASS |
| `test_api_endpoints.py` | 19 | 17 REST routes, parameter validation, 404 handling, Section 38 PDF download stream | 🟢 PASS |
| `test_database.py` | 6 | DB connectivity, PostGIS extension verification, ORM relationships, credential security | 🟢 PASS |
| `test_routing.py` | 4 | OSRM road driving route queries, GeoJSON output, distance/duration validation | 🟢 PASS |
| `test_weather.py` | 5 | Open-Meteo telemetry integration, WMO weather codes, prototype fallback resilience | 🟢 PASS |
| `test_gis_decision_engine.py` | 7 | Dynamic Red Zone polygon buffers, safe parcel criteria, spatial containment audits | 🟢 PASS |
| **Total Automated Tests** | **58** | **Comprehensive backend, GIS, and integration validation** | **58/58 PASS** |

---

## 📊 Current Data & Prototype Scope

To provide an immediate, hands-on demonstration without requiring external GIS downloads during hackathon presentations, the prototype is pre-configured with curated baseline datasets:

- **Monitored Geographic Corridors:**
  - **Raigad & Pune Districts (Maharashtra):** Western Ghats landslide and flash-flood corridors (e.g., Taliye Wadi, Malin, Jui Wadi).
  - **Ratnagiri District (Maharashtra):** Coastal escarpment and heavy precipitation zones.
  - **Wayanad District (Kerala):** High-relief tea estate landslide scarps (e.g., Meppadi, Chooralmala).
  - **Shimla District (Himachal Pradesh):** Himalayan cloudburst and slope instability corridors.
- **Pre-Loaded Entities:**
  - **15 Georeferenced Vulnerable Settlements:** Full demographic breakdown, kutcha housing percentages, and TreeSHAP explainability factor attributions.
  - **5 Audited Candidate Relocation Parcels:** Pre-calculated slope angles, aquifer indicators, road distance, and carrying capacity ratios.
  - **3 Severe Hazard Red Zone Boundary Polygons:** PostGIS `POLYGON` geometries with enclosing settlement calculations.

---

## 🔮 Future Scope & Scaling Roadmap

- [ ] **Automated Satellite Raster Pipeline:** Ingestion of Copernicus GLO-30 DEM and Sentinel-2 optical imagery directly into PostGIS raster tables (`raster2pgsql`) for dynamic slope recalculation.
- [ ] **Real-Time IoT Webhooks:** Automated ingestors for Central Water Commission (CWC) river telemetry and IMD Doppler radar alerts.
- [ ] **Multi-User RBAC & Audit Ledger:** Role-based access control distinguishing State Relief Commissioners (SDMA approval authority) from District Collectors (DDMA inspection officers).
- [ ] **Offline Mobile Field Survey App:** React Native / Flutter field application for on-ground revenue surveyors to verify candidate relocation parcel soil stability and borehole yield.
- [ ] **Micro-Topography via UAV LiDAR:** High-resolution drone elevation mapping resolving localized excavation cuts and retaining wall slip planes ($< 5\text{ m}$).

---

## 🤝 Contributing & License

### Contributing Guidelines

1. **Fork the Repository** on GitHub.
2. **Create a Feature Branch:**
   ```bash
   git checkout -b feature/spatial-hazard-engine
   ```
3. **Adhere to Code Standards:**
   - Python code must follow **PEP 8** standards with explicit type annotations.
   - All spatial geometries must explicitly handle their Coordinate Reference System (storage: `EPSG:4326`, metric calculations: `EPSG:32643`).
   - Frontend React components must maintain clean separation of concerns and use the established CSS design system.
4. **Ensure All Tests Pass:**
   ```bash
   python -m unittest backend.tests.test_engines backend.tests.test_api_endpoints
   ```
5. **Submit a Pull Request** with a concise description of your changes and test results.

### License

This project was developed for **Smart India Hackathon (SIH) 2026** under **Problem Statement ID 191**. Prospective distribution is licensed under the [MIT License](LICENSE) (or as designated by the participating institution and hackathon guidelines).

---

<div align="center">
  <sub>Developed for Smart India Hackathon 2026 • Problem Statement ID 191 • Domain: AI + GIS + Disaster Management</sub>
</div>