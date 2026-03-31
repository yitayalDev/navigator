import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/models.dart';
import '../services/data_service.dart';
import '../services/location_service.dart';
import '../shortest_path_service.dart';
import '../walking_route_service.dart';
import '../location_share_service.dart';
import '../services/api_service.dart';
import 'ai_chat_screen.dart';

/// Campus Map Screen - Shows Google Map with user's current location
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
    final campusLocations = DataService.allLocations.where((loc) => loc.campus == widget.campus.id);
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
    final waypoints = DataService.allLocations
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

  /// Share current location to a friend via Telegram
  Future<void> _shareCurrentLocation() async {
    if (_userPosition == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please get your location first'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    // Show dialog to enter friend's username
    final friendController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Share My Location'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Share your current location with a friend via Telegram.',
              style: TextStyle(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: friendController,
              decoration: const InputDecoration(
                labelText: "Friend's username",
                hintText: 'Enter username (without @)',
                prefixText: '@',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final friendUsername = friendController.text.trim();
              if (friendUsername.isEmpty) {
                return;
              }
              
              Navigator.pop(dialogContext);
              
              // Show loading
              showDialog(
                context: context,
                barrierDismissible: false,
                builder: (context) => const Center(child: CircularProgressIndicator()),
              );
              
              try {
                final coords = '${_userPosition!.latitude},${_userPosition!.longitude}';
                final result = await ApiService.shareLocationToFriend(
                  senderId: 'app_user',
                  friendUsername: friendUsername,
                  coords: coords,
                  locationName: 'My Current Location',
                  senderName: 'UOG Navigator User',
                );
                
                if (mounted) {
                  Navigator.pop(context); // Close loading
                  
                  if (result != null && result['success'] == true) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('✅ Location sent to @$friendUsername!'),
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
                }
              } catch (e) {
                if (mounted) {
                  Navigator.pop(context); // Close loading
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Error: $e'),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF0088CC),
              foregroundColor: Colors.white,
            ),
            child: const Text('Share'),
          ),
        ],
      ),
    );
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
          // Share My Location button in app bar
          IconButton(
            icon: const Icon(Icons.share_location),
            onPressed: _shareCurrentLocation,
            tooltip: 'Share my location to friend',
          ),
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