package main

import (
	"crypto"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"math/big"
	"os"
	"time"
)

var csr string
var key string
var out string
var cacert string

func randomSerialNumber() *big.Int {
	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	checkErr(err)
	return serialNumber
}

func loadPrivateKey(key string) (crypto.PrivateKey, error) {
	file, err := os.Open(key)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	data, err := ioutil.ReadAll(file)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil || block.Type != "PRIVATE KEY" {
		return nil, fmt.Errorf("解码私钥失败")
	}

	priv, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	return priv, nil
}

func main() {
	flag.StringVar(&csr, "csr", "server.csr", "证书签名请求文件路径")
	flag.StringVar(&cacert, "ca", "ca.crt", "ca证书文件路径")
	flag.StringVar(&out, "out", "server.crt", "证书输出路径")
	flag.StringVar(&key, "key", "server.key", "私钥路径")
	flag.Parse()

	priv, err := loadPrivateKey(key)
	checkErr(err)
	csrPEMBytes, err := ioutil.ReadFile(csr)
	checkErr(err)
	csrPEM, _ := pem.Decode(csrPEMBytes)
	if csrPEM == nil {
		log.Fatalln("加载证书签名失败")
	}
	if csrPEM.Type != "CERTIFICATE REQUEST" &&
		csrPEM.Type != "NEW CERTIFICATE REQUEST" {
		log.Fatalln("未知的证书签名类型, 期望的值是CERTIFICATE REQUEST, 得到的却是 " + csrPEM.Type)
	}
	csr, err := x509.ParseCertificateRequest(csrPEM.Bytes)
	checkErr(err)
	certPEMBlock, err := ioutil.ReadFile(cacert)
	checkErr(err)
	certDERBlock, _ := pem.Decode(certPEMBlock)
	if certDERBlock == nil || certDERBlock.Type != "CERTIFICATE" {
		log.Fatalln("读取CA证书失败")
	}
	ca, err := x509.ParseCertificate(certDERBlock.Bytes)
	checkErr(err)

	expiration := time.Now().AddDate(2, 3, 0)
	tpl := &x509.Certificate{
		SerialNumber:    randomSerialNumber(),
		Subject:         csr.Subject,
		ExtraExtensions: csr.Extensions,
		NotBefore:       time.Now(), NotAfter: expiration,
		DNSNames:    []string{csr.Subject.CommonName},
		KeyUsage:    x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}
	cert, err := x509.CreateCertificate(rand.Reader, tpl, ca, csr.PublicKey, priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE", Bytes: cert}), 0644)
	checkErr(err)

}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
