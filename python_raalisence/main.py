"""Main entry point for the Python raalisence server."""

if __name__ == "__main__":
    from python_raalisence.server import app
    import uvicorn
    from python_raalisence.config.config import Config
    
    # Load config for server address
    config = Config.load()
    host, port = config.server_addr.split(':') if ':' in config.server_addr else ('0.0.0.0', config.server_addr)
    
    uvicorn.run(app, host=host, port=int(port))

