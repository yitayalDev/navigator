import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:permission_handler/permission_handler.dart';

/// Result of blind detection analysis
class BlindDetectionResult {
  final bool isBlind;
  final double confidence;
  final String message;
  final DateTime timestamp;

  BlindDetectionResult({
    required this.isBlind,
    required this.confidence,
    required this.message,
    required this.timestamp,
  });
}

/// Service for detecting if user is blind using camera and ML face detection
class BlindDetectionService {
  static final BlindDetectionService _instance = BlindDetectionService._internal();
  factory BlindDetectionService() => _instance;
  BlindDetectionService._internal();

  // Camera and ML
  CameraController? _cameraController;
  FaceDetector? _faceDetector;
  List<CameraDescription>? _cameras;
  
  // State
  bool _isInitialized = false;
  bool _isAnalyzing = false;
  bool _isBlindModeEnabled = false;
  
  // Settings
  int _analysisDurationSeconds = 5;
  int _minDetectionsForBlind = 3;
  int _detectionThreshold = 10; // Frames with no face/eyes detected
  
  // Callbacks
  Function(BlindDetectionResult)? onDetectionComplete;
  Function(String)? onError;
  Function(int)? onProgressUpdate;

  // Internal tracking
  int _consecutiveNoFaceCount = 0;
  int _consecutiveNoEyesCount = 0;
  int _analysisFrameCount = 0;

