package weather

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
)

type OpenMeteoClient struct {
	baseURL string
	client  *http.Client
}

type ForecastPoint struct {
	Time             time.Time `json:"time"`
	WindSpeed10M     float64   `json:"wind_speed_10m_ms"`
	WindDirection10M float64   `json:"wind_direction_10m_deg"`
	WaveHeight       float64   `json:"wave_height_m"`
	SwellHeight      float64   `json:"swell_height_m"`
	SignificantWaveH float64   `json:"significant_wave_height_m"`
	AirTemperature   float64   `json:"air_temperature_c"`
	SeaSurfaceTemp   float64   `json:"sea_surface_temperature_c"`
	CurrentSpeed     float64   `json:"current_speed_ms"`
	CurrentDirection float64   `json:"current_direction_deg"`
}

type openMeteoResponse struct {
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Hourly    struct {
		Time                    []string  `json:"time"`
		WindSpeed10M            []float64 `json:"wind_speed_10m"`
		WindDirection10M        []float64 `json:"wind_direction_10m"`
		WaveHeight              []float64 `json:"wave_height"`
		SwellWaveHeight         []float64 `json:"swell_wave_height"`
		SignificantWaveHeight   []float64 `json:"significant_wave_height"`
		Temperature2M           []float64 `json:"temperature_2m"`
		SeaSurfaceTemperature   []float64 `json:"sea_surface_temperature"`
		OceanCurrentVelocity    []float64 `json:"ocean_current_velocity"`
		OceanCurrentDirection   []float64 `json:"ocean_current_direction"`
	} `json:"hourly"`
}

func NewOpenMeteoClient() *OpenMeteoClient {
	return &OpenMeteoClient{
		baseURL: "https://api.open-meteo.com/v1",
		client:  &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *OpenMeteoClient) Forecast(lat, lon float64, hours int) ([]ForecastPoint, error) {
	if hours < 1 {
		hours = 24
	}
	if hours > 168 {
		hours = 168
	}

	params := url.Values{}
	params.Set("latitude", fmt.Sprintf("%.4f", lat))
	params.Set("longitude", fmt.Sprintf("%.4f", lon))
	params.Set("hourly", "wind_speed_10m,wind_direction_10m,wave_height,swell_wave_height,significant_wave_height,temperature_2m,sea_surface_temperature,ocean_current_velocity,ocean_current_direction")
	params.Set("forecast_hours", fmt.Sprintf("%d", hours))
	params.Set("timezone", "UTC")

	endpoint := fmt.Sprintf("%s/forecast?%s", c.baseURL, params.Encode())
	resp, err := c.client.Get(endpoint)
	if err != nil {
		return nil, fmt.Errorf("open-meteo request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("open-meteo status %d: %s", resp.StatusCode, string(body))
	}

	var omResp openMeteoResponse
	if err := json.Unmarshal(body, &omResp); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	points := make([]ForecastPoint, 0, len(omResp.Hourly.Time))
	for i, t := range omResp.Hourly.Time {
		parsed, err := time.Parse("2006-01-02T15:04", t)
		if err != nil {
			continue
		}
		fp := ForecastPoint{
			Time:             parsed,
			WindSpeed10M:     safeFloat(omResp.Hourly.WindSpeed10M, i),
			WindDirection10M: safeFloat(omResp.Hourly.WindDirection10M, i),
			WaveHeight:       safeFloat(omResp.Hourly.WaveHeight, i),
			SwellHeight:      safeFloat(omResp.Hourly.SwellWaveHeight, i),
			SignificantWaveH: safeFloat(omResp.Hourly.SignificantWaveHeight, i),
			AirTemperature:   safeFloat(omResp.Hourly.Temperature2M, i),
			SeaSurfaceTemp:   safeFloat(omResp.Hourly.SeaSurfaceTemperature, i),
			CurrentSpeed:     safeFloat(omResp.Hourly.OceanCurrentVelocity, i),
			CurrentDirection: safeFloat(omResp.Hourly.OceanCurrentDirection, i),
		}
		points = append(points, fp)
	}
	return points, nil
}

func (c *OpenMeteoClient) Historical(lat, lon float64, start, end time.Time) ([]ForecastPoint, error) {
	params := url.Values{}
	params.Set("latitude", fmt.Sprintf("%.4f", lat))
	params.Set("longitude", fmt.Sprintf("%.4f", lon))
	params.Set("hourly", "wind_speed_10m,wind_direction_10m,wave_height,swell_wave_height,significant_wave_height,temperature_2m,sea_surface_temperature,ocean_current_velocity,ocean_current_direction")
	params.Set("start_date", start.Format("2006-01-02"))
	params.Set("end_date", end.Format("2006-01-02"))
	params.Set("timezone", "UTC")

	endpoint := fmt.Sprintf("%s/forecast?%s", c.baseURL, params.Encode())
	resp, err := c.client.Get(endpoint)
	if err != nil {
		return nil, fmt.Errorf("open-meteo historical request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("open-meteo status %d: %s", resp.StatusCode, string(body))
	}

	var omResp openMeteoResponse
	if err := json.Unmarshal(body, &omResp); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	points := make([]ForecastPoint, 0, len(omResp.Hourly.Time))
	for i, t := range omResp.Hourly.Time {
		parsed, err := time.Parse("2006-01-02T15:04", t)
		if err != nil {
			continue
		}
		points = append(points, ForecastPoint{
			Time:             parsed,
			WindSpeed10M:     safeFloat(omResp.Hourly.WindSpeed10M, i),
			WindDirection10M: safeFloat(omResp.Hourly.WindDirection10M, i),
			WaveHeight:       safeFloat(omResp.Hourly.WaveHeight, i),
			SwellHeight:      safeFloat(omResp.Hourly.SwellWaveHeight, i),
			SignificantWaveH: safeFloat(omResp.Hourly.SignificantWaveHeight, i),
			AirTemperature:   safeFloat(omResp.Hourly.Temperature2M, i),
			SeaSurfaceTemp:   safeFloat(omResp.Hourly.SeaSurfaceTemperature, i),
			CurrentSpeed:     safeFloat(omResp.Hourly.OceanCurrentVelocity, i),
			CurrentDirection: safeFloat(omResp.Hourly.OceanCurrentDirection, i),
		})
	}
	return points, nil
}

func safeFloat(slice []float64, idx int) float64 {
	if idx < len(slice) {
		return slice[idx]
	}
	return 0
}
