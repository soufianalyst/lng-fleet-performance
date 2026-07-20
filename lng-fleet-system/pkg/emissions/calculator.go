package emissions

import "math"

type EngineType string

const (
	EngineDFDE   EngineType = "DFDE"
	EngineTFDE   EngineType = "TFDE"
	EngineMEGI   EngineType = "ME-GI"
	EngineXDF    EngineType = "X-DF"
	EngineSteam   EngineType = "Steam"
)

type FuelType string

const (
	FuelHFO       FuelType = "HFO"
	FuelMGO       FuelType = "MGO"
	FuelLNG       FuelType = "LNG"
	FuelLNGPilot  FuelType = "LNG_Pilot"
)

type EmissionFactors struct {
	CO2   float64
	NOx   float64
	SOx   float64
	CH4   float64
	PM    float64
	N2O   float64
}

var fuelFactors = map[FuelType]EmissionFactors{
	FuelHFO: {CO2: 3.114, NOx: 0.087, SOx: 0.050, CH4: 0.00003, PM: 0.007, N2O: 0.00016},
	FuelMGO: {CO2: 3.206, NOx: 0.081, SOx: 0.007, CH4: 0.00003, PM: 0.002, N2O: 0.00016},
	FuelLNG: {CO2: 2.750, NOx: 0.007, SOx: 0.000, CH4: 0.028, PM: 0.000, N2O: 0.00011},
}

type FuelConsumption struct {
	HFOTonnes  float64 `json:"hfo_tonnes"`
	MGOTonnes  float64 `json:"mgo_tonnes"`
	LNGTonnes  float64 `json:"lng_tonnes"`
}

type EmissionsResult struct {
	CO2Total  float64 `json:"co2_total_tonnes"`
	NOxTotal  float64 `json:"nox_total_tonnes"`
	SOxTotal  float64 `json:"sox_total_tonnes"`
	CH4Total  float64 `json:"ch4_total_tonnes"`
	PMTotal   float64 `json:"pm_total_tonnes"`
	N2OTotal  float64 `json:"n2o_total_tonnes"`
	CO2WEQ    float64 `json:"co2_equivalent_tonnes"`
}

func Calculate(consumption FuelConsumption, engineType EngineType) EmissionsResult {
	var co2, nox, sox, ch4, pm, n2o float64

	for _, pair := range []struct {
		tonnes float64
		fuel   FuelType
	}{
		{consumption.HFOTonnes, FuelHFO},
		{consumption.MGOTonnes, FuelMGO},
		{consumption.LNGTonnes, FuelLNG},
	} {
		if factors, ok := fuelFactors[pair.fuel]; ok {
			co2 += pair.tonnes * factors.CO2
			nox += pair.tonnes * factors.NOx
			sox += pair.tonnes * factors.SOx
			ch4 += pair.tonnes * factors.CH4
			pm += pair.tonnes * factors.PM
			n2o += pair.tonnes * factors.N2O
		}
	}

	methaneSlipFactor := 0.028
	switch engineType {
	case EngineDFDE:
		methaneSlipFactor = 0.035
	case EngineTFDE:
		methaneSlipFactor = 0.030
	case EngineMEGI:
		methaneSlipFactor = 0.001
	case EngineXDF:
		methaneSlipFactor = 0.015
	case EngineSteam:
		methaneSlipFactor = 0.001
	}
	ch4FromLNG := consumption.LNGTonnes * methaneSlipFactor
	ch4 += ch4FromLNG

	co2weq := co2 + (ch4 * 28) + (n2o * 265)

	return EmissionsResult{
		CO2Total: round(co2),
		NOxTotal: round(nox),
		SOxTotal: round(sox),
		CH4Total: round(ch4),
		PMTotal:  round(pm),
		N2OTotal: round(n2o),
		CO2WEQ:   round(co2weq),
	}
}

func round(v float64) float64 {
	return math.Round(v*1000) / 1000
}
