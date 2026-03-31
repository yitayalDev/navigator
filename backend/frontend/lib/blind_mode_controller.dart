import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'voice_service.dart';
import 'pedestrian_navigation_service.dart';
import 'walking_route_service.dart';
import 'models/models.dart';
import 'services/data_service.dart';

/// Blind Mode State
enum BlindModeState {
  disabled,
  enabled,
  listeningForDestination,
  navigating,
}

/// Controller for Blind Mode functionality
/// Handles double-click activation, voice navigation, and real-time guidance
class BlindModeController {
  static final BlindModeController _instance = BlindModeController._internal();
  factory BlindModeController() => _instance;
  BlindModeController._internal();

  // Services
  final VoiceService voiceService = VoiceService();
  final PedestrianNavigationService navigationService = PedestrianNavigationService();
  final WalkingRouteService walkingRouteService = WalkingRouteService();

  // State
  BlindModeState _state = BlindModeState.disabled;
  Position? _currentPosition;
  Location? _selectedDestination;
  String? _currentInstruction;

  // Callbacks
  Function(BlindModeState)? onStateChanged;
  Function(String)? onDestinationFound;
  Function(String)? onNavigationUpdate;
  Function()? onArrived;

  // Getters
  BlindModeState get state => _state;
  bool get isEnabled => _state != BlindModeState.disabled;
  bool get isNavigating => _state == BlindModeState.navigating;
  Location? get destination => _selectedDestination;

  /// Initialize the blind mode controller
  Future<void> initialize() async {
    await voiceService.initialize();
    await navigationService.initialize();

    // Set up voice service callback to process speech results
    voiceService.onSpeechResult = handleSpeechResult;
    voiceService.onListeningStarted = _handleListeningStarted;
    voiceService.onListeningStopped = _handleListeningStopped;

    // Set up navigation callbacks
    navigationService.onInstructionChanged = _handleNavigationInstruction;
    navigationService.onArrived = _handleArrival;
    navigationService.onOffRoute = _handleOffRoute;
    navigationService.onPositionUpdated = _handlePositionUpdate;

    debugPrint('BlindModeController initialized');
  }

  /// Handle double-click to enable blind mode
  Future<void> enableBlindMode() async {
    if (_state != BlindModeState.disabled) return;

    _state = BlindModeState.enabled;
    onStateChanged?.call(_state);

    // Welcome message
    await voiceService.speak(
      'Blind mode activated. Double click again to disable. '
      'Say the name of a place to navigate to it. '
      'For example, say Library or Cafeteria.'
    );

    // Start listening for destination
    await startListeningForDestination();
  }

  /// Disable blind mode
  Future<void> disableBlindMode() async {
    if (_state == BlindModeState.disabled) return;

    navigationService.stopNavigation();
    _state = BlindModeState.disabled;
    _selectedDestination = null;
    onStateChanged?.call(_state);

    await voiceService.speak('Blind mode disabled.');
  }

  /// Toggle blind mode
  Future<void> toggleBlindMode() async {
    if (_state == BlindModeState.disabled) {
      await enableBlindMode();
    } else {
      await disableBlindMode();
    }
  }

  /// Start listening for voice destination input
  Future<void> startListeningForDestination() async {
    _state = BlindModeState.listeningForDestination;
    onStateChanged?.call(_state);

    await voiceService.askForDestination();

    // Start speech recognition
    final success = await voiceService.startListening(
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
    );

    if (!success) {
      await voiceService.speak(
        'Could not start voice recognition. Please try again.'
      );
      _state = BlindModeState.enabled;
      onStateChanged?.call(_state);
    }
  }

  /// Process the spoken destination
  /// Called when speech result is received from VoiceService
  Future<void> processDestination(String spokenText) async {
    if (_state != BlindModeState.listeningForDestination) return;

    debugPrint('Processing destination: $spokenText');

    // Find matching location from campus data
    final location = _findLocationByName(spokenText);

    if (location != null) {
      // Confirm destination
      await voiceService.confirmDestination(location.name);
      
      // Start navigation
      await startNavigationTo(location);
    } else {
      // Location not found
      await voiceService.speak(
        'Sorry, I could not find "$spokenText". '
        'Please say another place name.'
      );
      
      // Continue listening
      await startListeningForDestination();
    }
  }

  /// Find location by name from campus data
  Location? _findLocationByName(String name) {
    // Search through allLocations for matching name
    final normalizedName = name.toLowerCase().trim();
    
    for (final location in DataService.allLocations) {
      final locName = location.name.toLowerCase().trim();
      // Exact match
      if (locName == normalizedName) {
        return location;
      }
      // Contains match
      if (locName.contains(normalizedName) || normalizedName.contains(locName)) {
        return location;
      }
    }
    
    return null;
  }

