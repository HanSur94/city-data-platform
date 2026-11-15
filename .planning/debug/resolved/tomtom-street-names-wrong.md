---
status: resolved
trigger: "TomTom traffic flow segments display 'frc3' (or similar FRC codes) as the street name instead of the actual street name. Some segments also show incorrect/wrong street names."
created: 2026-04-09T20:30:00+02:00
updated: 2026-04-09T21:10:00+02:00
---

## Current Focus

hypothesis: RESOLVED — three bugs confirmed and fixed; end-to-end verification passed (52/159 segments now have real street names, remainder are rural/highway segments with no streetName from API)
test: Live API call verification completed
expecting: N/A
next_action: N/A — session archived

## Symptoms

expected: TomTom traffic segments should display real street names (e.g., "Friedrichstraße", "Bahnhofstraße") obtained via reverse geocoding
actual: Some segments show FRC class codes like "frc3" as their display name; some segments show wrong/incorrect street names
errors: No crash or error — it's a data quality / logic bug
reproduction: View the TomTom traffic flow layer on the map, observe segment names in tooltips or labels
started: After commit 42b436b which added "FRC4 streets + reverse geocode street names for TomTom segments"

## Eliminated

- hypothesis: Frontend is reading the wrong property field for road name
  evidence: TrafficFlowPopup.tsx correctly reads props.road_name. The backend sets road_name: segment_def["name"]. Data flow is correct — the bug is in how seg["name"] gets set.
  timestamp: 2026-04-09T20:33:00+02:00

## Evidence

- timestamp: 2026-04-09T20:31:00+02:00
  checked: backend/app/connectors/tomtom.py reverse geocode block (lines 266-285)
  found: |
    seg["name"] is initialized to frc (e.g. "FRC3") on line 255.
    Reverse geocode uses addr.get("streetName") or addr.get("freeformAddress") or seg["frc"].
    Exception block does `pass` — silently keeps frc as name if ANY error occurs.
    No entityType filter on the reverseGeocode URL — returns nearest *address*, not nearest road.
  implication: |
    Bug 1 (FRC as name): Any exception (timeout, rate limit, HTTP error) silently leaves seg["name"] = "FRC3".
    Bug 2 (wrong name): reverseGeocode without entityType=Street returns the nearest address point, which
    may be for a different road at intersections. freeformAddress also falls through as full address string
    like "Bahnhofstr. 1, 73430 Aalen" — which includes house number and city, not just street name.

- timestamp: 2026-04-09T20:33:00+02:00
  checked: TomTom Search API reverseGeocode documentation
  found: |
    The TomTom reverseGeocode API supports an `entityType` query parameter.
    entityType=Street restricts results to roads/streets only, improving accuracy.
    Also supports `radius` parameter to constrain search distance.
    streetName field in response contains only the street name without address details.
  implication: |
    Adding entityType=Street to the URL would constrain results to actual road entities.
    The freeformAddress fallback should be avoided or parsed to extract only the street portion.

## Resolution

root_cause: |
  Three bugs in backend/app/connectors/tomtom.py _discover_segments():
  
  1. SILENT EXCEPTION SWALLOW: The `except Exception: pass` on line 283 silently discarded all 
     reverse geocode errors (timeouts, rate limits, HTTP errors), leaving seg["name"] = seg["frc"] 
     (e.g., "FRC3", "FRC4") for any failed lookup. No logging meant the operator could not detect 
     how many segments failed geocoding.
  
  2. INVALID entityType PARAMETER (root cause of 100% FRC fallback in live run): A previous fix 
     attempt added `&entityType=Street` to the reverseGeocode URL. However, TomTom's reverseGeocode 
     endpoint does NOT support entityType=Street — it returns HTTP 400 for this value. This caused 
     every reverse geocode call to fail, the exception was swallowed, and every segment kept its 
     FRC code as its name. Verified via live API testing.
  
  3. FREEFORM ADDRESS FALLBACK: When streetName was absent but freeformAddress existed, the 
     original fallback used the full freeformAddress string (e.g., "Bahnhofstraße 1, 73430 Aalen") 
     instead of just the street name portion. This resulted in verbose, incorrect-looking display names.

fix: |
  In backend/app/connectors/tomtom.py:
  1. Removed invalid `&entityType=Street` parameter from reverseGeocode URL (TomTom returns 400)
  2. Removed `&radius=50` (unnecessary without entityType)
  3. Changed `except Exception: pass` to `logger.debug(...)` so failures are visible
  4. Removed freeformAddress fallback — use only streetName or keep frc placeholder
  
  In backend/tests/connectors/test_tomtom.py:
  1. Updated test_discover_reverse_geocode_uses_entity_type_street → test_discover_reverse_geocode_uses_street_name
  2. Changed assertion from "entityType=Street in URL" to "entityType NOT in URL"

verification: |
  - All 23 pytest tests pass
  - Live end-to-end verification: 52/159 Aalen segments (32%) now have real German street names
    (e.g., "Straße der Staufer", "Hauptstraße", "Röchlingstraße", "Gmünder Straße")
  - Remaining 107 segments without streetName are rural/highway segments where TomTom API
    returns no streetName for those coordinates — FRC fallback is appropriate for these
files_changed:
  - backend/app/connectors/tomtom.py
  - backend/tests/connectors/test_tomtom.py
