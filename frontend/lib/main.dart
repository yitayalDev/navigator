import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_service.dart';
import 'bluetooth_service.dart';
import 'location_share_service.dart';
import 'shortest_path_service.dart';
import 'accessibility_manager.dart';
import 'draggable_widget.dart';
import 'gesture_service.dart';
import 'walking_route_service.dart';
import 'screens/ai_chat_screen.dart';

// Bot username for location sharing
const String botUsername = 'UOGStudentNavBot';

void main() {
  runApp(const UogNavigatorApp());
}

// Google Maps API Key
const String googleMapsApiKey = 'AIzaSyDxb9fKkpWmrupnMt0ijKGJi9pgILbLoPE';

class UogNavigatorApp extends StatelessWidget {
  const UogNavigatorApp({super.key});

  // Accessibility Manager instance
  static final AccessibilityManager accessibilityManager = AccessibilityManager();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'UOG Student Navigation',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1E88E5),
          brightness: Brightness.light,
        ),
        fontFamily: 'Roboto',
      ),
      home: const SplashScreen(),
    );
  }
}

// Location Service Helper
class LocationService {
  static Future<Position?> getCurrentLocation() async {
    try {
      // First check if location services are enabled
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return null;
      }

      // Check permission
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return null;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return null;
      }

      // Get position with high accuracy - this is the REAL GPS location
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      
      // Return the actual position
      return position;
    } catch (e) {
      // If error, try one more time with default settings
      try {
        return await Geolocator.getCurrentPosition();
      } catch (e2) {
        return null;
      }
    }
  }

  // Get location with force refresh - bypasses any cache
  static Future<Position?> getRealTimeLocation() async {
    try {
      // Ensure location services are enabled
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return null;
      }

      // Request permission
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      
      if (permission == LocationPermission.denied || 
          permission == LocationPermission.deniedForever) {
        return null;
      }
      
      // Get current position
      return await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
    } catch (e) {
      return null;
    }
  }

  // Calculate distance between two points in meters
  static double calculateDistance(
    double lat1,
    double lng1,
    double lat2,
    double lng2,
  ) {
    return Geolocator.distanceBetween(lat1, lng1, lat2, lng2);
  }

  // Format distance for display
  static String formatDistance(double meters) {
    if (meters < 1000) {
      return '${meters.toStringAsFixed(0)}m';
    } else {
      return '${(meters / 1000).toStringAsFixed(1)}km';
    }
  }

  // Estimate walking time in minutes
  static String estimateWalkingTime(double meters) {
    // Average walking speed is about 5 km/h = 83.33 m/min
    final minutes = (meters / 83.33).ceil();
    if (minutes < 1) {
      return '<1';
    } else if (minutes == 1) {
      return '1';
    } else {
      return '$minutes';
    }
  }
}

/// Location Details Bottom Sheet with Bluetooth Occupancy Detection
class LocationDetailsSheet extends StatefulWidget {
  final Location location;
  final String distanceText;
  final Color campusColor;
  final bool canCheckOccupancy;
  final VoidCallback onNavigate;

  const LocationDetailsSheet({
    super.key,
    required this.location,
    required this.distanceText,
    required this.campusColor,
    required this.canCheckOccupancy,
    required this.onNavigate,
  });

  @override
  State<LocationDetailsSheet> createState() => _LocationDetailsSheetState();
}

class _LocationDetailsSheetState extends State<LocationDetailsSheet> {
  final BluetoothService _bluetoothService = BluetoothService();
  bool _isScanning = false;
  int _deviceCount = 0;
  String _occupancyStatus = 'Unknown';

  @override
  void initState() {
    super.initState();
    if (widget.canCheckOccupancy) {
      _startBluetoothScan();
    }
  }

