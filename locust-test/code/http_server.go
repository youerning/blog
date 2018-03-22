package main

import (
	// "fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

type myHandler struct{}

func (*myHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// time.Sleep(time.Second * 1)
	io.WriteString(w, "ok")
}

func main() {
	var port string
	port = ":" + os.Args[1]

	srv := &http.Server{
		Addr:         port,
		Handler:      &myHandler{},
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	log.Fatal(srv.ListenAndServe())
}
