package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/lngfleet/platform/internal/models"
	"github.com/lngfleet/platform/internal/services"
)

type VoyageHandler struct {
	svc *services.VoyageService
}

func NewVoyageHandler(svc *services.VoyageService) *VoyageHandler {
	return &VoyageHandler{svc: svc}
}

func (h *VoyageHandler) List(c *gin.Context) {
	vesselIDStr := c.Query("vessel_id")
	var vesselID *uuid.UUID
	if vesselIDStr != "" {
		parsed, err := uuid.Parse(vesselIDStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid vessel_id"})
			return
		}
		vesselID = &parsed
	}
	voyages, err := h.svc.List(c.Request.Context(), vesselID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": voyages})
}

func (h *VoyageHandler) GetByID(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid voyage id"})
		return
	}
	voyage, err := h.svc.GetByID(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"status": "error", "message": "voyage not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": voyage})
}

func (h *VoyageHandler) Create(c *gin.Context) {
	var v models.Voyage
	if err := c.ShouldBindJSON(&v); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": err.Error()})
		return
	}
	if err := h.svc.Create(c.Request.Context(), &v); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"status": "success", "data": v})
}

func (h *VoyageHandler) Update(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid voyage id"})
		return
	}
	var v models.Voyage
	if err := c.ShouldBindJSON(&v); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": err.Error()})
		return
	}
	v.ID = id
	if err := h.svc.Update(c.Request.Context(), &v); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": v})
}

func (h *VoyageHandler) Delete(c *gin.Context) {
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": "error", "message": "invalid voyage id"})
		return
	}
	if err := h.svc.Delete(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "message": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success", "data": nil})
}
