package main

import (
	"flag"
	"fmt"
	"log"

	"golang.org/x/crypto/bcrypt"
)

func main() {
	cost := flag.Int("cost", bcrypt.DefaultCost, "bcrypt cost to use for hashing")
	flag.Parse()
	if flag.NArg() != 1 {
		log.Fatalf("usage: %s [--cost=<cost>] <token>", flag.CommandLine.Name())
	}

	token := flag.Arg(0)
	hash, err := bcrypt.GenerateFromPassword([]byte(token), *cost)
	if err != nil {
		log.Fatalf("hash token: %v", err)
	}

	fmt.Println(string(hash))
}
