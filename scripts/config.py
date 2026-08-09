import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()

# Root directory of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Helper function to load yaml configurations
def load_yaml_config(file_name, default_data=None):
    if default_data is None:
        default_data = {}
    config_path = PROJECT_ROOT / 'config' / file_name
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or default_data
        except Exception as err:
            print(f"[WARNING] Failed to load config file '{config_path}': {err}")
    return default_data


# Load YAML configurations
pipeline_config = load_yaml_config('pipeline.yaml')
filters_config = load_yaml_config('filters.yaml')
themes_config = load_yaml_config('themes.yaml')


# Extract settings with environment variable overrides
SCOPES = os.getenv('SCOPES', '').split(',') if os.getenv('SCOPES') else pipeline_config.get('SCOPES', ['https://www.googleapis.com/auth/gmail.modify'])

TOKEN_FILE = Path(os.getenv('TOKEN_FILE', pipeline_config.get('TOKEN_FILE', 'token.json')))
CREDENTIALS_FILE = Path(os.getenv('CREDENTIALS_FILE', pipeline_config.get('CREDENTIALS_FILE', 'credentials.json')))
PROCESSED_EMAILS_FILE = Path(os.getenv('PROCESSED_EMAILS_FILE', pipeline_config.get('PROCESSED_EMAILS_FILE', 'processed_emails.json')))
NEWSLETTER_SPAM_LABEL = os.getenv('NEWSLETTER_SPAM_LABEL', pipeline_config.get('NEWSLETTER_SPAM_LABEL', 'newsletter-spam'))
NEWSLETTER_LABEL_NAME = os.getenv('NEWSLETTER_LABEL_NAME', pipeline_config.get('NEWSLETTER_LABEL_NAME', 'Newsletter'))

FETCH_INTERVAL_HOURS = int(os.getenv('FETCH_INTERVAL_HOURS', str(pipeline_config.get('FETCH_INTERVAL_HOURS', 4))))
POSTS_DIR = os.getenv('POSTS_DIR', pipeline_config.get('POSTS_DIR', '_posts')).strip('/')
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() in ('true', '1', 'yes')
GITHUB_REPO = os.getenv('GITHUB_REPO', pipeline_config.get('GITHUB_REPO', 'vampcoder/daily-newsletters'))

ENABLE_LLM_CURATION = os.getenv('ENABLE_LLM_CURATION', str(pipeline_config.get('ENABLE_LLM_CURATION', True))).lower() in ('true', '1', 'yes')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', pipeline_config.get('LLM_MODEL', 'deepseek/deepseek-chat'))
LLM_API_BASE = os.getenv('LLM_API_BASE', pipeline_config.get('LLM_API_BASE', 'https://api.deepseek.com'))
# Thinking level for DeepSeek: "disabled" | "low" (enabled with small budget) | "high" (full)
LLM_THINKING_LEVEL = os.getenv('LLM_THINKING_LEVEL', str(pipeline_config.get('LLM_THINKING_LEVEL', 'low'))).lower()
LLM_THINKING_BUDGET_TOKENS = int(os.getenv('LLM_THINKING_BUDGET_TOKENS', str(pipeline_config.get('LLM_THINKING_BUDGET_TOKENS', 512))))
MIN_RELEVANCE_SCORE = int(os.getenv('MIN_RELEVANCE_SCORE', str(pipeline_config.get('MIN_RELEVANCE_SCORE', 6))))

# Filters Configurations
PROMO_KEYWORDS = filters_config.get('PROMO_KEYWORDS', [])
SENDER_SUBJECT_FILTERS = filters_config.get('SENDER_SUBJECT_FILTERS', {})

# Themes Configurations
THEME_GRADIENTS = themes_config.get('THEME_GRADIENTS', [])
