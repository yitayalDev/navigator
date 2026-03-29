import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'models/models.dart';
import 'services/api_service.dart';
import 'services/data_service.dart';
import 'services/location_service.dart';
import 'utils/constants.dart';
import 'screens/splash_screen.dart';
import 'screens/campus_list_screen.dart';
import 'screens/campus_detail_screen.dart';
import 'screens/campus_map_screen.dart';
import 'screens/ai_chat_screen.dart';
import 'accessibility_manager.dart';

// Re-export LocationService for convenience
export 'services/location_service.dart';

// Data access helpers - delegate to DataService
List<Campus> get campuses => DataService.campuses;
List<Location> get allLocations => DataService.allLocations;
bool get isDataLoadedFromApi => DataService.isDataLoadedFromApi;

Future<void> loadLocationsFromApi() => DataService.loadLocationsFromApi();

void main() {
  runApp(const UogNavigatorApp());
}

class UogNavigatorApp extends StatelessWidget {
  const UogNavigatorApp({super.key});

  // Accessibility Manager instance
  static final AccessibilityManager accessibilityManager = AccessibilityManager();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primaryColor,
          brightness: Brightness.light,
        ),
        fontFamily: 'Roboto',
      ),
      home: SplashScreen(accessibilityManager: accessibilityManager),
    );
  }
}
