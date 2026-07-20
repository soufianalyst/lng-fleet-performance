package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/lngfleet/platform/internal/models"
	"github.com/lngfleet/platform/internal/services"
)

type TelemetryHandler struct {
	svc *services.TelemetryService
}

func NewTelemetryHandler(svc *services.TelemetryService) *TelemetryHandler {
	return &TelemetryHandler{svc: svc}
}

type telemetryQueryParams struct {
	From string `form:"from"`
	To   string `form:"to"`
}

func (h *TelemetryHandler) Query(c *gin.Context) {
	vesselID, err := uuid.Parse(c.Param("vesselId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel id"})
		return
	}

	var params telemetryQueryParams
	if err := c.ShouldBindQuery(&params); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": err.Error()})
		return
	}

	from := time.Now().UTC().Add(-24 * time.Hour)
	to := time.Now().UTC()
	if params.From != "" {
		if t, err := time.Parse(time.RFC3339, params.From); err == nil {
			from = t
		}
	}
	if params.To != "" {
		if t, err := time.Parse(time.RFC3339, params.To); err == nil {
			to = t
		}
	}

	data, err := h.svc.Query(c.Request.Context(), vesselID, from, to)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": data})
}

func (h *TelemetryHandler) Ingest(c *gin.Context) {
	var t models.Telemetry
	if err := c.ShouldBindJSON(&t); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": err.Error()})
		return
	}
	if err := h.svc.Ingest(c.Request.Context(), &t); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"status": "success", "data": t})
}

func (h *TelemetryHandler) Latest(c *gin.Context) {
	vesselID, err := uuid.Parse(c.Param("vesselId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel id"})
		return
	}
	data, err := h.svc.Latest(c.Request.Context(), vesselID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "error", "message": "no telemetry found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": data})
}
