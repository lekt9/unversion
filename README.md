# unversion

Simple prompt versioning for AI applications. Store prompts in JSON, track usage, no hardcoding.

## Why unversion?

- **No hardcoded prompts** - Store all prompts in a single JSON file
- **Easy editing** - Update prompts without touching code
- **Usage tracking** - Know which prompts are used and how often
- **Zero dependencies** - Core library has no required dependencies
- **CLI included** - Manage prompts from the command line

## Installation

```bash
pip install unversion
```

With observability (Langfuse integration):
```bash
pip install unversion[observer]
```

## Quick Start

### 1. Create your prompts file

Create `prompts/bundled.json`:

```json
{
  "version": "1.0",
  "prompts": {
    "greeting": {
      "text": "Hello {name}! Welcome to {app_name}.",
      "variables": ["name", "app_name"],
      "source": "manual",
      "notes": "Simple greeting prompt"
    },
    "analysis.sentiment": {
      "text": "Analyze the sentiment of the following text:\n\n{text}\n\nRespond with: positive, negative, or neutral.",
      "variables": ["text"],
      "source": "manual",
      "notes": "Basic sentiment analysis prompt"
    }
  }
}
```

### 2. Use prompts in your code

```python
from unversion import init_store, get_prompt

# Initialize with path to your prompts file
init_store("prompts/bundled.json")

# Get a prompt (returns empty string if not found)
prompt = get_prompt("greeting", name="Alice", app_name="MyApp")
# "Hello Alice! Welcome to MyApp."

# Get prompt without formatting
raw = get_prompt("greeting")
# "Hello {name}! Welcome to {app_name}."

# List all prompts
from unversion import list_prompts
keys = list_prompts()
# ["greeting", "analysis.sentiment"]
```

### 3. Track usage (optional)

```python
from unversion import log_usage, get_stats

# Log when a prompt is used
log_usage("greeting", stage="chat", model="gpt-4")

# Get usage statistics
stats = get_stats("greeting")
print(f"Used {stats['total_usage']} times")
```

## CLI Usage

```bash
# List all prompts
unversion list

# List with filtering
unversion list --filter analysis

# View a prompt
unversion view greeting

# Search prompts
unversion search "sentiment"

# Show statistics
unversion stats

# Validate prompts file
unversion validate prompts/bundled.json
```

## Prompt File Format

```json
{
  "version": "1.0",
  "prompts": {
    "prompt_key": {
      "text": "The prompt text with {variables}",
      "variables": ["variables"],
      "source": "where it came from",
      "notes": "documentation"
    }
  }
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `text` | Yes | The prompt template text |
| `variables` | No | List of variable names used in the template |
| `source` | No | Origin of the prompt (manual, imported, etc.) |
| `notes` | No | Documentation about the prompt |

### Naming Convention

Use dot notation for hierarchical organization:

```
category.subcategory.name
```

Examples:
- `chat.greeting`
- `analysis.sentiment`
- `generation.video.intro`
- `safety.content_filter`

## API Reference

### Store Functions

```python
from unversion import (
    init_store,      # Initialize with prompts file path
    get_store,       # Get the store instance
    get_prompt,      # Get and optionally format a prompt
    list_prompts,    # List all prompt keys
    reload_prompts,  # Reload prompts from file
    has_prompt,      # Check if a prompt exists
)
```

### Observer Functions

```python
from unversion import (
    log_usage,           # Log prompt usage
    get_stats,           # Get usage stats for a prompt
    get_recent_logs,     # Get recent usage logs
    get_top_prompts,     # Get most used prompts
)
```

### Types

```python
from unversion import Prompt, PromptStore, UsageLog
```

## Examples

### Multi-file Organization

```python
# config.py
from unversion import init_store
init_store("prompts/bundled.json")

# chat.py
from unversion import get_prompt

def greet_user(name: str) -> str:
    prompt = get_prompt("chat.greeting", name=name)
    return call_llm(prompt)
```

### With Observability

```python
from unversion import get_prompt, log_usage
import time

def analyze_sentiment(text: str) -> str:
    prompt = get_prompt("analysis.sentiment", text=text)

    start = time.time()
    result = call_llm(prompt)
    latency = (time.time() - start) * 1000

    log_usage(
        "analysis.sentiment",
        stage="analysis",
        model="gpt-4",
        latency_ms=latency,
        success=True,
    )

    return result
```

### Category Filtering

```python
from unversion import list_prompts, get_prompt

# Get all analysis prompts
analysis_keys = [k for k in list_prompts() if k.startswith("analysis.")]

# Load all safety prompts
safety_prompts = {
    key: get_prompt(key)
    for key in list_prompts()
    if key.startswith("safety.")
}
```

## Integration with Langfuse

If you have Langfuse configured, usage logs can be sent automatically:

```bash
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...

pip install unversion[observer]
```

```python
from unversion import log_usage

# Logs will be sent to Langfuse automatically
log_usage("my_prompt", stage="generation", model="claude-3")
```

## Development

```bash
# Clone the repo
git clone https://github.com/unreelai/unversion
cd unversion

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check src tests
```

## License

MIT License - see [LICENSE](LICENSE) for details.
