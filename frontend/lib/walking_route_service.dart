import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'shortest_path_service.dart';

/// Result of a walking route calculation
class WalkingRouteResult {
  final List<Map<String, double>> path; // List of lat,lng points
  final List<RouteStep> steps; // Turn-by-turn steps
  final double totalDistanceMeters;
  final int estimatedTimeSeconds;
  final String? error;

  WalkingRouteResult({
    required this.path,
    required this.steps,
    required this.totalDistanceMeters,
    required this.estimatedTimeSeconds,
    this.error,
  });

  bool get isValid => error == null && path.isNotEmpty;
  
  String get formattedDistance => ShortestPathAlgorithm.formatDistance(totalDistanceMeters);
  
  String get formattedTime {
    final minutes = (estimatedTimeSeconds / 60).ceil();
    if (minutes < 1) return 'Less than 1 min';
    if (minutes == 1) return '1 min';
    return '$minutes mins';
  }
}

/// A single step in the walking route
class RouteStep {
  final String instruction;
  final double distanceMeters;
  final double startLat;
  final double startLng;
  final double endLat;
  final double endLng;
  final String? maneuver; // turn type: turn-left, turn-right, etc.

  RouteStep({
    required this.instruction,
    required this.distanceMeters,
    required this.startLat,
    required this.startLng,
    required this.endLat,
    required this.endLng,
    this.maneuver,
  });

  String get formattedDistance => ShortestPathAlgorithm.formatDistance(distanceMeters);
}

/// Service for getting walking directions from Google Maps
/// and calculating shortest pedestrian paths
class WalkingRouteService {
  static final WalkingRouteService _instance = WalkingRouteService._internal();
  factory WalkingRouteService() => _instance;
  WalkingRouteService._internal();

  // Google Maps API Key
  static const String _apiKey = 'AIzaSyDxb9fKkpWmrupnMt0ijKGJi9pgILbLoPE';
  static const String _baseUrl = 'https://maps.googleapis.com/maps/api';

  /// Get walking directions from Google Maps
  Future<WalkingRouteResult> getWalkingRoute({
    required double originLat,
    required double originLng,
    required double destinationLat,
    required double destinationLng,
  }) async {
    try {
      final url = Uri.parse(
        '$_baseUrl/directions/json'
        '?origin=$originLat,$originLng'
        '&destination=$destinationLat,$destinationLng'
        '&mode=walking'
        '&key=$_apiKey',
      );

      debugPrint('Fetching walking route from Google Maps...');

      final response = await http.get(url).timeout(
        const Duration(seconds: 10),
        onTimeout: () => throw Exception('Request timeout'),
      );

      if (response.statusCode != 200) {
        return WalkingRouteResult(
          path: [],
          steps: [],
          totalDistanceMeters: 0,
          estimatedTimeSeconds: 0,
          error: 'HTTP Error: ${response.statusCode}',
        );
      }

      final data = json.decode(response.body);

      if (data['status'] != 'OK') {
        return WalkingRouteResult(
          path: [],
          steps: [],
          totalDistanceMeters: 0,
          estimatedTimeSeconds: 0,
          error: 'API Error: ${data['status']}',
        );
      }

      final route = data['routes'][0];
      final legs = route['legs'][0];
      final steps = legs['steps'] as List;

      // Parse the route
      List<Map<String, double>> pathPoints = [];
      List<RouteStep> routeSteps = [];
      double totalDistance = 0;
      int totalTime = 0;

      for (var step in steps) {
        final startLocation = step['start_location'];
        final endLocation = step['end_location'];
        
        final distance = (step['distance']['value'] as num).toDouble();
        final time = (step['duration']['value'] as num).toInt();
        
        totalDistance += distance;
        totalTime += time;

        // Add start point of this step
        pathPoints.add({
          'lat': (startLocation['lat'] as num).toDouble(),
          'lng': (startLocation['lng'] as num).toDouble(),
        });

        // Add step to route steps
        routeSteps.add(RouteStep(
          instruction: _cleanHtmlTags(step['html_instructions'] ?? ''),
          distanceMeters: distance,
          startLat: (startLocation['lat'] as num).toDouble(),
          startLng: (startLocation['lng'] as num).toDouble(),
          endLat: (endLocation['lat'] as num).toDouble(),
          endLng: (endLocation['lng'] as num).toDouble(),
          maneuver: step['maneuver'],
        ));
      }

      // Add final destination point
      pathPoints.add({
        'lat': destinationLat,
        'lng': destinationLng,
      });

      debugPrint('Route found: ${pathPoints.length} points, ${routeSteps.length} steps');
      debugPrint('Total distance: ${ShortestPathAlgorithm.formatDistance(totalDistance)}');

      return WalkingRouteResult(
        path: pathPoints,
        steps: routeSteps,
        totalDistanceMeters: totalDistance,
        estimatedTimeSeconds: totalTime,
      );
    } catch (e) {
      debugPrint('Error getting walking route: $e');
      return WalkingRouteResult(
        path: [],
        steps: [],
        totalDistanceMeters: 0,
        estimatedTimeSeconds: 0,
        error: e.toString(),
      );
    }
  }

