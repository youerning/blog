package main

import (
	"fmt"

	"github.com/kr/pretty"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type Host struct {
	gorm.Model
	// 城市-区-环境-团队(组)-应用名
	Hostname string
	IP       string
	CPU      uint
	// 以MB为单位
	MEM uint
}

var Hosts = []Host{
	{Hostname: "sh-pd-prd-ops-mysql", IP: "10.20.99.38", CPU: 4, MEM: 8 * 1024},
	{Hostname: "sz-ft-test-dev-es", IP: "10.30.99.138", CPU: 8, MEM: 16 * 1024},
	{Hostname: "hk-st-dev-dev-redis", IP: "10.44.12.28", CPU: 2, MEM: 8 * 1024},
}

func main() {
	var err error
	db, err := gorm.Open(sqlite.Open("test.db"), &gorm.Config{})
	if err != nil {
		panic("连接数据库失败")
	}

	// 迁移 schema
	err = db.AutoMigrate(&Host{})
	if err != nil {
		panic("创建或迁移数据表失败")
	}
	pretty.Println("x")

	// 插入数据
	db.Create(&Hosts)

	var hosts []Host
	var host Host
	// 查询所有数据, 用hosts接收
	db.Find(&hosts)
	pretty.Println(hosts)

	// 查询id为1的单个数据， 用host接收
	db.First(&host, 1)
	fmt.Println("查询")
	fmt.Println("所有数据: ")
	pretty.Println(hosts)
	fmt.Println("单条数据: ")
	pretty.Println(host)
	fmt.Println("修改")
	db.Model(&host).Update("Hostname", "changed")
	db.First(&host, 1)
	pretty.Println("id为1修改后的数据: ")
	pretty.Println(&host)

	// 删除数据
	db.Delete(&host)
	err = db.First(&host, 1).Error
	if err != nil {
		fmt.Println("err: ", err.Error())
	}
}
