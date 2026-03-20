import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';

/// Occupancy level based on Bluetooth device count
enum OccupancyLevel {
  empty,
  low,
  moderate,
  high,
  veryHigh,
}

/// Bluetooth scanning service for crowd detection
/// Scans for nearby Bluetooth devices to estimate how crowded a location is
class BluetoothService {
  static final BluetoothService _instance = BluetoothService._internal();
  factory BluetoothService() => _instance;
  BluetoothService._internal();

  StreamSubscription<List<ScanResult>>? _scanSubscription;
  final List<BluetoothDevice> _discoveredDevices = [];
  bool _isScanning = false;

  /// Check if Bluetooth is available and enabled
  Future<bool> isBluetoothAvailable() async {
    try {
      // Check if Bluetooth adapter is available
      final state = await FlutterBluePlus.adapterState.first;
      return state == BluetoothAdapterState.on;
    } catch (e) {
      return false;
    }
  }

  /// Request Bluetooth permissions
  Future<bool> requestPermissions() async {
    // Request Bluetooth scan permission (Android 12+)
    final scanStatus = await Permission.bluetoothScan.request();
    // Request Bluetooth connect permission (Android 12+)
    final connectStatus = await Permission.bluetoothConnect.request();
    // Request location permission (needed for Bluetooth scanning on older Android)
    final locationStatus = await Permission.locationWhenInUse.request();

    return scanStatus.isGranted && 
           (connectStatus.isGranted || connectStatus.isLimited) &&
           (locationStatus.isGranted || locationStatus.isLimited);
  }

  /// Check if Bluetooth and location services are enabled
  Future<bool> checkPermissions() async {
    final scanStatus = await Permission.bluetoothScan.status;
    final locationStatus = await Permission.locationWhenInUse.status;
    
    return scanStatus.isGranted && locationStatus.isGranted;
  }

  /// Scan for nearby Bluetooth devices
  /// Returns the number of devices found
  Future<int> scanForDevices({int timeoutSeconds = 10}) async {
    if (_isScanning) {
      return _discoveredDevices.length;
    }

    _isScanning = true;
    _discoveredDevices.clear();

    try {
      // Check if Bluetooth is available
      if (!await isBluetoothAvailable()) {
        _isScanning = false;
        return 0;
      }

      // Request permissions
      if (!await requestPermissions()) {
        _isScanning = false;
        return 0;
      }

      // Start scanning
      await FlutterBluePlus.startScan(
        timeout: Duration(seconds: timeoutSeconds),
        androidUsesFineLocation: true,
      );

      // Listen to scan results
      _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
        _discoveredDevices.clear();
        for (var result in results) {
          // Filter out devices without names (they might not be phones)
          if (result.device.platformName.isNotEmpty) {
            _discoveredDevices.add(result.device);
          }
        }
      });

      // Wait for scan to complete
      await Future.delayed(Duration(seconds: timeoutSeconds));

      // Stop scanning
      await stopScanning();

      return _discoveredDevices.length;
    } catch (e) {
      _isScanning = false;
      return 0;
    }
  }

  /// Stop ongoing Bluetooth scan
  Future<void> stopScanning() async {
    try {
      await _scanSubscription?.cancel();
      _scanSubscription = null;
      await FlutterBluePlus.stopScan();
    } catch (e) {
      // Ignore errors when stopping
    }
    _isScanning = false;
  }

  /// Determine occupancy level based on device count
  /// This is a simple heuristic - in a real app, you might want to calibrate this
  OccupancyLevel getOccupancyLevel(int deviceCount) {
    if (deviceCount <= 2) {
      return OccupancyLevel.empty;
    } else if (deviceCount <= 5) {
      return OccupancyLevel.low;
    } else if (deviceCount <= 15) {
      return OccupancyLevel.moderate;
    } else if (deviceCount <= 30) {
      return OccupancyLevel.high;
    } else {
      return OccupancyLevel.veryHigh;
    }
  }

  /// Get human-readable occupancy status
  String getOccupancyStatus(int deviceCount) {
    final level = getOccupancyLevel(deviceCount);
    switch (level) {
      case OccupancyLevel.empty:
        return '🟢 Empty';
      case OccupancyLevel.low:
        return '🟢 Few people';
      case OccupancyLevel.moderate:
        return '🟡 Moderate';
      case OccupancyLevel.high:
        return '🔴 Crowded';
      case OccupancyLevel.veryHigh:
        return '🔴 Very Crowded';
    }
  }

  /// Get occupancy description
  String getOccupancyDescription(int deviceCount) {
    final level = getOccupancyLevel(deviceCount);
    switch (level) {
      case OccupancyLevel.empty:
        return 'Almost no one is here. Great time to study!';
      case OccupancyLevel.low:
        return 'There are a few people here. Good chance to find a seat.';
      case OccupancyLevel.moderate:
        return 'It\'s moderately busy. You might need to wait for a seat.';
      case OccupancyLevel.high:
        return 'It\'s quite crowded. Consider coming back later.';
      case OccupancyLevel.veryHigh:
        return 'Very crowded! Consider going somewhere else or waiting.';
    }
  }

  /// Check if currently scanning
  bool get isScanning => _isScanning;
}
