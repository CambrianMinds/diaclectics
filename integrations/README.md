# Diaclectics Integrations & Turnkey Presets

Drop Diaclectics in front of your favorite local tools (Open-WebUI, Continue.dev, LibreChat, Cursor) to gain real-time anti-sycophancy pre-emission token gating, epistemic tension scoring, and active OpenAlex literature search.

---

## 1. Quickstart with Docker Compose

Launch the complete Diaclectics proxy middleware and Open-WebUI with a single command:

```bash
docker-compose up -d
```

- **Open-WebUI**: [http://localhost:3000](http://localhost:3000) (pre-configured to route through Diaclectics)
- **Diaclectics Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (live 2D Phase Portrait & RCI Gauges)
- **OpenAI Proxy Endpoint**: `http://localhost:8000/v1`

To include local offline Ollama inference:
```bash
docker-compose -f docker-compose.full.yml up -d
```

---

## 2. Open-WebUI Integration

### Option A: Direct OpenAI API Connection
1. In Open-WebUI, go to **Admin Panel > Settings > Connections**.
2. Add an OpenAI API Connection:
   - **Base URL**: `http://localhost:8000/v1` (or `http://diaclectics:8000/v1` in Docker)
   - **API Key**: `diaclectics-local-proxy`
3. Save connection. All models (e.g. `nvidia/nemotron-3-ultra-550b-a55b:free`, `deepseek/deepseek-chat`, `mock-dialectical-engine`) will appear automatically.

### Option B: Custom Pipe / Filter Plugin
1. Go to **Admin Panel > Functions**.
2. Click **Add Function** and paste `integrations/open_webui/diaclectics_filter.py`.
3. Enable the filter globally to see live epistemic telemetry and citation cards inside chat threads.

---

## 3. Continue.dev Integration (VS Code / JetBrains)

1. Open `~/.continue/config.json`.
2. Add the Diaclectics models from `integrations/continue_dev/config.json`:

```json
{
  "models": [
    {
      "title": "Diaclectics // Nemotron 550B",
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

1. Add the custom endpoint block from `integrations/librechat/librechat.yaml` to your root `librechat.yaml`:

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
```

---

## 5. Cursor Integration

1. Copy `integrations/cursor/.cursorrules` to your project root.
2. In Cursor Settings > Models, configure OpenAI Base URL to `http://localhost:8000/v1`.

---

## 6. System Prompt Presets

Pre-packaged prompts are located in `integrations/prompts/`:
- `anti_sycophancy_core.md`: General-purpose anti-sycophantic assistant.
- `forensic_arbiter.md`: Physical sciences, toolmarks, kinematics, and metrology.
- `socratic_adversary.md`: Socratic red-teaming and assumption stress-testing.
