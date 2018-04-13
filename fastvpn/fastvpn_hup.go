package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	//	"golang.org/x/net/ipv4"
)

const (
	BUFFERSIZE = 1500
	MTU        = "1300"
)

var (
	listen  = flag.String("listen", ":8796", "listen ip, default listent in :8796")
	peerMap = make(map[string]string)
)

func checkFatalErr(err error, msg string) {
	if err != nil {
		log.Println(msg)
		log.Fatal(err)
	}
}

func main() {
	flag.Parse()
	listenAddr, err := net.ResolveUDPAddr("udp", *listen)
	checkFatalErr(err, "Unable to get UDP socket:")

	// 监听在8796
	conn, err := net.ListenUDP("udp", listenAddr)
	checkFatalErr(err, "Unable to listen on UDP socket:")
	log.Println("server start at 0.0.0.0", listen)

	defer conn.Close()

	buf := make([]byte, BUFFERSIZE)

	for {
		var clientAddr *net.UDPAddr
		n, addr, err := conn.ReadFromUDP(buf)

		fmt.Println("Reciverd data: ", string(buf[:n]))
		if err != nil || n == 0 {
			log.Println("Error: ", err)
			continue
		}
		//获取内网地址
		privateIP := string(buf[:n])

		//将内网地址及其公网的连接端口保存在peermap里面
		peerMap[privateIP] = fmt.Sprintf("%v", addr)
		fmt.Printf("peer map: \n%+v\n", peerMap)
		msg, err := json.Marshal(peerMap)

		if err != nil {
			log.Println("...")
		}

		// 遍历所有peer列表，并发送peermap所有peerclient
		for _, val := range peerMap {
			clientAddr, err = net.ResolveUDPAddr("udp", val)
			if err != nil {
				continue
			}
			conn.WriteToUDP(msg, clientAddr)
		}

	}
}
