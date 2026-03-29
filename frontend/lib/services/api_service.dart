import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// API Service for communicating with the backend server
class ApiService {
  // For web browser (Edge/Chrome) or local testing, use localhost
  // For physical device testing on same network, use your computer's IP address
  // For Android Emulator: use 'http://10.0.2.2:5000'
  // Local backend running on port 5000
  // Use physical device IP when testing on real device
  static String baseUrl = 'http://10.139.26.179:5000';
  
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
  
  /// Share location to friend via bot - INSTANT VERSION
  /// Gets GPS and sends to friend immediately via Telegram
  static Future<Map<String, dynamic>?> shareLocationToFriend({
    required String senderId,
    required String friendUsername,
    required String coords,
    String locationName = 'Shared Location',
    String senderName = 'A friend',
  }) async {
    try {
      // Try instant share endpoint first
      final response = await http.post(
        Uri.parse('$baseUrl/api/instant-share'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': senderId,
          'friend_username': friendUsername,
          'coords': coords,
          'location_name': locationName,
          'sender_name': senderName,
        }),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      
      // Fallback to original endpoint
      final fallbackResponse = await http.post(
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
      
      if (fallbackResponse.statusCode == 200) {
        return json.decode(fallbackResponse.body);
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
  
  /// Check if bot requested location from the app
  static Future<Map<String, dynamic>?> checkLocationRequest(String userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/location-request?user_id=$userId'),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
  
  /// Submit location to the server (after bot requested it)
  static Future<Map<String, dynamic>?> submitLocation({
    required String userId,
    required String coords,
    String locationName = 'Current Location',
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/submit-location'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'coords': coords,
          'location_name': locationName,
        }),
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {
        'success': false,
        'error': 'Failed to submit location',
      };
    } catch (e) {
      return {
        'success': false,
        'error': e.toString(),
      };
    }
  }
  
  /// Update user's location on server (so bot can get it)
  static Future<bool> updateLocation({
    required String userId,
    required String coords,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/update-location'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'coords': coords,
        }),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Save Telegram user ID locally
  static Future<bool> saveTelegramUserId(String userId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return await prefs.setString('telegram_user_id', userId);
    } catch (e) {
      return false;
    }
  }
  
  /// Get saved Telegram user ID
  static Future<String?> getTelegramUserId() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString('telegram_user_id');
    } catch (e) {
      return null;
    }
  }
  
  /// Get all registered users (for selecting friend to share location)
  static Future<List<Map<String, String>>?> getUsers() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/users'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          return List<Map<String, String>>.from(
            (data['users'] as List).map((u) => {
              'username': u['username'] ?? '',
              'name': u['name'] ?? 'Unknown',
            })
          );
        }
      }
      return null;
    } catch (e) {
      return null;
    }
  }
}
