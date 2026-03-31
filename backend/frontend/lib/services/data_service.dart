import 'package:flutter/material.dart';
import '../models/models.dart';
import 'api_service.dart';

/// Data service for loading campus and location data from API
class DataService {
  // All Locations - Loaded from MongoDB via API
  static List<Location> allLocations = [];

  // All Campuses
  static List<Campus> campuses = [];

  // Flag to track if data is loaded from API
  static bool isDataLoadedFromApi = false;

  /// Load from cache (offline storage)
  static void loadFromCache(List<dynamic> cachedCampuses, List<dynamic> cachedLocations) {
    campuses = cachedCampuses.cast<Campus>();
    allLocations = cachedLocations.cast<Location>();
    isDataLoadedFromApi = false;
    debugPrint('Loaded ${allLocations.length} locations from cache');
  }

  /// Load locations from MongoDB API
  static Future<void> loadLocationsFromApi() async {
    try {
      final data = await ApiService.getLocations();
      if (data != null && data['success'] == true) {
        // Clear existing data
        allLocations.clear();

        // Load locations from API
        final locationsList = data['locations'] as List<dynamic>;
        for (var loc in locationsList) {
          allLocations.add(Location.fromJson(loc as Map<String, dynamic>));
        }

        // Load campuses
        final campusesData = data['campuses'] as Map<String, dynamic>?;
        if (campusesData != null) {
          campuses = campusesData.entries.map((e) {
            return Campus.fromJson({
              'id': e.key,
              ...e.value as Map<String, dynamic>,
            });
          }).toList();
        }

        isDataLoadedFromApi = true;
        print('Loaded ${allLocations.length} locations from MongoDB');
      }
    } catch (e) {
      print('Error loading locations from API: $e');
      // Load fallback hardcoded data
      loadFallbackData();
      isDataLoadedFromApi = false;
    }
  }

