package main

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/kr/pretty"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

type Host struct {
	gorm.Model
	// 城市-区-环境-团队(组)-应用名
	Hostname string `json:"hostname"`
	IP       string `json:"ip"`
	CPU      uint   `json:"cpu"`
	// 以MB为单位
	MEM uint `json:"mem"`
}

var Hosts = []Host{
	{Hostname: "sh-pd-prd-ops-mysql", IP: "10.20.99.38", CPU: 4, MEM: 8 * 1024},
	{Hostname: "sz-ft-test-dev-es", IP: "10.30.99.138", CPU: 8, MEM: 16 * 1024},
	{Hostname: "hk-st-dev-dev-redis", IP: "10.44.12.28", CPU: 2, MEM: 8 * 1024},
}

type HostAPI struct{}

func (h *HostAPI) List(offset, limit int) (hosts []Host) {
	DB.Offset(offset).Limit(limit).Find(&hosts)
	return
}

func (h *HostAPI) Create(host *Host) error {
	err := DB.Create(host).Error
	return err
}

func (h *HostAPI) Get(id int) (host Host) {
	DB.Find(&host, id)
	return
}

func (h *HostAPI) Update(id int, updates *Host) error {
	var host *Host
	err := DB.First(&host, id).Error
	if err != nil {
		return err
	}
	err = DB.Model(&host).Updates(updates).Error
	return err
}

func (h *HostAPI) Delete(id int) error {
	var host Host
	err := DB.First(&host, id).Error
	if err != nil {
		return err
	}
	err = DB.Delete(&host).Error
	return err
}

type HostJson struct {
	Hostname string `json:"hostname" form:"hostname"`
	IP       string `json:"ip" form:"ip"`
	CPU      uint   `json:"cpu" form:"cpu" bind:"required,gt=0"`
	// 以MB为单位
	MEM uint `json:"mem" form:"mem" binding:"required,gt=0"`
}

func main() {
	var err error
	DB, err = gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		panic("连接数据库失败")
	}

	// 迁移 schema
	err = DB.AutoMigrate(&Host{})
	if err != nil {
		panic("创建或迁移数据表失败")
	}
	pretty.Println("x")

	// 插入数据
	DB.Create(&Hosts)

	api := &HostAPI{}
	router := gin.Default()
	router.GET("/hosts", func(ctx *gin.Context) {
		offset, limit := 0, 10
		queryOffset := ctx.Query("offset")
		if queryOffset != "" {
			// 削减了错误检查的代码
			offset, _ = strconv.Atoi(queryOffset)
		}
		queryLimit := ctx.Query("limit")
		if queryLimit != "" {
			// 削减了错误检查的代码
			limit, _ = strconv.Atoi(queryLimit)
		}
		ctx.JSON(http.StatusOK, gin.H{
			"msg":  "success",
			"data": api.List(offset, limit),
		})
	})
	router.POST("/hosts", func(ctx *gin.Context) {
		var host Host
		if err := ctx.ShouldBindJSON(&host); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": err,
			})
			return
		}

		if err := api.Create(&host); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": err,
			})
			return
		}
		ctx.JSON(http.StatusOK, gin.H{
			"msg":  "success",
			"data": host,
		})
	})

	router.GET("/hosts/:id", func(ctx *gin.Context) {
		var id int
		pathId := ctx.Param("id")
		if _id, err := strconv.Atoi(pathId); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": "请输入合法的数字值id",
			})
		} else {
			id = _id
		}
		host := api.Get(id)
		ctx.JSON(http.StatusOK, gin.H{
			"msg":  "success",
			"data": host,
		})
	})

	router.PUT("/hosts/:id", func(ctx *gin.Context) {
		var id int
		var updates Host
		pathId := ctx.Param("id")
		if _id, err := strconv.Atoi(pathId); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": "请输入合法的数字值id",
			})
			return
		} else {
			id = _id
		}
		if err := ctx.ShouldBindJSON(&updates); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": err,
			})
			return
		}

		if err := api.Update(id, &updates); err != nil {
			ctx.JSON(http.StatusOK, gin.H{
				"msg": err.Error(),
			})
		}
		host := api.Get(id)
		ctx.JSON(http.StatusOK, gin.H{
			"msg":  "success",
			"data": host,
		})
	})

	router.DELETE("/hosts/:id", func(ctx *gin.Context) {
		var id int
		pathId := ctx.Param("id")
		if _id, err := strconv.Atoi(pathId); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": "请输入合法的数字值id",
			})
			return
		} else {
			id = _id
		}

		if err := api.Delete(id); err != nil {
			ctx.JSON(http.StatusBadRequest, gin.H{
				"msg": err.Error(),
			})
			return
		}
		ctx.JSON(http.StatusOK, gin.H{
			"msg": "success",
		})
	})
	router.Run()
}
