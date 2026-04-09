# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## tomtom-street-names-wrong — TomTom segments show FRC codes instead of real street names
- **Date:** 2026-04-09
- **Error patterns:** frc3, frc4, FRC, street name, road name, reverseGeocode, entityType, tomtom, traffic flow, silent exception
- **Root cause:** `entityType=Street` in TomTom reverseGeocode URL returns HTTP 400 (unsupported parameter), causing every geocode call to fail. Exception was swallowed with bare `pass`, so all segments kept their FRC code as display name. Additionally freeformAddress fallback produced full address strings (with house number + city) instead of just street name.
- **Fix:** Remove `entityType=Street` and `radius=50` from reverseGeocode URL. Use plain endpoint which reliably returns `streetName`. Replace `except Exception: pass` with `logger.debug(...)`. Drop freeformAddress fallback — use `streetName` only or keep FRC placeholder.
- **Files changed:** backend/app/connectors/tomtom.py, backend/tests/connectors/test_tomtom.py
---

