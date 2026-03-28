import 'dart:async';
import 'dart:math';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/foundation.dart';
import 'shortest_path_service.dart';

/// Navigation state
enum NavigationState {
  idle,
  calculating,
  navigating,
  paused,
  arrived,
}

/// Turn-by-turn instruction type
enum TurnType {
  straight,
  slightLeft,
  left,
  sharpLeft,
  slightRight,
  right,
  sharpRight,
  uTurn,
  start,
  arrived,
}

/// Navigation instruction
class NavigationInstruction {
  final TurnType turnType;
  final String description;
  final double distance; // in meters
  final double? latitude;
  final double? longitude;
  final int stepIndex;

  NavigationInstruction({
    required this.turnType,
    required this.description,
    required this.distance,
    this.latitude,
    this.longitude,
    required this.stepIndex,
  });

  /// Get distance formatted for display
  String get formattedDistance => ShortestPathAlgorithm.formatDistance(distance);

  /// Get turn direction for voice announcement
  String get voiceAnnouncement {
    switch (turnType) {
      case TurnType.start:
        return 'Start walking';
      case TurnType.straight:
        return 'Continue straight for $formattedDistance';
      case TurnType.slightLeft:
        return 'Bear left for $formattedDistance';
      case TurnType.left:
        return 'Turn left in $formattedDistance';
      case TurnType.sharpLeft:
        return 'Turn sharp left in $formattedDistance';
      case TurnType.slightRight:
        return 'Bear right for $formattedDistance';
      case TurnType.right:
        return 'Turn right in $formattedDistance';
      case TurnType.sharpRight:
        return 'Turn sharp right in $formattedDistance';
      case TurnType.uTurn:
        return 'Make a U-turn in $formattedDistance';
      case TurnType.arrived:
        return 'You have arrived at your destination';
    }
  }
}

/// Navigation result containing path and instructions
class NavigationResult {
  final List<Map<String, double>> path;
  final List<NavigationInstruction> instructions;
  final double totalDistance;
  final int estimatedTimeMinutes;

  NavigationResult({
    required this.path,
    required this.instructions,
    required this.totalDistance,
    required this.estimatedTimeMinutes,
  });
}

/// Service for pedestrian navigation with continuous tracking
class PedestrianNavigationService {
  static final PedestrianNavigationService _instance = PedestrianNavigationService._internal();
  factory PedestrianNavigationService() => _instance;
  PedestrianNavigationService._internal();

  // Current state
  NavigationState _state = NavigationState.idle;
  Position? _currentPosition;
  Position? _previousPosition;
  List<Map<String, double>> _path = [];
  List<NavigationInstruction> _instructions = [];
  int _currentInstructionIndex = 0;
  String? _destinationName;
  
  // Tracking settings
  double _reachedThreshold = 15.0; // meters to consider reached
  double _offRouteThreshold = 30.0; // meters to consider off route
  
  // Callbacks
  Function(NavigationState)? onStateChanged;
  Function(Position)? onPositionUpdated;
  Function(NavigationInstruction)? onInstructionChanged;
  Function(String)? onArrived;
  Function(String)? onOffRoute;
  Function(double, String)? onDistanceUpdate;

  // Timer for continuous tracking
  Timer? _trackingTimer;
  StreamSubscription<Position>? _positionSubscription;

  // Getters
  NavigationState get state => _state;
  Position? get currentPosition => _currentPosition;
  String? get destinationName => _destinationName;
  int get currentInstructionIndex => _currentInstructionIndex;
  NavigationInstruction? get currentInstruction => 
      _instructions.isNotEmpty && _currentInstructionIndex < _instructions.length
          ? _instructions[_currentInstructionIndex]
          : null;
  double get totalDistanceRemaining {
    double distance = 0;
    for (int i = _currentInstructionIndex; i < _instructions.length; i++) {
      distance += _instructions[i].distance;
    }
    return distance;
  }

