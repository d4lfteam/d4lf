______________________________________________________________________

## name: d4lf-importer-browser description: Investigate browser-dependent importer problems in d4lf. Use for profile import issues involving Selenium, SeleniumBase, Chrome, Edge, Firefox, driver selection, uc/undetected browser behavior, anti-bot-sensitive pages, login/import flow failures, or browser-specific regressions.

1. Identify the exact failure stage: browser detection, Selenium/SeleniumBase startup, profile selection, navigation, anti-bot block, parsing, transfer, or cleanup.
1. Read the importer flow across browser selection, driver creation, SeleniumBase usage, browser-specific branches, fallback logic, waits, and parser handoff.
1. Prefer the repository's existing SeleniumBase patterns for pages that are sensitive to automation. Do not replace them with plain Selenium unless that is the requested fix and the tradeoff is clear.
1. Compare browser branches for inconsistent options, assumptions, waits, profile handling, headless behavior, and error handling.
1. Prefer fixing shared logic first when the same bug affects multiple browsers or importer sites.
1. Avoid brittle browser-specific or anti-detection hacks unless the issue is clearly isolated and no existing shared path can handle it.
1. Preserve currently working browser flows, including cleanup and profile/session handling.
1. If the symptom suggests timing or partial page load, focus on precise readiness checks before adding broad retries or sleeps.
1. In the final summary, state which importer site and browser path were affected, what branch or shared logic changed, and what remains unverified.
