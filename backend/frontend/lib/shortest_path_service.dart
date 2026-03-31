import 'dart:math';

/// Shortest path algorithm using Dijkstra's algorithm
/// Calculates the shortest path between two points on the campus
class ShortestPathAlgorithm {
  /// Calculate shortest path between two coordinates
  /// Returns list of LatLng points representing the path
  static List<Map<String, double>> findShortestPath(
    double startLat,
    double startLng,
    double endLat,
    double endLng,
    List<Map<String, double>> waypoints,
  ) {
    // If there are no waypoints, just return direct path
    if (waypoints.isEmpty) {
      return [
        {'lat': startLat, 'lng': startLng},
        {'lat': endLat, 'lng': endLng},
      ];
    }

    // Create a graph with all points
    final List<_Point> points = [];
    
    // Add start point
    points.add(_Point(startLat, startLng, 'start'));
    
    // Add waypoints
    for (int i = 0; i < waypoints.length; i++) {
      points.add(_Point(
        waypoints[i]['lat']!,
        waypoints[i]['lng']!,
        'waypoint_$i',
      ));
    }
    
    // Add end point
    points.add(_Point(endLat, endLng, 'end'));
    
    // Build adjacency list (graph)
    final Map<int, List<_Edge>> graph = _buildGraph(points);
    
    // Run Dijkstra's algorithm
    final List<int> path = dijkstra(graph, 0, points.length - 1);
    
    // Convert path indices back to coordinates
    return path.map((index) => {
      'lat': points[index].lat,
      'lng': points[index].lng,
    }).toList();
  }

  /// Build graph with weighted edges based on distance
  static Map<int, List<_Edge>> _buildGraph(List<_Point> points) {
    final Map<int, List<_Edge>> graph = {};
    
    // Initialize empty adjacency list
    for (int i = 0; i < points.length; i++) {
      graph[i] = [];
    }
    
    // Connect all points (fully connected graph)
    // In a real app, you'd only connect walkable paths
    for (int i = 0; i < points.length; i++) {
      for (int j = i + 1; j < points.length; j++) {
        final distance = calculateDistance(
          points[i].lat,
          points[i].lng,
          points[j].lat,
          points[j].lng,
        );
        
        // Add edges in both directions (undirected graph)
        graph[i]!.add(_Edge(j, distance));
        graph[j]!.add(_Edge(i, distance));
      }
    }
    
    return graph;
  }

  /// Dijkstra's algorithm implementation
  static List<int> dijkstra(Map<int, List<_Edge>> graph, int start, int end) {
    final int n = graph.length;
    final List<double> dist = List.filled(n, double.infinity);
    final List<int> parent = List.filled(n, -1);
    final List<bool> visited = List.filled(n, false);
    
    dist[start] = 0;
    
    for (int i = 0; i < n; i++) {
      // Find minimum distance vertex
      int u = -1;
      double minDist = double.infinity;
      
      for (int v = 0; v < n; v++) {
        if (!visited[v] && dist[v] < minDist) {
          minDist = dist[v];
          u = v;
        }
      }
      
      if (u == -1 || u == end) break;
      visited[u] = true;
      
      // Update distances
      for (final edge in graph[u]!) {
        final int v = edge.to;
        final double newDist = dist[u] + edge.weight;
        
        if (newDist < dist[v]) {
          dist[v] = newDist;
          parent[v] = u;
        }
      }
    }
    
    // Reconstruct path
    final List<int> path = [];
    int current = end;
    
    while (current != -1) {
      path.add(current);
      current = parent[current];
    }
    
    return path.reversed.toList();
  }

  /// Calculate distance between two coordinates using Haversine formula
  static double calculateDistance(
    double lat1,
    double lng1,
    double lat2,
    double lng2,
  ) {
    const double earthRadius = 6371000; // meters
    
    final double dLat = _toRadians(lat2 - lat1);
    final double dLng = _toRadians(lng2 - lng1);
    
    final double a = sin(dLat / 2) * sin(dLat / 2) +
        cos(_toRadians(lat1)) *
            cos(_toRadians(lat2)) *
            sin(dLng / 2) *
            sin(dLng / 2);
    
    final double c = 2 * atan2(sqrt(a), sqrt(1 - a));
    
    return earthRadius * c;
  }

  static double _toRadians(double degrees) {
    return degrees * pi / 180;
  }

  /// Format distance for display
  static String formatDistance(double meters) {
    if (meters < 1000) {
      return '${meters.toStringAsFixed(0)} m';
    } else {
      return '${(meters / 1000).toStringAsFixed(2)} km';
    }
  }

  /// Estimate walking time in minutes
  static int estimateWalkingTime(double meters) {
    // Average walking speed: 5 km/h = 83.33 m/min
    const double walkingSpeed = 83.33;
    return (meters / walkingSpeed).round();
  }
}

/// Point class for graph
class _Point {
  final double lat;
  final double lng;
  final String id;
  
  _Point(this.lat, this.lng, this.id);
}

/// Edge class for graph
class _Edge {
  final int to;
  final double weight;
  
  _Edge(this.to, this.weight);
}
