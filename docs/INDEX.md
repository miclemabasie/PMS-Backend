# 🏢 PMS Backend Documentation

> **Last Updated**: {{ git log -1 --format=%cd --date=short }}  
> **Version**: `{{ git describe --tags }}`  
> **Status**: 🟢 Production-Ready

## 🚀 Quick Start

- [Local Setup](GETTING_STARTED/local-setup.md)
- [First API Call](GETTING_STARTED/first-api-call.md)
- [Troubleshooting](GETTING_STARTED/troubleshooting.md)

## 🗺️ Explore by Topic

| Area               | Key Docs                                                                                |
| ------------------ | --------------------------------------------------------------------------------------- |
| 🔐 Auth & Security | [Policies](SECURITY/policies.md) • [JWT Flow](ARCHITECTURE/authentication-flow.md)      |
| 🔌 API Reference   | [Endpoints](API/reference/) • [Examples](API/examples/) • [Errors](API/error-codes.md)  |
| 🧪 Testing         | [Strategy](TESTING/strategy.md) • [Fixtures](TESTING/fixtures.md)                       |
| 🐳 Deployment      | [Environments](DEPLOYMENT/environments.md) • [Docker Guide](DEPLOYMENT/docker-guide.md) |
| 🌍 i18n            | [Translation Workflow](I18N/translation-workflow.md) • [Glossary](GLOSSARY.md)          |

## 🔄 Recent Changes

<!-- Auto-updated by scripts/update_changelog_preview.py -->

{{ include: CHANGELOG/upcoming.md (last 5 items) }}

## 🤝 Contributing

- [Workflow](CONTRIBUTING/workflow.md)
- [Code Style](CONTRIBUTING/code-style.md)
- [Onboarding](CONTRIBUTING/onboarding.md)

> 💡 **Pro Tip**: Run `make docs-serve` to preview changes locally with live reload.[📝 Changelog](CHANGELOG/notes.md)
