# Phase 2A: Design Critique & Adversarial Architecture Review — `LOCAL-REQ-001`

## Adversarial Reviewer Findings & Recommendations

### 1. Memory Growth & Unbounded Telemetry Accumulation
- **Critique:** In-memory metric store could grow without bound in prolonged sessions, eventually causing Out-Of-Memory (OOM) failures.
- **Mitigation Mandate:** Cap the in-memory circular buffer at 5,000 records using a sliding window. Old records are pruned when limit is exceeded.

### 2. Path Traversal in Static File Serving
- **Critique:** Naive static file handlers can be exploited via `GET /../../etc/passwd` or `GET /..\..\Windows\win.ini`.
- **Mitigation Mandate:** Implement strict canonical path resolution checking `os.path.commonpath([base_dir, requested_path]) == base_dir` before serving any file. Reject illegal paths with `403 Forbidden`.

### 3. CSV Injection Vulnerability in Data Export
- **Critique:** If metric descriptions contain leading `=`, `+`, `-`, or `@` characters, formula injection attacks can execute in spreadsheet software.
- **Mitigation Mandate:** Sanitize cell contents by prefixing sensitive symbols with a single quote `'` during CSV serialization.

### 4. Cross-Origin Resource Sharing (CORS) Security
- **Critique:** Wildcard `Access-Control-Allow-Origin: *` allows any domain to query private metrics.
- **Mitigation Mandate:** Restrict allowed headers and methods; permit standard local development origins.

### 5. Input Payload Size Clamping
- **Critique:** Giant POST payloads can cause denial of service.
- **Mitigation Mandate:** Limit request body ingestion to 1 MB maximum.
