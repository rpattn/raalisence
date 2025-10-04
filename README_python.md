# raalisence - Python License Server

This is a Python implementation of the raalisence license server, providing the same functionality as the Go version with FastAPI and modern Python tooling.

## Features

- **License Management**: Issue, validate, revoke, and update licenses
- **Cryptographic Signing**: ECDSA P-256 digital signatures for license integrity
- **Database Support**: PostgreSQL and SQLite support
- **Admin Panel**: Web interface for license management (reuses static/admin.html)
- **Rate Limiting**: Per-client rate limiting with token bucket algorithm
- **Authentication**: Admin API key authentication with bcrypt hashing
- **Request Logging**: Structured logging with request IDs
- **Health Checks**: Built-in health monitoring endpoint

## Quick Start

### Prerequisites

- Python 3.9 or higher
- uv (recommended) or pip for package management
- PostgreSQL (optional, SQLite works out of the box)

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd raalisence
   ```

2. **Install dependencies**:
   
   **Windows (recommended):**
   ```bash
   scripts\setup.bat
   ```
   
   **Linux/Mac:**
   ```bash
   python scripts/setup.py
   ```
   
   **Or manually with uv** (recommended):
   ```bash
   uv sync
   ```
   
   **Or with pip:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate signing keys**:
   ```bash
   # Windows
   scripts\gen_keys.bat
   # or PowerShell
   scripts\gen_keys.ps1
   
   # Linux/Mac
   python scripts/gen_keys.py
   ```
   
   **Note:** If you get import errors, make sure you've installed the dependencies first with the setup script.

4. **Create configuration**:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your keys and settings
   ```

5. **Generate admin key hash**:
   ```bash
   # Windows
   scripts\gen.bat my-secret-admin-key
   # PowerShell
   scripts\gen.ps1 my-secret-admin-key
   
   # Linux/Mac
   python scripts/gen.py my-secret-admin-key
   ```

6. **Start the server**:
   ```bash
   # Windows
   scripts\run.bat
   # PowerShell
   scripts\run.ps1
   
   # Linux/Mac
   python -m python_raalisence.server
   ```

## Configuration

The server uses YAML configuration with environment variable overrides:

```yaml
server:
  addr: ":8080"
  admin_api_key_hashes:
    - "$2a$10$your_bcrypt_hash_here"

db:
  driver: "postgresql"  # or "sqlite3"
  dsn: "postgresql://user:pass@localhost:5432/raalisence"
  path: "./raalisence.db"  # for SQLite

signing:
  private_key_pem: |
    -----BEGIN EC PRIVATE KEY-----
    # your private key here
    -----END EC PRIVATE KEY-----
  public_key_pem: |
    -----BEGIN PUBLIC KEY-----
    # your public key here
    -----END PUBLIC KEY-----
```

### Environment Variables

All configuration can be overridden with environment variables:

- `RAAL_SERVER_ADDR`: Server address (default: ":8080")
- `RAAL_SERVER_ADMIN_API_KEY`: Plain admin key (not recommended for production)
- `RAAL_SERVER_ADMIN_API_KEY_HASHES`: Comma-separated bcrypt hashes
- `RAAL_DB_DRIVER`: Database driver ("postgresql" or "sqlite3")
- `RAAL_DB_DSN`: PostgreSQL connection string
- `RAAL_DB_PATH`: SQLite database file path
- `RAAL_SIGNING_PRIVATE_KEY_PEM`: Private key PEM
- `RAAL_SIGNING_PUBLIC_KEY_PEM`: Public key PEM

## Database Setup

### PostgreSQL

1. **Start development database**:
   ```bash
   # Windows
   scripts\dev_db_up.bat
   # PowerShell
   scripts\dev_db_up.ps1
   ```

2. **Stop database**:
   ```bash
   # Windows
   scripts\dev_db_down.bat
   # PowerShell
   scripts\dev_db_down.ps1
   ```

### SQLite

SQLite works out of the box. Just set the driver to "sqlite3" in your config:

```bash
# Windows
scripts\dev_sqlite_up.bat
# PowerShell
scripts\dev_sqlite_up.ps1
```

## API Endpoints

### Health Check
- `GET /healthz` - Server health status

### License Management (Admin)
- `POST /api/v1/licenses/issue` - Issue new license
- `POST /api/v1/licenses/revoke` - Revoke license
- `POST /api/v1/licenses/update` - Update license
- `GET /api/v1/licenses` - List all licenses

### License Operations (Public)
- `POST /api/v1/licenses/validate` - Validate license
- `POST /api/v1/licenses/heartbeat` - Update last seen time

### Static Files
- `GET /` - Redirects to admin panel
- `GET /static/*` - Static files (admin panel)

## Admin Panel

Access the web interface at `http://localhost:8080` after starting the server. The admin panel provides:

- License issuance and management
- License validation testing
- License listing and updates
- Heartbeat testing
- Real-time API interaction

## Development

### Running Tests

```bash
# Windows
scripts\test.bat
# PowerShell
scripts\test.ps1

# Linux/Mac
python -m pytest tests/ -v
```

### Code Quality

The project includes linting and formatting tools:

```bash
# Format code
black python_raalisence/

# Type checking
mypy python_raalisence/

# Linting
flake8 python_raalisence/
```

## Production Deployment

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY python_raalisence/ ./python_raalisence/
COPY static/ ./static/
COPY config.yaml .

EXPOSE 8080
CMD ["python", "-m", "python_raalisence.server"]
```

### Environment Configuration

For production, use environment variables instead of config files:

```bash
export RAAL_SERVER_ADDR=":8080"
export RAAL_SERVER_ADMIN_API_KEY_HASHES="$(scripts/gen.py my-secret-key)"
export RAAL_DB_DSN="postgresql://user:pass@db:5432/raalisence"
# ... other variables
```

## Comparison with Go Version

| Feature | Go Version | Python Version |
|---------|------------|----------------|
| Framework | net/http | FastAPI |
| Database | sql.DB | asyncpg/psycopg2 |
| Configuration | viper | PyYAML + env vars |
| Crypto | crypto/ecdsa | cryptography |
| Rate Limiting | Custom | Custom |
| Admin Auth | bcrypt | bcrypt |
| Static Files | http.FileServer | StaticFiles |

Both versions provide identical functionality and API compatibility.

## License

Same license as the original Go implementation.

