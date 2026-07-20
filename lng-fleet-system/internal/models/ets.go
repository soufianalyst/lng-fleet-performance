package models

import (
	"time"

	"github.com/google/uuid"
)

type ETSScheme string

const (
	ETSSchemeEU    ETSScheme = "EU_ETS"
	ETSSchemeUK    ETSScheme = "UK_ETS"
	ETSSchemeIMOSc ETSScheme = "IMO_Scoping"
)

type ETSComplianceStatus string

const (
	ETSStatusCompliant    ETSComplianceStatus = "compliant"
	ETSStatusPartial      ETSComplianceStatus = "partial"
	ETSStatusNonCompliant ETSComplianceStatus = "non_compliant"
)

type ETSRecord struct {
	ID               uuid.UUID            `json:"id"`
	VesselID         uuid.UUID            `json:"vessel_id"`
	Year             int                  `json:"year"`
	Scheme           ETSScheme            `json:"scheme"`
	TotalEmissionsTonne float64           `json:"total_emissions_tonne"`
	VerifiedEmissionsTonne *float64       `json:"verified_emissions_tonne,omitempty"`
	AllowancesAllocated float64           `json:"allowances_allocated"`
	AllowancesSurrendered float64          `json:"allowances_surrendered"`
	AllowancesShortfall *float64           `json:"allowances_shortfall,omitempty"`
	ComplianceStatus  ETSComplianceStatus  `json:"compliance_status"`
	CarbonPriceEUR    *float64            `json:"carbon_price_eur,omitempty"`
	EstimatedCostEUR  *float64            `json:"estimated_cost_eur,omitempty"`
	PortsVisited      []string            `json:"ports_visited,omitempty"`
	CreatedAt         time.Time           `json:"created_at"`
	UpdatedAt         time.Time           `json:"updated_at"`
}
