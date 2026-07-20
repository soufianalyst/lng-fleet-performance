package bog

import "math"

type TankType string

const (
	TankMoss     TankType = "MOSS"
	TankMembrane TankType = "MEMBRANE"
	TankTypeC    TankType = "TYPE_C"
	TankTypeB    TankType = "TYPE_B"
)

type TankSpec struct {
	Type           TankType
	CapacityCBM    float64
	SurfaceAreaM2  float64
	InsulationK    float64
	DesignBOR      float64
	VaporPressureBar float64
}

type OperatingConditions struct {
	TankFillPct    float64
	AmbientTempC   float64
	LNGSaturationTempC float64
	VaporPressure  float64
	SloshingFactor float64
}

type BORResult struct {
	BORPercentPerDay  float64 `json:"bor_percent_per_day"`
	BORRateKgHr       float64 `json:"bor_rate_kg_hr"`
	DailyLossCBM      float64 `json:"daily_loss_cbm"`
	DailyLossTonne    float64 `json:"daily_loss_tonne"`
	ThermalFlowMW     float64 `json:"thermal_flow_mw"`
}

func EstimateBOR(spec TankSpec, cond OperatingConditions) BORResult {
	deltaT := cond.AmbientTempC - cond.LNGSaturationTempC
	if deltaT < 0 {
		deltaT = 0
	}

	thermalFlow := spec.SurfaceAreaM2 * spec.InsulationK * deltaT / 1000

	lngDensity := kgPerCBM(cond.LNGSaturationTempC)
	vaporizationHeat := 510.0

	borKgHr := (thermalFlow * 1000) / vaporizationHeat
	liquidVolume := spec.CapacityCBM * (cond.TankFillPct / 100)

	borPctPerDay := 0.0
	if liquidVolume > 0 {
		borPctPerDay = (borKgHr * 24) / (liquidVolume * lngDensity) * 100
	}

	borPctPerDay *= (1 + cond.SloshingFactor)

	borCBM := (borPctPerDay / 100) * liquidVolume
	borTonne := borCBM * lngDensity

	return BORResult{
		BORPercentPerDay:  math.Round(borPctPerDay*1000) / 1000,
		BORRateKgHr:       math.Round(borKgHr*100) / 100,
		DailyLossCBM:      math.Round(borCBM*100) / 100,
		DailyLossTonne:    math.Round(borTonne*100) / 100,
		ThermalFlowMW:     math.Round(thermalFlow*1000) / 1000,
	}
}

func kgPerCBM(tempC float64) float64 {
	if tempC < -170 {
		return 470
	}
	if tempC < -165 {
		return 460
	}
	if tempC < -160 {
		return 450
	}
	return 440
}
