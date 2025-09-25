package config

import (
	"crypto/ecdsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/viper"
)

// Config is the top-level application configuration.
// Loaded from config file (viper) with env fallback.

type Config struct {
	Server struct {
		Addr        string `mapstructure:"addr"`
		AdminAPIKey string `mapstructure:"admin_api_key"`
	} `mapstructure:"server"`
	DB struct {
		DSN string `mapstructure:"dsn"`
	} `mapstructure:"db"`
	Signing struct {
		PrivateKeyPEM string `mapstructure:"private_key_pem"`
		PublicKeyPEM  string `mapstructure:"public_key_pem"`
	} `mapstructure:"signing"`

	// Parsed keys (lazy)
	privateKey *ecdsa.PrivateKey
	publicKey  *ecdsa.PublicKey
}

func Load() (*Config, error) {
	v := viper.New()
	v.SetConfigName("config")
	v.SetConfigType("yaml")
	v.AddConfigPath(".")
	v.AddConfigPath("./configs")
	v.AddConfigPath("/etc/raalisence")

	v.SetEnvPrefix("RAAL")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	// defaults
	v.SetDefault("server.addr", ":8080")
	v.SetDefault("db.dsn", "postgres://postgres:postgres@localhost:5432/raalisence?sslmode=disable")

	_ = v.ReadInConfig() // optional

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}
	return &cfg, nil
}

func (c *Config) AdminKeyOK(got string) bool {
	return c.Server.AdminAPIKey != "" && got == c.Server.AdminAPIKey
}

func (c *Config) PrivateKey() (*ecdsa.PrivateKey, error) {
	if c.privateKey != nil {
		return c.privateKey, nil
	}
	b := []byte(c.Signing.PrivateKeyPEM)
	if len(b) == 0 {
		return nil, fmt.Errorf("missing signing.private_key_pem")
	}
	block, _ := pem.Decode(b)
	if block == nil {
		return nil, fmt.Errorf("invalid PEM private key")
	}
	key, err := x509.ParseECPrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	c.privateKey = key
	return key, nil
}

func (c *Config) PublicKey() (*ecdsa.PublicKey, error) {
	if c.publicKey != nil {
		return c.publicKey, nil
	}
	b := []byte(c.Signing.PublicKeyPEM)
	if len(b) == 0 {
		return nil, fmt.Errorf("missing signing.public_key_pem")
	}
	block, _ := pem.Decode(b)
	if block == nil {
		return nil, fmt.Errorf("invalid PEM public key")
	}
	pubAny, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	pub, ok := pubAny.(*ecdsa.PublicKey)
	if !ok {
		return nil, fmt.Errorf("public key is not ECDSA")
	}
	c.publicKey = pub
	return pub, nil
}

func MustEnv(k string) string {
	v := os.Getenv(k)
	if v == "" {
		panic("missing env: " + k)
	}
	return v
}
