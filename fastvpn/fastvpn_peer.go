package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/exec"
	"strings"

	// "fastvpn/common"
	"github.com/songgao/water"
	"golang.org/x/net/ipv4"
)

const (
	BUFFERSIZE = 1500
	MTU        = "1300"
)

var (
	hubServer = flag.String("hub", "", "server addr like 192.168.11.100:8796")
	local     = flag.String("local", "", "local ip like 172.16.97.101")
	listen    = flag.String("listen", ":6222", "udp for bind")
	port      = flag.String("port", "9999", "local port like 9999, default 9999, if you want to run multi clinet in same machine,change the port")
	peerMap   = make(map[string]string)
)

func checkFatalErr(err error, msg string) {
	if err != nil {
		log.Println(msg)
		log.Fatal(err)
	}
}

func runIP(args ...string) {
	cmd := exec.Command("/sbin/ip", args...)
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout

	err := cmd.Run()

	if err != nil {
		log.Fatal("Error runing /sbin/ip:", err)
	}
}

func main() {
	flag.Parse()
	// parse args
	if *hubServer == "" {
		flag.Usage()
		log.Fatal("\nhub Server is not specified")
	}

	if *local == "" {
		flag.Usage()
		log.Fatal("\nlocal ip is not specified")
	}

	if *port == "" {
		*port = fmt.Sprintf(":%s", *port)
	}

	// 将地址字符串解析成*net.UDPAddr
	hubAddr, err := net.ResolveUDPAddr("udp", *hubServer)
	checkFatalErr(err, "Unable to resolve server UDP socket")
	listenAddr, err := net.ResolveUDPAddr("udp", *listen)
	checkFatalErr(err, "Unable to resolve local UDP socket")

	// 初始化创建的tun设备的配置文件
	config := water.Config{
		DeviceType: water.TUN,
	}

	// 创建一个tun设备
	iface, err := water.New(config)
	checkFatalErr(err, "Unable to allocate TUN interface: ")
	log.Println("Interface allocated: ", iface.Name())

	// 设置ip地址并启动设备
	runIP("link", "set", "dev", iface.Name(), "mtu", MTU)
	runIP("addr", "add", *local, "dev", iface.Name())
	runIP("link", "set", "dev", iface.Name(), "up")

	// 监听一个udp socket,通过listenUDP创建的socket,既能发送到指定的ip地址也能接受
	conn, err := net.ListenUDP("udp", listenAddr)
	checkFatalErr(err, "Unable to connect server")
	defer conn.Close()
	privateIP := strings.Split(*local, "/")
	// 将自己的内网IP发送给hubserver
	conn.WriteToUDP([]byte(privateIP[0]), hubAddr)

	go func() {
		buf := make([]byte, BUFFERSIZE)

		// 不停的接受信息
		for {
			n, addr, err := conn.ReadFromUDP(buf)

			if addr.String() == hubAddr.String() {
				log.Println("recieve data from server:")

				// 解析hubserver发送过来的peermap
				err = json.Unmarshal(buf[:n], &peerMap)
				if err != nil {
					log.Println("peermap unmarshal error")
					log.Println(err)
				}
			} else {
				log.Println("recive data from peer:")
			}

			if err != nil || n == 0 {
				fmt.Println("Error: ", err)
				continue
			}
			log.Println(string(buf[:n]))
			// 将对端发送过来的数据写到本地的tun设备
			iface.Write(buf[:n])
		}

	}()

	packet := make([]byte, BUFFERSIZE)

	// 不停的读取本地tun设备接受到的数据包
	for {
		plen, err := iface.Read(packet)
		if err != nil {
			break
		}

		// 解析数据包头部
		header, _ := ipv4.ParseHeader(packet[:plen])
		dstIP := header.Dst.String()
		// 如果数据发送的目标地址在peermap内则通过udp发送到对端
		realDest, ok := peerMap[dstIP]
		if ok {
			realDestAddr, err := net.ResolveUDPAddr("udp", realDest)
			if err != nil {
				log.Println("resolve real dest ip error")
				log.Println(err)
				continue
			}

			fmt.Printf("Sending to remote: %+v (%=v)\n", header, err)
			conn.WriteTo(packet[:plen], realDestAddr)
		} else {
			continue
		}

	}
}
