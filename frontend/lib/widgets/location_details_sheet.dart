import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/models.dart';
import '../services/bluetooth_service.dart';

/// Location Details Bottom Sheet with Bluetooth Occupancy Detection
class LocationDetailsSheet extends StatefulWidget {
  final Location location;
  final String distanceText;
  final Color campusColor;
  final bool canCheckOccupancy;
  final VoidCallback onNavigate;

  const LocationDetailsSheet({
    super.key,
    required this.location,
    required this.distanceText,
    required this.campusColor,
    required this.canCheckOccupancy,
    required this.onNavigate,
  });

  @override
  State<LocationDetailsSheet> createState() => _LocationDetailsSheetState();
}

class _LocationDetailsSheetState extends State<LocationDetailsSheet> {
  final BluetoothService _bluetoothService = BluetoothService();
  bool _isScanning = false;
  int _deviceCount = 0;
  String _occupancyStatus = 'Unknown';

  @override
  void initState() {
    super.initState();
    if (widget.canCheckOccupancy) {
      _startBluetoothScan();
    }
  }

  Future<void> _startBluetoothScan() async {
    setState(() {
      _isScanning = true;
    });

    // Request Bluetooth permission
    final bluetoothStatus = await Permission.bluetooth.request();
    final locationStatus = await Permission.locationWhenInUse.request();

    if (bluetoothStatus.isGranted && locationStatus.isGranted) {
      // Start scanning for Bluetooth devices
      final deviceCount = await _bluetoothService.scanForDevices(timeoutSeconds: 5);

      setState(() {
        _deviceCount = deviceCount;
        _isScanning = false;

        // Estimate occupancy based on device count
        if (_deviceCount < 5) {
          _occupancyStatus = 'Low';
        } else if (_deviceCount < 20) {
          _occupancyStatus = 'Moderate';
        } else {
          _occupancyStatus = 'High';
        }
      });
    } else {
      setState(() {
        _isScanning = false;
        _occupancyStatus = 'Permission denied';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with icon and name
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: widget.location.color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(
                  widget.location.icon,
                  color: widget.location.color,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.location.name,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: widget.location.color.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        widget.location.category.toUpperCase(),
                        style: TextStyle(
                          color: widget.location.color,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Description
          Text(
            widget.location.description,
            style: TextStyle(
              fontSize: 15,
              color: Colors.grey[700],
            ),
          ),
          const SizedBox(height: 16),

          // Info rows
          _buildDetailRow(Icons.location_on, 'Coordinates',
              '${widget.location.lat.toStringAsFixed(6)}, ${widget.location.lng.toStringAsFixed(6)}'),
          const SizedBox(height: 12),
          _buildDetailRow(Icons.straighten, 'Distance', widget.distanceText),

          // Show occupancy if this is a library or lab
          if (widget.canCheckOccupancy) ...[
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),
            Text(
              'Current Occupancy',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.grey[800],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _getOccupancyColor().withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _getOccupancyIcon(),
                    color: _getOccupancyColor(),
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _occupancyStatus,
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _getOccupancyColor(),
                        ),
                      ),
                      if (_isScanning)
                        Text(
                          'Scanning for devices...',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        )
                      else
                        Text(
                          '$_deviceCount devices detected',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _isScanning ? null : _startBluetoothScan,
                  color: widget.campusColor,
                ),
              ],
            ),
          ],

          const SizedBox(height: 24),

          // Action buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: widget.onNavigate,
                  icon: const Icon(Icons.directions),
                  label: const Text('Navigate'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: widget.campusColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () async {
                    // Open Telegram bot for sharing
                    final telegramUrl = 'https://t.me/UOGStudentNavBot';
                    if (await canLaunchUrl(Uri.parse(telegramUrl))) {
                      await launchUrl(
                        Uri.parse(telegramUrl),
                        mode: LaunchMode.externalApplication,
                      );
                    } else {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Could not open Telegram'),
                            backgroundColor: Colors.red,
                          ),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.send, size: 18),
                  label: const Text('Share via Telegram'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF0088CC),
                    side: const BorderSide(color: Color(0xFF0088CC)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
            ],
          ),

          // Bottom safe area
          SizedBox(height: MediaQuery.of(context).padding.bottom),
        ],
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.grey[100],
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: Colors.grey[700], size: 20),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Color _getOccupancyColor() {
    switch (_occupancyStatus) {
      case 'Low':
        return Colors.green;
      case 'Moderate':
        return Colors.orange;
      case 'High':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _getOccupancyIcon() {
    switch (_occupancyStatus) {
      case 'Low':
        return Icons.check_circle;
      case 'Moderate':
        return Icons.warning;
      case 'High':
        return Icons.error;
      default:
        return Icons.help;
    }
  }
}