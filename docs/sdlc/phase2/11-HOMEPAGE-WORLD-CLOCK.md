# 11 — Homepage Universal World Clock (Proposed)

## Requirement
Place a compact, live world clock **in the homepage header next to the existing page refresh-rate control**. Provide a dropdown of IANA time zones with searchable/friendly city names and a UTC option. Default to browser/user preference (or explicitly selected organization's preference, if product design later supports it); persist the user's selection.

## UI/behavior
- Header order: page title / scope selector (existing) → refresh interval control → **globe icon + HH:mm:ss + timezone dropdown**.
- Dropdown examples: UTC, Asia/Kolkata, America/New_York, America/Chicago, America/Los_Angeles, Europe/London, Europe/Berlin, Asia/Dubai, Asia/Singapore, Asia/Tokyo, Australia/Sydney. Use full IANA IDs, not fixed offsets.
- Show weekday/date, local time and unambiguous timezone/offset. Support 12h/24h preference. Date must roll over correctly; DST handled automatically.
- Update display once per second using browser clock and `Intl.DateTimeFormat({timeZone})`. Use a single cleanup-safe timer, no API request for every tick; do not tie to 5-second dashboard polling.
- Persist user selection in localStorage initially; later sync to user profile if account preferences exist. If stored zone becomes invalid, safely fall back to UTC or browser zone.
- The selected clock zone is **display-only**. Backend stores timestamps in UTC; metric samples, alerts, schedules and ETL executions retain their original semantics. Timezone conversion for tables is a separate explicit user setting, not an automatic side effect.
- Accessible labeled select/combobox, keyboard navigation, readable high-contrast digits, narrow/mobile header behavior, SSR/test deterministic clock injection if needed.

## Example layout
`[ Operations Overview ]   [ Refresh: 5s ▼ ]  [ 🌐 14:32:09  IST ▼ ]`

## Acceptance tests
1. Switch Kolkata → New York → UTC, verify formatted clock and date using deterministic injected instant.
2. DST transition in New York/London displays correct offset without manual rules.
3. Selected zone survives navigation/reload; no cross-user preference leakage once login exists.
4. Clock ticks every second while dashboard refresh remains independently set to 5 seconds.
5. No backend timestamp or monitoring schedule changes when display zone changes.
6. Mobile and keyboard/screen-reader accessibility.

**Status:** UI design only. No frontend implementation yet.
