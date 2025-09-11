import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


def get_env_var(key: str, default: str | None = None) -> str:
	value = os.getenv(key, default)
	if value is None:
		raise RuntimeError(f"Missing required environment variable: {key}")
	return value


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
VECTOR_DIR = ROOT_DIR / ".vectorstore"

DOC_PATH = Path(os.getenv("DOC_PATH", DATA_DIR / "Corpus.pdf"))
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Napa, CA")
TIMEZONE = os.getenv("TZ", "America/Los_Angeles")

# Model defaults
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# API keys (do not fail hard here to allow partial functionality during dev)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")



