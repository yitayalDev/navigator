import 'package:flutter/material.dart';

/// Location model representing a location on campus
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

  /// Create a Location from JSON map
  factory Location.fromJson(Map<String, dynamic> json) {
    String coords = json['coords'] ?? '';
    double? lat;
    double? lng;
    
    if (coords.contains(',')) {
      final parts = coords.split(',');
      lat = double.tryParse(parts[0]);
      lng = double.tryParse(parts[1]);
    }

    return Location(
      name: json['name'] ?? '',
      category: json['category'] ?? '',
      campus: json['campus'] ?? '',
      coords: coords,
      description: json['description'] ?? '',
      lat: lat ?? 0,
      lng: lng ?? 0,
    );
  }

  /// Convert Location to JSON map
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'category': category,
      'campus': campus,
      'coords': coords,
      'description': description,
      'lat': lat,
      'lng': lng,
    };
  }

  /// Get icon based on category
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

  /// Get color based on category
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

  /// Check if this location can check occupancy (library or lab)
  bool get canCheckOccupancy {
    return category == 'library' || category == 'lab';
  }
}