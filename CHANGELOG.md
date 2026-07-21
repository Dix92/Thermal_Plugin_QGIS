# Changelog

All notable changes to the Thermal Temperature Reconstructor QGIS plugin are documented in this file.

## [1.3] - 2026-07-21

### Added
- Multilanguage interface: English, Italian, German and French.
- By default the plugin follows the QGIS language setting (Settings → Options → General); users of other languages see English as fallback.
- Language selector in the dialog to override the automatic choice; the selection is applied immediately and remembered across sessions.
- Translation sources (`.ts`) and compiled catalogs (`.qm`) in the new `i18n/` folder; translations can be edited with Qt Linguist.

## [1.2] - 2026-07-14

### Fixed
- Handle wrong CRS tags in input files: drone-service exports sometimes tag the file with a projected CRS (e.g. EPSG:2056) while the coordinates are actually longitude/latitude degrees. A new "Source CRS" option auto-detects and fixes the mismatch (default), with the alternative of trusting the file tag or specifying the source CRS manually.

### Changed
- Use scoped enum for the color ramp type (Qt6 compatibility check).

## [1.1.1] - 2026-07-14

### Fixed
- Reprojection issues when the target CRS differs from the input CRS: the output is now warped with bilinear resampling (suited to continuous temperature data) and nodata is masked during resampling.
- The output file is always tagged with a real CRS, even when the input file has an empty projection (WGS84 assumed).
- The map canvas now zooms to the correct extent when the layer CRS differs from the project CRS.

## [1.1] - 2026-07-14

### Added
- QGIS 4 / Qt6 compatibility (`supportsQt6=True`).
- Plugin icon.

### Removed
- Unused resource-compilation scripts flagged by the plugin repository scan.

## [1.0] - 2026-07-14 - Initial release

### Added
- Reconstruction of temperature values from thermal RGB orthomosaics that have lost their original temperature data.
- Color profiles: Rainbow ISO 2 (recommended — the only tested and proven profile), Rainbow, Ironbow, Gray, White Hot, Black Hot, Rainbow HC, Arctic, Custom RGB.
- Temperature range configuration (minimum/maximum) to calibrate the reconstruction; a fixed temperature/color scale in the source imagery is required.
- Input selection by file or by folder (automatically finds `result.tif` in subfolders).
- GeoTIFF export (LZW-compressed, single Float32 band in °C) and automatic loading into the QGIS project with a thermal color ramp.
