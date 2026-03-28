import 'package:flutter/foundation.dart';
import 'voice_service.dart';
import 'gesture_service.dart';
import 'blind_detection_service.dart';
import 'pedestrian_navigation_service.dart';

/// Main accessibility manager that coordinates all accessibility services
class AccessibilityManager {
  static final AccessibilityManager _instance = AccessibilityManager._internal();
  factory AccessibilityManager() => _instance;
  AccessibilityManager._internal();

  // Services
  final VoiceService voiceService = VoiceService();
  final GestureService gestureService = GestureService();
  final BlindDetectionService blindDetectionService = BlindDetectionService();
  final PedestrianNavigationService navigationService = PedestrianNavigationService();

  // State
  bool _isInitialized = false;
  bool _isBlindMode = false;
  bool _isVoiceCommandMode = false;
  bool _isEmergencyMode = false;

  // Getters
  bool get isInitialized => _isInitialized;
  bool get isBlindMode => _isBlindMode;
  bool get isVoiceCommandMode => _isVoiceCommandMode;
  bool get isEmergencyMode => _isEmergencyMode;

  /// Initialize all accessibility services
  Future<void> initialize() async {
    if (_isInitialized) return;

    debugPrint('Initializing Accessibility Manager...');

    // Initialize voice service
    await voiceService.initialize();
    voiceService.onSpeechResult = _handleSpeechResult;
    voiceService.onSpeechError = _handleSpeechError;

    // Initialize gesture service
    gestureService.initialize();
    gestureService.onGestureDetected = _handleGesture;

    // Initialize blind detection service
    blindDetectionService.onDetectionComplete = _handleBlindDetection;
    blindDetectionService.onError = _handleBlindDetectionError;

    // Initialize navigation service
    await navigationService.initialize();
    navigationService.onInstructionChanged = _handleNavigationInstruction;
    navigationService.onArrived = _handleArrival;
    navigationService.onOffRoute = _handleOffRoute;
    navigationService.onStateChanged = _handleNavigationState;

    _isInitialized = true;
    debugPrint('Accessibility Manager initialized');
  }

  // ==================== Speech Handling ====================

  void _handleSpeechResult(String result) {
    debugPrint('Speech result: $result');
    _processVoiceCommand(result.toLowerCase());
  }

  void _handleSpeechError(String error) {
    debugPrint('Speech error: $error');
    voiceService.speak('Sorry, I did not understand. Please try again.');
  }

  void _handleNavigationInstruction(NavigationInstruction instruction) {
    if (_isBlindMode) {
      voiceService.speak(instruction.voiceAnnouncement);
    }
  }

  void _handleArrival(String destination) {
    if (_isBlindMode) {
      voiceService.speakImmediate('You have arrived at $destination');
    }
  }

  void _handleOffRoute(String message) {
    if (_isBlindMode) {
      voiceService.speakImmediate(message);
    }
  }

  void _handleNavigationState(NavigationState state) {
    if (_isBlindMode && state == NavigationState.navigating) {
      voiceService.speak('Navigation started. Follow my instructions.');
    }
  }

  // ==================== Blind Detection Handling ====================

  void _handleBlindDetection(BlindDetectionResult result) {
    debugPrint('Blind detection result: ${result.isBlind}');
    
    if (result.isBlind && result.confidence > 0.5) {
      enableBlindMode();
      voiceService.speak('Blind mode enabled. I will guide you with voice instructions.');
    } else if (!result.isBlind) {
      // Optionally ask user if they want to enable blind mode manually
    }
  }

  void _handleBlindDetectionError(String error) {
    debugPrint('Blind detection error: $error');
  }

  // ==================== Gesture Handling ====================

  void _handleGesture(GestureCommand command) {
    debugPrint('Gesture received: $command');

    switch (command) {
      case GestureCommand.doubleClick:
        _handleDoubleClick();
        break;
      case GestureCommand.tripleClick:
        _handleTripleClick();
        break;
      case GestureCommand.swipeUp:
        _handleSwipeUp();
        break;
      case GestureCommand.swipeDown:
        _handleSwipeDown();
        break;
      case GestureCommand.swipeLeft:
        _handleSwipeLeft();
        break;
      case GestureCommand.swipeRight:
        _handleSwipeRight();
        break;
      case GestureCommand.longPress:
        _handleLongPress();
        break;
      case GestureCommand.none:
        break;
    }
  }

  void _handleDoubleClick() {
    if (_isBlindMode) {
      // Activate voice command mode
      _isVoiceCommandMode = true;
      voiceService.speak('Voice command mode activated. Say a command.');
      
      // Start listening
      voiceService.startListening();
    }
  }

  void _handleTripleClick() {
    // Emergency mode
    _isEmergencyMode = true;
    voiceService.speakEmergency('Emergency! Triple click detected. Sending alert.');
    
    // In a real app, this would send an emergency alert
    Future.delayed(const Duration(seconds: 5), () {
      _isEmergencyMode = false;
    });
  }

  void _handleSwipeUp() {
    if (_isBlindMode && navigationService.state == NavigationState.navigating) {
      // Repeat current instruction or go to next
      navigationService.nextInstruction();
      final instruction = navigationService.currentInstruction;
      if (instruction != null) {
        voiceService.speak(instruction.voiceAnnouncement);
      }
    }
  }

