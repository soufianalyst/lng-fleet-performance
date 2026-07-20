package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/lngfleet/platform/internal/services"
)

type CIIHandler struct {
	svc *services.CIIService
}

func NewCIIHandler(svc *services.CIIService) *CIIHandler {
	return &CIIHandler{svc: svc}
}

func (h *CIIHandler) GetHistory(c *gin.Context) {
	vesselID, err := uuid.Parse(c.Param("vesselId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel id"})
		return
	}
	records, err := h.svc.GetHistory(c.Request.Context(), vesselID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": records})
}

func (h *CIIHandler) Calculate(c *gin.Context) {
	vesselID, err := uuid.Parse(c.Param("vesselId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel id"})
		return
	}
	year := 2025
	if y := c.Query("year"); y != "" {
		if parsed, err := strconv.Atoi(y); err == nil {
			year = parsed
		}
	}
	record, err := h.svc.Calculate(c.Request.Context(), vesselID, year)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": record})
}

func (h *CIIHandler) Forecast(c *gin.Context) {
	vesselID, err := uuid.Parse(c.Param("vesselId"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel id"})
		return
	}
	records, err := h.svc.Forecast(c.Request.Context(), vesselID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": records})
}
