import os
from phase6.api import app

if __name__ == "__main__":
    # Render binds to 0.0.0.0 and specifies the port via the PORT environment variable
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    
    # If running on Render or other container platforms, PORT will be set, so bind to all interfaces by default
    if "PORT" in os.environ and "FLASK_RUN_HOST" not in os.environ:
        host = "0.0.0.0"
        
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    # In production environments like Render, we disable debug mode
    if "PORT" in os.environ:
        debug_mode = False

    app.run(host=host, port=port, debug=debug_mode)

