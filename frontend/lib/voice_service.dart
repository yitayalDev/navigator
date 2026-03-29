import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';

/// Service for Voice features (Text-to-Speech and Speech-to-Text)
/// Provides accessibility features for blind users
class VoiceService {
  static final VoiceService _instance = VoiceService._internal();
  factory VoiceService() => _instance;
  VoiceService._internal();

  // Text-to-Speech
  late FlutterTts _flutterTts;
  bool _isTtsInitialized = false;
  bool _isSpeaking = false; // Track speaking state
  double _speechRate = 0.4; // Slower for Ethiopian English listeners
  double _volume = 1.0;
  double _pitch = 1.0;
  String _language = 'en-US';

  // Speech-to-Text
  late stt.SpeechToText _speechToText;
  bool _isSttInitialized = false;
  bool _isListening = false;
  String _lastWords = '';

  // Callbacks
  Function(String)? onSpeechResult;
  Function(String)? onSpeechError;
  Function()? onListeningStarted;
  Function()? onListeningStopped;

  /// Initialize all voice services
  Future<void> initialize() async {
    await _initTts();
    await _initStt();
  }

  Future<void> _initTts() async {
    _flutterTts = FlutterTts();
    
    await _flutterTts.setLanguage('en-US');
    await _flutterTts.setSpeechRate(_speechRate);
    await _flutterTts.setVolume(_volume);
    await _flutterTts.setPitch(_pitch);
    
    // Handle TTS completion
    _flutterTts.setCompletionHandler(() {
      _isSpeaking = false;
      debugPrint('TTS completed');
    });
    
    // Handle TTS start
    _flutterTts.setStartHandler(() {
      _isSpeaking = true;
      debugPrint('TTS started');
    });
    
    _flutterTts.setErrorHandler((msg) {
      debugPrint('TTS error: $msg');
      onSpeechError?.call(msg);
    });

    _isTtsInitialized = true;
    debugPrint('TTS initialized');
  }

  Future<void> _initStt() async {
    _speechToText = stt.SpeechToText();
    
    try {
      _isSttInitialized = await _speechToText.initialize(
        onStatus: (status) {
          debugPrint('STT Status: $status');
          if (status == 'done' || status == 'notListening') {
            _isListening = false;
            onListeningStopped?.call();
          }
        },
        onError: (error) {
          debugPrint('STT Error: $error');
          onSpeechError?.call(error.errorMsg);
          _isListening = false;
        },
      );
      debugPrint('STT initialized: $_isSttInitialized');
    } catch (e) {
      debugPrint('STT initialization error: $e');
      _isSttInitialized = false;
    }
  }

  // ==================== Text-to-Speech Methods ====================

  /// Speak the given text
  Future<void> speak(String text) async {
    if (!_isTtsInitialized) {
      await _initTts();
    }
    
    if (text.isNotEmpty) {
      await _flutterTts.speak(text);
      debugPrint('TTS speaking: $text');
    }
  }

  /// Speak immediately interrupting any current speech
  Future<void> speakImmediate(String text) async {
    if (!_isTtsInitialized) {
      await _initTts();
    }
    
    await _flutterTts.stop();
    if (text.isNotEmpty) {
      await _flutterTts.speak(text);
      debugPrint('TTS speaking immediate: $text');
    }
  }

  /// Stop speaking
  Future<void> stop() async {
    await _flutterTts.stop();
  }

  /// Set speech rate (0.0 to 1.0)
  Future<void> setSpeechRate(double rate) async {
    _speechRate = rate.clamp(0.0, 1.0);
    await _flutterTts.setSpeechRate(_speechRate);
  }

  /// Set volume (0.0 to 1.0)
  Future<void> setVolume(double volume) async {
    _volume = volume.clamp(0.0, 1.0);
    await _flutterTts.setVolume(_volume);
  }

  /// Set pitch (0.5 to 2.0)
  Future<void> setPitch(double pitch) async {
    _pitch = pitch.clamp(0.5, 2.0);
    await _flutterTts.setPitch(_pitch);
  }

  // ==================== Speech-to-Text Methods ====================

  /// Check if speech recognition is available
  bool get isAvailable => _isSttInitialized;

  /// Check if currently listening
  bool get isListening => _isListening;

  /// Get the last recognized words
  String get lastWords => _lastWords;

