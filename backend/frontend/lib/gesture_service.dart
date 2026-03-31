import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

/// Enum representing different gesture commands
enum GestureCommand {
  doubleClick,
  tripleClick,
  swipeUp,
  swipeDown,
  swipeLeft,
  swipeRight,
  longPress,
  none,
}

/// Service for detecting gestures and mapping them to commands
/// Provides accessibility features for blind users
class GestureService {
  static final GestureService _instance = GestureService._internal();
  factory GestureService() => _instance;
  GestureService._internal();

  // Gesture detection state
  int _tapCount = 0;
  DateTime _lastTapTime = DateTime.now();
  static const int _doubleTapTimeout = 300; // milliseconds
  static const int _tripleTapTimeout = 500; // milliseconds

  // Callbacks
  Function(GestureCommand)? onGestureDetected;

  // Configuration
  double _swipeThreshold = 50.0; // Minimum distance for swipe detection
  int _requiredTaps = 3; // For triple click detection

  /// Initialize the gesture service
  void initialize() {
    debugPrint('GestureService initialized');
  }

  /// Create a gesture detector widget that wraps any child widget
  Widget wrapWithGestureDetector({
    required Widget child,
    Function(GestureCommand)? onGesture,
  }) {
    // Store the callback but also allow it to be provided
    if (onGesture != null) {
      final existingCallback = onGestureDetected;
      onGestureDetected = (command) {
        // Call both existing and new callback
        existingCallback?.call(command);
        onGesture?.call(command);
      };
    }

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: _handleTapDown,
      onPanStart: _handlePanStart,
      onPanUpdate: _handlePanUpdate,
      onLongPress: _handleLongPress,
      excludeFromSemantics: false,
      child: child,
    );
  }

  /// Handle tap events for double/triple click detection
  void _handleTapDown(TapDownDetails details) {
    final now = DateTime.now();
    final timeSinceLastTap = now.difference(_lastTapTime).inMilliseconds;

    if (timeSinceLastTap < _tripleTapTimeout) {
      _tapCount++;
    } else {
      _tapCount = 1;
    }

    _lastTapTime = now;

    // Determine gesture after a short delay to allow for third tap
    if (_tapCount >= _requiredTaps) {
      _triggerGesture(GestureCommand.tripleClick);
      _tapCount = 0;
    } else {
      // Check for double tap after a delay
      Future.delayed(const Duration(milliseconds: _doubleTapTimeout), () {
        if (_tapCount == 2 && 
            DateTime.now().difference(_lastTapTime).inMilliseconds >= _doubleTapTimeout) {
          _triggerGesture(GestureCommand.doubleClick);
          _tapCount = 0;
        }
      });
    }
  }

  /// Handle pan start (swipe detection)
  Offset? _panStartPosition;

  void _handlePanStart(DragStartDetails details) {
    _panStartPosition = details.localPosition;
  }

  void _handlePanUpdate(DragUpdateDetails details) {
    if (_panStartPosition == null) return;

    final delta = details.localPosition - _panStartPosition!;

    // Check if swipe threshold is met
    if (delta.distance >= _swipeThreshold) {
      final GestureCommand command = _determineSwipeDirection(delta);
      if (command != GestureCommand.none) {
        _triggerGesture(command);
        _panStartPosition = null; // Reset to prevent multiple triggers
      }
    }
  }

  /// Determine swipe direction based on delta
  GestureCommand _determineSwipeDirection(Offset delta) {
    final dx = delta.dx.abs();
    final dy = delta.dy.abs();

    // Determine if horizontal or vertical swipe is dominant
    if (dy > dx) {
      // Vertical swipe
      if (delta.dy < 0) {
        return GestureCommand.swipeUp; // Swipe up (negative dy in Flutter)
      } else {
        return GestureCommand.swipeDown; // Swipe down (positive dy in Flutter)
      }
    } else {
      // Horizontal swipe
      if (delta.dx < 0) {
        return GestureCommand.swipeLeft;
      } else {
        return GestureCommand.swipeRight;
      }
    }
  }

  /// Handle long press
  void _handleLongPress() {
    _triggerGesture(GestureCommand.longPress);
    _tapCount = 0; // Reset tap count
  }

  /// Trigger the gesture callback
  void _triggerGesture(GestureCommand command) {
    debugPrint('Gesture detected: $command');
    onGestureDetected?.call(command);
  }

  /// Set swipe threshold
  void setSwipeThreshold(double threshold) {
    _swipeThreshold = threshold;
  }

  /// Set required taps for multi-tap detection
  void setRequiredTaps(int taps) {
    _requiredTaps = taps;
  }

  /// Get the human-readable name for a gesture command
  static String getGestureName(GestureCommand command) {
    switch (command) {
      case GestureCommand.doubleClick:
        return 'Double Click';
      case GestureCommand.tripleClick:
        return 'Triple Click (Help)';
      case GestureCommand.swipeUp:
        return 'Swipe Up (Next)';
      case GestureCommand.swipeDown:
        return 'Swipe Down (Stop/Pause)';
      case GestureCommand.swipeLeft:
        return 'Swipe Left';
      case GestureCommand.swipeRight:
        return 'Swipe Right';
      case GestureCommand.longPress:
        return 'Long Press';
      case GestureCommand.none:
        return 'None';
    }
  }

  /// Get the action description for a gesture command
  static String getGestureAction(GestureCommand command) {
    switch (command) {
      case GestureCommand.doubleClick:
        return 'Activate voice command mode';
      case GestureCommand.tripleClick:
        return 'Emergency help mode';
      case GestureCommand.swipeUp:
        return 'Repeat last instruction / Next step';
      case GestureCommand.swipeDown:
        return 'Stop/Pause navigation';
      case GestureCommand.swipeLeft:
        return 'Go back / Previous';
      case GestureCommand.swipeRight:
        return 'Go forward / Confirm';
      case GestureCommand.longPress:
        return 'Open accessibility menu';
      case GestureCommand.none:
        return 'No action';
    }
  }
}

/// Mixin for using gesture detection in widgets
mixin GestureMixin<T extends StatefulWidget> on State<T>, WidgetsBindingObserver {
  late GestureService _gestureService;
  bool _isGestureInitialized = false;

  /// Initialize gesture detection
  void initGestures() {
    _gestureService = GestureService();
    _gestureService.initialize();
    _isGestureInitialized = true;
    WidgetsBinding.instance.addObserver(this);
  }

  /// Handle detected gestures - override in your widget
  void handleGesture(GestureCommand command) {
    debugPrint('GestureMixin received: $command');
  }

  /// Wrap your build method's child with gesture detector
  Widget wrapWithGestureDetection(Widget child) {
    if (!_isGestureInitialized) {
      initGestures();
    }
    return _gestureService.wrapWithGestureDetector(
      child: child,
      onGesture: handleGesture,
    );
  }

  @override
  void dispose() {
    if (_isGestureInitialized) {
      WidgetsBinding.instance.removeObserver(this);
    }
    super.dispose();
  }
}