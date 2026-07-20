package models

import (
	"time"

	"github.com/google/uuid"
)

type AlertSeverity string

const (
	AlertSeverityLow       AlertSeverity = "low"
	AlertSeverityMedium    AlertSeverity = "medium"
	AlertSeverityHigh      AlertSeverity = "high"
	AlertSeverityCritical  AlertSeverity = "critical"
)

type AlertCategory string

const (
	AlertCategoryCII       AlertCategory = "cii"
	AlertCategoryETS       AlertCategory = "ets"
	AlertCategoryCompliance AlertCategory = "compliance"
	AlertCategoryPerformance AlertCategory = "performance"
	AlertCategoryBOG       AlertCategory = "bog"
	AlertCategoryECA       AlertCategory = "eca"
	AlertCategoryCharterparty AlertCategory = "charterparty"
	AlertCategoryMaintenance AlertCategory = "maintenance"
)

type Alert struct {
	ID          uuid.UUID      `json:"id"`
	VesselID    uuid.UUID      `json:"vessel_id"`
	VoyageID    *uuid.UUID     `json:"voyage_id,omitempty"`
	Category    AlertCategory  `json:"category"`
	Severity    AlertSeverity  `json:"severity"`
	Title       string         `json:"title"`
	Description string         `json:"description"`
	Resolved    bool           `json:"resolved"`
	ResolvedAt  *time.Time     `json:"resolved_at,omitempty"`
	CreatedAt   time.Time      `json:"created_at"`
}