  /// Initialize the blind detection service
  Future<bool> initialize() async {
    try {
      // Request camera permission
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        debugPrint('Camera permission denied');
        onError?.call('Camera permission denied');
        return false;
      }

      // Get available cameras (front camera for selfie)
      _cameras = await availableCameras();
      if (_cameras == null || _cameras!.isEmpty) {
        debugPrint('No cameras available');
        onError?.call('No cameras available');
        return false;
      }

      // Find front camera
      CameraDescription? frontCamera;
      for (var camera in _cameras!) {
        if (camera.lensDirection == CameraLensDirection.front) {
          frontCamera = camera;
          break;
        }
      }
      frontCamera ??= _cameras!.first;

      // Initialize camera controller
      _cameraController = CameraController(
        frontCamera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.nv21,
      );

      await _cameraController!.initialize();
      debugPrint('Camera initialized');

      // Initialize face detector
      final options = FaceDetectorOptions(
        enableLandmarks: true,
        enableContours: true,
        enableClassification: true,
        enableTracking: true,
        performanceMode: FaceDetectorMode.fast,
      );
      _faceDetector = FaceDetector(options: options);
      debugPrint('Face detector initialized');

      _isInitialized = true;
      return true;
    } catch (e) {
      debugPrint('Initialization error: $e');
      onError?.call('Failed to initialize: $e');
      return false;
    }
  }

  /// Check if service is initialized
  bool get isInitialized => _isInitialized;

  /// Check if blind mode is enabled
  bool get isBlindModeEnabled => _isBlindModeEnabled;

  /// Set blind mode enabled state
  void setBlindMode(bool enabled) {
    _isBlindModeEnabled = enabled;
    debugPrint('Blind mode: $enabled');
  }

  /// Toggle blind mode
  bool toggleBlindMode() {
    _isBlindModeEnabled = !_isBlindModeEnabled;
    debugPrint('Blind mode toggled: $_isBlindModeEnabled');
    return _isBlindModeEnabled;
  }

  /// Start analyzing to detect if user is blind
  Future<BlindDetectionResult?> analyzeUser() async {
    if (!_isInitialized) {
      final initialized = await initialize();
      if (!initialized) {
        return null;
      }
    }

    if (_isAnalyzing) {
      debugPrint('Already analyzing');
      return null;
    }

    _isAnalyzing = true;
    _consecutiveNoFaceCount = 0;
    _consecutiveNoEyesCount = 0;
    _analysisFrameCount = 0;

    debugPrint('Starting blind detection analysis...');

    // Start continuous analysis
    final analysisTimer = Timer.periodic(
      const Duration(milliseconds: 500),
      (timer) async {
        if (!_isAnalyzing || _analysisFrameCount >= _analysisDurationSeconds * 2) {
          timer.cancel();
          _completeAnalysis();
          return;
        }

        await _analyzeFrame();
        _analysisFrameCount++;
        onProgressUpdate?.call(_analysisFrameCount);
      },
    );

    return null; // Result will be provided via callback
  }

  /// Analyze a single frame
  Future<void> _analyzeFrame() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }

    try {
      final XFile imageFile = await _cameraController!.takePicture();
      final inputImage = InputImage.fromFilePath(imageFile.path);
      
      final faces = await _faceDetector!.processImage(inputImage);
      
      await File(imageFile.path).delete();

      if (faces.isEmpty) {
        _consecutiveNoFaceCount++;
        debugPrint('No face detected - count: $_consecutiveNoFaceCount');
      } else {
        // Reset no face count when face is found
        _consecutiveNoFaceCount = 0;

        // Check for eye landmarks
        final firstFace = faces.first;
        final leftEye = firstFace.landmarks[FaceLandmarkType.leftEye];
        final rightEye = firstFace.landmarks[FaceLandmarkType.rightEye];

        if (leftEye == null || rightEye == null) {
          _consecutiveNoEyesCount++;
          debugPrint('No eye landmarks detected - count: $_consecutiveNoEyesCount');
        } else {
          _consecutiveNoEyesCount = 0;
        }
      }
    } catch (e) {
      debugPrint('Frame analysis error: $e');
    }
  }

  /// Complete the analysis and determine result
  void _completeAnalysis() {
    _isAnalyzing = false;

    // Determine if user is blind based on analysis
    // If no face detected many times OR no eyes detected many times
    // (could indicate blindness or camera covered/closed eyes)
    final isBlind = _consecutiveNoFaceCount >= _detectionThreshold ||
        _consecutiveNoEyesCount >= _detectionThreshold;

    // Calculate confidence
    final confidence = _calculateConfidence();

    final result = BlindDetectionResult(
      isBlind: isBlind,
      confidence: confidence,
      message: _getResultMessage(isBlind, confidence),
      timestamp: DateTime.now(),
    );

    debugPrint('Blind detection result: $result');
    onDetectionComplete?.call(result);
  }

  /// Calculate confidence of the detection
  double _calculateConfidence() {
    // Higher confidence if more frames with no face/eyes
    final maxCount = _consecutiveNoFaceCount > _consecutiveNoEyesCount
        ? _consecutiveNoFaceCount
        : _consecutiveNoEyesCount;
    
    return (maxCount / _detectionThreshold).clamp(0.0, 1.0);
  }

  /// Get human-readable result message
  String _getResultMessage(bool isBlind, double confidence) {
    final confidencePercent = (confidence * 100).toStringAsFixed(0);
    
    if (isBlind) {
      if (confidence >= 0.8) {
        return 'High confidence: User appears to be blind ($confidencePercent%)';
      } else if (confidence >= 0.5) {
        return 'Medium confidence: Possibly blind ($confidencePercent%)';
      } else {
        return 'Low confidence: May be blind ($confidencePercent%)';
      }
    } else {
      return 'User appears to be sighted (confidence: $confidencePercent%)';
    }
  }

  /// Manual detection - user confirms they are blind
  void confirmBlind(bool isBlind) {
    _isBlindModeEnabled = isBlind;
    debugPrint('Manual blind mode set: $isBlind');
  }

  /// Take a single photo for face detection (manual trigger)
  Future<BlindDetectionResult?> takePhoto() async {
    if (!_isInitialized) {
      return null;
    }

    try {
      final XFile imageFile = await _cameraController!.takePicture();
      final inputImage = InputImage.fromFilePath(imageFile.path);
      
      final faces = await _faceDetector!.processImage(inputImage);
      
      await File(imageFile.path).delete();

      if (faces.isEmpty) {
        return BlindDetectionResult(
          isBlind: true,
          confidence: 0.9,
          message: 'No face detected - possible blind',
          timestamp: DateTime.now(),
        );
      }

      final firstFace = faces.first;
      final leftEye = firstFace.landmarks[FaceLandmarkType.leftEye];
      final rightEye = firstFace.landmarks[FaceLandmarkType.rightEye];

      if (leftEye == null || rightEye == null) {
        return BlindDetectionResult(
          isBlind: true,
          confidence: 0.8,
          message: 'No eye landmarks detected - possible blind',
          timestamp: DateTime.now(),
        );
      }

      return BlindDetectionResult(
        isBlind: false,
        confidence: 0.9,
        message: 'Face and eyes detected - sighted',
        timestamp: DateTime.now(),
      );
    } catch (e) {
      debugPrint('Take photo error: $e');
      return null;
    }
  }

  /// Set analysis duration
  void setAnalysisDuration(int seconds) {
    _analysisDurationSeconds = seconds;
  }

  /// Set detection threshold
  void setDetectionThreshold(int threshold) {
    _detectionThreshold = threshold;
  }

  /// Clean up resources
  Future<void> dispose() async {
    _isAnalyzing = false;
    await _cameraController?.dispose();
    _cameraController = null;
    _faceDetector = null;
    _isInitialized = false;
    debugPrint('BlindDetectionService disposed');
  }
}