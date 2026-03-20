import 'package:url_launcher/url_launcher.dart';
import 'package:geolocator/geolocator.dart';
import 'api_service.dart';

/// Location sharing service for sharing user location via Telegram or other apps
class LocationShareService {
  /// Share location directly via Telegram app
  /// Opens Telegram with location pre-filled
  static Future<bool> shareViaTelegram(double lat, double lng, {String? message}) async {
    try {
      // Create Google Maps URL for the location
      final mapsUrl = 'https://www.google.com/maps?q=$lat,$lng';
      
      // Create Telegram share URL
      // Using tg:// URL scheme to open Telegram
      final encodedMessage = Uri.encodeComponent(
        message ?? '📍 My current location:\n$mapsUrl\n\nLat: $lat, Lng: $lng'
      );
      
      // Try Telegram app first
      final telegramUrl = 'tg://msg_url?text=$encodedMessage';
      final webTelegramUrl = 'https://t.me/share/url?url=$mapsUrl&text=${Uri.encodeComponent(message ?? 'Check out my location!')}';
      
      // Try to open Telegram app
      bool launched = false;
      try {
        launched = await launchUrl(
          Uri.parse(telegramUrl),
          mode: LaunchMode.externalApplication,
        );
      } catch (e) {
        // If Telegram app not available, try web version
        launched = await launchUrl(
          Uri.parse(webTelegramUrl),
          mode: LaunchMode.externalApplication,
        );
      }
      
      return launched;
    } catch (e) {
      return false;
    }
  }

  /// Share location to friend via API (new method)
  static Future<Map<String, dynamic>?> shareLocationToFriend({
    required String senderId,
    required String friendUsername,
    required double lat,
    required double lng,
    String? locationName,
  }) async {
    final coords = '$lat,$lng';
    return await ApiService.shareLocationToFriend(
      senderId: senderId,
      friendUsername: friendUsername,
      coords: coords,
      locationName: locationName ?? 'Current Location',
    );
  }

  /// Generate a shareable location message
  static String generateLocationMessage(double lat, double lng, {String? customMessage}) {
    final mapsUrl = 'https://www.google.com/maps?q=$lat,$lng';
    
    if (customMessage != null) {
      return '$customMessage\n\n📍 Location: $mapsUrl\n📌 Coordinates: $lat, $lng';
    }
    
    return '''
📍 *My Current Location*

*Coordinates:* $lat, $lng

🗺️ [View on Google Maps]($mapsUrl)

_Shared via UOG Navigator_
''';
  }

  /// Generate a short shareable link
  static String getShortLocationLink(double lat, double lng) {
    return 'https://www.google.com/maps?q=$lat,$lng';
  }

  /// Get current location and prepare for sharing
  static Future<Position?> getCurrentLocation() async {
    try {
      // Check if location services are enabled
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        // Try to get last known position as fallback
        try {
          final lastKnown = await Geolocator.getLastKnownPosition();
          if (lastKnown != null) return lastKnown;
        } catch (e) {
          // Ignore
        }
        return null;
      }

      // Check permissions
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

      // Try high accuracy first, with fallbacks
      Position? position;
      try {
        position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 15),
        );
      } catch (e) {
        // Fallback to best accuracy
        try {
          position = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.best,
            timeLimit: const Duration(seconds: 10),
          );
        } catch (e2) {
          // Fallback to best for navigation
          try {
            position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.bestForNavigation,
              timeLimit: const Duration(seconds: 10),
            );
          } catch (e3) {
            // Try without any specifications
            position = await Geolocator.getCurrentPosition();
          }
        }
      }
      
      return position;
    } catch (e) {
      return null;
    }
  }

  /// Share location via URL scheme (for other apps)
  static Future<bool> shareLocation(double lat, double lng, {String? message}) async {
    final mapsUrl = 'https://www.google.com/maps?q=$lat,$lng';
    final encodedMessage = Uri.encodeComponent(
      message ?? 'My location: $mapsUrl'
    );
    
    try {
      // Try to open share dialog
      final shareUrl = 'https://wa.me/?text=$encodedMessage';
      return await launchUrl(
        Uri.parse(shareUrl),
        mode: LaunchMode.externalApplication,
      );
    } catch (e) {
      return false;
    }
  }
}