  /// Start navigation to a destination
  Future<void> startNavigationTo(Location destination) async {
    if (_currentPosition == null) {
      _currentPosition = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
    }

    if (_currentPosition == null) {
      await voiceService.speak('Could not get your current location.');
      return;
    }

    _selectedDestination = destination;
    _state = BlindModeState.navigating;
    onStateChanged?.call(_state);
    onDestinationFound?.call(destination.name);

    // Get walking route
    final route = await walkingRouteService.getBestWalkingRoute(
      startLat: _currentPosition!.latitude,
      startLng: _currentPosition!.longitude,
      endLat: destination.lat,
      endLng: destination.lng,
    );

    if (route.isValid) {
      // Start navigation with voice guidance
      await navigationService.startNavigation(
        destinationLat: destination.lat,
        destinationLng: destination.lng,
        destinationName: destination.name,
      );

      // Announce start
      await voiceService.startNavigationGuidance(
        destination.name,
        route.formattedDistance,
        route.formattedTime,
      );
    } else {
      await voiceService.speak('Could not find a route to ${destination.name}.');
      _state = BlindModeState.enabled;
      onStateChanged?.call(_state);
    }
  }

  /// Handle navigation instruction changes
  void _handleNavigationInstruction(NavigationInstruction instruction) {
    _currentInstruction = instruction.voiceAnnouncement;
    onNavigationUpdate?.call(instruction.voiceAnnouncement);
    
    // Speak the instruction
    voiceService.speak(instruction.voiceAnnouncement);
  }

  /// Handle arrival at destination
  void _handleArrival(String destinationName) {
    _state = BlindModeState.enabled;
    onStateChanged?.call(_state);
    onArrived?.call();

    // Announce arrival
    voiceService.announceArrival(destinationName);
  }

  /// Handle off-route detection
  void _handleOffRoute(String message) {
    debugPrint('Off route: $message');
    voiceService.speak(message);
  }

  /// Handle position update
  void _handlePositionUpdate(Position position) {
    _currentPosition = position;

    // Check if still on route
    if (_selectedDestination != null) {
      final isOffRoute = walkingRouteService.isOffRoute(
        position.latitude,
        position.longitude,
        [],
      );

      if (isOffRoute) {
        voiceService.announceWrongDirection('turn around');
      }
    }
  }

  void _handleListeningStarted() {
    debugPrint('Listening started for destination');
  }

  void _handleListeningStopped() {
    debugPrint('Listening stopped');
    // If we're waiting for destination and no result was received, ask again
    if (_state == BlindModeState.listeningForDestination) {
      Future.delayed(const Duration(milliseconds: 500), () {
        if (_state == BlindModeState.listeningForDestination) {
          voiceService.speak('I did not hear a location. Please try again.');
          startListeningForDestination();
        }
      });
    }
  }

  /// Handle speech result from VoiceService
  void handleSpeechResult(String text) {
    if (_state == BlindModeState.listeningForDestination) {
      processDestination(text);
    } else if (_state == BlindModeState.enabled) {
      // Any voice command when just enabled
      processDestination(text);
    }
  }

  /// Go to next navigation instruction (swipe up gesture)
  Future<void> nextInstruction() async {
    if (_state != BlindModeState.navigating) return;
    
    navigationService.nextInstruction();
  }

  /// Repeat current instruction (swipe down gesture)
  Future<void> repeatInstruction() async {
    if (_state != BlindModeState.navigating) return;
    
    if (_currentInstruction != null) {
      await voiceService.speak(_currentInstruction!);
    }
  }

  /// Stop navigation but keep blind mode enabled
  Future<void> stopNavigation() async {
    navigationService.stopNavigation();
    _selectedDestination = null;
    _state = BlindModeState.enabled;
    onStateChanged?.call(_state);
    
    await voiceService.speak('Navigation stopped. Say a new destination to continue.');
  }

  /// Get current status
  String getStatusMessage() {
    switch (_state) {
      case BlindModeState.disabled:
        return 'Blind mode is off';
      case BlindModeState.enabled:
        return 'Blind mode is on. Say a destination.';
      case BlindModeState.listeningForDestination:
        return 'Listening for destination...';
      case BlindModeState.navigating:
        return 'Navigating to ${_selectedDestination?.name ?? "destination"}';
    }
  }

  /// Clean up
  Future<void> dispose() async {
    await voiceService.dispose();
    navigationService.dispose();
  }
}