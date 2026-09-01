# Integrations & Ecosystem Presets

Diaclectics provides turnkey integrations for top AI developer interfaces, chat frontends, and IDEs.

---

## 1. Quickstart with Docker Compose

Launch the complete Diaclectics proxy middleware alongside Open-WebUI:

```bash
docker-compose up -d
```

- **Open-WebUI**: [http://localhost:3000](http://localhost:3000)
- **Live Telemetry Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **OpenAI Proxy Endpoint**: `http://localhost:8000/v1`

---

## 2. Open-WebUI Integration

### Method A: OpenAI API Base URL Proxy
1. In Open-WebUI, navigate to **Admin Settings > Connections > OpenAI API**.
2. Add Connection:
   - **Base URL**: `http://localhost:8000/v1` (or `http://diaclectics:8000/v1` inside Docker network)
   - **API Key**: `diaclectics-local-proxy`
3. Save. All models exposed by Diaclectics will be available with active pre-emission token gating.

### Method B: Native Open-WebUI Filter Plugin (`integrations/open_webui/diaclectics_filter.py`)
1. Go to **Admin Settings > Functions**.
2. Click **Add Function**, select Type: **Filter / Pipe**, and paste the contents of `integrations/open_webui/diaclectics_filter.py`.
3. Enable the filter globally to inject real-time epistemic tension gauges and OpenAlex academic citations directly into chat message footers.

---

## 3. Continue.dev (VS Code & JetBrains)

Add the Diaclectics proxy model to your `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Diaclectics // Anti-Sycophancy Proxy",
      "provider": "openai",
      "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
      "apiBase": "http://localhost:8000/v1",
      "apiKey": "diaclectics-local-proxy"
    }
  ]
}
```

---

## 4. LibreChat Integration

Add the custom endpoint to your root `librechat.yaml`:

```yaml
endpoints:
  custom:
    - name: "Diaclectics Engine"
      apiKey: "diaclectics-local-proxy"
      baseURL: "http://localhost:8000/v1"
      models:
        default:
          - "nvidia/nemotron-3-ultra-550b-a55b:free"
          - "deepseek/deepseek-chat"
      titleConvo: true
      titleModel: "deepseek/deepseek-chat"
```

---

## 5. Cursor IDE Integration

1. Copy `integrations/cursor/.cursorrules` to your workspace root.
2. In **Cursor Settings > Models > OpenAI API Key**:
   - Set Base URL: `http://localhost:8000/v1`
   - Set Key: `diaclectics-local-proxy`

---

## 6. Python SDK & Middleware (LangChain / LlamaIndex / Custom Agent)

Wrap any standard OpenAI client in 3 lines of code:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="diaclectics-local-proxy"
)

response = client.chat.completions.create(
    model="deepseek/deepseek-chat",
    messages=[
        {"role": "user", "content": "I believe friction is completely independent of normal force in dry contact."}
    ],
    extra_headers={"X-Session-ID": "research_session_001"}
)

print(response.choices[0].message.content)
```
