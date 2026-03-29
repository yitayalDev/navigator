import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/data_service.dart';
import '../accessibility_manager.dart';
import '../draggable_widget.dart';
import 'campus_detail_screen.dart';
import 'campus_map_screen.dart';
import 'ai_chat_screen.dart';

/// Campus List Screen - Shows all campuses
class CampusListScreen extends StatefulWidget {
  final Position? currentPosition;
  final AccessibilityManager accessibilityManager;

  const CampusListScreen({
    super.key,
    this.currentPosition,
    required this.accessibilityManager,
  });

  @override
  State<CampusListScreen> createState() => _CampusListScreenState();
}

class _CampusListScreenState extends State<CampusListScreen> {
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
    _startLocationRequestPolling();
  }

  void _startLocationRequestPolling() {
    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 2));
      if (mounted) {
        await _checkLocationRequest();
      }
      return mounted;
    });
  }

  Future<void> _checkLocationRequest() async {
    final userId = await _getTelegramUserId();
    if (userId == null) return;

    try {
      final response = await ApiService.checkLocationRequest(userId);
      if (response != null && response['requested'] == true) {
        if (_pendingFriendUsername == null) {
          _pendingFriendUsername = 'pending';
          await _respondToLocationRequest(userId);
        }
      }
    } catch (e) {
      // Ignore polling errors
    }
  }

  Future<String?> _getTelegramUserId() async {
    return 'app_user';
  }

  Future<void> _respondToLocationRequest(String userId) async {
    Position? position = _position;
    if (position == null) {
      // Import location share service dynamically
      position = await _getCurrentLocationFromService();
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

  Future<Position?> _getCurrentLocationFromService() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return null;

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }

      return await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
    } catch (e) {
      return null;
    }
  }

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
        _updateServerLocation('${position.latitude},${position.longitude}');
      } else {
        _locationError = 'Could not get location';
      }
    });
  }

  void _showAccessibilityDialog(BuildContext context) {
    final accessibilityManager = widget.accessibilityManager;

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

  Future<void> _updateServerLocation(String coords) async {
    final userId = 'app_user';
    try {
      await ApiService.updateLocation(userId: userId, coords: coords);
    } catch (e) {
      // Silently fail
    }
  }

  void _shareCurrentLocation() async {
    final selectedUserController = TextEditingController();
    List<Map<String, String>> users = [];
    bool isLoading = true;

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
                    value: selectedUserController.text.isEmpty
                        ? null
                        : selectedUserController.text,
                    items: users
                        .map((user) => DropdownMenuItem<String>(
                              value: user['username'],
                              child: Row(
                                children: [
                                  const Icon(Icons.person, size: 20),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          '@${user['username']}',
                                          style: const TextStyle(
                                              fontWeight: FontWeight.bold),
                                        ),
                                        if (user['name'] != null &&
                                            user['name']!.isNotEmpty)
                                          Text(
                                            user['name']!,
                                            style: TextStyle(
                                                fontSize: 12,
                                                color: Colors.grey[600]),
                                          ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ))
                        .toList(),
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

                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('📍 Getting your location and sharing...'),
                    backgroundColor: Colors.blue,
                    duration: Duration(seconds: 10),
                  ),
                );

                Position? position = _position;
                if (position == null) {
                  position = await _getCurrentLocationFromService();
                }

                if (position == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content:
                          Text('❌ Could not get your location. Please enable GPS.'),
                      backgroundColor: Colors.red,
                    ),
                  );
                  return;
                }

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
                      content:
                          Text('✅ Location sent to @$friendUsername!\n📍 $coords'),
                      backgroundColor: Colors.green,
                    ),
                  );
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                          '❌ Failed: ${result?['error'] ?? 'Unknown error'}'),
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
              IconButton(
                icon: const Icon(Icons.accessibility_new),
                onPressed: () => _showAccessibilityDialog(context),
                tooltip: 'Accessibility Settings',
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              title: const Text(
                'Select Campus',
                style: TextStyle(fontWeight: FontWeight.bold),
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
                  ],
                ),
              ),
            ),
          ),
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
                      child: Text(_locationError!,
                          style: const TextStyle(color: Colors.red)),
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
                  final campus = DataService.campuses[index];
                  return _buildCampusCard(context, campus);
                },
                childCount: DataService.campuses.length,
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
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
    final locationCount =
        DataService.allLocations.where((l) => l.campus == campus.id).length;
    final categoryCount = DataService.allLocations
        .where((l) => l.campus == campus.id)
        .map((l) => l.category)
        .toSet()
        .length;

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
                      child: Icon(campus.icon, color: Colors.white, size: 32),
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
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.9),
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Flexible(
                      child: _buildInfoChip(Icons.location_on, '$locationCount Places'),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: _buildInfoChip(Icons.category, '$categoryCount Categories'),
                    ),
                    if (distanceText.isNotEmpty) ...[
                      const SizedBox(width: 8),
                      Flexible(
                        child: _buildInfoChip(Icons.directions_walk, distanceText),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
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
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: Colors.white),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              text,
              style: const TextStyle(color: Colors.white, fontSize: 11),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}