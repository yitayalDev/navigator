import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show Color, Icons;
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/campus.dart';
import '../models/location.dart';

/// Offline Storage Service
/// Handles all offline data caching and sync functionality
class OfflineStorageService {
  static final OfflineStorageService _instance = OfflineStorageService._internal();
  factory OfflineStorageService() => _instance;
  OfflineStorageService._internal();

  Database? _database;
  late SharedPreferences _prefs;
  bool _isInitialized = false;

  // Keys for SharedPreferences
  static const String KEY_LAST_SYNC = 'last_sync_timestamp';
  static const String KEY_LAST_LOCATION = 'last_known_location';
  static const String KEY_USER_PREFERENCES = 'user_preferences';
  static const String KEY_VOICE_COMMANDS = 'voice_commands_cache';
  static const String KEY_AI_CHAT_HISTORY = 'ai_chat_history';

  /// Initialize the offline storage system
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // Initialize SharedPreferences
      _prefs = await SharedPreferences.getInstance();

      // Initialize SQLite database
      final dbPath = await getDatabasesPath();
      final path = join(dbPath, 'uog_navigator_cache.db');
      
      _database = await openDatabase(
        path,
        version: 1,
        onCreate: _createTables, // ignore: avoid_types_as_parameter_names
      );

      _isInitialized = true;
      debugPrint('[OfflineStorage] Initialized successfully');
    } catch (e) {
      debugPrint('[OfflineStorage] Initialization error: $e');
    }
  }

  /// Create database tables for caching
  Future<void> _createTables(Database db, int version) async {
    // Campuses table
    await db.execute('''
      CREATE TABLE campuses (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        center TEXT,
        lat REAL,
        lng REAL,
        created_at TEXT,
        updated_at TEXT
      )
    ''');

    // Locations table
    await db.execute('''
      CREATE TABLE locations (
        name TEXT PRIMARY KEY,
        category TEXT,
        campus TEXT,
        coords TEXT,
        description TEXT,
        lat REAL,
        lng REAL,
        created_at TEXT,
        updated_at TEXT
      )
    ''');

    // AI Chat history table
    await db.execute('''
      CREATE TABLE ai_chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        content TEXT,
        timestamp TEXT
      )
    ''');

    debugPrint('[OfflineStorage] Database tables created');
  }

  /// Check if device is online
  Future<bool> isOnline() async {
    try {
      final connectivityResult = await Connectivity().checkConnectivity();
      return connectivityResult != ConnectivityResult.none;
    } catch (e) {
      debugPrint('[OfflineStorage] Connectivity check error: $e');
      return false;
    }
  }

  /// Stream connectivity changes
  Stream<ConnectivityResult> get connectivityStream => Connectivity().onConnectivityChanged;

  // ============ CAMPUS OPERATIONS ============

  /// Save campuses to local cache
  Future<void> cacheCampuses(List<Campus> campuses) async {
    if (_database == null) return;

    try {
      await _database!.delete('campuses');
      
      for (final campus in campuses) {
        await _database!.insert('campuses', {
          'id': campus.id,
          'name': campus.name,
          'description': campus.description,
          'center': campus.center,
          'lat': campus.lat,
          'lng': campus.lng,
        });
      }
      
      await _updateLastSyncTime();
      debugPrint('[OfflineStorage] Cached ${campuses.length} campuses');
    } catch (e) {
      debugPrint('[OfflineStorage] Error caching campuses: $e');
    }
  }

  /// Get cached campuses
  Future<List<Campus>> getCachedCampuses() async {
    if (_database == null) return [];

    try {
      final results = await _database!.query('campuses', orderBy: 'name ASC');
      return results.map((map) {
        final id = map['id'] as String? ?? '';
        return Campus(
          id: id,
          name: map['name'] as String? ?? '',
          description: map['description'] as String? ?? '',
          center: map['center'] as String? ?? '',
          lat: (map['lat'] as num?)?.toDouble() ?? 0.0,
          lng: (map['lng'] as num?)?.toDouble() ?? 0.0,
          color: Color(id.hashCode | 0xFF000000),
          icon: Icons.location_city,
        );
      }).toList();
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting cached campuses: $e');
      return [];
    }
  }

  // ============ LOCATION OPERATIONS ============

  /// Save locations to local cache
  Future<void> cacheLocations(List<Location> locations) async {
    if (_database == null) return;

    try {
      // Get unique campuses
      final campuses = locations.map((l) => l.campus).toSet();
      
      for (final campus in campuses) {
        await _database!.delete('locations', where: 'campus = ?', whereArgs: [campus]);
      }
      
      for (final location in locations) {
        await _database!.insert('locations', {
          'name': location.name,
          'category': location.category,
          'campus': location.campus,
          'coords': location.coords,
          'description': location.description,
          'lat': location.lat,
          'lng': location.lng,
        });
      }
      
      debugPrint('[OfflineStorage] Cached ${locations.length} locations');
    } catch (e) {
      debugPrint('[OfflineStorage] Error caching locations: $e');
    }
  }

  /// Get cached locations
  Future<List<Location>> getCachedLocations({String? campus}) async {
    if (_database == null) return [];

    try {
      List<Map<String, dynamic>> results;
      
      if (campus != null) {
        results = await _database!.query(
          'locations',
          where: 'campus = ?',
          whereArgs: [campus],
          orderBy: 'name ASC',
        );
      } else {
        results = await _database!.query('locations', orderBy: 'name ASC');
      }
      
      return results.map((map) => Location(
        name: map['name'] as String,
        category: map['category'] as String,
        campus: map['campus'] as String,
        coords: map['coords'] as String,
        description: map['description'] as String,
        lat: map['lat'] as double,
        lng: map['lng'] as double,
      )).toList();
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting cached locations: $e');
      return [];
    }
  }

  /// Search cached locations
  Future<List<Location>> searchCachedLocations(String query) async {
    if (_database == null) return [];

    try {
      final results = await _database!.query(
        'locations',
        where: 'name LIKE ? OR description LIKE ? OR category LIKE ?',
        whereArgs: ['%$query%', '%$query%', '%$query%'],
        orderBy: 'name ASC',
      );
      
      return results.map((map) => Location(
        name: map['name'] as String,
        category: map['category'] as String,
        campus: map['campus'] as String,
        coords: map['coords'] as String,
        description: map['description'] as String,
        lat: map['lat'] as double,
        lng: map['lng'] as double,
      )).toList();
    } catch (e) {
      debugPrint('[OfflineStorage] Error searching locations: $e');
      return [];
    }
  }

  // ============ USER PREFERENCES ============

  /// Save user preferences
  Future<void> saveUserPreferences(Map<String, dynamic> preferences) async {
    try {
      await _prefs.setString(KEY_USER_PREFERENCES, jsonEncode(preferences));
      debugPrint('[OfflineStorage] User preferences saved');
    } catch (e) {
      debugPrint('[OfflineStorage] Error saving preferences: $e');
    }
  }

  /// Get user preferences
  Map<String, dynamic>? getUserPreferences() {
    try {
      final data = _prefs.getString(KEY_USER_PREFERENCES);
      if (data != null) {
        return jsonDecode(data) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting preferences: $e');
    }
    return null;
  }

  // ============ VOICE COMMANDS ============

  /// Cache voice commands
  Future<void> cacheVoiceCommands(List<Map<String, String>> commands) async {
    try {
      await _prefs.setString(KEY_VOICE_COMMANDS, jsonEncode(commands));
      debugPrint('[OfflineStorage] Voice commands cached');
    } catch (e) {
      debugPrint('[OfflineStorage] Error caching voice commands: $e');
    }
  }

  /// Get cached voice commands
  List<Map<String, String>> getCachedVoiceCommands() {
    try {
      final data = _prefs.getString(KEY_VOICE_COMMANDS);
      if (data != null) {
        final List<dynamic> decoded = jsonDecode(data);
        return decoded.map((e) => Map<String, String>.from(e)).toList();
      }
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting voice commands: $e');
    }
    return [];
  }

  // ============ LAST KNOWN LOCATION ============

  /// Save last known location
  Future<void> saveLastKnownLocation(double latitude, double longitude) async {
    try {
      final location = {
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': DateTime.now().toIso8601String(),
      };
      await _prefs.setString(KEY_LAST_LOCATION, jsonEncode(location));
      debugPrint('[OfflineStorage] Last location saved');
    } catch (e) {
      debugPrint('[OfflineStorage] Error saving last location: $e');
    }
  }

  /// Get last known location
  Map<String, dynamic>? getLastKnownLocation() {
    try {
      final data = _prefs.getString(KEY_LAST_LOCATION);
      if (data != null) {
        return jsonDecode(data) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting last location: $e');
    }
    return null;
  }

  // ============ AI CHAT HISTORY ============

  /// Save AI chat message
  Future<void> saveChatMessage(String role, String content) async {
    if (_database == null) return;

    try {
      await _database!.insert('ai_chat_history', {
        'role': role,
        'content': content,
        'timestamp': DateTime.now().toIso8601String(),
      });
      
      // Keep only last 100 messages
      await _database!.rawDelete('''
        DELETE FROM ai_chat_history 
        WHERE id NOT IN (
          SELECT id FROM ai_chat_history ORDER BY timestamp DESC LIMIT 100
        )
      ''');
    } catch (e) {
      debugPrint('[OfflineStorage] Error saving chat message: $e');
    }
  }

  /// Get AI chat history
  Future<List<Map<String, String>>> getChatHistory() async {
    if (_database == null) return [];

    try {
      final results = await _database!.query(
        'ai_chat_history',
        orderBy: 'timestamp ASC',
      );
      
      return results.map((map) => {
        'role': map['role'] as String,
        'content': map['content'] as String,
        'timestamp': map['timestamp'] as String,
      }).toList();
    } catch (e) {
      debugPrint('[OfflineStorage] Error getting chat history: $e');
      return [];
    }
  }

  /// Clear chat history
  Future<void> clearChatHistory() async {
    if (_database == null) return;

    try {
      await _database!.delete('ai_chat_history');
      debugPrint('[OfflineStorage] Chat history cleared');
    } catch (e) {
      debugPrint('[OfflineStorage] Error clearing chat history: $e');
    }
  }

  // ============ SYNC STATUS ============

  /// Update last sync time
  Future<void> _updateLastSyncTime() async {
    await _prefs.setInt(KEY_LAST_SYNC, DateTime.now().millisecondsSinceEpoch);
  }

  /// Get last sync time
  DateTime? getLastSyncTime() {
    final timestamp = _prefs.getInt(KEY_LAST_SYNC);
    if (timestamp != null) {
      return DateTime.fromMillisecondsSinceEpoch(timestamp);
    }
    return null;
  }

  /// Check if data needs refresh (older than 24 hours)
  bool needsRefresh() {
    final lastSync = getLastSyncTime();
    if (lastSync == null) return true;
    
    final difference = DateTime.now().difference(lastSync);
    return difference.inHours >= 24;
  }

  // ============ CLEANUP ============

  /// Clear all cached data
  Future<void> clearAllCache() async {
    if (_database == null) return;

    try {
      await _database!.delete('campuses');
      await _database!.delete('locations');
      await _database!.delete('ai_chat_history');
      await _prefs.remove(KEY_LAST_SYNC);
      await _prefs.remove(KEY_LAST_LOCATION);
      debugPrint('[OfflineStorage] All cache cleared');
    } catch (e) {
      debugPrint('[OfflineStorage] Error clearing cache: $e');
    }
  }
}