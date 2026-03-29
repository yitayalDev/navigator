import 'package:flutter/material.dart';

/// Campus model representing a university campus
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

  /// Create a Campus from JSON map
  factory Campus.fromJson(Map<String, dynamic> json) {
    final colorValue = json['id'].toString().hashCode | 0xFF000000;
    return Campus(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      center: json['center'] ?? '',
      lat: double.tryParse(json['center']?.split(',')[0] ?? '0') ?? 0,
      lng: double.tryParse(json['center']?.split(',')[1] ?? '0') ?? 0,
      color: Color(colorValue),
      icon: Icons.location_city,
    );
  }

  /// Convert Campus to JSON map
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'center': center,
      'lat': lat,
      'lng': lng,
    };
  }
}