import 'package:geolocator/geolocator.dart';

/// Location service for handling GPS and location operations
class LocationService {
  /// Get current location with high accuracy
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

  /// Get location with force refresh - bypasses any cache
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

  /// Calculate distance between two points in meters
  static double calculateDistance(
    double lat1,
    double lng1,
    double lat2,
    double lng2,
  ) {
    return Geolocator.distanceBetween(lat1, lng1, lat2, lng2);
  }

  /// Format distance for display
  static String formatDistance(double meters) {
    if (meters < 1000) {
      return '${meters.toStringAsFixed(0)}m';
    } else {
      return '${(meters / 1000).toStringAsFixed(1)}km';
    }
  }

  /// Estimate walking time in minutes
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

  /// Check if location services are enabled
  static Future<bool> isLocationServiceEnabled() async {
    return await Geolocator.isLocationServiceEnabled();
  }

  /// Check and request location permission
  static Future<LocationPermission> checkAndRequestPermission() async {
    LocationPermission permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    return permission;
  }
}