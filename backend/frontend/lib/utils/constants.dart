import 'package:flutter/material.dart';

/// App constants
class AppConstants {
  // App info
  static const String appName = 'UOG Navigator';
  static const String universityName = 'University of Gondar';

  // Telegram bot username
  static const String botUsername = 'UOGStudentNavBot';

  // Google Maps API Key
  static const String googleMapsApiKey = 'AIzaSyDxb9fKkpWmrupnMt0ijKGJi9pgILbLoPE';

  // API base URL
  static const String apiBaseUrl = 'https://navigator-backend-ku90.onrender.com';

  // Default timeout for requests
  static const int defaultTimeout = 30;

  // Location polling interval (seconds)
  static const int locationPollingInterval = 2;

  // Bluetooth scan timeout (seconds)
  static const int bluetoothScanTimeout = 5;

  // Walking speed (meters per minute) - ~5 km/h
  static const double walkingSpeed = 83.33;
}

/// Category icons and colors
class CategoryConstants {
  static IconData getIcon(String category) {
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

  static Color getColor(String category) {
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

  static String getDisplayName(String category) {
    switch (category) {
      case 'building':
        return 'Building';
      case 'library':
        return 'Library';
      case 'cafe':
        return 'Café';
      case 'dorm':
        return 'Dormitory';
      case 'lab':
        return 'Laboratory';
      case 'administration':
        return 'Administration';
      default:
        return 'Location';
    }
  }
}

/// App theme colors
class AppColors {
  static const Color primaryColor = Color(0xFF1E88E5);
  static const Color primaryDark = Color(0xFF1565C0);
  static const Color primaryLight = Color(0xFF42A5F5);

  static const Color secondaryColor = Color(0xFF0088CC);

  static const Color successColor = Colors.green;
  static const Color warningColor = Colors.orange;
  static const Color errorColor = Colors.red;

  // Campus colors
  static const Color marakiColor = Color(0xFF1565C0);
  static const Color tewodrosColor = Color(0xFF2E7D32);
  static const Color fasilColor = Color(0xFFC62828);
}