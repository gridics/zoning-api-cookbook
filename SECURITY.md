# Security

Do not report exposed API keys, customer data, or security vulnerabilities in a public GitHub issue.

If a Gridics credential is exposed, revoke or rotate it immediately in **Developer Portal → Workspace → API Keys**, remove it from every log/artifact/history under your control, and contact Gridics through the private security or support channel provided with your account. If no private channel is available, use `support@gridics.com` and include no active secret in the message.

Examples read `GRIDICS_API_KEY` from the process environment, send it only in the `x-api-key` header, and redact the header from output. Keep `.env` untracked. Never pass a Gridics key as an MCP/LLM tool argument or return it to a model.

The fixture server accepts only the literal synthetic key `fixture_key_not_secret`. It is not a live credential.