  void _handleSwipeDown() {
    if (_isBlindMode && navigationService.state == NavigationState.navigating) {
      // Pause navigation
      navigationService.pauseNavigation();
      voiceService.speak('Navigation paused.');
    }
  }

  void _handleSwipeLeft() {
    if (_isBlindMode) {
      // Go back / previous
      voiceService.speak('Going back.');
    }
  }

  void _handleSwipeRight() {
    if (_isBlindMode) {
      // Confirm / next
      voiceService.speak('Confirmed.');
    }
  }

  void _handleLongPress() {
    if (_isBlindMode) {
      // Open accessibility menu
      voiceService.speak('Accessibility menu. Say: navigation, location, or help.');
    }
  }

  // ==================== Voice Command Processing ====================

  void _processVoiceCommand(String command) {
    if (!_isVoiceCommandMode) return;

    _isVoiceCommandMode = false;

    if (command.contains('navigate') || command.contains('go to')) {
      _handleNavigationVoiceCommand(command);
    } else if (command.contains('where') || command.contains('location')) {
      _handleLocationCommand();
    } else if (command.contains('help')) {
      _handleHelpCommand();
    } else if (command.contains('stop') || command.contains('pause')) {
      navigationService.pauseNavigation();
      voiceService.speak('Navigation paused.');
    } else if (command.contains('resume') || command.contains('continue')) {
      navigationService.resumeNavigation();
      voiceService.speak('Navigation resumed.');
    } else {
      voiceService.speak('Command not recognized. Try: navigate, location, or help.');
    }
  }

  void _handleNavigationVoiceCommand(String command) {
    // Extract destination from command and start navigation
    // This would typically search for the location
    voiceService.speak('Starting navigation to your destination.');
  }

  void _handleLocationCommand() {
    if (navigationService.currentPosition != null) {
      final pos = navigationService.currentPosition!;
      voiceService.speak('Your current location is at latitude ${pos.latitude.toStringAsFixed(4)}, longitude ${pos.longitude.toStringAsFixed(4)}.');
    } else {
      voiceService.speak('Unable to determine your location.');
    }
  }

  void _handleHelpCommand() {
    voiceService.speak('''
      Available commands:
      - Double click: Voice command mode
      - Triple click: Emergency alert
      - Swipe up: Next instruction
      - Swipe down: Pause navigation
      - Long press: Accessibility menu
      Say 'navigate' to start navigation.
      Say 'where am I' for your location.
    ''');
  }

  // ==================== Public Control Methods ====================

  /// Enable blind mode
  void enableBlindMode() {
    _isBlindMode = true;
    blindDetectionService.setBlindMode(true);
    voiceService.setSpeechRate(0.4); // Slower speech for better understanding
    debugPrint('Blind mode enabled');
  }

  /// Disable blind mode
  void disableBlindMode() {
    _isBlindMode = false;
    blindDetectionService.setBlindMode(false);
    debugPrint('Blind mode disabled');
  }

  /// Toggle blind mode
  bool toggleBlindMode() {
    _isBlindMode = !_isBlindMode;
    blindDetectionService.setBlindMode(_isBlindMode);
    return _isBlindMode;
  }

  /// Start blind detection analysis
  Future<void> detectBlindUser() async {
    await blindDetectionService.analyzeUser();
  }

  /// Manually confirm blind status
  void confirmBlindUser(bool isBlind) {
    if (isBlind) {
      enableBlindMode();
      voiceService.speak('Blind mode enabled. Use gestures to control the app.');
    } else {
      disableBlindMode();
    }
  }

  /// Start navigation to a destination
  Future<NavigationResult?> startNavigation({
    required double destinationLat,
    required double destinationLng,
    required String destinationName,
  }) async {
    final result = await navigationService.startNavigation(
      destinationLat: destinationLat,
      destinationLng: destinationLng,
      destinationName: destinationName,
    );

    if (_isBlindMode && result != null) {
      final timeStr = result.estimatedTimeMinutes >= 1 
          ? '${result.estimatedTimeMinutes} minutes'
          : 'less than a minute';
      voiceService.speak('Navigation started. Your destination is $destinationName. Estimated time: $timeStr.');
    }

    return result;
  }

  /// Stop navigation
  void stopNavigation() {
    navigationService.stopNavigation();
    if (_isBlindMode) {
      voiceService.speak('Navigation stopped.');
    }
  }

  /// Repeat current navigation instruction
  void repeatInstruction() {
    if (_isBlindMode) {
      navigationService.repeatCurrentInstruction();
    }
  }

  /// Announce current status
  void announceStatus() {
    if (_isBlindMode) {
      final navState = navigationService.state;
      switch (navState) {
        case NavigationState.navigating:
          final distance = navigationService.getRemainingDistance();
          final time = navigationService.getEstimatedTime();
          voiceService.speak('Navigating. $distance meters remaining. Estimated time: $time minutes.');
          break;
        case NavigationState.paused:
          voiceService.speak('Navigation paused.');
          break;
        case NavigationState.arrived:
          voiceService.speak('You have arrived at your destination.');
          break;
        default:
          voiceService.speak('Ready. Say a command or use gestures.');
      }
    }
  }

  /// Clean up resources
  Future<void> dispose() async {
    await voiceService.dispose();
    await blindDetectionService.dispose();
    navigationService.dispose();
    _isInitialized = false;
  }
}

/// Extension for Emergency speak
extension VoiceServiceExtension on VoiceService {
  Future<void> speakEmergency(String message) async {
    await speakImmediate(message);
  }
}