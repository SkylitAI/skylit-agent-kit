# Curated free toolkit

This starter includes the catalogue and connection guidance below. **Only the offline calculation example is implemented.** External adapters are planned; listing a tool does not install, activate or certify it.

| Capability | Source | Delivery/status | Access and limits |
|---|---|---|---|
| Company filings | [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Adapter planned | Public data; declared User-Agent and fair-access rules |
| Jobs and inflation | [BLS](https://www.bls.gov/developers/api_faqs.htm) | Adapter planned | Registration-dependent query limits |
| Central-bank news | [Federal Reserve RSS](https://www.federalreserve.gov/feeds/feeds.htm) | Reader planned | Public feeds; cache and preserve links |
| Web text | [Trafilatura](https://trafilatura.readthedocs.io/en/latest/) | Optional adapter planned | Software license and each website's terms apply |
| PDF text | [pypdf](https://pypdf.readthedocs.io/en/stable/) | Optional adapter planned | Text extraction; scanned documents need separate OCR |
| Calculation and charts | Python standard library; future chart adapter | Revenue/premium calculations implemented; charts planned | Local compute; no model required |
| Economic series | [Official FRED MCP](https://fredhelp.stlouisfed.org/fred/data/ai/fred-mcp-connector/) | [Connection profile](fred.md); not host-certified | Free-account sign-in; series usage terms apply |

Free software/data does not mean free agent subscriptions, compute or Skylit calls. Each future adapter needs an owner, pinned dependencies, license notes, bounded behavior, provenance, tests and a clean unavailable state. Activate only the tools needed for a workflow. Experimental additions start in [Agent Lab](https://github.com/SkylitAI/skylit-agent-lab).
