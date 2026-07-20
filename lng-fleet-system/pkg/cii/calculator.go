package cii

import "math"

func Calculate(fuelConsumptionTonne, distanceNM, co2EmissionsTonne, capacityCBM float64) float64 {
	if distanceNM <= 0 || capacityCBM <= 0 {
		return 0
	}
	cii := co2EmissionsTonne / (distanceNM * capacityCBM / 1000)
	return math.Round(cii*10000) / 10000
}

func RequiredCII(year int, capacityCBM float64) float64 {
	ref := referenceCII(capacityCBM)
	rf := reductionFactor(year)
	required := ref * (1 - rf)
	return math.Round(required*10000) / 10000
}

func Rating(attained, required float64, year int, capacityCBM float64) string {
	if required <= 0 {
		return "C"
	}
	ratio := attained / required
	rf := reductionFactor(year)

	upperA := 1.0
	upperB := 1.0 + 0.10*(1-rf)
	upperC := 1.0 + 0.15*(1-rf)
	upperD := 1.0 + 0.20*(1-rf)

	switch {
	case ratio < upperA:
		return "A"
	case ratio < upperB:
		return "B"
	case ratio < upperC:
		return "C"
	case ratio < upperD:
		return "D"
	default:
		return "E"
	}
}

func referenceCII(capacityCBM float64) float64 {
	return 4200 * math.Pow(capacityCBM/1000, -0.65)
}

func reductionFactor(year int) float64 {
	reductions := map[int]float64{
		2019: 0.00, 2020: 0.00, 2021: 0.00, 2022: 0.00, 2023: 0.05,
		2024: 0.07, 2025: 0.09, 2026: 0.11, 2027: 0.13, 2028: 0.15,
		2029: 0.17, 2030: 0.20,
	}
	if rf, ok := reductions[year]; ok {
		return rf
	}
	if year > 2030 {
		return 0.20 + float64(year-2030)*0.02
	}
	return 0.0
}
