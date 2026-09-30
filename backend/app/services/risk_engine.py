import math
from typing import Dict, Any, List, Tuple, Optional


class RiskEngine:
    """Deterministic Multi-Hazard Risk Engine implementing:
    Composite Risk = 0.45 x Hazard (H) + 0.25 x Exposure (E) + 0.30 x Vulnerability (V)
    Normalized to a 0 - 100 continuous statutory administrative index.
    
    All factor attributions are transparent, deterministic spatial rules.
    Zero ML / Zero fabricated TreeSHAP.
    """

    CRITICAL_THRESHOLD = 75.0
    HIGH_THRESHOLD = 55.0
    MODERATE_THRESHOLD = 35.0

    @classmethod
    def calculate_hazard_index(
        cls,
        slope_degree: float = 10.0,
        rainfall_3d_mm: float = 50.0,
        rainfall_anomaly_pct: float = 0.0,
        historical_disasters: int = 0,
        distance_to_red_zone_km: Optional[float] = None,
    ) -> float:
        """Computes physical hazard susceptibility score (0 to 100).
        
        Sub-factors:
        1. Topographic Slope (0 - 35): Slope failure threshold accelerates > 28-30 degrees
        2. Hyetometric Precipitation (0 - 35): Trigger curve breaches > 200mm / 72h
        3. Proximity to Active Hazard Zone (0 - 15): Severe penalty if inside or contiguous
        4. Historical Disasters Recurrence (0 - 15)
        """
        # Slope sub-score (0-35)
        if slope_degree > 35.0:
            slope_score = 35.0
        elif slope_degree > 5.0:
            slope_score = (slope_degree / 35.0) * 35.0
        else:
            slope_score = 4.0

        # Rainfall sub-score (0-35)
        rain_score = min(35.0, (max(0.0, rainfall_3d_mm) / 250.0) * 35.0)

        # Proximity to active red zone (0-15)
        if distance_to_red_zone_km is not None:
            if distance_to_red_zone_km <= 0.2:
                proximity_score = 15.0  # Inside or boundary
            elif distance_to_red_zone_km <= 1.0:
                proximity_score = 10.0
            elif distance_to_red_zone_km <= 3.0:
                proximity_score = 5.0
            else:
                proximity_score = 0.0
        else:
            # Baseline proxy from rainfall anomaly if hazard polygon distance unavailable
            proximity_score = min(15.0, max(0.0, rainfall_anomaly_pct * 0.15))

        # Historical recurrence (0-15)
        history_score = min(15.0, max(0, historical_disasters) * 3.5)

        total_h = round(slope_score + rain_score + proximity_score + history_score, 2)
        return min(100.0, max(0.0, total_h))

    @classmethod
    def calculate_exposure_index(cls, population: int, households: int = 0) -> float:
        """Computes human and asset exposure score (0 to 100).
        Uses logarithmic scaling calibrated for Himalayan / Western Ghats rural settlements
        ranging from 50 to 15,000 residents.
        """
        if population <= 0:
            return 5.0
        # log10(10)=1.0 -> 25, log10(100)=2.0 -> 50, log10(1000)=3.0 -> 75, log10(10000)=4.0 -> 100
        pop_score = (math.log10(max(10, population)) / 4.0) * 100.0
        return round(min(100.0, max(0.0, pop_score)), 2)

    @classmethod
    def calculate_vulnerability_index(
        cls,
        kutcha_housing_pct: float = 30.0,
        road_isolation_km: float = 3.0,
        hospital_distance_km: float = 5.0,
    ) -> float:
        """Computes socio-demographic and structural fragility score (0 to 100).
        
        Sub-factors:
        1. Kutcha mud/unreinforced dwelling weight: 45%
        2. Evacuation road corridor cutoff isolation: 35%
        3. Emergency medical response transit delay: 20%
        """
        # Kutcha structural fragility (0 - 45)
        housing_sub = (min(100.0, max(0.0, kutcha_housing_pct)) / 100.0) * 45.0

        # Road isolation (0 - 35) (critical cutoff > 15 km)
        road_sub = min(35.0, (max(0.0, road_isolation_km) / 15.0) * 35.0)

        # Emergency medical access decay (0 - 20) (decay > 25 km)
        hospital_sub = min(20.0, (max(0.0, hospital_distance_km) / 25.0) * 20.0)

        total_v = round(housing_sub + road_sub + hospital_sub, 2)
        return min(100.0, max(0.0, total_v))

    @classmethod
    def calculate_composite_risk(
        cls,
        slope_degree: float,
        rainfall_3d_mm: float,
        rainfall_anomaly_pct: float,
        historical_disasters: int,
        population: int,
        households: int,
        kutcha_housing_pct: float,
        road_isolation_km: float,
        hospital_distance_km: float,
        distance_to_red_zone_km: Optional[float] = None,
    ) -> Tuple[float, str, float]:
        """Calculates Composite Risk Score (0-100), Risk Tier, and Vulnerability Index.
        Formula: Composite = 0.45 * H + 0.25 * E + 0.30 * V
        """
        h = cls.calculate_hazard_index(
            slope_degree=slope_degree,
            rainfall_3d_mm=rainfall_3d_mm,
            rainfall_anomaly_pct=rainfall_anomaly_pct,
            historical_disasters=historical_disasters,
            distance_to_red_zone_km=distance_to_red_zone_km,
        )
        e = cls.calculate_exposure_index(population=population, households=households)
        v = cls.calculate_vulnerability_index(
            kutcha_housing_pct=kutcha_housing_pct,
            road_isolation_km=road_isolation_km,
            hospital_distance_km=hospital_distance_km,
        )

        composite = round((0.45 * h) + (0.25 * e) + (0.30 * v), 1)
        composite = max(0.0, min(100.0, composite))

        tier = cls.classify_tier(composite)
        return composite, tier, v

    @classmethod
    def classify_tier(cls, risk_score: float) -> str:
        """Classifies continuous risk score into statutory administrative risk tier."""
        if risk_score >= cls.CRITICAL_THRESHOLD:
            return "Critical"
        elif risk_score >= cls.HIGH_THRESHOLD:
            return "High"
        elif risk_score >= cls.MODERATE_THRESHOLD:
            return "Moderate"
        else:
            return "Low"

    @classmethod
    def generate_xai_factors(cls, habitation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates transparent deterministic rule-based factor attribution cards
        answering: 'Why is this settlement classified as High or Critical Risk?'.
        
        Zero ML / Zero fabricated TreeSHAP.
        """
        factors = []
        slope = habitation_data.get("slopeDegree", 0.0)
        rain = habitation_data.get("rainfall3dMm", 0.0)
        kutcha = habitation_data.get("kutchaHousingPercent", 0.0)
        road = habitation_data.get("roadIsolationDistanceKm", 0.0)
        hospital = habitation_data.get("hospitalDistanceKm", 0.0)
        dist_hazard = habitation_data.get("distanceFromRedZoneKm")

        if dist_hazard is not None and dist_hazard <= 0.5:
            factors.append({
                "factor": f"Active Hazard Zone Contiguity ({dist_hazard} km)",
                "impact": "High",
                "direction": "up",
                "description": "Settlement boundary intersects severe landslide scarp or flash flood inundation corridor.",
                "weight": 35.0,
            })

        if slope > 28.0:
            factors.append({
                "factor": f"Topographic Slope Gradient ({slope}°)",
                "impact": "High",
                "direction": "up",
                "description": "Exceeds critical shear failure threshold (28°) for weathered volcanic basalt.",
                "weight": round(min(40.0, slope * 0.95), 1),
            })

        if rain > 180.0:
            factors.append({
                "factor": f"3-Day Extreme Precipitation ({rain} mm)",
                "impact": "High",
                "direction": "up",
                "description": "Exceeds 90th percentile hyetometric threshold accelerating pore water pressure.",
                "weight": round(min(45.0, rain * 0.14), 1),
            })

        if kutcha > 45.0:
            factors.append({
                "factor": f"Kutcha Mud-Walled Structures ({kutcha}%)",
                "impact": "High",
                "direction": "up",
                "description": "Majority of dwellings lack reinforced lateral load-bearing and water resistance.",
                "weight": round(kutcha * 0.28, 1),
            })

        if road > 8.0:
            factors.append({
                "factor": f"Single Evacuation Road Isolation ({road} km)",
                "impact": "Medium",
                "direction": "up",
                "description": "Single-corridor cul-de-sac prone to slope cuts, bridge failure, and relief cutoffs.",
                "weight": round(min(30.0, road * 1.5), 1),
            })

        if hospital > 15.0:
            factors.append({
                "factor": f"Hospital Transit Delay ({hospital} km)",
                "impact": "Medium",
                "direction": "up",
                "description": "Emergency medical response exceeds statutory golden-hour window.",
                "weight": round(min(20.0, hospital * 0.8), 1),
            })

        if not factors:
            factors.append({
                "factor": "Geological Bedrock Stability",
                "impact": "Low",
                "direction": "down",
                "description": "Competent basalt foundation and gentle gradient reduce slope slip mechanics.",
                "weight": 25.0,
            })

        return factors


risk_engine = RiskEngine()
