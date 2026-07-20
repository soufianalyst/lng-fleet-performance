package charterparty

import (
	"math"
	"time"
)

type CharterTerms struct {
	GuaranteedSpeedKN     float64 `json:"guaranteed_speed_kn"`
	GuaranteedConsumption float64 `json:"guaranteed_consumption_tonne_day"`
	MaxDraftM             float64 `json:"max_draft_m"`
	LoadCondition         string  `json:"load_condition"`
	SpeedTolerancePct     float64 `json:"speed_tolerance_pct"`
	ConsumptionTolerancePct float64 `json:"consumption_tolerance_pct"`
}

type VoyagePerformance struct {
	ActualSpeedKN        float64   `json:"actual_speed_kn"`
	ActualConsumption    float64   `json:"actual_consumption_tonne_day"`
	WeatherCorrectedSpeed float64  `json:"weather_corrected_speed_kn"`
	WeatherCorrectedConsumption float64 `json:"weather_corrected_consumption_tonne_day"`
	SpeedDeviationPct    float64   `json:"speed_deviation_pct"`
	ConsumptionDeviationPct float64 `json:"consumption_deviation_pct"`
	SpeedCompliant       bool      `json:"speed_compliant"`
	ConsumptionCompliant bool      `json:"consumption_compliant"`
	OverallCompliant     bool      `json:"overall_compliant"`
}

type WeatherCondition struct {
	WindSpeedMS         float64 `json:"wind_speed_ms"`
	WindDirectionDeg    float64 `json:"wind_direction_deg"`
	WaveHeightM         float64 `json:"wave_height_m"`
	CurrentSpeedMS      float64 `json:"current_speed_ms"`
	CurrentDirectionDeg float64 `json:"current_direction_deg"`
	SeaState           int     `json:"sea_state"`
}

func VerifyPerformance(actualSpeed, actualConsumption float64, terms CharterTerms, avgWeather WeatherCondition, durationHrs float64) VoyagePerformance {
	windCorrection := weatherSpeedCorrection(avgWeather.WindSpeedMS, avgWeather.WaveHeightM)
	correctedSpeed := actualSpeed + windCorrection
	if correctedSpeed <= 0 {
		correctedSpeed = actualSpeed
	}

	weatherFactor := 1.0 + (math.Abs(windCorrection) / math.Max(actualSpeed, 0.1)) * 0.5
	correctedConsumption := actualConsumption / weatherFactor

	speedDev := ((correctedSpeed - terms.GuaranteedSpeedKN) / terms.GuaranteedSpeedKN) * 100
	consDev := ((correctedConsumption - terms.GuaranteedConsumption) / terms.GuaranteedConsumption) * 100

	durationDays := durationHrs / 24
	if durationDays <= 0 {
		durationDays = 1
	}
	actualDailyCons := actualConsumption

	return VoyagePerformance{
		ActualSpeedKN:         math.Round(actualSpeed*100) / 100,
		ActualConsumption:     math.Round(actualDailyCons*100) / 100,
		WeatherCorrectedSpeed: math.Round(correctedSpeed*100) / 100,
		WeatherCorrectedConsumption: math.Round(correctedConsumption*100) / 100,
		SpeedDeviationPct:     math.Round(speedDev*100) / 100,
		ConsumptionDeviationPct: math.Round(consDev*100) / 100,
		SpeedCompliant:        math.Abs(speedDev) <= terms.SpeedTolerancePct,
		ConsumptionCompliant:  consDev <= terms.ConsumptionTolerancePct,
		OverallCompliant:      math.Abs(speedDev) <= terms.SpeedTolerancePct &&
			consDev <= terms.ConsumptionTolerancePct,
	}
}

func weatherSpeedCorrection(windMS, waveM float64) float64 {
	correction := 0.0
	if windMS > 10 {
		correction -= (windMS - 10) * 0.05
	}
	if waveM > 2 {
		correction -= (waveM - 2) * 0.15
	}
	return correction
}

func EstimateWeather(courseHeadingDeg float64, weather []WeatherCondition, duration time.Duration) WeatherCondition {
	if len(weather) == 0 {
		return WeatherCondition{}
	}

	avgWind := 0.0
	avgWave := 0.0
	count := 0
	for _, w := range weather {
		avgWind += w.WindSpeedMS
		avgWave += w.WaveHeightM
		count++
	}

	if count > 0 {
		avgWind /= float64(count)
		avgWave /= float64(count)
	}

	return WeatherCondition{
		WindSpeedMS:  math.Round(avgWind*10) / 10,
		WaveHeightM:  math.Round(avgWave*100) / 100,
		SeaState:     int(math.Round(avgWave / 0.5)),
	}
}
