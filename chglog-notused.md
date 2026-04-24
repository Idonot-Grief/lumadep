# Changelog - Luma Minecraft Launcher v2.0

## v2.0.0 - Complete Overhaul

### New Features

#### Logging System
- ✅ Minecraft-compliant log format: `[HH:MM:SS] [Thread/LEVEL]: Message`
- ✅ Color-coded log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Automatic log file rotation with timestamps
- ✅ Thread-safe logging with global logger instance
- ✅ Game log capture and parsing
- ✅ Log callbacks for GUI integration

#### Enhanced Console Widget
- ✅ Right-click context menu (Copy, Copy All, Clear)
- ✅ Pyperclip integration for cross-platform clipboard
- ✅ Syntax highlighting by log level
- ✅ Maximum line limit to prevent memory bloat
- ✅ Smooth scrolling and text selection
- ✅ Monospace font rendering

#### Update System
- ✅ .upt patch file format (ZIP-based)
- ✅ Auto-detection from custom server
- ✅ Checksum verification (SHA256)
- ✅ Patch download with progress
- ✅ Applied patches history (JSON)
- ✅ Patch application with rollback support
- ✅ Manual patch import from file dialog

#### Update Server
- ✅ Flask-based REST API server
- ✅ XML and JSON update list formats
- ✅ Admin endpoints for patch management
- ✅ File hosting for patches
- ✅ Health check endpoint
- ✅ CORS support

#### Patch Management Tools
- ✅ Command-line admin tool (server/admin.py)
- ✅ Create patches from directories
- ✅ Register patches in update list
- ✅ Delete patches
- ✅ List all available updates
- ✅ Hash computation and verification

#### Standalone Patcher
- ✅ Separate executable for applying updates
- ✅ Multi-patch application
- ✅ Detailed logging with timestamps
- ✅ Patch history tracking
- ✅ Error handling and reporting

#### Proper Argument Parsing
- ✅ Parse complex JSON manifest arguments
- ✅ Support for conditional arguments (rules)
- ✅ Feature-based argument selection
- ✅ OS-specific argument handling (Windows, macOS, Linux)
- ✅ Architecture detection (x86, x64)
- ✅ Variable substitution (${auth_player_name}, etc.)
- ✅ Native library path configuration

#### Enhanced Settings
- ✅ MultiMC-style detailed configuration
- ✅ Per-instance and global settings
- ✅ Java executable selection
- ✅ RAM allocation (min/max)
- ✅ JVM arguments customization
- ✅ Offline username configuration
- ✅ API type selection (Mojang, Fabric, Custom)
- ✅ Update server URL configuration
- ✅ Logging level control
- ✅ Settings persistence

#### Theme System
- ✅ Dark theme (default, modern Aero design)
- ✅ Light theme (professional style)
- ✅ Auto theme detection
- ✅ Custom launcher icon support
- ✅ Custom palette configuration
- ✅ Stylesheet-based styling
- ✅ Font customization

#### Settings Dialog
- ✅ Tabbed interface
- ✅ General tab (updates, console, launcher behavior)
- ✅ Java tab (path, RAM, JVM args)
- ✅ Authentication tab (offline username, modes)
- ✅ Appearance tab (theme, custom icon)
- ✅ Advanced tab (API, update server, logging)
- ✅ File dialogs for path selection
- ✅ Real-time validation

#### Update Dialog
- ✅ Display available updates with descriptions
- ✅ Download patches
- ✅ Apply patches in sequence
- ✅ Show success/failure status
- ✅ Auto-restart launcher after update

#### Configuration Enhancements
- ✅ Dataclass-based config with type hints
- ✅ Nested config sections (Auth, Java, Theme)
- ✅ Auto-migration from old config format
- ✅ Config validation
- ✅ Default values
- ✅ Window geometry persistence
- ✅ Easy serialization/deserialization

### Improved Features

#### Authentication
- Enhanced offline mode with default username
- Support for custom authentication backends
- Token management improvements
- UUID handling

#### Game Launching
- Proper classpath construction
- Dynamic library loading
- Native library detection
- Fabric loader integration
- Asset management

#### Instance Management
- Enhanced instance metadata
- Custom instance icons
- Instance-specific Java settings
- Instance-specific JVM arguments

### Architecture Improvements

#### Code Organization
- Separated concerns (core, gui, server, patcher)
- Modular design for extensibility
- Type hints throughout
- Comprehensive docstrings

#### Thread Safety
- Singleton logger with locks
- Background worker threads
- Non-blocking UI updates
- Safe concurrent operations

#### Error Handling
- Comprehensive error logging
- Graceful degradation
- User-friendly error messages
- Debug information in logs

#### Performance
- Lazy initialization
- Resource caching
- Efficient file operations
- Memory-efficient logging

### Dependencies Added

```
PyQt6==6.6.1              # Modern Qt framework
PyQt6-sip==13.6.0         # Qt bindings
requests==2.31.0          # HTTP client
beautifulsoup4==4.12.2    # HTML parsing
lxml==4.9.3               # XML processing
cryptography==41.0.7      # Crypto operations
pyperclip==1.8.2          # Clipboard access
Pillow==10.1.0            # Image processing
psutil==5.9.6             # System utilities
Flask==2.3.0              # Web framework (server)
Flask-CORS==4.0.0         # CORS support (server)
pyopenssl==23.3.0         # SSL support (server)
```

### Configuration Migration

Old config files are automatically migrated to v2.0 format:
- `launcher_config.json` → `config.json`
- Legacy fields mapped to new structure
- Backward compatibility maintained

### Breaking Changes

None - maintains backward compatibility with v1.0 instances.

### Known Limitations

- Update server requires valid SSL certificate in production
- Patch files limited to 5MB per key in storage
- Concurrent patch downloads not supported (sequential only)
- Windows service patcher not implemented yet

### Future Enhancements

Planned for v2.1+:
- Digital signatures for patches
- Delta patches for bandwidth optimization
- Staged rollout of updates
- Launcher configuration import/export
- Multi-language UI
- Dark/Light theme detection on startup
- Automatic backup before patching
- Patch rollback functionality

---

**Migration Guide** (v1.0 → v2.0):

1. Backup your `.minecraft_launcher` directory
2. Extract new launcher
3. Run: `python main.py`
4. Old config will be auto-migrated
5. Review settings in Settings dialog
6. All instances will continue to work

For manual config updates, see `core/config.py` for new structure.
