package crypto

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/asn1"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"math/big"
)

type ecdsaSig struct{ R, S *big.Int }

// SignJSON signs the canonical JSON encoding of payload using ECDSA P-256/SHA-256.
func SignJSON(priv *ecdsa.PrivateKey, payload map[string]any) (string, error) {
	b, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	h := sha256.Sum256(b)
	r, s, err := ecdsa.Sign(rand.Reader, priv, h[:])
	if err != nil {
		return "", err
	}
	sig, err := asn1.Marshal(ecdsaSig{R: r, S: s})
	if err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(sig), nil
}

// VerifyJSON verifies a signature over payload with a public key.
func VerifyJSON(pub *ecdsa.PublicKey, payload map[string]any, sigB64 string) (bool, error) {
	b, err := json.Marshal(payload)
	if err != nil {
		return false, err
	}
	h := sha256.Sum256(b)
	sig, err := base64.RawURLEncoding.DecodeString(sigB64)
	if err != nil {
		return false, err
	}
	var es ecdsaSig
	if _, err := asn1.Unmarshal(sig, &es); err != nil {
		return false, err
	}
	ok := ecdsa.Verify(pub, h[:], es.R, es.S)
	return ok, nil
}

// Helpers to generate PEM keys (useful in tests/dev)
func GeneratePEM() (privPEM, pubPEM string, err error) {
	priv, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	if err != nil {
		return "", "", err
	}
	b, err := x509.MarshalECPrivateKey(priv)
	if err != nil {
		return "", "", err
	}
	privPEM = string(pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: b}))
	pubDER, err := x509.MarshalPKIXPublicKey(&priv.PublicKey)
	if err != nil {
		return "", "", err
	}
	pubPEM = string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pubDER}))
	return
}

// Parse public key from PEM
func ParsePublicKey(pemStr string) (*ecdsa.PublicKey, error) {
	block, _ := pem.Decode([]byte(pemStr))
	if block == nil {
		return nil, fmt.Errorf("invalid PEM")
	}
	any, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	pub, ok := any.(*ecdsa.PublicKey)
	if !ok {
		return nil, fmt.Errorf("not ECDSA key")
	}
	return pub, nil
}