  Future<void> _startBluetoothScan() async {
    setState(() {
      _isScanning = true;
    });

    // Request Bluetooth permission
    final bluetoothStatus = await Permission.bluetooth.request();
    final locationStatus = await Permission.locationWhenInUse.request();

    if (bluetoothStatus.isGranted && locationStatus.isGranted) {
      // Start scanning for Bluetooth devices
      final deviceCount = await _bluetoothService.scanForDevices(timeoutSeconds: 5);
      
      setState(() {
        _deviceCount = deviceCount;
        _isScanning = false;
        
        // Estimate occupancy based on device count
        if (_deviceCount < 5) {
          _occupancyStatus = 'Low';
        } else if (_deviceCount < 20) {
          _occupancyStatus = 'Moderate';
        } else {
          _occupancyStatus = 'High';
        }
      });
    } else {
      setState(() {
        _isScanning = false;
        _occupancyStatus = 'Permission denied';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with icon and name
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: widget.location.color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  widget.location.icon,
                  color: widget.location.color,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.location.name,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: widget.location.color.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        widget.location.category.toUpperCase(),
                        style: TextStyle(
                          color: widget.location.color,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Description
          Text(
            widget.location.description,
            style: TextStyle(
              fontSize: 15,
              color: Colors.grey[700],
            ),
          ),
          const SizedBox(height: 16),
          
          // Info rows
          _buildDetailRow(Icons.location_on, 'Coordinates', 
            '${widget.location.lat.toStringAsFixed(6)}, ${widget.location.lng.toStringAsFixed(6)}'),
          const SizedBox(height: 12),
          _buildDetailRow(Icons.straighten, 'Distance', widget.distanceText),
          
          // Show occupancy if this is a library or lab
          if (widget.canCheckOccupancy) ...[
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),
            Text(
              'Current Occupancy',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.grey[800],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _getOccupancyColor().withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _getOccupancyIcon(),
                    color: _getOccupancyColor(),
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _occupancyStatus,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _getOccupancyColor(),
                        ),
                      ),
                      if (_isScanning)
                        Text(
                          'Scanning for devices...',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        )
                      else
                        Text(
                          '$_deviceCount devices detected',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _isScanning ? null : _startBluetoothScan,
                  color: widget.campusColor,
                ),
              ],
            ),
          ],
          
          const SizedBox(height: 24),
          
          // Action buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: widget.onNavigate,
                  icon: const Icon(Icons.directions),
                  label: const Text('Navigate'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: widget.campusColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () async {
                    // Open Telegram bot for sharing
                    final telegramUrl = 'https://t.me/UOGStudentNavBot';
                    if (await canLaunchUrl(Uri.parse(telegramUrl))) {
                      await launchUrl(
                        Uri.parse(telegramUrl),
                        mode: LaunchMode.externalApplication,
                      );
                    } else {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Could not open Telegram'),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.send, size: 18),
                  label: const Text('Share via Telegram'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF0088CC),
                    side: const BorderSide(color: Color(0xFF0088CC)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
            ],
          ),
          
          // Bottom safe area
          SizedBox(height: MediaQuery.of(context).padding.bottom),
        ],
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.grey[100],
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: Colors.grey[700], size: 20),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Color _getOccupancyColor() {
    switch (_occupancyStatus) {
      case 'Low':
        return Colors.green;
      case 'Moderate':
        return Colors.orange;
      case 'High':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getOccupancyIcon() {
    switch (_occupancyStatus) {
      case 'Low':
        return Icons.check_circle;
      case 'Moderate':
        return Icons.warning;
      case 'High':
        return Icons.error;
      default:
        return Icons.help;
    }
  }
}

// Splash Screen
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // Initialize accessibility services
    await UogNavigatorApp.accessibilityManager.initialize();
    debugPrint('Accessibility services initialized');
    
    // Load locations from API
    await loadLocationsFromApi();
    
    // Wait for splash screen animation
    await Future.delayed(const Duration(seconds: 2));
    
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (context) => const CampusListPage()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF1E88E5),
              Color(0xFF1565C0),
              Color(0xFF0D47A1),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // App Icon
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.school,
                    size: 80,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 32),
                const Text(
                  'UOG Navigator',
                  style: TextStyle(
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'University of Gondar',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white.withOpacity(0.9),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 50),
                const CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
                const SizedBox(height: 20),
                Text(
                  'Loading campus data...',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// Campus Data Models
class Campus {
  final String id;
  final String name;
  final String description;
  final String center;
  final Color color;
  final IconData icon;
  final double lat;
  final double lng;

  const Campus({
    required this.id,
    required this.name,
    required this.description,
    required this.center,
    required this.color,
    required this.icon,
    required this.lat,
    required this.lng,
  });
}

class Location {
  final String name;
  final String category;
  final String campus;
  final String coords;
  final String description;
  final double lat;
  final double lng;

  const Location({
    required this.name,
    required this.category,
    required this.campus,
    required this.coords,
    required this.description,
    required this.lat,
    required this.lng,
  });

  IconData get icon {
    switch (category) {
      case 'building':
        return Icons.business;
      case 'library':
        return Icons.local_library;
      case 'cafe':
        return Icons.local_cafe;
      case 'dorm':
        return Icons.hotel;
      case 'lab':
        return Icons.science;
      case 'administration':
        return Icons.admin_panel_settings;
      default:
        return Icons.location_on;
    }
  }

  Color get color {
    switch (category) {
      case 'building':
        return Colors.blue;
      case 'library':
        return Colors.purple;
      case 'cafe':
        return Colors.orange;
      case 'dorm':
        return Colors.brown;
      case 'lab':
        return Colors.teal;
      case 'administration':
        return Colors.indigo;
      default:
        return Colors.grey;
    }
  }
}

// Campus Data
List<Campus> campuses = [
  Campus(
    id: 'maraki',
    name: 'Maraki Campus',
    description: 'Main campus of University of Gondar',
    center: '12.58613,37.44605',
    color: Color(0xFF1565C0),
    icon: Icons.account_balance,
    lat: 12.58613,
    lng: 37.44605,
  ),
  Campus(
    id: 'tewodros',
    name: 'Tewodros Campus',
    description: 'Arts, Business & Law campus',
    center: '12.58559,37.43943',
    color: Color(0xFF2E7D32),
    icon: Icons.business_center,
    lat: 12.58559,
    lng: 37.43943,
  ),
  Campus(
    id: 'fasil',
    name: 'Fasil Campus',
    description: 'Medical & Health Sciences campus',
    center: '12.5775,37.4455',
    color: Color(0xFFC62828),
    icon: Icons.local_hospital,
    lat: 12.5775,
    lng: 37.4455,
  ),
];

// All Locations - Loaded from MongoDB via API
List<Location> allLocations = [];

// Flag to track if data is loaded from API
bool isDataLoadedFromApi = false;

// Load locations from MongoDB API
Future<void> loadLocationsFromApi() async {
  try {
    final data = await ApiService.getLocations();
    if (data != null && data['success'] == true) {
      // Clear existing data
      allLocations.clear();
      
      // Load locations from API
      final locationsList = data['locations'] as List<dynamic>;
      for (var loc in locationsList) {
        // Parse coords to lat/lng
        String coords = loc['coords'] ?? '';
        double? lat;
        double? lng;
        if (coords.contains(',')) {
          final parts = coords.split(',');
          lat = double.tryParse(parts[0]);
          lng = double.tryParse(parts[1]);
        }
        
        allLocations.add(Location(
          name: loc['name'] ?? '',
          category: loc['category'] ?? '',
          campus: loc['campus'] ?? '',
          coords: coords,
          description: loc['description'] ?? '',
          lat: lat ?? 0,
          lng: lng ?? 0,
        ));
      }
      
      // Load campuses
      final campusesData = data['campuses'] as Map<String, dynamic>?;
      if (campusesData != null) {
        campuses = campusesData.entries.map((e) {
          final value = e.value as Map<String, dynamic>;
          // Generate a color based on campus id
          final colorValue = e.key.hashCode | 0xFF000000;
          return Campus(
            id: e.key,
            name: value['name'] ?? '',
            description: value['description'] ?? '',
            center: value['center'] ?? '',
            lat: double.tryParse(value['center']?.split(',')[0] ?? '0') ?? 0,
            lng: double.tryParse(value['center']?.split(',')[1] ?? '0') ?? 0,
            color: Color(colorValue),
            icon: Icons.location_city,
          );
        }).toList();
      }
      
      isDataLoadedFromApi = true;
      print('Loaded ${allLocations.length} locations from MongoDB');
    }
  } catch (e) {
    print('Error loading locations from API: $e');
    // Load fallback hardcoded data
    _loadFallbackData();
    isDataLoadedFromApi = false;
  }
}

// Fallback data in case API fails
void _loadFallbackData() {
  allLocations = [
    // Tewodros Campus - Buildings
    Location(name: 'President Office 1', category: 'administration', campus: 'tewodros', coords: '12.59078,37.44360', description: 'President Office', lat: 12.59078, lng: 37.44360),
    Location(name: 'President Office 2', category: 'administration', campus: 'tewodros', coords: '12.58905,37.44273', description: 'President Office 2', lat: 12.58905, lng: 37.44273),
    Location(name: 'Sador Building', category: 'building', campus: 'tewodros', coords: '12.58999,37.44300', description: 'Sador Building', lat: 12.58999, lng: 37.44300),
    Location(name: 'Main Store', category: 'building', campus: 'tewodros', coords: '12.58966,37.44264', description: 'Main Store', lat: 12.58966, lng: 37.44264),
    Location(name: 'Registrar ICT', category: 'administration', campus: 'tewodros', coords: '12.58903,37.44238', description: 'Registrar ICT', lat: 12.58903, lng: 37.44238),
    Location(name: 'Informatics', category: 'building', campus: 'tewodros', coords: '12.58883,37.44188', description: 'Informatics', lat: 12.58883, lng: 37.44188),
    Location(name: 'New Building', category: 'building', campus: 'tewodros', coords: '12.58783,37.44015', description: 'New Building', lat: 12.58783, lng: 37.44015),
    Location(name: 'Main Registrar', category: 'administration', campus: 'tewodros', coords: '12.58765,37.43945', description: 'Main Registrar', lat: 12.58765, lng: 37.43945),
    Location(name: 'Student Association', category: 'administration', campus: 'tewodros', coords: '12.58536,37.44007', description: 'Student Association', lat: 12.58536, lng: 37.44007),
    Location(name: 'Veterinary Registration', category: 'administration', campus: 'tewodros', coords: '12.58486,37.43905', description: 'Veterinary Registration', lat: 12.58486, lng: 37.43905),
    Location(name: 'Lecture Houses', category: 'building', campus: 'tewodros', coords: '12.58579,37.43788', description: 'Lecture Houses', lat: 12.58579, lng: 37.43788),
    // Libraries
    Location(name: 'Post Library', category: 'library', campus: 'tewodros', coords: '12.58910,37.44125', description: 'Post Library', lat: 12.58910, lng: 37.44125),
    Location(name: 'T15 Library', category: 'library', campus: 'tewodros', coords: '12.58775,37.44134', description: 'T15 Library', lat: 12.58775, lng: 37.44134),
    Location(name: 'Veterinary Library', category: 'library', campus: 'tewodros', coords: '12.58349,37.44003', description: 'Veterinary Library', lat: 12.58349, lng: 37.44003),
    // Labs
    Location(name: 'T9 Computer Lab', category: 'lab', campus: 'tewodros', coords: '12.58826,37.44157', description: 'T9 Computer Lab', lat: 12.58826, lng: 37.44157),
    Location(name: 'T10 Lab', category: 'lab', campus: 'tewodros', coords: '12.58827,37.44192', description: 'T10 Lab', lat: 12.58827, lng: 37.44192),
    Location(name: 'Biology Lab', category: 'lab', campus: 'tewodros', coords: '12.58727,37.44123', description: 'Biology Lab', lat: 12.58727, lng: 37.44123),
    Location(name: 'Chemistry Lab', category: 'lab', campus: 'tewodros', coords: '12.58721,37.44160', description: 'Chemistry Lab', lat: 12.58721, lng: 37.44160),
    Location(name: 'Physics Lab', category: 'lab', campus: 'tewodros', coords: '12.58671,37.44160', description: 'Physics Lab', lat: 12.58671, lng: 37.44160),
    // Cafes
    Location(name: 'Main Cafeteria', category: 'cafe', campus: 'tewodros', coords: '12.58382,37.44225', description: 'Main Cafeteria', lat: 12.58382, lng: 37.44225),
    Location(name: 'Cafe Store', category: 'cafe', campus: 'tewodros', coords: '12.58320,37.44225', description: 'Cafe Store', lat: 12.58320, lng: 37.44225),
    Location(name: 'Addis Hiywot', category: 'cafe', campus: 'tewodros', coords: '12.58405,37.44092', description: 'Addis Hiywot', lat: 12.58405, lng: 37.44092),
    // Dormitories
    Location(name: 'Federal Dormitory', category: 'dorm', campus: 'tewodros', coords: '12.58278,37.44037', description: 'Federal Dormitory', lat: 12.58278, lng: 37.44037),
    Location(name: 'Prep Dormitory', category: 'dorm', campus: 'tewodros', coords: '12.58201,37.44033', description: 'Prep Dormitory', lat: 12.58201, lng: 37.44033),
  ];
  
  // Fallback campuses
  campuses = [
    Campus(id: 'maraki', name: 'Maraki Campus', description: 'Main campus', center: '12.58613,37.44605', lat: 12.58613, lng: 37.44605, color: Colors.blue, icon: Icons.school),
    Campus(id: 'tewodros', name: 'Tewodros Campus', description: 'Arts, Business & Law', center: '12.58559,37.43943', lat: 12.58559, lng: 37.43943, color: Colors.green, icon: Icons.business),
    Campus(id: 'fasil', name: 'Fasil Campus', description: 'Medical campus', center: '12.5775,37.4455', lat: 12.5775, lng: 37.4455, color: Colors.red, icon: Icons.local_hospital),
  ];
}

// Campus List Page - Shows all 3 campuses
class CampusListPage extends StatefulWidget {
  final Position? currentPosition;

  const CampusListPage({super.key, this.currentPosition});

  @override
  State<CampusListPage> createState() => _CampusListPageState();
}

class _CampusListPageState extends State<CampusListPage> {
  Position? _position;
  bool _isLoadingLocation = false;
  String? _locationError;
  String? _pendingFriendUsername;

  @override
  void initState() {
    super.initState();
    _position = widget.currentPosition;
    if (_position == null) {
      _getCurrentLocation();
    }
    // Start polling for location requests from bot
    _startLocationRequestPolling();
  }

  void _startLocationRequestPolling() {
    // Poll every 2 seconds for location requests (faster response)
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 2));
      if (mounted) {
        await _checkLocationRequest();
      }
      return mounted;
    });
  }

  Future<void> _checkLocationRequest() async {
    // Get the Telegram user ID (for demo, using a stored value)
    final userId = await _getTelegramUserId();
    if (userId == null) return;

    try {
      final response = await ApiService.checkLocationRequest(userId);
      if (response != null && response['requested'] == true) {
        // We use a dummy pending value to avoid multiple rapid responses
        if (_pendingFriendUsername == null) {
          // Bot requested location, get current GPS and send to server
          _pendingFriendUsername = 'pending';
          await _respondToLocationRequest(userId);
        }
      }
    } catch (e) {
      // Ignore polling errors
    }
  }

  Future<String?> _getTelegramUserId() async {
    // Hardcoded Telegram user ID for the app
    return 'app_user';
  }

  Future<void> _respondToLocationRequest(String userId) async {
    // Get location using the improved location service
    Position? position = _position;
    if (position == null) {
      position = await LocationShareService.getCurrentLocation();
    }
    
    if (position != null) {
      final coords = '${position.latitude},${position.longitude}';
      final result = await ApiService.submitLocation(
        userId: userId,
        coords: coords,
        locationName: 'My Current Location',
      );
      
      if (result != null && result['success'] == true) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('✅ Location shared: $coords'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('❌ Failed: ${result?['error'] ?? 'Unknown error'}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('❌ Could not get GPS location'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
    
    _pendingFriendUsername = null;
  }

  // Get current location for campus list
  Future<void> _getCurrentLocation() async {
    setState(() {
      _isLoadingLocation = true;
      _locationError = null;
    });

    final position = await LocationService.getCurrentLocation();
    setState(() {
      _isLoadingLocation = false;
      if (position != null) {
        _position = position;
        
        // Send location to server so bot can get it
        _updateServerLocation('${position.latitude},${position.longitude}');
      } else {
        _locationError = 'Could not get location';
      }
    });
  }

  // Show accessibility settings dialog
  void _showAccessibilityDialog(BuildContext context) {
    final accessibilityManager = UogNavigatorApp.accessibilityManager;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.accessibility_new, color: Color(0xFF1E88E5)),
            SizedBox(width: 8),
            Text('Accessibility Settings'),
          ],
        ),
        content: StatefulBuilder(
          builder: (context, setState) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Blind Mode Toggle
              SwitchListTile(
                title: const Text('Blind Mode'),
                subtitle: const Text('Enable voice guidance and gestures'),
                value: accessibilityManager.isBlindMode,
                onChanged: (value) {
                  setState(() {
                    if (value) {
                      accessibilityManager.enableBlindMode();
                      accessibilityManager.voiceService.speak('Blind mode enabled');
                    } else {
                      accessibilityManager.disableBlindMode();
                    }
                  });
                },
              ),
              const Divider(),
              // Gesture Info
              const ListTile(
                leading: Icon(Icons.touch_app),
                title: Text('Gestures'),
                subtitle: Text(
                  '• Double click: Voice command\n'
                  '• Triple click: Emergency\n'
                  '• Swipe up: Next instruction\n'
                  '• Swipe down: Pause navigation',
                ),
              ),
              const Divider(),
              // Detect Blind User Button
              ElevatedButton.icon(
                onPressed: () {
                  accessibilityManager.detectBlindUser();
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Analyzing... Please look at the camera'),
                      duration: Duration(seconds: 3),
                    ),
                  );
                },
                icon: const Icon(Icons.camera_alt),
                label: const Text('Detect Blind User'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E88E5),
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
  
  // Update server with current location (so bot can get it when needed)
  Future<void> _updateServerLocation(String coords) async {
    // Get hardcoded Telegram user ID
    final userId = 'app_user';
    
    try {
      await ApiService.updateLocation(
        userId: userId,
        coords: coords,
      );
    } catch (e) {
      // Silently fail - location update is not critical
    }
  }
  

  /// Share current GPS location to a friend
  void _shareCurrentLocation() async {
    // Show dialog to select friend from list
    final selectedUserController = TextEditingController();
    List<Map<String, String>> users = [];
    bool isLoading = true;
    
    // Load users from API
    final loadedUsers = await ApiService.getUsers();
    if (loadedUsers != null && loadedUsers.isNotEmpty) {
      users = loadedUsers;
    }
    isLoading = false;
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Share My Location'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Share your current GPS location with a friend via Telegram.',
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 16),
              if (isLoading)
                const Center(child: CircularProgressIndicator())
              else if (users.isEmpty)
                const Text(
                  'No friends found.\nAsk your friends to start the Telegram bot first!',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.orange),
                )
              else ...[
                const Text(
                  'Select a friend:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: DropdownButton<String>(
                    isExpanded: true,
                    underline: const SizedBox(),
                    hint: const Text('Choose a friend'),
                    value: selectedUserController.text.isEmpty ? null : selectedUserController.text,
                    items: users.map((user) {
                      return DropdownMenuItem<String>(
                        value: user['username'],
                        child: Row(
                          children: [
                            const Icon(Icons.person, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '@${user['username']}',
                                    style: const TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  if (user['name'] != null && user['name']!.isNotEmpty)
                                    Text(
                                      user['name']!,
                                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                    onChanged: (value) {
                      setState(() {
                        selectedUserController.text = value ?? '';
                      });
                    },
                  ),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
          ElevatedButton(
            onPressed: () async {
              final friendUsername = selectedUserController.text.trim();
              if (friendUsername.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Please select a friend'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              
              Navigator.pop(context);
              
              // Show loading indicator
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('📍 Getting your location and sharing...'),
                  backgroundColor: Colors.blue,
                  duration: Duration(seconds: 10),
                ),
              );
              
              // Get current GPS location instantly
              Position? position = _position;
              if (position == null) {
                position = await LocationShareService.getCurrentLocation();
              }
              
              if (position == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('❌ Could not get your location. Please enable GPS.'),
                    backgroundColor: Colors.red,
                  ),
                );
                return;
              }
              
              // Share the location immediately
              final coords = '${position.latitude},${position.longitude}';
              final result = await ApiService.shareLocationToFriend(
                senderId: 'app_user',
                friendUsername: friendUsername,
                coords: coords,
                locationName: 'My Current Location',
                senderName: 'UOG Navigator User',
              );
              
              if (result != null && result['success'] == true) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('✅ Location sent to @$friendUsername!\n📍 $coords'),
                    backgroundColor: Colors.green,
                  ),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('❌ Failed: ${result?['error'] ?? 'Unknown error'}'),
                    backgroundColor: Colors.red,
                  ),
                );
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0088CC),
              foregroundColor: Colors.white,
            ),
            child: const Text('Share Location'),
          ),
        ],
      ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 180,
            floating: false,
            pinned: true,
            backgroundColor: const Color(0xFF1E88E5),
            foregroundColor: Colors.white,
            actions: [
              // Location button in app bar
              IconButton(
                icon: _isLoadingLocation
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.my_location),
                onPressed: _isLoadingLocation ? null : _getCurrentLocation,
                tooltip: 'Get my location',
              ),
              // Accessibility settings button
              IconButton(
                icon: const Icon(Icons.accessibility_new),
                onPressed: () => _showAccessibilityDialog(context),
                tooltip: 'Accessibility Settings',
              ),

            ],
            flexibleSpace: FlexibleSpaceBar(
              title: const Text(
                'Select Campus',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                ),
              ),
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color(0xFF1E88E5),
                      Color(0xFF1565C0),
                      Color(0xFF0D47A1),
                    ],
                  ),
                ),
                child: Stack(
                  children: [
                    Positioned(
                      right: -30,
                      top: 30,
                      child: Icon(
                        Icons.school,
                        size: 150,
                        color: Colors.white.withOpacity(0.1),
                      ),
                    ),
                    // Show current location in header
                    if (_position != null)
                      Positioned(
                        left: 16,
                        bottom: 60,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.location_on,
                                size: 16,
                                color: Colors.white,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'Lat: ${_position!.latitude.toStringAsFixed(4)}, Lng: ${_position!.longitude.toStringAsFixed(4)}',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
          // Show location error if any
          if (_locationError != null)
            SliverToBoxAdapter(
              child: Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning, color: Colors.red, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _locationError!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ),
                    TextButton(
                      onPressed: _getCurrentLocation,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final campus = campuses[index];
                  return _buildCampusCard(context, campus);
                },
                childCount: campuses.length,
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // My Location FAB
          FloatingActionButton.small(
            heroTag: 'location',
            onPressed: _getCurrentLocation,
            backgroundColor: Colors.white,
            child: _isLoadingLocation
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.my_location, color: Color(0xFF1E88E5)),
          ),
          const SizedBox(height: 8),
          // Share My Location FAB
          FloatingActionButton.small(
            heroTag: 'share_location',
            onPressed: _shareCurrentLocation,
            backgroundColor: const Color(0xFF0088CC),
            tooltip: 'Share My Location',
            child: const Icon(Icons.share_location, color: Colors.white),
          ),
          const SizedBox(height: 8),
          // AI Campus Assistant FAB (Draggable)
          DraggableFAB(
            icon: Icons.smart_toy_outlined,
            label: 'AI Assistant',
            backgroundColor: const Color(0xFF6750A4),
            foregroundColor: Colors.white,
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AIChatScreen()),
              );
            },
            initialX: 20,
            initialY: 120,
          ),
        ],
      ),
    );
  }

  Widget _buildCampusCard(BuildContext context, Campus campus) {
    final locationCount = allLocations.where((l) => l.campus == campus.id).length;
    final categoryCount = allLocations
        .where((l) => l.campus == campus.id)
        .map((l) => l.category)
        .toSet()
        .length;

    // Calculate distance from current location
    String distanceText = '';
    if (_position != null) {
      final distance = LocationService.calculateDistance(
        _position!.latitude,
        _position!.longitude,
        campus.lat,
        campus.lng,
      );
      distanceText = LocationService.formatDistance(distance);
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            campus.color,
            campus.color.withOpacity(0.7),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: campus.color.withOpacity(0.4),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            right: -20,
            bottom: -20,
            child: Icon(
              campus.icon,
              size: 120,
              color: Colors.white.withOpacity(0.15),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        campus.icon,
                        color: Colors.white,
                        size: 32,
                      ),
                    ),
                    const Spacer(),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  campus.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  campus.description,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    _buildInfoChip(Icons.location_on, '$locationCount Places'),
                    const SizedBox(width: 12),
                    _buildInfoChip(Icons.category, '$categoryCount Categories'),
                    if (distanceText.isNotEmpty) ...[
                      const SizedBox(width: 12),
                      _buildInfoChip(Icons.directions_walk, distanceText),
                    ],
                  ],
                ),
                const SizedBox(height: 20),
                // Action buttons row
                Row(
                  children: [
                    // View Map button
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => CampusMapScreen(
                                campus: campus,
                                currentPosition: _position,
                              ),
                            ),
                          );
                        },
                        icon: const Icon(Icons.map, size: 18),
                        label: const Text('View Map'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: campus.color,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    // View Details button
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => CampusDetailPage(
                                campus: campus,
                                currentPosition: _position,
                              ),
                            ),
                          );
                        },
                        icon: const Icon(Icons.list, size: 18),
                        label: const Text('Details'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white,
                          side: const BorderSide(color: Colors.white),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

// Campus Detail Page - Shows locations for selected campus
class CampusDetailPage extends StatefulWidget {
  final Campus campus;
  final Position? currentPosition;

  const CampusDetailPage({
    super.key,
    required this.campus,
    this.currentPosition,
  });

  @override
  State<CampusDetailPage> createState() => _CampusDetailPageState();
}

class _CampusDetailPageState extends State<CampusDetailPage> {
  String _selectedCategory = 'all';
  String _searchQuery = '';
  Position? _position;

  @override
  void initState() {
    super.initState();
    _position = widget.currentPosition;
    if (_position == null) {
      _getCurrentLocation();
    }
  }

  Future<void> _getCurrentLocation() async {
    final position = await LocationService.getCurrentLocation();
    if (position != null) {
      setState(() {
        _position = position;
      });
    }
  }

  List<Location> get campusLocations {
    return allLocations.where((loc) {
      final matchesCampus = loc.campus == widget.campus.id;
      final matchesCategory =
          _selectedCategory == 'all' || loc.category == _selectedCategory;
      final matchesSearch = _searchQuery.isEmpty ||
          loc.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          loc.description.toLowerCase().contains(_searchQuery.toLowerCase());
      return matchesCampus && matchesCategory && matchesSearch;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 160,
            floating: false,
            pinned: true,
            backgroundColor: widget.campus.color,
            foregroundColor: Colors.white,
            actions: [
              IconButton(
                icon: const Icon(Icons.my_location),
                onPressed: _getCurrentLocation,
                tooltip: 'Get my location',
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              title: Text(
                widget.campus.name,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      widget.campus.color,
                      widget.campus.color.withOpacity(0.7),
                    ],
                  ),
                ),
                child: Stack(
                  children: [
                    Positioned(
                      right: -30,
                      top: 30,
                      child: Icon(
                        widget.campus.icon,
                        size: 150,
                        color: Colors.white.withOpacity(0.1),
                      ),
                    ),
                    // Show current location in header
                    if (_position != null)
                      Positioned(
                        left: 16,
                        bottom: 60,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.location_on,
                                size: 16,
                                color: Colors.white,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                'Your Location: ${_position!.latitude.toStringAsFixed(4)}, ${_position!.longitude.toStringAsFixed(4)}',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Column(
              children: [
                _buildSearchBar(),
                _buildFilterChips(),
              ],
            ),
          ),
          _buildLocationList(),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // AI Assistant FAB
          FloatingActionButton.small(
            heroTag: 'ai_chat_campus',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AIChatScreen()),
              );
            },
            backgroundColor: const Color(0xFF6750A4),
            child: const Icon(Icons.smart_toy_outlined, color: Colors.white),
          ),
          const SizedBox(height: 8),
          // Navigate to Campus FAB
          FloatingActionButton.extended(
            heroTag: 'navigate',
            onPressed: () async {
              // Get fresh location before navigating
              final pos = await LocationService.getCurrentLocation();
              final currentPos = pos ?? _position;
              
              if (currentPos != null) {
                final origin = '${currentPos.latitude},${currentPos.longitude}';
                final destination = '${widget.campus.lat},${widget.campus.lng}';
                final uri = Uri.parse(
                  'https://www.google.com/maps/dir/?api=1&origin=$origin&destination=$destination&travelmode=walking',
                );
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              } else {
                // Fallback to just destination if no current location
                final destination = '${widget.campus.lat},${widget.campus.lng}';
                final uri = Uri.parse(
                  'https://www.google.com/maps/dir/?api=1&destination=$destination&travelmode=walking',
                );
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              }
            },
            icon: const Icon(Icons.directions_walk),
            label: const Text('Navigate to Campus'),
            backgroundColor: widget.campus.color,
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: TextField(
        decoration: InputDecoration(
          hintText: 'Search in ${widget.campus.name}...',
          prefixIcon: Icon(Icons.search, color: widget.campus.color),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear, color: Colors.grey),
                  onPressed: () {
                    setState(() {
                      _searchQuery = '';
                    });
                  },
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide.none,
          ),
          filled: true,
          fillColor: Colors.grey[100],
        ),
        onChanged: (value) {
          setState(() {
            _searchQuery = value;
          });
        },
      ),
    );
  }

  Widget _buildFilterChips() {
    final categories = _getCategoriesForCampus();
    
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _buildFilterChip('All', 'all', Icons.apps, widget.campus.color),
          const SizedBox(width: 8),
          ...categories.map((cat) => Padding(
            padding: const EdgeInsets.only(right: 8),
            child: _buildFilterChip(
              cat['name'] as String,
              cat['value'] as String,
              cat['icon'] as IconData,
              cat['color'] as Color,
            ),
          )),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _getCategoriesForCampus() {
    final campusLocs = allLocations.where((l) => l.campus == widget.campus.id);
    final categories = campusLocs.map((l) => l.category).toSet();
    
    List<Map<String, dynamic>> result = [];
    
    // Predefined categories with their display names and icons
    final predefinedCategories = {
      'building': {'name': 'Buildings', 'icon': Icons.business, 'color': Colors.blue},
      'lab': {'name': 'Labs', 'icon': Icons.science, 'color': Colors.teal},
      'library': {'name': 'Libraries', 'icon': Icons.local_library, 'color': Colors.purple},
      'cafe': {'name': 'Cafes/Lounges', 'icon': Icons.local_cafe, 'color': Colors.orange},
      'dorm': {'name': 'Dorms', 'icon': Icons.hotel, 'color': Colors.brown},
      'administration': {'name': 'Administration', 'icon': Icons.admin_panel_settings, 'color': Colors.indigo},
    };
    
    // Add custom categories FIRST (at the top) - these are categories not in predefined list
    final customCategories = categories.where((c) => !predefinedCategories.containsKey(c));
    for (var cat in customCategories) {
      result.add({
        'name': _capitalizeFirst(cat),
        'value': cat,
        'icon': Icons.place,
        'color': Colors.green,
      });
    }
    
    // Add predefined categories after custom ones
    for (var entry in predefinedCategories.entries) {
      if (categories.contains(entry.key)) {
        result.add({
          'name': entry.value['name'],
          'value': entry.key,
          'icon': entry.value['icon'],
          'color': entry.value['color'],
        });
      }
    }
    
    return result;
  }

  String _capitalizeFirst(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }

  Widget _buildFilterChip(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    final isSelected = _selectedCategory == value;
    return FilterChip(
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 16,
            color: isSelected ? Colors.white : color,
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.black87,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ],
      ),
      selected: isSelected,
      selectedColor: color,
      backgroundColor: color.withOpacity(0.1),
      checkmarkColor: Colors.white,
      onSelected: (selected) {
        setState(() {
          _selectedCategory = selected ? value : 'all';
        });
      },
    );
  }

  Widget _buildLocationList() {
    final filtered = campusLocations;

    if (filtered.isEmpty) {
      return SliverFillRemaining(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.search_off, size: 80, color: Colors.grey[300]),
              const SizedBox(height: 16),
              Text(
                'No locations found',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(color: Colors.grey),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () {
                  setState(() {
                    _selectedCategory = 'all';
                    _searchQuery = '';
                  });
                },
                child: const Text('Clear filters'),
              ),
            ],
          ),
        ),
      );
    }

    return SliverPadding(
      padding: const EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) {
            final location = filtered[index];
            return _buildLocationCard(location);
          },
          childCount: filtered.length,
        ),
      ),
    );
  }

  Widget _buildLocationCard(Location location) {
    // Calculate distance from current location
    String distanceText = '';
    if (_position != null) {
      final distance = LocationService.calculateDistance(
        _position!.latitude,
        _position!.longitude,
        location.lat,
        location.lng,
      );
      distanceText = LocationService.formatDistance(distance);
    }

    return Dismissible(
      key: Key(location.name),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: Colors.green,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Icon(Icons.directions, color: Colors.white, size: 30),
      ),
      confirmDismiss: (direction) async {
        await _openMapsNavigation(location);
        return false;
      },
      child: Card(
        margin: const EdgeInsets.only(bottom: 12),
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: InkWell(
          onTap: () => _showLocationDetails(location),
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: location.color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(location.icon, color: location.color, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        location.name,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: location.color.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          location.category.toUpperCase(),
                          style: TextStyle(fontSize: 10, color: location.color, fontWeight: FontWeight.w600),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          if (distanceText.isNotEmpty) ...[
                            Icon(Icons.directions_walk, size: 14, color: Colors.grey[600]),
                            const SizedBox(width: 4),
                            Text(
                              distanceText,
                              style: TextStyle(color: Colors.grey[600], fontSize: 12),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: widget.campus.color.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.directions, color: widget.campus.color, size: 20),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showLocationDetails(Location location) {
    // Calculate distance from current location
    String distanceText = '';
    if (_position != null) {
      final distance = LocationService.calculateDistance(
        _position!.latitude,
        _position!.longitude,
        location.lat,
        location.lng,
      );
      distanceText = LocationService.formatDistance(distance);
    }

    // Check if this location can check occupancy (library or lab)
    final bool canCheckOccupancy = location.category == 'library' || location.category == 'lab';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return LocationDetailsSheet(
          location: location,
          distanceText: distanceText,
          campusColor: widget.campus.color,
          canCheckOccupancy: canCheckOccupancy,
          onNavigate: () {
            Navigator.pop(context);
            _openMapsNavigation(location);
          },
        );
      },
    );
  }

  Future<void> _openMapsNavigation(Location location) async {
    // Get fresh current location
    final currentPos = await LocationService.getCurrentLocation();
    final startPos = currentPos ?? _position;
    
    if (startPos != null) {
      final origin = '${startPos.latitude},${startPos.longitude}';
      final destination = '${location.lat},${location.lng}';
      final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&origin=$origin&destination=$destination&travelmode=walking',
      );
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      // Fallback - just open destination
      final destination = '${location.lat},${location.lng}';
      final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$destination&travelmode=walking',
      );
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

// Campus Map Screen - Shows Google Map with user's current location
class CampusMapScreen extends StatefulWidget {
  final Campus campus;
  final Position? currentPosition;

  const CampusMapScreen({
    super.key,
    required this.campus,
    this.currentPosition,
  });

  @override
  State<CampusMapScreen> createState() => _CampusMapScreenState();
}

class _CampusMapScreenState extends State<CampusMapScreen> {
  GoogleMapController? _mapController;
  Position? _userPosition;
  bool _isGettingLocation = false;
  Set<Marker> _markers = {};
  Set<Circle> _circles = {};
  List<LatLng>? _routePoints; // Shortest path route
  bool _isCalculatingRoute = false;
  Location? _selectedDestination;

  // Initial camera position - will be set to campus center or user location if available
  CameraPosition get _initialCameraPosition {
    // If we have user location, center on user
    if (_userPosition != null) {
      return CameraPosition(
        target: LatLng(_userPosition!.latitude, _userPosition!.longitude),
        zoom: 17,
      );
    }
    // Otherwise center on campus
    return CameraPosition(
      target: LatLng(widget.campus.lat, widget.campus.lng),
      zoom: 16,
    );
  }

  @override
  void initState() {
    super.initState();
    _userPosition = widget.currentPosition;
    _updateMarkers();
  }

  void _updateMarkers() {
    final markers = <Marker>{};
    final circles = <Circle>{};

    // Add campus marker
    markers.add(
      Marker(
        markerId: MarkerId('campus_${widget.campus.id}'),
        position: LatLng(widget.campus.lat, widget.campus.lng),
        infoWindow: InfoWindow(
          title: widget.campus.name,
          snippet: widget.campus.description,
        ),
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure),
      ),
    );

    // Add location markers for this campus
    final campusLocations = allLocations.where((loc) => loc.campus == widget.campus.id);
    for (final location in campusLocations) {
      markers.add(
        Marker(
          markerId: MarkerId('location_${location.name}'),
          position: LatLng(location.lat, location.lng),
          infoWindow: InfoWindow(
            title: location.name,
            snippet: location.description,
          ),
          icon: _getMarkerIcon(location.category),
          onTap: () => _showLocationDetails(location),
        ),
      );
    }

    // Add user location marker if available
    if (_userPosition != null) {
      markers.add(
        Marker(
          markerId: const MarkerId('user_location'),
          position: LatLng(_userPosition!.latitude, _userPosition!.longitude),
          infoWindow: const InfoWindow(
            title: 'Your Location',
            snippet: 'You are here',
          ),
          icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueGreen),
        ),
      );

      // Add accuracy circle
      circles.add(
        Circle(
          circleId: const CircleId('user_accuracy'),
          center: LatLng(_userPosition!.latitude, _userPosition!.longitude),
          radius: 20, // 20 meters accuracy
          fillColor: Colors.green.withOpacity(0.2),
          strokeColor: Colors.green,
          strokeWidth: 2,
        ),
      );
    }

    setState(() {
      _markers = markers;
      _circles = circles;
    });
  }

  BitmapDescriptor _getMarkerIcon(String category) {
    switch (category) {
      case 'building':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueBlue);
      case 'library':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueViolet);
      case 'cafe':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueOrange);
      case 'dorm':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRose);
      case 'lab':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueCyan);
      case 'administration':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueMagenta);
      default:
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed);
    }
  }

  void _showLocationDetails(Location location) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: location.color.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(location.icon, color: location.color, size: 32),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        location.name,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        location.category.toUpperCase(),
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(location.description),
            const SizedBox(height: 8),
            Text(
              'Coordinates: ${location.lat.toStringAsFixed(6)}, ${location.lng.toStringAsFixed(6)}',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
            const SizedBox(height: 24),
            // Show route on map button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _calculateAndShowRoute(location);
                },
                icon: const Icon(Icons.route),
                label: const Text('Show Shortest Route on Map'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Open in Google Maps button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _navigateToLocation(location);
                },
                icon: const Icon(Icons.navigation),
                label: const Text('Open in Google Maps'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: widget.campus.color,
                  side: BorderSide(color: widget.campus.color),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Open Telegram button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  Navigator.pop(context);
                  final telegramUrl = 'https://t.me/UOGStudentNavBot';
                  if (await canLaunchUrl(Uri.parse(telegramUrl))) {
                    await launchUrl(
                      Uri.parse(telegramUrl),
                      mode: LaunchMode.externalApplication,
                    );
                  } else {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Could not open Telegram'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  }
                },
                icon: const Icon(Icons.send),
                label: const Text('Share via Telegram Bot'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF0088CC),
                  side: const BorderSide(color: Color(0xFF0088CC)),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Share location to friend via Telegram
  void _shareLocationToFriend(Location location) async {
    // Show a dialog to enter friend's username manually
    final friendUsernameController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Share Location via Telegram'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Enter the username of your friend to send the location.',
              style: TextStyle(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: friendUsernameController,
              decoration: InputDecoration(
                labelText: 'Friend\'s Username',
                hintText: 'Enter username (e.g., john_doe)',
                prefixText: '@',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                prefixIcon: const Icon(Icons.person),
              ),
              keyboardType: TextInputType.text,
              textInputAction: TextInputAction.done,
              onSubmitted: (value) {
                // Trigger share when user presses enter
                _sendLocationToFriend(context, location, friendUsernameController.text.trim());
              },
            ),
            const SizedBox(height: 8),
            Text(
              'Your friend must have started the Telegram bot to receive the location.',
              style: TextStyle(fontSize: 12, color: Colors.grey[500]),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              _sendLocationToFriend(context, location, friendUsernameController.text.trim());
            },
            icon: const Icon(Icons.send),
            label: const Text('Share'),
          ),
        ],
      ),
    );
  }

  /// Send location to friend
  void _sendLocationToFriend(BuildContext dialogContext, Location location, String friendUsername) async {
    if (friendUsername.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter a friend\'s username'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    // Remove @ symbol if user included it
    final cleanUsername = friendUsername.startsWith('@') 
        ? friendUsername.substring(1) 
        : friendUsername;
    
    Navigator.pop(dialogContext); // Close the dialog
    
    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );
    
    try {
      // Get current user location
      final position = await LocationShareService.getCurrentLocation();
      
      if (position == null) {
        if (context.mounted) {
          Navigator.pop(context); // Close loading
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Could not get your current location'),
              backgroundColor: Colors.red,
            ),
          );
        }
        return;
      }
      
      // Share location to friend via API
      final result = await ApiService.shareLocationToFriend(
        senderId: 'app_user',
        friendUsername: cleanUsername,
        coords: '${position.latitude},${position.longitude}',
        locationName: location.name,
        senderName: 'UOG Navigator User',
      );
      
      if (context.mounted) {
        Navigator.pop(context); // Close loading
        
        if (result != null && result['success'] == true) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Location sent to @${cleanUsername}!'),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed: ${result?['error'] ?? 'Unknown error'}'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        Navigator.pop(context); // Close loading
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  /// Calculate and show shortest route on map
  void _calculateAndShowRoute(Location destination) async {
    if (_userPosition == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please get your location first'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() {
      _isCalculatingRoute = true;
    });

    // Get waypoints from campus locations (these act as nodes in our graph)
    final waypoints = allLocations
        .where((loc) => loc.campus == widget.campus.id)
        .map((loc) => {'lat': loc.lat, 'lng': loc.lng})
        .toList();

    // First try our shortest path algorithm with campus waypoints
    final path = ShortestPathAlgorithm.findShortestPath(
      _userPosition!.latitude,
      _userPosition!.longitude,
      destination.lat,
      destination.lng,
      waypoints,
    );

    // Calculate distance using our algorithm
    double ourDistance = 0;
    for (int i = 1; i < path.length; i++) {
      ourDistance += ShortestPathAlgorithm.calculateDistance(
        path[i - 1]['lat']!,
        path[i - 1]['lng']!,
        path[i]['lat']!,
        path[i]['lng']!,
      );
    }

    // Also try Google Maps walking directions
    final walkingRoute = await WalkingRouteService().getBestWalkingRoute(
      startLat: _userPosition!.latitude,
      startLng: _userPosition!.longitude,
      endLat: destination.lat,
      endLng: destination.lng,
      campusWaypoints: waypoints,
    );

    // Use the shorter route
    List<Map<String, double>> finalPath;
    if (walkingRoute.isValid && walkingRoute.totalDistanceMeters < ourDistance) {
      debugPrint('Using Google Maps walking route (shorter)');
      finalPath = walkingRoute.path;
    } else {
      debugPrint('Using our shortest path algorithm');
      finalPath = path;
    }

    // Convert to LatLng points
    final routePoints = finalPath
        .map((p) => LatLng(p['lat']!, p['lng']!))
        .toList();

    // Calculate total distance
    double totalDistance = 0;
    for (int i = 0; i < routePoints.length - 1; i++) {
      totalDistance += ShortestPathAlgorithm.calculateDistance(
        routePoints[i].latitude,
        routePoints[i].longitude,
        routePoints[i + 1].latitude,
        routePoints[i + 1].longitude,
      );
    }

    final estimatedTime = ShortestPathAlgorithm.estimateWalkingTime(totalDistance);

    setState(() {
      _routePoints = routePoints;
      _selectedDestination = destination;
      _isCalculatingRoute = false;
    });

    // Animate camera to show entire route
    if (routePoints.isNotEmpty) {
      _mapController?.animateCamera(
        CameraUpdate.newLatLngBounds(
          _boundsFromPoints(routePoints),
          50,
        ),
      );
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '🚶 Walking Route Found!\n'
          'Distance: ${ShortestPathAlgorithm.formatDistance(totalDistance)}\n'
          'Walking time: ~$estimatedTime minutes',
        ),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 5),
      ),
    );
  }

  /// Calculate bounds from route points
  LatLngBounds _boundsFromPoints(List<LatLng> points) {
    double minLat = points[0].latitude;
    double maxLat = points[0].latitude;
    double minLng = points[0].longitude;
    double maxLng = points[0].longitude;

    for (final point in points) {
      if (point.latitude < minLat) minLat = point.latitude;
      if (point.latitude > maxLat) maxLat = point.latitude;
      if (point.longitude < minLng) minLng = point.longitude;
      if (point.longitude > maxLng) maxLng = point.longitude;
    }

    return LatLngBounds(
      southwest: LatLng(minLat, minLng),
      northeast: LatLng(maxLat, maxLng),
    );
  }

  Future<void> _navigateToLocation(Location location) async {
    final origin = '${_userPosition?.latitude ?? widget.campus.lat},${_userPosition?.longitude ?? widget.campus.lng}';
    final destination = '${location.lat},${location.lng}';
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&origin=$origin&destination=$destination&travelmode=walking',
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  // Method to get user's real current location - this is the "Get Location" button functionality
  Future<void> _getUserLocation() async {
    setState(() {
      _isGettingLocation = true;
    });

    try {
      // First try to get last known location as quick fallback
      Position? lastKnownPosition;
      try {
        lastKnownPosition = await Geolocator.getLastKnownPosition();
      } catch (e) {
        // Ignore errors from getLastKnownPosition
      }

      // Check if location services are enabled
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        // Try using last known position if available
        if (lastKnownPosition != null) {
          setState(() {
            _userPosition = lastKnownPosition;
          });
          _updateMarkers();
          _mapController?.animateCamera(
            CameraUpdate.newLatLngZoom(
              LatLng(lastKnownPosition.latitude, lastKnownPosition.longitude),
              17,
            ),
          );
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Using last known location (location services disabled)'),
                backgroundColor: Colors.orange,
              ),
            );
          }
          setState(() => _isGettingLocation = false);
          return;
        }
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Please enable location services on your phone'),
              backgroundColor: Colors.red,
            ),
          );
        }
        setState(() => _isGettingLocation = false);
        return;
      }

      // Check and request permissions
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Location permission denied. Please allow location access.'),
                backgroundColor: Colors.red,
              ),
            );
          }
          setState(() => _isGettingLocation = false);
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Location permission permanently denied. Please enable in phone Settings > Apps > UOG Navigation > Permissions.'),
              backgroundColor: Colors.red,
              duration: Duration(seconds: 5),
            ),
          );
        }
        setState(() => _isGettingLocation = false);
        return;
      }

      // Try to get current position with high accuracy first
      Position? position;
      
      try {
        // Get current position with high accuracy
        position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 15),
        );
      } catch (e) {
        // If high accuracy fails, try with best accuracy
        try {
          position = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.best,
            timeLimit: const Duration(seconds: 10),
          );
        } catch (e2) {
          // If that also fails, try with best for navigation
          try {
            position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.bestForNavigation,
              timeLimit: const Duration(seconds: 10),
            );
          } catch (e3) {
            // Use last known position as final fallback
            position = lastKnownPosition;
          }
        }
      }

      if (position == null) {
        // Try one more time with any available method
        try {
          position = await Geolocator.getCurrentPosition();
        } catch (e4) {
          // If all methods fail, try last known
          try {
            position = await Geolocator.getLastKnownPosition();
          } catch (e5) {
            // Give up
          }
        }
      }

      // Use whatever position we got (could still be null)
      if (position != null) {
        setState(() {
          _userPosition = position;
        });

        // Update markers with new user location
        _updateMarkers();

        // Animate camera to user location - THIS IS THE KEY - move to user's actual GPS location
        _mapController?.animateCamera(
          CameraUpdate.newLatLngZoom(
            LatLng(position.latitude, position.longitude), // Use the ACTUAL user coordinates
            17,
          ),
        );

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '📍 YOUR REAL LOCATION:\nLat: ${position.latitude.toStringAsFixed(6)}\nLng: ${position.longitude.toStringAsFixed(6)}\n\nThe map is now showing YOUR GPS location!',
              ),
              backgroundColor: Colors.green,
              duration: const Duration(seconds: 8),
            ),
          );
        }
      } else {
        // Show error if no position could be obtained
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Could not get your location. Please try again or check GPS.'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error getting location: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isGettingLocation = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.campus.name} Map'),
        backgroundColor: widget.campus.color,
        foregroundColor: Colors.white,
        actions: [
          // Get My Location button in app bar
          IconButton(
            icon: _isGettingLocation
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.my_location),
            onPressed: _isGettingLocation ? null : _getUserLocation,
            tooltip: 'Get my real location',
          ),
        ],
      ),
      body: Stack(
        children: [
          // Google Map
          GoogleMap(
            initialCameraPosition: _initialCameraPosition,
            markers: _markers,
            circles: _circles,
            polylines: _routePoints != null && _routePoints!.length > 1
                ? {
                    Polyline(
                      polylineId: const PolylineId('route'),
                      points: _routePoints!,
                      color: Colors.green,
                      width: 5,
                      patterns: [PatternItem.dash(20), PatternItem.gap(10)],
                    ),
                  }
                : {},
            myLocationEnabled: true, // Use Google's native location (blue dot)
            myLocationButtonEnabled: true, // Show Google's location button
            mapToolbarEnabled: false,
            zoomControlsEnabled: false,
            onMapCreated: (controller) {
              _mapController = controller;
            },
          ),

          // Legend
          Positioned(
            top: 16,
            left: 16,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildLegendItem(Colors.blue, 'Buildings'),
                  const SizedBox(height: 4),
                  _buildLegendItem(Colors.purple, 'Libraries'),
                  const SizedBox(height: 4),
                  _buildLegendItem(Colors.orange, 'Cafes'),
                  const SizedBox(height: 4),
                  _buildLegendItem(Colors.green, 'Your Location'),
                  if (_routePoints != null && _routePoints!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    const Divider(height: 1),
                    const SizedBox(height: 8),
                    _buildLegendItem(Colors.green, 'Route Path'),
                    const SizedBox(height: 8),
                    GestureDetector(
                      onTap: () {
                        setState(() {
                          _routePoints = null;
                          _selectedDestination = null;
                        });
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.red.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.close, size: 14, color: Colors.red),
                            SizedBox(width: 4),
                            Text(
                              'Clear Route',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.red,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Show user location info at bottom
          if (_userPosition != null)
            Positioned(
              bottom: 16,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.1),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.green.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.location_on, color: Colors.green),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text(
                            'Your Current Location',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Lat: ${_userPosition!.latitude.toStringAsFixed(6)}, Lng: ${_userPosition!.longitude.toStringAsFixed(6)}',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),

      // FAB buttons
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // AI Assistant FAB
          FloatingActionButton.small(
            heroTag: 'ai_chat_map',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const AIChatScreen()),
              );
            },
            backgroundColor: const Color(0xFF6750A4),
            child: const Icon(Icons.smart_toy_outlined, color: Colors.white),
          ),
          const SizedBox(height: 8),
          // Get My Location FAB button
          FloatingActionButton.extended(
            heroTag: 'my_location',
            onPressed: _isGettingLocation ? null : _getUserLocation,
            backgroundColor: widget.campus.color,
            icon: _isGettingLocation
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.my_location),
            label: Text(_isGettingLocation ? 'Getting Location...' : 'Get My Location'),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}
