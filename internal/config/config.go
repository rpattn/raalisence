package config

import (
	"crypto/ecdsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/viper"
	"golang.org/x/crypto/bcrypt"
)

type Config struct {
	Server struct {
		Addr              string   `mapstructure:"addr"`
		AdminAPIKey       string   `mapstructure:"admin_api_key"`
		AdminAPIKeyHashes []string `mapstructure:"admin_api_key_hashes"`
	} `mapstructure:"server"`
	DB struct {
		Driver string `mapstructure:"driver"`
		DSN    string `mapstructure:"dsn"`
		Path   string `mapstructure:"path"`
	} `mapstructure:"db"`
	Signing struct {
		PrivateKeyPEM string `mapstructure:"private_key_pem"`
		PublicKeyPEM  string `mapstructure:"public_key_pem"`
	} `mapstructure:"signing"`

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

	// Explicit env bindings (ensure nested keys work)
	_ = v.BindEnv("server.addr")
	_ = v.BindEnv("server.admin_api_key")
	_ = v.BindEnv("server.admin_api_key_hashes")
	_ = v.BindEnv("db.driver")
	_ = v.BindEnv("db.dsn")
	_ = v.BindEnv("db.path")
	_ = v.BindEnv("signing.private_key_pem")
	_ = v.BindEnv("signing.public_key_pem")

	// defaults
	v.SetDefault("server.addr", ":8080")
	v.SetDefault("db.driver", "pgx")
	v.SetDefault("db.dsn", "postgres://postgres:postgres@localhost:5432/raalisence?sslmode=disable")
	v.SetDefault("db.path", "./raalisence.db")

	_ = v.ReadInConfig() // optional

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}
	cfg.Server.AdminAPIKeyHashes = normalizeHashes(cfg.Server.AdminAPIKeyHashes)
	if raw := os.Getenv("RAAL_SERVER_ADMIN_API_KEY_HASHES"); raw != "" {
		cfg.Server.AdminAPIKeyHashes = normalizeHashes(splitHashes(raw))
	}
	return &cfg, nil
}

func (c *Config) AdminKeyOK(got string) bool {
	hashes := c.Server.AdminAPIKeyHashes
	if len(hashes) > 0 {
		gotBytes := []byte(got)
		for _, h := range hashes {
			if h == "" {
				continue
			}
			if err := bcrypt.CompareHashAndPassword([]byte(h), gotBytes); err == nil {
				return true
			}
		}
		return false
	}

	want := c.Server.AdminAPIKey
	if want == "" {
		return false
	}

	wantBytes := []byte(want)
	gotBytes := []byte(got)
	if len(gotBytes) != len(wantBytes) {
		return false
	}

	match := 0
	for i := range gotBytes {
		match |= int(wantBytes[i] ^ gotBytes[i])
	}
	return match == 0
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

func normalizeHashes(in []string) []string {
	out := make([]string, 0, len(in))
	for _, h := range in {
		h = strings.TrimSpace(h)
		if h == "" {
			continue
		}
		out = append(out, h)
	}
	return out
}

func splitHashes(raw string) []string {
	fields := strings.FieldsFunc(raw, func(r rune) bool {
		switch r {
		case ',', '\n', '\r', ';':
			return true
		default:
			return false
		}
	})
	return fields
}
