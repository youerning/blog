package main

import (
	"crypto"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
)

var out string
var key string

var (
	country       = "china"
	stateProvince = "GD"
	locality      = "SZ"
	org           = "self"
	orgUnit       = "self"
	commonName    = "example.com"
)

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

func newCSR(key crypto.PrivateKey) ([]byte, error) {
	subject := pkix.Name{Country: []string{country}, Province: []string{stateProvince}, Locality: []string{locality},
		Organization: []string{org}, OrganizationalUnit: []string{orgUnit}, CommonName: commonName}

	template := x509.CertificateRequest{Subject: subject, DNSNames: []string{commonName}}
	return x509.CreateCertificateRequest(rand.Reader, &template, key)
}

func main() {
	flag.StringVar(&out, "out", "server.csr", "证书签名请求输出路径")
	flag.StringVar(&key, "key", "server.key", "私钥路径")
	flag.Parse()
	priv, err := loadPrivateKey(key)
	checkErr(err)
	csr, err := newCSR(priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE REQUEST", Bytes: csr}), 0640)
	checkErr(err)

}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