  /// Load fallback data in case API fails
  static void loadFallbackData() {
    allLocations = [
      // Tewodros Campus - Buildings
      Location(
        name: 'President Office 1',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.59078,37.44360',
        description: 'President Office',
        lat: 12.59078,
        lng: 37.44360,
      ),
      Location(
        name: 'President Office 2',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.58905,37.44273',
        description: 'President Office 2',
        lat: 12.58905,
        lng: 37.44273,
      ),
      Location(
        name: 'Sador Building',
        category: 'building',
        campus: 'tewodros',
        coords: '12.58999,37.44300',
        description: 'Sador Building',
        lat: 12.58999,
        lng: 37.44300,
      ),
      Location(
        name: 'Main Store',
        category: 'building',
        campus: 'tewodros',
        coords: '12.58966,37.44264',
        description: 'Main Store',
        lat: 12.58966,
        lng: 37.44264,
      ),
      Location(
        name: 'Registrar ICT',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.58903,37.44238',
        description: 'Registrar ICT',
        lat: 12.58903,
        lng: 37.44238,
      ),
      Location(
        name: 'Informatics',
        category: 'building',
        campus: 'tewodros',
        coords: '12.58883,37.44188',
        description: 'Informatics',
        lat: 12.58883,
        lng: 37.44188,
      ),
      Location(
        name: 'New Building',
        category: 'building',
        campus: 'tewodros',
        coords: '12.58783,37.44015',
        description: 'New Building',
        lat: 12.58783,
        lng: 37.44015,
      ),
      Location(
        name: 'Main Registrar',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.58765,37.43945',
        description: 'Main Registrar',
        lat: 12.58765,
        lng: 37.43945,
      ),
      Location(
        name: 'Student Association',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.58536,37.44007',
        description: 'Student Association',
        lat: 12.58536,
        lng: 37.44007,
      ),
      Location(
        name: 'Veterinary Registration',
        category: 'administration',
        campus: 'tewodros',
        coords: '12.58486,37.43905',
        description: 'Veterinary Registration',
        lat: 12.58486,
        lng: 37.43905,
      ),
      Location(
        name: 'Lecture Houses',
        category: 'building',
        campus: 'tewodros',
        coords: '12.58579,37.43788',
        description: 'Lecture Houses',
        lat: 12.58579,
        lng: 37.43788,
      ),
      // Libraries
      Location(
        name: 'Post Library',
        category: 'library',
        campus: 'tewodros',
        coords: '12.58910,37.44125',
        description: 'Post Library',
        lat: 12.58910,
        lng: 37.44125,
      ),
      Location(
        name: 'T15 Library',
        category: 'library',
        campus: 'tewodros',
        coords: '12.58775,37.44134',
        description: 'T15 Library',
        lat: 12.58775,
        lng: 37.44134,
      ),
      Location(
        name: 'Veterinary Library',
        category: 'library',
        campus: 'tewodros',
        coords: '12.58349,37.44003',
        description: 'Veterinary Library',
        lat: 12.58349,
        lng: 37.44003,
      ),
      // Labs
      Location(
        name: 'T9 Computer Lab',
        category: 'lab',
        campus: 'tewodros',
        coords: '12.58826,37.44157',
        description: 'T9 Computer Lab',
        lat: 12.58826,
        lng: 37.44157,
      ),
      Location(
        name: 'T10 Lab',
        category: 'lab',
        campus: 'tewodros',
        coords: '12.58827,37.44192',
        description: 'T10 Lab',
        lat: 12.58827,
        lng: 37.44192,
      ),
      Location(
        name: 'Biology Lab',
        category: 'lab',
        campus: 'tewodros',
        coords: '12.58727,37.44123',
        description: 'Biology Lab',
        lat: 12.58727,
        lng: 37.44123,
      ),
      Location(
        name: 'Chemistry Lab',
        category: 'lab',
        campus: 'tewodros',
        coords: '12.58721,37.44160',
        description: 'Chemistry Lab',
        lat: 12.58721,
        lng: 37.44160,
      ),
      Location(
        name: 'Physics Lab',
        category: 'lab',
        campus: 'tewodros',
        coords: '12.58671,37.44160',
        description: 'Physics Lab',
        lat: 12.58671,
        lng: 37.44160,
      ),
      // Cafes
      Location(
        name: 'Main Cafeteria',
        category: 'cafe',
        campus: 'tewodros',
        coords: '12.58382,37.44225',
        description: 'Main Cafeteria',
        lat: 12.58382,
        lng: 37.44225,
      ),
      Location(
        name: 'Cafe Store',
        category: 'cafe',
        campus: 'tewodros',
        coords: '12.58320,37.44225',
        description: 'Cafe Store',
        lat: 12.58320,
        lng: 37.44225,
      ),
      Location(
        name: 'Addis Hiywot',
        category: 'cafe',
        campus: 'tewodros',
        coords: '12.58405,37.44092',
        description: 'Addis Hiywot',
        lat: 12.58405,
        lng: 37.44092,
      ),
      // Dormitories
      Location(
        name: 'Federal Dormitory',
        category: 'dorm',
        campus: 'tewodros',
        coords: '12.58278,37.44037',
        description: 'Federal Dormitory',
        lat: 12.58278,
        lng: 37.44037,
      ),
      Location(
        name: 'Prep Dormitory',
        category: 'dorm',
        campus: 'tewodros',
        coords: '12.58201,37.44033',
        description: 'Prep Dormitory',
        lat: 12.58201,
        lng: 37.44033,
      ),
    ];

    // Fallback campuses
    campuses = [
      Campus(
        id: 'maraki',
        name: 'Maraki Campus',
        description: 'Main campus',
        center: '12.58613,37.44605',
        color: const Color(0xFF1565C0),
        icon: Icons.school,
        lat: 12.58613,
        lng: 37.44605,
      ),
      Campus(
        id: 'tewodros',
        name: 'Tewodros Campus',
        description: 'Arts, Business & Law',
        center: '12.58559,37.43943',
        color: const Color(0xFF2E7D32),
        icon: Icons.business,
        lat: 12.58559,
        lng: 37.43943,
      ),
      Campus(
        id: 'fasil',
        name: 'Fasil Campus',
        description: 'Medical campus',
        center: '12.5775,37.4455',
        color: const Color(0xFFC62828),
        icon: Icons.local_hospital,
        lat: 12.5775,
        lng: 37.4455,
      ),
    ];
  }

  /// Get locations for a specific campus
  static List<Location> getLocationsForCampus(String campusId) {
    return allLocations.where((loc) => loc.campus == campusId).toList();
  }

  /// Get locations by category
  static List<Location> getLocationsByCategory(String category) {
    return allLocations.where((loc) => loc.category == category).toList();
  }

  /// Search locations by name
  static List<Location> searchLocations(String query) {
    final lowerQuery = query.toLowerCase();
    return allLocations
        .where((loc) => loc.name.toLowerCase().contains(lowerQuery))
        .toList();
  }
}