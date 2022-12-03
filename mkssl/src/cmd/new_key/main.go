package main

import (
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"io/ioutil"
	"log"
)

var ecc bool
var out string

func generateKey() (crypto.PrivateKey, error) {
	if ecc {
		return ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	}
	return rsa.GenerateKey(rand.Reader, 2048)
}

func main() {
	flag.BoolVar(&ecc, "ecdsa", false, "创建ecdsa算法创建秘钥")
	flag.StringVar(&out, "out", "server.key", "秘钥输出路径")
	flag.Parse()

	priv, err := generateKey()
	checkErr(err)
	privDER, err := x509.MarshalPKCS8PrivateKey(priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "PRIVATE KEY", Bytes: privDER}), 0640)
	checkErr(err)
}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
