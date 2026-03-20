import 'dart:convert';
import 'package:http/http.dart' as http;

/// API Service for communicating with the backend server
class ApiService {
  // For Android Emulator: use 'http://10.0.2.2:5000'
  // For Real Device on same WiFi: use 'http://192.168.x.x:5000'
  // For Web Browser: use 'http://localhost:5000'
  // Use 127.0.0.1 instead of localhost to avoid IPv6 issues
  static const String baseUrl = 'http://127.0.0.1:5000';
  
  /// Health check
  static Future<bool> healthCheck() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/health'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Check MongoDB connection status
  static Future<Map<String, dynamic>?> checkDatabaseConnection() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/health'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {
          'connected': data['database']?['mongodb'] == 'connected',
          'db_name': data['database']?['db_name'] ?? 'unknown',
          'status': data['status'] ?? 'unknown'
        };
      }
      return null;
    } catch (e) {
      return {
        'connected': false,
        'error': e.toString()
      };
    }
  }
  
  /// Get all locations
  static Future<Map<String, dynamic>?> getLocations() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/locations'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
  
  /// Get locations by campus
  static Future<Map<String, dynamic>?> getLocationsByCampus(String campusId) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/locations/$campusId'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
  
  /// Get locations by category
  static Future<Map<String, dynamic>?> getLocationsByCategory(String category) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/locations/category/$category'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
  
  /// Share location to friend via bot
  /// This calls the API which then sends the location through Telegram
  static Future<Map<String, dynamic>?> shareLocationToFriend({
    required String senderId,
    required String friendUsername,
    required String coords,
    String locationName = 'Shared Location',
    String senderName = 'A friend',
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/share-location'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'sender_id': senderId,
          'friend_username': friendUsername,
          'coords': coords,
          'location_name': locationName,
          'sender_name': senderName,
        }),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {
        'success': false,
        'error': 'Failed to share location',
      };
    } catch (e) {
      return {
        'success': false,
        'error': e.toString(),
      };
    }
  }
  
  /// Register user in the system
  static Future<bool> registerUser({
    required String userId,
    required String username,
    required String name,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/register-user'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'username': username,
          'name': name,
        }),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