  /// Calculate shortest path using our own algorithm (Dijkstra)
  /// This uses the campus waypoints we have in the database
  WalkingRouteResult calculateShortestPath({
    required double startLat,
    required double startLng,
    required double endLat,
    required double endLng,
    required List<Map<String, double>> waypoints,
  }) {
    final path = ShortestPathAlgorithm.findShortestPath(
      startLat,
      startLng,
      endLat,
      endLng,
      waypoints,
    );

    // Calculate total distance
    double totalDistance = 0;
    for (int i = 1; i < path.length; i++) {
      totalDistance += ShortestPathAlgorithm.calculateDistance(
        path[i - 1]['lat']!,
        path[i - 1]['lng']!,
        path[i]['lat']!,
        path[i]['lng']!,
      );
    }

    final time = ShortestPathAlgorithm.estimateWalkingTime(totalDistance);

    return WalkingRouteResult(
      path: path,
      steps: [], // No turn-by-turn for direct path
      totalDistanceMeters: totalDistance,
      estimatedTimeSeconds: time * 60,
    );
  }

  /// Get the best walking route - tries Google Maps first, falls back to our algorithm
  Future<WalkingRouteResult> getBestWalkingRoute({
    required double startLat,
    required double startLng,
    required double endLat,
    required double endLng,
    List<Map<String, double>>? campusWaypoints,
  }) async {
    // First try Google Maps walking directions
    final googleRoute = await getWalkingRoute(
      originLat: startLat,
      originLng: startLng,
      destinationLat: endLat,
      destinationLng: endLng,
    );

    if (googleRoute.isValid) {
      return googleRoute;
    }

    // Fall back to our shortest path algorithm
    debugPrint('Falling back to our shortest path algorithm');
    
    if (campusWaypoints != null && campusWaypoints.isNotEmpty) {
      return calculateShortestPathWithWaypoints(
        startLat: startLat,
        startLng: startLng,
        endLat: endLat,
        endLng: endLng,
        waypoints: campusWaypoints,
      );
    }

    // Simple direct path
    return calculateShortestPath(
      startLat: startLat,
      startLng: startLng,
      endLat: endLat,
      endLng: endLng,
      waypoints: [],
    );
  }

  /// Calculate shortest path with campus waypoints
  WalkingRouteResult calculateShortestPathWithWaypoints({
    required double startLat,
    required double startLng,
    required double endLat,
    required double endLng,
    required List<Map<String, double>> waypoints,
  }) {
    return calculateShortestPath(
      startLat: startLat,
      startLng: startLng,
      endLat: endLat,
      endLng: endLng,
      waypoints: waypoints,
    );
  }

  /// Clean HTML tags from Google Maps instructions
  String _cleanHtmlTags(String html) {
    return html
        .replaceAll(RegExp(r'<[^>]*>'), '')
        .replaceAll('&nbsp;', ' ')
        .replaceAll('&', '&')
        .replaceAll('<', '<')
        .replaceAll('>', '>')
        .trim();
  }

  /// Calculate distance from current position to next waypoint
  double getDistanceToNextWaypoint(
    double currentLat,
    double currentLng,
    double waypointLat,
    double waypointLng,
  ) {
    return ShortestPathAlgorithm.calculateDistance(
      currentLat,
      currentLng,
      waypointLat,
      waypointLng,
    );
  }

  /// Find the nearest waypoint on the route from current position
  int findNearestWaypointIndex(
    double currentLat,
    double currentLng,
    List<Map<String, double>> path,
  ) {
    if (path.isEmpty) return 0;

    int nearestIndex = 0;
    double minDistance = double.infinity;

    for (int i = 0; i < path.length; i++) {
      final distance = ShortestPathAlgorithm.calculateDistance(
        currentLat,
        currentLng,
        path[i]['lat']!,
        path[i]['lng']!,
      );

      if (distance < minDistance) {
        minDistance = distance;
        nearestIndex = i;
      }
    }

    return nearestIndex;
  }

  /// Check if user has reached the destination
  bool hasReachedDestination(
    double currentLat,
    double currentLng,
    double destLat,
    double destLng, {
    double threshold = 15.0, // meters
  }) {
    final distance = ShortestPathAlgorithm.calculateDistance(
      currentLat,
      currentLng,
      destLat,
      destLng,
    );
    return distance <= threshold;
  }

  /// Check if user has gone off the route
  bool isOffRoute(
    double currentLat,
    double currentLng,
    List<Map<String, double>> path, {
    double threshold = 30.0, // meters
  }) {
    if (path.isEmpty) return false;

    // Find minimum distance to any point on the path
    double minDistance = double.infinity;
    for (var point in path) {
      final distance = ShortestPathAlgorithm.calculateDistance(
        currentLat,
        currentLng,
        point['lat']!,
        point['lng']!,
      );
      if (distance < minDistance) {
        minDistance = distance;
      }
    }

    return minDistance > threshold;
  }
}