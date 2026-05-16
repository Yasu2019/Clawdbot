# AtsugiMechaCity Licensed Photo Search

This tool searches web photo sources and writes a license-aware manifest for station-front, road, building facade, and city texture references.

It is designed for the Hon-Atsugi 3D city workflow:

- Use photos as reference, texture candidates, or background candidates only when the manifest preserves source and license metadata.
- Prefer Wikimedia Commons first because license metadata is explicit and no API key is required.
- Use Pexels and Unsplash only when those sources are explicitly requested.
- Do not use Google Maps or Street View screenshots.

## Environment Keys

Supported `.env` keys:

```env
PEXELS_API_KEY=
UNSPLASH_ACCESS_KEY=
UNSPLASH_SECRET_KEY=
```

The current user-provided Unsplash key names with spaces are also supported for compatibility:

```env
Unsplash_Application ID=
Unsplash_Access Key=
Unsplash_Secret key=
```

Only `Unsplash_Access Key` / `UNSPLASH_ACCESS_KEY` is needed for public photo search. The secret key is not used by this script.

## Examples

Wikimedia only, no paid or quota-heavy provider:

```powershell
python projects\AtsugiMechaCity\asset_search\search_city_reference_photos.py --query "Hon-Atsugi station" --sources wikimedia --limit 8
```

Use Pexels and Unsplash explicitly:

```powershell
python projects\AtsugiMechaCity\asset_search\search_city_reference_photos.py --query "Japanese station front crossing" --sources wikimedia,pexels,unsplash --limit 6
```

Download the first two candidate images after writing the manifest:

```powershell
python projects\AtsugiMechaCity\asset_search\search_city_reference_photos.py --query "Japanese station front crossing" --sources wikimedia --limit 8 --download --max-downloads 2
```

## Safety Rules

- `NC`, `ND`, unknown, fair-use, and all-rights-reserved assets are filtered out.
- Attribution metadata is retained in the manifest.
- Downloads are optional and capped.
- Pexels and Unsplash are not queried unless named in `--sources`.
- The script does not write to `.env`.

