import 'package:flutter/material.dart';
import '../accessibility_manager.dart';
import '../services/data_service.dart';
import '../services/offline_storage_service.dart';
import 'campus_list_screen.dart';

/// Optimized Splash screen with fast loading
class SplashScreen extends StatefulWidget {
  final AccessibilityManager accessibilityManager;

  const SplashScreen({
    super.key,
    required this.accessibilityManager,
  });

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  String _statusText = 'Initializing...';
  double _progress = 0.0;

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    try {
      // Step 1: Initialize offline storage FIRST (fast, local)
      _updateStatus('Loading cached data...', 0.2);
      final offlineStorage = OfflineStorageService();
      await offlineStorage.initialize();
      
      // Load cached data immediately
      final cachedCampuses = await offlineStorage.getCachedCampuses();
      final cachedLocations = await offlineStorage.getCachedLocations();
      
      if (cachedCampuses.isNotEmpty && cachedLocations.isNotEmpty) {
        // Use cached data first - FAST
        DataService.loadFromCache(cachedCampuses, cachedLocations);
        debugPrint('Loaded ${cachedLocations.length} locations from cache');
      }

      // Step 2: Initialize accessibility (can run in parallel)
      _updateStatus('Setting up accessibility...', 0.4);
      await widget.accessibilityManager.initialize();

      // Step 3: Check connectivity and fetch fresh data
      final isOnline = await offlineStorage.isOnline();
      
      if (isOnline) {
        _updateStatus('Fetching latest data...', 0.6);
        // Load from API (background) - don't block
        DataService.loadLocationsFromApi().then((_) {
          // Cache the fresh data
          offlineStorage.cacheCampuses(DataService.campuses);
          offlineStorage.cacheLocations(DataService.allLocations);
        });
      } else {
        _updateStatus('Offline mode - using cached data', 0.6);
      }

      // Step 4: Minimal splash delay for branding
      _updateStatus('Starting app...', 0.8);
      await Future.delayed(const Duration(milliseconds: 800));

      if (mounted) {
        _updateStatus('Ready!', 1.0);
        await Future.delayed(const Duration(milliseconds: 200));
        
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (context) => CampusListScreen(
              accessibilityManager: widget.accessibilityManager,
            ),
          ),
        );
      }
    } catch (e) {
      debugPrint('Initialization error: $e');
      // Fallback to basic loading
      _updateStatus('Loading...', 1.0);
      await Future.delayed(const Duration(seconds: 2));
      
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (context) => CampusListScreen(
              accessibilityManager: widget.accessibilityManager,
            ),
          ),
        );
      }
    }
  }

  void _updateStatus(String text, double progress) {
    if (mounted) {
      setState(() {
        _statusText = text;
        _progress = progress;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF1E88E5),
              Color(0xFF1565C0),
              Color(0xFF0D47A1),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // App Icon with animation
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0.0, end: 1.0),
                  duration: const Duration(milliseconds: 800),
                  builder: (context, value, child) {
                    return Transform.scale(
                      scale: value,
                      child: Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.school,
                          size: 80,
                          color: Colors.white,
                        ),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 32),
                
                // App Name
                const Text(
                  'UOG Navigator',
                  style: TextStyle(
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                
                // University name
                Text(
                  'University of Gondar',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white.withValues(alpha: 0.9),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 50),
                
                // Progress indicator
                SizedBox(
                  width: 200,
                  child: Column(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: LinearProgressIndicator(
                          value: _progress,
                          backgroundColor: Colors.white.withValues(alpha: 0.3),
                          valueColor: const AlwaysStoppedAnimation<Color>(
                            Colors.white,
                          ),
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _statusText,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.9),
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}