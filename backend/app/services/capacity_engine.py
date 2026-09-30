from typing import Dict, Any, Optional


class CapacityEngine:
    """Carrying Capacity Assessment Engine.
    Prevents secondary humanitarian and environmental disasters by auditing
    population absorption against:
    1. Land Acreage Norm: 45 m²/person (Indian Town Planning / Rehabilitation Standard)
    2. Potable Water Supply Norm: 135 Liters/Person/Day (CPHEEO Standard)
    3. Emergency Healthcare Norm: 1 hospital bed per 500 residents
    
    Implements Liebig's Law of the Minimum: the feasible absorption capacity
    is strictly governed by the single most restrictive constraint.
    """

    PER_CAPITA_LAND_SQM = 45.0          # Indian Town Planning rehabilitation standard
    PER_CAPITA_WATER_LPD = 135.0        # CPHEEO Potable Water Supply Standard (Liters/Person/Day)
    PEOPLE_PER_HOSPITAL_BED = 500       # National Health Systems Resource Centre guidance

    @classmethod
    def calculate_water_demand_kl(cls, population: int) -> float:
        """Calculates daily potable water demand in kilo-liters (kL/day).
        Demand = (Population x 135 Liters) / 1000
        """
        return round((population * cls.PER_CAPITA_WATER_LPD) / 1000.0, 1)

    @classmethod
    def calculate_land_capacity(cls, usable_area_sqm: float) -> int:
        """Calculates maximum sustainable resident population based on usable land acreage."""
        if usable_area_sqm <= 0:
            return 0
        return int(usable_area_sqm / cls.PER_CAPITA_LAND_SQM)

    @classmethod
    def evaluate_carrying_capacity(
        cls,
        site_capacity: int,
        target_population: int,
        potable_water_supply_kl: float,
        available_hospital_beds: int = 10,
        usable_area_sqm: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Performs full carrying capacity audit for a candidate relocation parcel,
        evaluating Land, Water, and Healthcare ceilings and returning the limiting factor.
        """
        # 1. Land Absorption Ceiling
        land_capacity = (
            cls.calculate_land_capacity(usable_area_sqm)
            if usable_area_sqm and usable_area_sqm > 0
            else site_capacity
        )
        gross_capacity = land_capacity

        # 2. Water Availability Ceiling (CPHEEO 135 LPD)
        if potable_water_supply_kl and potable_water_supply_kl > 0:
            water_capacity = int((potable_water_supply_kl * 1000.0) / cls.PER_CAPITA_WATER_LPD)
        else:
            water_capacity = None

        # 3. Emergency Healthcare Ceiling (1 bed per 500 residents)
        if available_hospital_beds is not None and available_hospital_beds >= 0:
            health_capacity = available_hospital_beds * cls.PEOPLE_PER_HOSPITAL_BED
        else:
            health_capacity = None

        # 4. Liebig Feasible Capacity (most restrictive constraint)
        candidate_ceilings = [c for c in (land_capacity, water_capacity, health_capacity) if c is not None and c > 0]
        feasible_capacity = min(candidate_ceilings) if candidate_ceilings else site_capacity

        # 5. Bottleneck / Limiting Factor Attribution
        if water_capacity is not None and water_capacity == feasible_capacity and water_capacity < land_capacity:
            limiting_factor = "Potable Water Supply (CPHEEO 135 LPD)"
        elif health_capacity is not None and health_capacity == feasible_capacity and health_capacity < land_capacity:
            limiting_factor = "Emergency Healthcare Beds (1:500 Norm)"
        else:
            limiting_factor = "Land Area & Topography (45 m²/person)"

        # 6. Utilization and Headroom
        effective_capacity = max(1, feasible_capacity)
        headroom = feasible_capacity - target_population
        utilization_pct = round((target_population / effective_capacity) * 100, 1)

        water_needed_kl = cls.calculate_water_demand_kl(target_population)
        is_water_safe = (
            potable_water_supply_kl >= water_needed_kl
            if potable_water_supply_kl is not None and potable_water_supply_kl > 0
            else True
        )
        carrying_capacity_factor = round(feasible_capacity / max(1, target_population), 2)

        beds_required = max(1, int(target_population / cls.PEOPLE_PER_HOSPITAL_BED))

        if utilization_pct > 100:
            capacity_status = "Deficit Risk"
            feasibility = "Requires Split Relocation"
        elif utilization_pct > 85:
            capacity_status = "Moderate"
            feasibility = "Suitable with Minor Works"
        else:
            capacity_status = "Optimal"
            feasibility = "Feasible"

        return {
            "allocatedPopulation": target_population,
            "maximumAbsorption": feasible_capacity,
            "grossCapacity": gross_capacity,
            "feasibleCapacity": feasible_capacity,
            "remainingCapacity": headroom,
            "utilizationPercent": utilization_pct,
            "potableWaterDailyNeededKl": water_needed_kl,
            "potableWaterDailySuppliedKl": potable_water_supply_kl,
            "isWaterSafe": is_water_safe,
            "hospitalBedsRequired": beds_required,
            "hospitalBedsAvailable": available_hospital_beds,
            "carryingCapacityFactor": carrying_capacity_factor,
            "capacityStatus": capacity_status,
            "absorptionFeasibility": feasibility,
            "limitingFactor": limiting_factor,
            "landCapacity": land_capacity,
            "waterCapacity": water_capacity,
            "healthCapacity": health_capacity,
        }


capacity_engine = CapacityEngine()
