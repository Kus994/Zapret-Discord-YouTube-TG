# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: [donationalerts.com/r/kus_777](https://www.donationalerts.com/r/kus_777)
3. Include: description, steps to reproduce, potential impact

We will respond within 48 hours and work with you to address the issue.

## Security Model

KUS Pro is a system utility that operates with elevated privileges. We take security seriously:

- **No telemetry** — the app does not phone home or collect user data
- **Local only** — all operations happen on the local machine
- **Open source** — full code review possible
- **Minimal dependencies** — only PyQt5, psutil, certifi

## Binary Components

Some binary components are downloaded from trusted upstream projects:

- **zapret** — from [bol-van/zapret](https://github.com/bol-van/zapret) (MIT License)
- **tg-ws-proxy** — from [Flowseal/tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) (MIT License)

These are well-known open source projects with established security track records.

## Best Practices

1. **Run from a dedicated folder** — e.g., `C:\KUS Pro`
2. **Don't run untrusted code** — only use official releases
3. **Keep updated** — enable auto-updates in settings
4. **Review changes** — check CHANGELOG.md before updating