  /// Initialize the navigation service
  Future<bool> initialize() async {
    try {
      // Check location permission
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          debugPrint('Location permission denied');
          return false;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        debugPrint('Location permission permanently denied');
        return false;
      }

      // Get initial position
      _currentPosition = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      
      debugPrint('Navigation service initialized at: $_currentPosition');
      return true;
    } catch (e) {
      debugPrint('Navigation initialization error: $e');
      return false;
    }
  }

  /// Start navigation to a destination
  Future<NavigationResult?> startNavigation({
    required double destinationLat,
    required double destinationLng,
    required String destinationName,
    List<Map<String, double>>? waypoints,
  }) async {
    if (_currentPosition == null) {
      await initialize();
    }

    _destinationName = destinationName;
    _state = NavigationState.calculating;
    onStateChanged?.call(_state);

    // Calculate shortest path (using pedestrian paths)
    _path = ShortestPathAlgorithm.findShortestPath(
      _currentPosition!.latitude,
      _currentPosition!.longitude,
      destinationLat,
      destinationLng,
      waypoints ?? [],
    );

    // Generate turn-by-turn instructions
    _instructions = _generateInstructions(_path);
    _currentInstructionIndex = 0;

    _state = NavigationState.navigating;
    onStateChanged?.call(_state);

    // Start continuous tracking
    _startTracking();

    // Announce first instruction
    if (_instructions.isNotEmpty) {
      onInstructionChanged?.call(_instructions[0]);
    }

    return NavigationResult(
      path: _path,
      instructions: _instructions,
      totalDistance: _calculateTotalDistance(),
      estimatedTimeMinutes: ShortestPathAlgorithm.estimateWalkingTime(
        _calculateTotalDistance(),
      ),
    );
  }

  /// Generate turn-by-turn instructions from path
  List<NavigationInstruction> _generateInstructions(List<Map<String, double>> path) {
    final List<NavigationInstruction> instructions = [];

    if (path.length < 2) return instructions;

    // Add start instruction
    instructions.add(NavigationInstruction(
      turnType: TurnType.start,
      description: 'Start walking towards your destination',
      distance: 0,
      latitude: path[1]['lat'],
      longitude: path[1]['lng'],
      stepIndex: 0,
    ));

    // Generate instructions for each segment
    for (int i = 1; i < path.length - 1; i++) {
      final prev = path[i - 1];
      final curr = path[i];
      final next = path[i + 1];

      final distance = ShortestPathAlgorithm.calculateDistance(
        prev['lat']!,
        prev['lng']!,
        curr['lat']!,
        curr['lng']!,
      );

      final turnType = _calculateTurnType(prev, curr, next);
      final description = _getTurnDescription(turnType, distance);

      instructions.add(NavigationInstruction(
        turnType: turnType,
        description: description,
        distance: distance,
        latitude: next['lat'],
        longitude: next['lng'],
        stepIndex: i,
      ));
    }

    // Add arrival instruction
    instructions.add(NavigationInstruction(
      turnType: TurnType.arrived,
      description: 'You have arrived at $destinationName',
      distance: 0,
      stepIndex: path.length - 1,
    ));

    return instructions;
  }

  /// Calculate turn type based on three points
  TurnType _calculateTurnType(
    Map<String, double> prev,
    Map<String, double> curr,
    Map<String, double> next,
  ) {
    // Calculate bearing from current to next
    final bearing1 = _calculateBearing(
      curr['lat']!,
      curr['lng']!,
      next['lat']!,
      next['lng']!,
    );
    
    // Calculate bearing from previous to current
    final bearing2 = _calculateBearing(
      prev['lat']!,
      prev['lng']!,
      curr['lat']!,
      curr['lng']!,
    );

    // Calculate angle difference
    double angleDiff = bearing1 - bearing2;
    if (angleDiff > 180) angleDiff -= 360;
    if (angleDiff < -180) angleDiff += 360;

    // Determine turn type based on angle
    if (angleDiff.abs() < 15) {
      return TurnType.straight;
    } else if (angleDiff >= 15 && angleDiff < 45) {
      return angleDiff > 0 ? TurnType.slightRight : TurnType.slightLeft;
    } else if (angleDiff >= 45 && angleDiff < 120) {
      return angleDiff > 0 ? TurnType.right : TurnType.left;
    } else {
      return angleDiff > 0 ? TurnType.sharpRight : TurnType.sharpLeft;
    }
  }

  /// Calculate bearing between two points
  double _calculateBearing(double lat1, double lng1, double lat2, double lng2) {
    final dLng = (lng2 - lng1) * pi / 180;
    final lat1Rad = lat1 * pi / 180;
    final lat2Rad = lat2 * pi / 180;

    final x = sin(dLng) * cos(lat2Rad);
    final y = cos(lat1Rad) * sin(lat2Rad) - 
              sin(lat1Rad) * cos(lat2Rad) * cos(dLng);

    final bearing = atan2(x, y) * 180 / pi;
    return (bearing + 360) % 360;
  }

  /// Get human-readable turn description
  String _getTurnDescription(TurnType turn, double distance) {
    final distStr = ShortestPathAlgorithm.formatDistance(distance);
    
    switch (turn) {
      case TurnType.straight:
        return 'Continue for $distStr';
      case TurnType.slightLeft:
        return 'Bear left for $distStr';
      case TurnType.left:
        return 'Turn left in $distStr';
      case TurnType.sharpLeft:
        return 'Turn sharp left in $distStr';
      case TurnType.slightRight:
        return 'Bear right for $distStr';
      case TurnType.right:
        return 'Turn right in $distStr';
      case TurnType.sharpRight:
        return 'Turn sharp right in $distStr';
      case TurnType.uTurn:
        return 'Make a U-turn in $distStr';
      default:
        return 'Continue for $distStr';
    }
  }

  /// Start continuous location tracking
  void _startTracking() {
    _trackingTimer?.cancel();
    
    // Update position every 2 seconds
    _trackingTimer = Timer.periodic(const Duration(seconds: 2), (timer) async {
      if (_state != NavigationState.navigating) {
        timer.cancel();
        return;
      }

      try {
        _previousPosition = _currentPosition;
        _currentPosition = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
        );
        
        onPositionUpdated?.call(_currentPosition!);
        _checkProgress();
      } catch (e) {
        debugPrint('Position update error: $e');
      }
    });
  }

  /// Check progress along the route
  void _checkProgress() {
    if (_currentPosition == null || _instructions.isEmpty) return;

    final currentInstruction = _instructions[_currentInstructionIndex];
    
    // Check if reached current instruction point
    if (currentInstruction.latitude != null && currentInstruction.longitude != null) {
      final distanceToPoint = ShortestPathAlgorithm.calculateDistance(
        _currentPosition!.latitude,
        _currentPosition!.longitude,
        currentInstruction.latitude!,
        currentInstruction.longitude!,
      );

      if (distanceToPoint <= _reachedThreshold) {
        // Move to next instruction
        _currentInstructionIndex++;
        
        if (_currentInstructionIndex >= _instructions.length) {
          // Arrived!
          _state = NavigationState.arrived;
          onStateChanged?.call(_state);
          onArrived?.call(_destinationName ?? 'destination');
          stopNavigation();
        } else {
          onInstructionChanged?.call(_instructions[_currentInstructionIndex]);
        }
      } else {
        // Update remaining distance
        onDistanceUpdate?.call(
          totalDistanceRemaining,
          ShortestPathAlgorithm.formatDistance(totalDistanceRemaining),
        );
      }

      // Check if off route
      final distanceToPath = _distanceToPath(_currentPosition!);
      if (distanceToPath > _offRouteThreshold) {
        onOffRoute?.call('You have gone off the route. Please reorient.');
      }
    }
  }

  /// Calculate distance from position to the nearest point on path
  double _distanceToPath(Position position) {
    if (_path.isEmpty) return double.infinity;
    
    double minDistance = double.infinity;
    
    for (final point in _path) {
      final distance = ShortestPathAlgorithm.calculateDistance(
        position.latitude,
        position.longitude,
        point['lat']!,
        point['lng']!,
      );
      if (distance < minDistance) {
        minDistance = distance;
      }
    }
    
    return minDistance;
  }

  /// Calculate total distance of route
  double _calculateTotalDistance() {
    if (_path.length < 2) return 0;
    
    double total = 0;
    for (int i = 1; i < _path.length; i++) {
      total += ShortestPathAlgorithm.calculateDistance(
        _path[i - 1]['lat']!,
        _path[i - 1]['lng']!,
        _path[i]['lat']!,
        _path[i]['lng']!,
      );
    }
    return total;
  }

  /// Pause navigation
  void pauseNavigation() {
    if (_state == NavigationState.navigating) {
      _state = NavigationState.paused;
      onStateChanged?.call(_state);
      _trackingTimer?.cancel();
    }
  }

  /// Resume navigation
  void resumeNavigation() {
    if (_state == NavigationState.paused) {
      _state = NavigationState.navigating;
      onStateChanged?.call(_state);
      _startTracking();
    }
  }

  /// Stop navigation
  void stopNavigation() {
    _trackingTimer?.cancel();
    _state = NavigationState.idle;
    _path = [];
    _instructions = [];
    _currentInstructionIndex = 0;
    _destinationName = null;
    onStateChanged?.call(_state);
  }

  /// Repeat current instruction (for blind users)
  void repeatCurrentInstruction() {
    if (_instructions.isNotEmpty && _currentInstructionIndex < _instructions.length) {
      final instruction = _instructions[_currentInstructionIndex];
      // This will be called by VoiceService to speak
      debugPrint('Repeat: ${instruction.voiceAnnouncement}');
    }
  }

  /// Move to next instruction (swipe up gesture)
  void nextInstruction() {
    if (_currentInstructionIndex < _instructions.length - 1) {
      _currentInstructionIndex++;
      onInstructionChanged?.call(_instructions[_currentInstructionIndex]);
    }
  }

  /// Get remaining distance to destination
  double getRemainingDistance() {
    return totalDistanceRemaining;
  }

  /// Get estimated time to arrival
  int getEstimatedTime() {
    return ShortestPathAlgorithm.estimateWalkingTime(totalDistanceRemaining);
  }

  /// Set thresholds for navigation
  void setThresholds({double? reached, double? offRoute}) {
    if (reached != null) _reachedThreshold = reached;
    if (offRoute != null) _offRouteThreshold = offRoute;
  }

  /// Clean up resources
  void dispose() {
    _trackingTimer?.cancel();
    _positionSubscription?.cancel();
    stopNavigation();
  }
}