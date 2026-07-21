"""
Main plugin file for Thermal Temperature Reconstructor
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QFileDialog, QMessageBox
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsProcessingFeedback, 
    QgsCoordinateReferenceSystem, QgsRasterFileWriter,
    QgsRectangle, QgsProcessingContext, QgsCoordinateTransform,
    QgsWkbTypes, QgsRasterShader, QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer
)
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsProjectionSelectionWidget
from qgis import processing
import os
import numpy as np
from osgeo import gdal, osr

# Language setting: 'auto' follows the QGIS locale, otherwise a fixed code
LANGUAGE_SETTING_KEY = 'ThermalTemperatureReconstructor/language'
LANGUAGE_CODES = ['auto', 'en', 'it', 'de', 'fr']

# Keep a reference to the installed translator so it is not garbage-collected
_translator = None


def install_translator(plugin_dir):
    """(Re)install the plugin translator according to the language setting."""
    global _translator
    if _translator is not None:
        QCoreApplication.removeTranslator(_translator)
        _translator = None
    lang = QSettings().value(LANGUAGE_SETTING_KEY, 'auto')
    if lang == 'auto':
        lang = (QSettings().value('locale/userLocale') or 'en')[0:2]
    if lang and lang != 'en':
        qm_path = os.path.join(
            plugin_dir, 'i18n', 'ThermalTemperatureReconstructor_{}.qm'.format(lang))
        if os.path.exists(qm_path):
            translator = QTranslator()
            if translator.load(qm_path):
                QCoreApplication.installTranslator(translator)
                _translator = translator


def tr(message):
    """Translate a string using the shared plugin context."""
    return QCoreApplication.translate('ThermalTemperatureReconstructor', message)


class ThermalTemperatureReconstructor:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        install_translator(self.plugin_dir)
        self.actions = []
        self.menu = self.tr(u'&Thermal Temperature Reconstructor')

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('ThermalTemperatureReconstructor', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        # Use default icon if custom icon doesn't exist
        if not os.path.exists(icon_path):
            icon_path = ''
        self.add_action(
            icon_path,
            text=self.tr(u'Reconstruct Thermal Temperature'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Thermal Temperature Reconstructor'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        dialog = ThermalTemperatureDialog(self.iface, self.plugin_dir)
        dialog.exec()


class ThermalTemperatureDialog(QDialog):
    """Main dialog for thermal temperature reconstruction"""
    
    def __init__(self, iface, plugin_dir):
        super().__init__()
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.setMinimumWidth(500)
        self.setup_ui()
        self.retranslate_ui()

    def tr(self, message):
        """Get the translation for a string using the shared plugin context."""
        return QCoreApplication.translate('ThermalTemperatureReconstructor', message)

    def setup_ui(self):
        """Setup the user interface (texts are set in retranslate_ui)"""
        from qgis.PyQt.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
            QPushButton, QDoubleSpinBox, QComboBox, QGroupBox,
            QFormLayout, QProgressBar
        )

        layout = QVBoxLayout()

        # Language selection
        language_layout = QHBoxLayout()
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        # Item 0 is retranslated; native language names stay as they are
        self.language_combo.addItems(
            ["", "English", "Italiano", "Deutsch", "Français"])
        current_lang = QSettings().value(LANGUAGE_SETTING_KEY, 'auto')
        if current_lang in LANGUAGE_CODES:
            self.language_combo.setCurrentIndex(LANGUAGE_CODES.index(current_lang))
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        layout.addLayout(language_layout)

        # Input raster selection
        self.input_group = QGroupBox()
        input_layout = QHBoxLayout()
        self.input_raster_line = QLineEdit()
        self.input_raster_btn = QPushButton()
        self.input_raster_btn.clicked.connect(self.select_input_raster)
        self.input_folder_btn = QPushButton()
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        input_layout.addWidget(self.input_raster_line)
        input_layout.addWidget(self.input_raster_btn)
        input_layout.addWidget(self.input_folder_btn)
        self.input_group.setLayout(input_layout)
        layout.addWidget(self.input_group)

        # Temperature range
        self.temp_group = QGroupBox()
        temp_layout = QFormLayout()
        self.min_temp = QDoubleSpinBox()
        self.min_temp.setRange(-273.15, 2000)
        self.min_temp.setValue(-20)
        self.min_temp.setSuffix(" °C")
        self.max_temp = QDoubleSpinBox()
        self.max_temp.setRange(-273.15, 2000)
        self.max_temp.setValue(120)
        self.max_temp.setSuffix(" °C")
        self.min_temp_label = QLabel()
        self.max_temp_label = QLabel()
        temp_layout.addRow(self.min_temp_label, self.min_temp)
        temp_layout.addRow(self.max_temp_label, self.max_temp)
        self.temp_group.setLayout(temp_layout)
        layout.addWidget(self.temp_group)

        # Color profile selection (profile names are palette names, not translated)
        self.profile_group = QGroupBox()
        profile_layout = QFormLayout()
        self.color_profile = QComboBox()
        self.color_profile.addItems([
            "Rainbow",
            "Rainbow ISO 2",
            "Ironbow",
            "Gray",
            "White Hot",
            "Black Hot",
            "Rainbow HC",
            "Arctic",
            "Custom RGB"
        ])
        self.profile_label = QLabel()
        profile_layout.addRow(self.profile_label, self.color_profile)
        self.profile_group.setLayout(profile_layout)
        layout.addWidget(self.profile_group)

        # Output settings
        self.output_group = QGroupBox()
        output_layout = QVBoxLayout()

        # Output file selection
        file_layout = QHBoxLayout()
        self.output_raster_line = QLineEdit()
        self.output_raster_btn = QPushButton()
        self.output_raster_btn.clicked.connect(self.select_output_raster)
        file_layout.addWidget(self.output_raster_line)
        file_layout.addWidget(self.output_raster_btn)
        output_layout.addLayout(file_layout)

        # Layer name
        name_layout = QFormLayout()
        self.layer_name_line = QLineEdit()
        self.layer_name_line.setText(self.tr("Reconstructed Temperature"))
        self.layer_name_label = QLabel()
        name_layout.addRow(self.layer_name_label, self.layer_name_line)
        output_layout.addLayout(name_layout)

        # CRS selection
        crs_layout = QFormLayout()

        # Source CRS handling: drone-service exports often carry a wrong CRS
        # tag in the file (e.g. EPSG:2056 while the coordinates are lon/lat)
        self.source_crs_mode = QComboBox()
        self.source_crs_mode.addItems(["", "", ""])
        self.source_crs_mode.setCurrentIndex(0)
        self.source_crs_mode.currentIndexChanged.connect(self.toggle_crs_selector)
        self.source_crs_selector = QgsProjectionSelectionWidget()
        self.source_crs_selector.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.source_crs_label = QLabel()
        crs_layout.addRow(self.source_crs_label, self.source_crs_mode)
        crs_layout.addRow("", self.source_crs_selector)

        self.crs_selector = QgsProjectionSelectionWidget()
        # Default to project CRS, or EPSG:4326 if not set
        project_crs = QgsProject.instance().crs()
        if project_crs.isValid():
            self.crs_selector.setCrs(project_crs)
        else:
            self.crs_selector.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

        # Add option to use input CRS
        self.use_input_crs = QComboBox()
        self.use_input_crs.addItems(["", ""])
        self.use_input_crs.setCurrentIndex(0)
        self.use_input_crs.currentIndexChanged.connect(self.toggle_crs_selector)
        self.crs_option_label = QLabel()
        self.target_crs_label = QLabel()
        crs_layout.addRow(self.crs_option_label, self.use_input_crs)
        crs_layout.addRow(self.target_crs_label, self.crs_selector)
        output_layout.addLayout(crs_layout)

        self.output_group.setLayout(output_layout)
        layout.addWidget(self.output_group)

        # Initialize CRS selector state
        self.toggle_crs_selector()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()
        self.process_btn = QPushButton()
        self.process_btn.clicked.connect(self.process_raster)
        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def retranslate_ui(self):
        """Set (or refresh) all user-visible texts in the current language"""
        self.setWindowTitle(self.tr("Thermal Temperature Reconstructor"))
        self.language_label.setText(self.tr("Language:"))
        self.language_combo.setItemText(0, self.tr("Automatic (QGIS language)"))
        self.input_group.setTitle(self.tr("Input Raster"))
        self.input_raster_btn.setText(self.tr("Browse File..."))
        self.input_folder_btn.setText(self.tr("Browse Folder..."))
        self.input_folder_btn.setToolTip(
            self.tr("Select a folder containing 'result.tif'"))
        self.temp_group.setTitle(self.tr("Temperature Range"))
        self.min_temp_label.setText(self.tr("Minimum Temperature:"))
        self.max_temp_label.setText(self.tr("Maximum Temperature:"))
        self.profile_group.setTitle(self.tr("Color Profile"))
        self.profile_label.setText(self.tr("Profile:"))
        self.output_group.setTitle(self.tr("Output"))
        self.output_raster_btn.setText(self.tr("Browse..."))
        self.layer_name_line.setPlaceholderText(self.tr("Enter layer name..."))
        self.layer_name_label.setText(self.tr("Layer Name:"))
        for i, text in enumerate([
                self.tr("Auto-detect (fix wrong file tag)"),
                self.tr("Use file CRS as-is"),
                self.tr("Specify source CRS")]):
            self.source_crs_mode.setItemText(i, text)
        self.source_crs_label.setText(self.tr("Source CRS:"))
        for i, text in enumerate([
                self.tr("Use specified CRS"),
                self.tr("Use input raster CRS")]):
            self.use_input_crs.setItemText(i, text)
        self.crs_option_label.setText(self.tr("CRS Option:"))
        self.target_crs_label.setText(self.tr("Target CRS:"))
        self.process_btn.setText(self.tr("Process"))
        self.cancel_btn.setText(self.tr("Cancel"))

    def on_language_changed(self, index):
        """Persist the chosen language, reload the translator and refresh texts"""
        if index < 0 or index >= len(LANGUAGE_CODES):
            return
        QSettings().setValue(LANGUAGE_SETTING_KEY, LANGUAGE_CODES[index])
        install_translator(self.plugin_dir)
        self.retranslate_ui()

    def select_input_raster(self):
        """Select input thermal raster"""
        filename, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Thermal Raster"), "",
            self.tr("Raster Files (*.tif *.tiff *.png *.jpg *.jpeg)"))
        if filename:
            self.input_raster_line.setText(filename)
            # Auto-generate output filename
            if not self.output_raster_line.text():
                base_name = os.path.splitext(filename)[0]
                self.output_raster_line.setText(base_name + "_temperature.tif")
    
    def select_input_folder(self):
        """Select folder containing result.tif (searches subfolders too)"""
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select Folder Containing result.tif"), "")
        if folder:
            # Search for result.tif in the folder and all subfolders
            result_file = None
            for root, dirs, files in os.walk(folder):
                if "result.tif" in files:
                    result_file = os.path.join(root, "result.tif")
                    break  # Use the first one found
            
            if result_file:
                self.input_raster_line.setText(result_file)
                # Auto-generate output filename
                if not self.output_raster_line.text():
                    base_name = os.path.splitext(result_file)[0]
                    self.output_raster_line.setText(base_name + "_temperature.tif")
            else:
                QMessageBox.warning(
                    self, self.tr("File Not Found"),
                    self.tr("Could not find 'result.tif' in the selected folder "
                            "or its subfolders:\n{0}").format(folder)
                )
    
    def select_output_raster(self):
        """Select output raster location"""
        filename, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Output Raster"), "", self.tr("GeoTIFF (*.tif)"))
        if filename:
            if not filename.endswith('.tif'):
                filename += '.tif'
            self.output_raster_line.setText(filename)
    
    def toggle_crs_selector(self):
        """Enable/disable CRS selectors based on user choice"""
        use_specified = (self.use_input_crs.currentIndex() == 0)
        self.crs_selector.setEnabled(use_specified)
        self.source_crs_selector.setEnabled(self.source_crs_mode.currentIndex() == 2)
    
    def apply_thermal_color_ramp(self, layer, min_temp, max_temp):
        """Apply thermal color ramp to the layer based on temperature range.
        Creates color stops every 10 degrees from min to max temperature.
        Uses the TURBO colormap (Google's perceptually uniform rainbow colormap).
        """
        # TURBO colormap - 14 color stops for temperatures 0-130°C (every 10 degrees)
        # These are the TURBO colors sampled at even intervals
        # (temperature_value, R, G, B)
        turbo_colors = [
            (0, 48, 18, 59),        # Dark purple
            (10, 70, 60, 151),      # Blue-purple  
            (20, 65, 113, 217),     # Light blue
            (30, 39, 168, 242),     # Cyan
            (40, 40, 211, 221),     # Cyan-green
            (50, 94, 236, 157),     # Light green
            (60, 132, 242, 118),    # Green
            (70, 209, 240, 52),     # Yellow
            (80, 253, 202, 49),     # Orange-yellow
            (90, 254, 167, 52),     # Orange
            (100, 247, 127, 47),    # Red-orange
            (110, 231, 87, 38),     # Red
            (120, 206, 51, 27),     # Dark red
            (130, 144, 12, 0),      # Dark red-brown
        ]
        
        # Create color stops using the actual min/max temperature values
        # Round min_temp down to nearest 10 and max_temp up to nearest 10
        start_temp = int(min_temp // 10) * 10
        end_temp = int((max_temp + 9) // 10) * 10
        
        # Build a lookup for TURBO colors by temperature
        turbo_lookup = {t: (r, g, b) for t, r, g, b in turbo_colors}
        
        # Function to get color for any temperature (interpolate if needed)
        def get_turbo_color(temp):
            """Get TURBO color for a given temperature, interpolating if necessary"""
            # Clamp to 0-130 range for color lookup
            lookup_temp = max(0, min(130, temp))
            
            # Find the nearest 10-degree stops
            lower_stop = int(lookup_temp // 10) * 10
            upper_stop = lower_stop + 10
            
            if upper_stop > 130:
                upper_stop = 130
                lower_stop = 120
            
            # Get colors at the stops
            r1, g1, b1 = turbo_lookup.get(lower_stop, (48, 18, 59))
            r2, g2, b2 = turbo_lookup.get(upper_stop, (144, 12, 0))
            
            # Interpolate
            if upper_stop == lower_stop:
                return (r1, g1, b1)
            
            t = (lookup_temp - lower_stop) / (upper_stop - lower_stop)
            r = int(r1 + t * (r2 - r1))
            g = int(g1 + t * (g2 - g1))
            b = int(b1 + t * (b2 - b1))
            return (r, g, b)
        
        # Create color stops every 10 degrees
        color_ramp_items = []
        
        current_temp = start_temp
        while current_temp <= end_temp:
            # Get the TURBO color for this temperature
            r, g, b = get_turbo_color(current_temp)
            
            # Add color stop
            color_ramp_items.append(
                QgsColorRampShader.ColorRampItem(current_temp, QColor(r, g, b), f"{current_temp:.2f}")
            )
            
            current_temp += 10
        
        # Create shader and set color ramp
        shader = QgsRasterShader()
        color_ramp_shader = QgsColorRampShader()
        color_ramp_shader.setColorRampType(QgsColorRampShader.Type.Interpolated)
        color_ramp_shader.setColorRampItemList(color_ramp_items)
        
        # Set the min/max values for the shader to use actual temperature range
        color_ramp_shader.setMinimumValue(min_temp)
        color_ramp_shader.setMaximumValue(max_temp)
        
        shader.setRasterShaderFunction(color_ramp_shader)
        shader.setMinimumValue(min_temp)
        shader.setMaximumValue(max_temp)
        
        # Create and set renderer
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        renderer.setClassificationMin(min_temp)
        renderer.setClassificationMax(max_temp)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
    
    def process_raster(self):
        """Process the raster to reconstruct temperature values"""
        input_path = self.input_raster_line.text()
        output_path = self.output_raster_line.text()
        
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, self.tr("Error"),
                                self.tr("Please select a valid input raster file."))
            return

        if not output_path:
            QMessageBox.warning(self, self.tr("Error"),
                                self.tr("Please specify an output file path."))
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.process_btn.setEnabled(False)
            
            # Determine target CRS
            target_crs = None
            if self.use_input_crs.currentIndex() == 0:
                # Use specified CRS
                target_crs = self.crs_selector.crs()
                if not target_crs.isValid():
                    QMessageBox.warning(self, self.tr("Error"),
                                        self.tr("Please select a valid target CRS."))
                    self.process_btn.setEnabled(True)
                    self.progress_bar.setVisible(False)
                    return
            # If index == 1, use input raster CRS (target_crs remains None)

            # Determine source CRS handling
            source_crs = None
            auto_fix_source_crs = (self.source_crs_mode.currentIndex() == 0)
            if self.source_crs_mode.currentIndex() == 2:
                source_crs = self.source_crs_selector.crs()
                if not source_crs.isValid():
                    QMessageBox.warning(self, self.tr("Error"),
                                        self.tr("Please select a valid source CRS."))
                    self.process_btn.setEnabled(True)
                    self.progress_bar.setVisible(False)
                    return

            # Reconstruct temperature
            reconstructor = TemperatureReconstructor(
                input_path,
                output_path,
                self.min_temp.value(),
                self.max_temp.value(),
                self.color_profile.currentText(),
                target_crs=target_crs,
                source_crs=source_crs,
                auto_fix_source_crs=auto_fix_source_crs
            )

            reconstructor.progress_callback = lambda p: self.progress_bar.setValue(int(p))
            reconstructor.reconstruct()

            self.progress_bar.setValue(100)
            success_msg = self.tr(
                "Temperature reconstruction completed!\nOutput saved to:\n{0}"
            ).format(output_path)
            if reconstructor.source_crs_fixed:
                success_msg += "\n\n" + self.tr("Note: {0}").format(
                    reconstructor.source_crs_fixed)
            QMessageBox.information(self, self.tr("Success"), success_msg)

            # Get layer name (use custom name or default)
            layer_name = self.layer_name_line.text().strip()
            if not layer_name:
                layer_name = self.tr("Reconstructed Temperature")
            
            # Load the output raster into QGIS
            layer = QgsRasterLayer(output_path, layer_name)
            if layer.isValid():
                # Apply default color ramp (thermal palette)
                self.apply_thermal_color_ramp(layer, self.min_temp.value(), self.max_temp.value())
                QgsProject.instance().addMapLayer(layer)
                # layer.extent() is in the layer CRS; the canvas needs project CRS
                canvas_extent = QgsCoordinateTransform(
                    layer.crs(), QgsProject.instance().crs(), QgsProject.instance()
                ).transformBoundingBox(layer.extent())
                self.iface.mapCanvas().setExtent(canvas_extent)
                self.iface.mapCanvas().refresh()
            else:
                QMessageBox.warning(
                    self, self.tr("Warning"),
                    self.tr("Raster processed but could not be loaded into QGIS."))

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Error during processing:\n{0}").format(str(e)))
        finally:
            self.process_btn.setEnabled(True)
            self.progress_bar.setVisible(False)


class TemperatureReconstructor:
    """Class for reconstructing temperature values from RGB thermal images"""
    
    def __init__(self, input_path, output_path, min_temp, max_temp, color_profile,
                 target_crs=None, source_crs=None, auto_fix_source_crs=True):
        self.input_path = input_path
        self.output_path = output_path
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.color_profile = color_profile
        self.target_crs = target_crs  # QgsCoordinateReferenceSystem or None
        self.source_crs = source_crs  # QgsCoordinateReferenceSystem or None (overrides file CRS)
        self.auto_fix_source_crs = auto_fix_source_crs
        self.source_crs_fixed = None  # set to a message when a wrong file tag was corrected
        self.progress_callback = None
        
    def reconstruct(self):
        """Main reconstruction method"""
        # Open input raster
        dataset = gdal.Open(self.input_path)
        if dataset is None:
            raise ValueError(
                tr("Could not open raster file: {0}").format(self.input_path))
        
        # Get raster properties
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize
        bands = dataset.RasterCount
        
        if bands < 3:
            raise ValueError(tr("Input raster must have at least 3 bands (RGB)"))
        
        # Read RGB bands (optimized: read directly as arrays)
        r_band = dataset.GetRasterBand(1).ReadAsArray()
        g_band = dataset.GetRasterBand(2).ReadAsArray()
        b_band = dataset.GetRasterBand(3).ReadAsArray()
        
        if self.progress_callback:
            self.progress_callback(20)
        
        # Convert to float32 once if needed (avoids multiple conversions)
        if r_band.dtype != np.float32 and r_band.dtype != np.uint8:
            r_band = r_band.astype(np.float32)
        if g_band.dtype != np.float32 and g_band.dtype != np.uint8:
            g_band = g_band.astype(np.float32)
        if b_band.dtype != np.float32 and b_band.dtype != np.uint8:
            b_band = b_band.astype(np.float32)
        
        # Normalize to 0-255 range if needed.
        # IMPORTANT: use a SINGLE shared scale across the three channels so the
        # relative RGB balance (i.e. the colour) is preserved. Normalising each
        # channel independently on its own min/max would distort the hue and
        # corrupt the colour->temperature mapping for every palette.
        if r_band.dtype != np.uint8 or g_band.dtype != np.uint8 or b_band.dtype != np.uint8:
            all_min = float(min(r_band.min(), g_band.min(), b_band.min()))
            all_max = float(max(r_band.max(), g_band.max(), b_band.max()))
            if all_max > all_min:
                scale = 255.0 / (all_max - all_min)
                r_band = np.clip((r_band.astype(np.float32) - all_min) * scale, 0, 255).astype(np.uint8)
                g_band = np.clip((g_band.astype(np.float32) - all_min) * scale, 0, 255).astype(np.uint8)
                b_band = np.clip((b_band.astype(np.float32) - all_min) * scale, 0, 255).astype(np.uint8)
            else:
                r_band = np.zeros_like(r_band, dtype=np.uint8)
                g_band = np.zeros_like(g_band, dtype=np.uint8)
                b_band = np.zeros_like(b_band, dtype=np.uint8)
        
        # Convert RGB to temperature based on color profile
        temperature_array = self.rgb_to_temperature(r_band, g_band, b_band)
        
        if self.progress_callback:
            self.progress_callback(70)
        
        # Create output raster
        driver = gdal.GetDriverByName('GTiff')
        out_dataset = driver.Create(
            self.output_path,
            cols,
            rows,
            1,  # Single band for temperature
            gdal.GDT_Float32,
            ['COMPRESS=LZW']
        )
        
        # Get input CRS. The user-specified source CRS wins over the file tag;
        # otherwise trust the file, unless auto-fix detects that the tag
        # contradicts the coordinates.
        input_srs = osr.SpatialReference()
        if self.source_crs is not None and self.source_crs.isValid():
            input_srs.ImportFromWkt(self.source_crs.toWkt())
        else:
            input_proj = dataset.GetProjection()
            if input_proj:
                input_srs.ImportFromWkt(input_proj)
            else:
                input_srs.ImportFromEPSG(4326)  # Default to WGS84 if no projection

            if self.auto_fix_source_crs and input_proj and input_srs.IsProjected():
                # Drone-service exports sometimes tag the file with a projected
                # CRS (e.g. EPSG:2056) while the geotransform actually holds
                # lon/lat degrees. A projected raster whose coordinates fit in
                # the degree range with a sub-degree pixel is such a mismatch.
                gt = dataset.GetGeoTransform()
                xs = (gt[0], gt[0] + cols * gt[1] + rows * gt[2])
                ys = (gt[3], gt[3] + cols * gt[4] + rows * gt[5])
                looks_geographic = (
                    max(abs(x) for x in xs) <= 360.0
                    and max(abs(y) for y in ys) <= 90.0
                    and 0.0 < abs(gt[1]) < 0.05
                )
                if looks_geographic:
                    tag_name = input_srs.GetName()
                    input_srs.ImportFromEPSG(4326)
                    self.source_crs_fixed = tr(
                        "The input file is tagged as '{0}' but its coordinates "
                        "are longitude/latitude degrees. The source CRS was "
                        "treated as WGS84 (EPSG:4326)."
                    ).format(tag_name)
        input_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        
        # Copy geotransform; always tag the output with a real CRS so the
        # file matches the SRS later used for warping (the input file may
        # have an empty projection, in which case EPSG:4326 was assumed)
        out_dataset.SetGeoTransform(dataset.GetGeoTransform())
        out_dataset.SetProjection(input_srs.ExportToWkt())
        
        # Write temperature band
        out_band = out_dataset.GetRasterBand(1)
        out_band.WriteArray(temperature_array)
        out_band.SetDescription("Temperature")
        out_band.SetUnitType("Celsius")
        
        # Set no data value if needed
        out_band.SetNoDataValue(-9999)
        
        if self.progress_callback:
            self.progress_callback(70)
        
        # Flush and close initial output
        out_dataset.FlushCache()
        out_dataset = None
        dataset = None
        
        # Handle reprojection if target CRS is specified and different from input
        if self.target_crs and self.target_crs.isValid():
            target_srs = osr.SpatialReference()
            target_srs.ImportFromWkt(self.target_crs.toWkt())
            target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            
            # Check if reprojection is needed
            if not input_srs.IsSame(target_srs):
                if self.progress_callback:
                    self.progress_callback(75)
                
                # Create temporary output file for reprojection
                base, ext = os.path.splitext(self.output_path)
                temp_output = base + '_temp' + (ext if ext else '.tif')
                if os.path.exists(temp_output):
                    os.remove(temp_output)

                # Use GDAL Warp to reproject. Bilinear suits continuous
                # temperature data; nodata is masked during resampling.
                warp_options = gdal.WarpOptions(
                    srcSRS=input_srs.ExportToWkt(),
                    dstSRS=target_srs.ExportToWkt(),
                    resampleAlg='bilinear',
                    dstNodata=-9999,
                    outputType=gdal.GDT_Float32,
                    creationOptions=['COMPRESS=LZW']
                )
                
                # Reproject the raster
                reprojected = gdal.Warp(temp_output, self.output_path, options=warp_options)
                
                if reprojected is None:
                    raise ValueError(tr("Reprojection failed"))
                
                reprojected = None
                
                # Replace original with reprojected version
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(temp_output, self.output_path)
                
                if self.progress_callback:
                    self.progress_callback(90)
        
        if self.progress_callback:
            self.progress_callback(100)
    
    def rgb_to_temperature(self, r, g, b):
        """Convert RGB values to temperature based on color profile"""
        # Combine RGB into a single index for color profile lookup
        # Different methods based on color profile
        
        if self.color_profile in ["Rainbow", "Rainbow HC"]:
            # Rainbow: temperature increases from blue -> green -> yellow -> red
            # Use hue-based conversion
            return self.rainbow_rgb_to_temp(r, g, b)
        
        elif self.color_profile == "Rainbow ISO 2":
            # Rainbow ISO 2: ISO standardized rainbow palette
            # More standardized color transitions following ISO thermal imaging standards
            return self.rainbow_iso2_rgb_to_temp(r, g, b)
        
        elif self.color_profile == "Ironbow":
            # Ironbow: similar to rainbow but different color mapping
            return self.ironbow_rgb_to_temp(r, g, b)
        
        elif self.color_profile == "Gray":
            # Grayscale: use average intensity
            intensity = (r.astype(np.float32) + g.astype(np.float32) + b.astype(np.float32)) / 3.0
            return self.intensity_to_temp(intensity)
        
        elif self.color_profile == "White Hot":
            # White hot: white is hot, black is cold
            intensity = (r.astype(np.float32) + g.astype(np.float32) + b.astype(np.float32)) / 3.0
            return self.intensity_to_temp(intensity)
        
        elif self.color_profile == "Black Hot":
            # Black hot: black is hot, white is cold (inverted)
            intensity = (r.astype(np.float32) + g.astype(np.float32) + b.astype(np.float32)) / 3.0
            inverted_intensity = 255 - intensity
            return self.intensity_to_temp(inverted_intensity)
        
        elif self.color_profile == "Arctic":
            # Arctic: blue-green-white gradient
            return self.arctic_rgb_to_temp(r, g, b)
        
        else:  # Custom RGB or default
            # Default: use average intensity
            intensity = (r.astype(np.float32) + g.astype(np.float32) + b.astype(np.float32)) / 3.0
            return self.intensity_to_temp(intensity)
    
    def intensity_to_temp(self, intensity):
        """Convert intensity (0-255) to temperature"""
        # Normalize intensity to 0-1
        normalized = intensity / 255.0
        
        # Map to temperature range
        temperature = self.min_temp + normalized * (self.max_temp - self.min_temp)
        
        return temperature.astype(np.float32)
    
    def rainbow_rgb_to_temp(self, r, g, b):
        """Convert RGB to temperature using rainbow color profile"""
        # Rainbow mapping: blue (cold) -> cyan -> green -> yellow -> red (hot)
        # Calculate hue and map to temperature
        
        r = r.astype(np.float32)
        g = g.astype(np.float32)
        b = b.astype(np.float32)
        
        # Normalize RGB
        max_val = np.maximum(np.maximum(r, g), b)
        min_val = np.minimum(np.minimum(r, g), b)
        delta = max_val - min_val + 1e-10
        
        # Calculate hue
        hue = np.zeros_like(r)
        
        mask_r = (max_val == r) & (delta != 0)
        mask_g = (max_val == g) & (delta != 0)
        mask_b = (max_val == b) & (delta != 0)
        
        # Red dominant
        hue[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
        
        # Green dominant
        hue[mask_g] = 60 * ((b[mask_g] - r[mask_g]) / delta[mask_g] + 2)
        
        # Blue dominant
        hue[mask_b] = 60 * ((r[mask_b] - g[mask_b]) / delta[mask_b] + 4)
        
        # Normalize hue to 0-360, then map rainbow colors
        # Rainbow: 240° (blue, cold) -> 0° (red, hot)
        hue = hue % 360
        
        # Invert: blue (240) should map to min_temp, red (0) to max_temp
        # Map 240->0 to 0->1 for temperature
        hue_normalized = np.where(hue <= 120, 
                                   1 - (hue / 120.0),  # Red to yellow (0-120)
                                   (240 - hue) / 120.0)  # Green to blue (120-240)
        
        # Handle saturation (use intensity for gray areas)
        saturation = delta / (max_val + 1e-10)
        intensity = (r + g + b) / 3.0
        
        # Combine hue-based and intensity-based mapping
        hue_factor = 0.7
        intensity_factor = 0.3
        combined = hue_normalized * hue_factor + (intensity / 255.0) * intensity_factor
        
        # Map to temperature range
        temperature = self.min_temp + combined * (self.max_temp - self.min_temp)
        
        return temperature.astype(np.float32)
    
    # Standard Rainbow ISO 2 palette, defined as colour stops from cold (0.0)
    # to hot (1.0). The ramp is regular and monotonic, so reconstruction is an
    # exact inverse lookup. If you have the exact vendor RGB values, replace
    # these stops with them; the algorithm below stays identical.
    RAINBOW_ISO2_STOPS = [
        (0.00,   0,   0,   0),    # black  - coldest
        (0.10,   0,   0, 130),    # dark blue
        (0.20,   0,   0, 255),    # blue
        (0.35,   0, 255, 255),    # cyan
        (0.50,   0, 255,   0),    # green
        (0.65, 255, 255,   0),    # yellow
        (0.80, 255, 128,   0),    # orange
        (0.90, 255,   0,   0),    # red
        (1.00, 255, 255, 255),    # white  - hottest
    ]

    def _build_color_lut(self, stops, n=256):
        """Interpolate colour stops into an n-entry RGB lookup table.

        :param stops: list of (position_0to1, R, G, B) tuples, sorted by position.
        :returns: float32 array of shape (n, 3) with the interpolated ramp.
        """
        positions = np.array([s[0] for s in stops], dtype=np.float32)
        colors = np.array([[s[1], s[2], s[3]] for s in stops], dtype=np.float32)
        xs = np.linspace(0.0, 1.0, n).astype(np.float32)
        lut = np.empty((n, 3), dtype=np.float32)
        for c in range(3):
            lut[:, c] = np.interp(xs, positions, colors[:, c])
        return lut

    def _positions_from_lut(self, r, g, b, lut):
        """Map each pixel to its position along the ramp via nearest colour.

        For every pixel, find the LUT entry whose colour is closest in RGB
        Euclidean distance and return that entry's normalised position (0..1).
        Runs in O(len(lut)) vectorised passes with O(pixels) memory.
        """
        r = r.astype(np.float32)
        g = g.astype(np.float32)
        b = b.astype(np.float32)
        best_idx = np.zeros(r.shape, dtype=np.int32)
        best_dist = np.full(r.shape, np.inf, dtype=np.float32)
        for i in range(lut.shape[0]):
            lr, lg, lb = lut[i]
            dist = (r - lr) ** 2 + (g - lg) ** 2 + (b - lb) ** 2
            closer = dist < best_dist
            best_dist[closer] = dist[closer]
            best_idx[closer] = i
        return best_idx.astype(np.float32) / (lut.shape[0] - 1)

    def rainbow_iso2_rgb_to_temp(self, r, g, b):
        """Convert RGB to temperature using the Rainbow ISO 2 colour profile.

        Rainbow ISO 2 is a standard, regularly-incrementing thermal palette, so
        the correct reconstruction is an exact inverse lookup: build the known
        colour ramp as a LUT, match each pixel to the nearest ramp colour, and
        map its position linearly onto the temperature range.
        """
        if getattr(self, "_rainbow_iso2_lut", None) is None:
            self._rainbow_iso2_lut = self._build_color_lut(self.RAINBOW_ISO2_STOPS, n=256)
        position = self._positions_from_lut(r, g, b, self._rainbow_iso2_lut)
        temperature = self.min_temp + position * (self.max_temp - self.min_temp)
        return temperature.astype(np.float32)
    
    def ironbow_rgb_to_temp(self, r, g, b):
        """Convert RGB to temperature using ironbow color profile"""
        # Similar to rainbow but with different color mapping
        # Ironbow typically: black -> purple -> blue -> cyan -> yellow -> red -> white
        return self.rainbow_rgb_to_temp(r, g, b)  # Simplified version
    
    def arctic_rgb_to_temp(self, r, g, b):
        """Convert RGB to temperature using arctic color profile"""
        # Arctic: blue-green-white gradient
        # Higher blue/green = colder, higher overall intensity = warmer
        intensity = (r.astype(np.float32) + g.astype(np.float32) + b.astype(np.float32)) / 3.0
        blue_green = (b.astype(np.float32) + g.astype(np.float32)) / 2.0
        
        # Combine: less blue-green and more intensity = warmer
        combined = (intensity - blue_green + 255) / (2 * 255)
        combined = np.clip(combined, 0, 1)
        
        temperature = self.min_temp + combined * (self.max_temp - self.min_temp)
        return temperature.astype(np.float32)

