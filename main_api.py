import os
import utils.dns_patch
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    is_render = bool(os.getenv("RENDER"))
    debug_mode = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
    # Reload only during local development, never in Render production
    should_reload = debug_mode or (not is_render and os.getenv("API_RELOAD", "true").lower() in ("1", "true", "yes"))

    print(f"[Main API] Starting FastAPI outreach server on 0.0.0.0:{port} (reload={should_reload}, render={is_render})...")
    uvicorn.run("Backend.api:app", host="0.0.0.0", port=port, reload=should_reload)
