package main

import (
	"net/http"
	"os"

	"github.com/gin-gonic/gin"

	// ⚠️ change to: <module-from-go.mod>/controllers
	"api.tickleright.in/go/controllers"
)

func main() {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())

	// sanity check
	r.GET("/health", func(c *gin.Context) { c.JSON(200, gin.H{"status": "ok"}) })

	// see what's registered
	r.GET("/go/_debug", func(c *gin.Context) { c.JSON(200, controllers.Registry) })

	// dynamic dispatch: /go/:name -> controllers.Registry[name]
	r.Any("/go/:name", func(c *gin.Context) {
		name := c.Param("name")
		if h, ok := controllers.Registry[name]; ok {
			h(c)
			return
		}
		c.JSON(http.StatusNotFound, gin.H{"ok": false, "error": "unknown endpoint", "file": name})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "5000"
	}
	_ = r.Run("127.0.0.1:" + port)
}
