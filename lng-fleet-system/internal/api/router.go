package api

import (
	"github.com/gin-gonic/gin"
	"github.com/lngfleet/platform/internal/api/handlers"
	"github.com/lngfleet/platform/internal/api/middleware"
	"github.com/lngfleet/platform/internal/services"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func NewRouter(
	env string,
	jwtSecret string,
	vesselSvc *services.VesselService,
	voyageSvc *services.VoyageService,
	telemetrySvc *services.TelemetryService,
	ciiSvc *services.CIIService,
	dashboardSvc *services.DashboardService,
) *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(middleware.RequestLogger())
	r.Use(func(c *gin.Context) {
		c.Set("env", env)
		c.Next()
	})

	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "success", "data": gin.H{"service": "lng-fleet-system", "version": "1.0.0"}})
	})
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	auth := r.Group("/api/v1", middleware.JWTAuth(jwtSecret))

	vh := handlers.NewVesselHandler(vesselSvc)
	vessels := auth.Group("/vessels")
	{
		vessels.GET("", vh.List)
		vessels.GET("/:id", vh.GetByID)
		vessels.POST("", vh.Create)
		vessels.PUT("/:id", vh.Update)
		vessels.DELETE("/:id", vh.Delete)
	}

	voyageH := handlers.NewVoyageHandler(voyageSvc)
	voyages := auth.Group("/voyages")
	{
		voyages.GET("", voyageH.List)
		voyages.GET("/:id", voyageH.GetByID)
		voyages.POST("", voyageH.Create)
		voyages.PUT("/:id", voyageH.Update)
		voyages.DELETE("/:id", voyageH.Delete)
	}

	th := handlers.NewTelemetryHandler(telemetrySvc)
	telemetry := auth.Group("/telemetry")
	{
		telemetry.GET("/:vesselId", th.Query)
		telemetry.POST("", th.Ingest)
		telemetry.GET("/:vesselId/latest", th.Latest)
	}

	ch := handlers.NewCIIHandler(ciiSvc)
	cii := auth.Group("/cii")
	{
		cii.GET("/:vesselId", ch.GetHistory)
		cii.GET("/:vesselId/forecast", ch.Forecast)
		cii.POST("/:vesselId/calculate", ch.Calculate)
	}

	dh := handlers.NewDashboardHandler(dashboardSvc)
	dash := auth.Group("/dashboard")
	{
		dash.GET("/fleet-overview", dh.FleetOverview)
		dash.GET("/vessel/:vesselId", dh.VesselDetail)
		dash.GET("/cii-summary", dh.CIISummary)
		dash.GET("/compliance", dh.ComplianceSummary)
		dash.GET("/alerts", dh.Alerts)
	}

	return r
}
