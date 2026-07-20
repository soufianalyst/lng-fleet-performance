package geofencing

type ECAZone struct {
	Name      string
	MinLat    float64
	MaxLat    float64
	MinLon    float64
	MaxLon    float64
	Boundary  [][2]float64
}

func (z *ECAZone) Contains(lat, lon float64) bool {
	return lat >= z.MinLat && lat <= z.MaxLat &&
		lon >= z.MinLon && lon <= z.MaxLon
}

func ECAZones() []ECAZone {
	return []ECAZone{
		{
			Name:   "Baltic Sea",
			MinLat: 53.0, MaxLat: 66.0,
			MinLon: 9.0, MaxLon: 30.0,
		},
		{
			Name:   "North Sea",
			MinLat: 48.0, MaxLat: 62.0,
			MinLon: -5.0, MaxLon: 10.0,
		},
		{
			Name:   "North American East Coast",
			MinLat: 24.0, MaxLat: 48.0,
			MinLon: -82.0, MaxLon: -50.0,
		},
		{
			Name:   "US Caribbean",
			MinLat: 8.0, MaxLat: 22.0,
			MinLon: -90.0, MaxLon: -60.0,
		},
		{
			Name:   "Mediterranean Sea",
			MinLat: 30.0, MaxLat: 46.0,
			MinLon: -6.0, MaxLon: 36.0,
		},
		{
			Name:   "North American West Coast",
			MinLat: 30.0, MaxLat: 52.0,
			MinLon: -128.0, MaxLon: -116.0,
		},
	}
}

func InAnyECAZone(lat, lon float64) (bool, string) {
	for _, z := range ECAZones() {
		if z.Contains(lat, lon) {
			return true, z.Name
		}
	}
	return false, ""
}
