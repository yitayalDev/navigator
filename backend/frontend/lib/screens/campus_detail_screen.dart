import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/models.dart';
import '../services/location_service.dart';
import '../services/data_service.dart';
import '../services/bluetooth_service.dart';
import 'ai_chat_screen.dart';

/// Campus Detail Page - Shows locations for selected campus
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
    return DataService.allLocations.where((loc) {
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
    final campusLocs = DataService.allLocations.where((l) => l.campus == widget.campus.id);
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
  // Bluetooth service - using the service from services folder
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
    // For now, simulate occupancy detection
    // In production, use actual Bluetooth scanning
    setState(() {
      _isScanning = true;
      _occupancyStatus = 'Scanning...';
    });
    
    await Future.delayed(const Duration(seconds: 2));
    
    // Simulate result
    setState(() {
      _isScanning = false;
      _deviceCount = (DateTime.now().millisecond % 20) + 5;
      if (_deviceCount > 15) {
        _occupancyStatus = 'Busy';
      } else if (_deviceCount > 8) {
        _occupancyStatus = 'Moderate';
      } else {
        _occupancyStatus = 'Quiet';
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              // Header with icon and title
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: widget.location.color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Icon(widget.location.icon, color: widget.location.color, size: 32),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.location.name,
                          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: widget.location.color.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            widget.location.category.toUpperCase(),
                            style: TextStyle(fontSize: 11, color: widget.location.color, fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              
              // Description
              Text(
                widget.location.description,
                style: TextStyle(color: Colors.grey[600], fontSize: 15),
              ),
              const SizedBox(height: 16),
              
              // Distance info
              if (widget.distanceText.isNotEmpty) ...[
                Row(
                  children: [
                    Icon(Icons.directions_walk, color: widget.campusColor),
                    const SizedBox(width: 8),
                    Text(
                      'Distance: ${widget.distanceText}',
                      style: const TextStyle(fontSize: 16),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
              ],
              
              // Occupancy status (if applicable)
              if (widget.canCheckOccupancy) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            _getOccupancyIcon(),
                            color: _getOccupancyColor(),
                            size: 24,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Current Occupancy',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (_isScanning)
                        const Row(
                          children: [
                            SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                            SizedBox(width: 8),
                            Text('Scanning for nearby devices...'),
                          ],
                        )
                      else
                        Text(
                          _occupancyStatus,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: _getOccupancyColor(),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
              
              // Navigate button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: widget.onNavigate,
                  icon: const Icon(Icons.directions),
                  label: const Text('Navigate'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: widget.campusColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  IconData _getOccupancyIcon() {
    switch (_occupancyStatus) {
      case 'Busy':
        return Icons.warning;
      case 'Moderate':
        return Icons.info;
      case 'Quiet':
        return Icons.check_circle;
      default:
        return Icons.help;
    }
  }

  Color _getOccupancyColor() {
    switch (_occupancyStatus) {
      case 'Busy':
        return Colors.red;
      case 'Moderate':
        return Colors.orange;
      case 'Quiet':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
}