# Thermal Temperature Reconstructor - QGIS Plugin

A QGIS plugin that reconstructs temperature values from thermal RGB orthomosaics that have lost their original temperature data.

## Features

- **Multiple Color Profile Support**: Supports various thermal camera color profiles including:
  - **Rainbow ISO 2** (recommended — the only tested and proven profile)
  - Rainbow
  - Ironbow
  - Gray
  - White Hot
  - Black Hot
  - Rainbow HC
  - Arctic
  - Custom RGB

- **Temperature Range Configuration**: Set minimum and maximum temperature values to calibrate the reconstruction

- **Raster Processing**: Converts RGB thermal images back to temperature rasters using color analysis

- **QGIS Integration**: Automatically loads processed rasters into your QGIS project

## Installation

### Manual Installation

1. Download or clone this repository
2. Copy the entire plugin folder to your QGIS plugins directory:
   - **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

3. Rename the folder to `thermal_temperature_reconstructor` (ensure no spaces or special characters)

4. Open QGIS and go to `Plugins` → `Manage and Install Plugins`

5. Find "Thermal Temperature Reconstructor" in the Installed tab and enable it

### Development Installation

If you want to develop or modify the plugin:

1. Clone this repository to your QGIS plugins directory (see paths above)
2. Restart QGIS or reload the plugin (e.g. with the "Plugin Reloader" plugin) after each change

## Usage

1. **Launch the Plugin**: 
   - Click the plugin icon in the toolbar, or
   - Go to `Plugins` → `Thermal Temperature Reconstructor` → `Reconstruct Thermal Temperature`

2. **Select Input Raster**: 
   - Click "Browse..." to select your thermal RGB orthomosaic

3. **Configure Temperature Range**:
   - Set the minimum temperature (coldest point in your image)
   - Set the maximum temperature (hottest point in your image)
   - These values should match the settings used when the thermal image was captured
   - **Important**: The thermal image must have been captured/exported with a **fixed (defined) color scale and temperature scale**. Images using a dynamic (auto-adjusting) temperature scale cannot be reconstructed, because the color-to-temperature mapping changes from frame to frame

4. **Choose Color Profile**:
   - Select the color profile that matches your thermal camera settings
   - This determines how RGB colors are interpreted as temperatures
   - **Recommended**: Use **Rainbow ISO 2** — it is currently the only tested and proven color profile. If possible, capture/export your thermal images with this color scale

5. **Source CRS** (optional):
   - Leave on **Auto-detect** (recommended): some drone-processing exports tag the file with a projected CRS (e.g. EPSG:2056) while the coordinates are actually longitude/latitude degrees; the plugin detects this and treats the source as WGS84
   - Or choose "Use file CRS as-is" / "Specify source CRS" to control it manually

6. **Set Output Location**:
   - Choose where to save the reconstructed temperature raster
   - The output will be a single-band GeoTIFF with temperature values in Celsius

7. **Process**:
   - Click "Process" to begin reconstruction
   - The plugin will analyze the RGB values and reconstruct temperature data
   - The output raster will be automatically loaded into your QGIS project

## How It Works

The plugin analyzes the RGB values in your thermal orthomosaic and reconstructs temperature values based on:

1. **Color Profile Analysis**: Different color profiles map colors to temperatures differently:
   - **Rainbow/Ironbow**: Uses hue analysis to determine temperature (blue=cold, red=hot)
   - **Gray/White Hot/Black Hot**: Uses intensity values (brightness) to determine temperature
   - **Arctic**: Analyzes blue-green-white gradients

2. **Temperature Mapping**: Maps the analyzed color values to the specified temperature range (min to max)

3. **Raster Output**: Creates a new single-band raster where each pixel value represents the reconstructed temperature in Celsius

## Requirements

- QGIS 3.0 or higher
- Python 3.x
- GDAL/OGR (included with QGIS)
- NumPy (usually included with QGIS)

## Limitations

- **Accuracy**: The reconstruction is an approximation. Accuracy depends on:
  - Correct temperature range settings
  - Matching color profile selection
  - Quality of the original thermal image
  
- **Color Profiles**: Only **Rainbow ISO 2** has been tested and proven so far. The other profiles are provided as-is and may require additional calibration and validation

- **Metadata Loss**: If the original image had calibration data, emissivity settings, or other metadata, this information cannot be reconstructed

## Tips for Best Results

1. **Know Your Camera Settings**: Use the exact temperature range and color profile from when the image was captured

2. **Color Profile Matching**: Ensure the selected color profile matches the one used when capturing the image

3. **Temperature Range**: Set realistic temperature ranges based on your scene (e.g., -20°C to 120°C for outdoor scenes)

## Troubleshooting

- **Plugin not appearing**: Ensure the folder name has no spaces and is in the correct plugins directory
- **Processing errors**: Check that your input raster has at least 3 bands (RGB)
- **Incorrect temperatures**: Verify your temperature range and color profile match the original image settings
- **Output in the wrong location / reprojection looks wrong**: The input file probably has a wrong CRS tag embedded (common with drone-processing exports that write a projected CRS while the coordinates are lon/lat degrees). Keep "Source CRS" on **Auto-detect**, or set the correct source CRS manually

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This plugin is licensed under the [GNU General Public License v3.0](LICENSE).

## Author

Developed by [Drone Agri Tech](mailto:info@droneagritech.ch) for reconstructing temperature values from thermal orthomosaics in QGIS.