  /// Start listening for speech
  Future<bool> startListening({
    String? localeId,
    Duration? listenFor,
    Duration? pauseFor,
  }) async {
    if (!_isSttInitialized) {
      final initialized = await _speechToText.initialize();
      if (!initialized) {
        debugPrint('Failed to initialize STT');
        return false;
      }
      _isSttInitialized = true;
    }

    if (_isListening) {
      await stopListening();
    }

    _lastWords = '';
    _isListening = true;
    onListeningStarted?.call();

    try {
      await _speechToText.listen(
        onResult: (SpeechRecognitionResult result) {
          _lastWords = result.recognizedWords;
          debugPrint('STT result: $_lastWords');
          
          if (result.finalResult) {
            onSpeechResult?.call(_lastWords);
            _isListening = false;
            onListeningStopped?.call();
          }
        },
        listenFor: listenFor ?? const Duration(seconds: 30),
        pauseFor: pauseFor ?? const Duration(seconds: 3),
        localeId: localeId ?? 'en_US',
        listenMode: stt.ListenMode.confirmation,
        cancelOnError: true,
        partialResults: true,
      );
      return true;
    } catch (e) {
      debugPrint('STT listen error: $e');
      _isListening = false;
      onListeningStopped?.call();
      return false;
    }
  }

  /// Stop listening
  Future<void> stopListening() async {
    await _speechToText.stop();
    _isListening = false;
    onListeningStopped?.call();
  }

  /// Cancel listening
  Future<void> cancelListening() async {
    await _speechToText.cancel();
    _isListening = false;
    _lastWords = '';
    onListeningStopped?.call();
  }

  /// Get available locales for speech recognition
  Future<List<stt.LocaleName>> get locales async {
    if (!_isSttInitialized) {
      await _speechToText.initialize();
    }
    return await _speechToText.locales();
  }

  // ==================== Navigation Announcements (Ethiopian English Optimized) ====================

  /// Announce navigation instruction with clear Ethiopian English pronunciation
  Future<void> announceNavigation(String instruction) async {
    await speak(instruction);
  }

  /// Announce arrival at destination
  Future<void> announceArrival(String destination) async {
    await speakImmediate('You have arrived at $destination. This is your destination.');
  }

  /// Announce distance and direction clearly
  Future<void> announceDirection(String direction, String distance) async {
    final message = '$direction. $distance ahead.';
    await speak(message);
  }

  /// Announce turning point with clear instruction
  Future<void> announceTurn(String turnType, String street) async {
    String turnPhrase;
    switch (turnType.toLowerCase()) {
      case 'left':
        turnPhrase = 'Turn left';
        break;
      case 'right':
        turnPhrase = 'Turn right';
        break;
      case 'slight left':
        turnPhrase = 'Bear left';
        break;
      case 'slight right':
        turnPhrase = 'Bear right';
        break;
      case 'sharp left':
        turnPhrase = 'Turn sharp left';
        break;
      case 'sharp right':
        turnPhrase = 'Turn sharp right';
        break;
      case 'u-turn':
        turnPhrase = 'Make a U-turn';
        break;
      default:
        turnPhrase = 'Continue straight';
    }
    
    if (street.isNotEmpty) {
      await speak('$turnPhrase onto $street.');
    } else {
      await speak('$turnPhrase.');
    }
  }

  /// Guide user when they go wrong direction
  Future<void> announceWrongDirection(String correctDirection) async {
    await speakImmediate('You are going the wrong way. Please $correctDirection.');
  }

  /// Announce that user needs to go back
  Future<void> announceGoBack() async {
    await speakImmediate('You have gone past the turn. Please go back.');
  }

  /// Announce continue straight
  Future<void> announceContinueStraight(String distance) async {
    await speak('Continue straight for $distance.');
  }

  /// Ask for destination using voice
  Future<void> askForDestination() async {
    await speak('Please say the name of the place you want to go to.');
  }

  /// Confirm destination
  Future<bool> confirmDestination(String destinationName) async {
    await speak('Do you want to go to $destinationName? Say yes or no.');
    // Return true after asking - actual confirmation will come from speech result
    return true;
  }

  /// Start navigation with voice guidance
  Future<void> startNavigationGuidance(String destinationName, String distance, String time) async {
    await speakImmediate(
      'Starting navigation to $destinationName. '
      'The destination is about $distance away. '
      'Estimated time is $time. '
      'Follow my voice instructions.'
    );
  }

  // ==================== Utility Methods ====================

  /// Clean up resources
  Future<void> dispose() async {
    await _flutterTts.stop();
    await _speechToText.cancel();
    _isTtsInitialized = false;
    _isSttInitialized = false;
    _isListening = false;
  }

  /// Check if TTS is currently speaking
  bool get isSpeaking => _isSpeaking;
}