import 'package:flutter/material.dart';
import '../models/voice_state_model.dart';
import '../core/theme.dart';

class StatusIndicator extends StatelessWidget {
  final VoiceState state;

  const StatusIndicator({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _getStatusColor().withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _getStatusColor().withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildStatusIcon(),
          const SizedBox(width: 12),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _getStatusTitle(),
                  style: TextStyle(
                    color: _getStatusColor(),
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
                if (state.statusMessage.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    state.statusMessage,
                    style: TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIcon() {
    if (state.connectionStatus == VoiceConnectionStatus.connecting ||
        state.connectionStatus == VoiceConnectionStatus.reconnecting) {
      return SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation(_getStatusColor()),
        ),
      );
    }

    return Icon(
      _getStatusIcon(),
      color: _getStatusColor(),
      size: 20,
    );
  }

  IconData _getStatusIcon() {
    switch (state.activityStatus) {
      case VoiceActivityStatus.listening:
        return Icons.hearing;
      case VoiceActivityStatus.processing:
        return Icons.psychology;
      case VoiceActivityStatus.speaking:
        return Icons.volume_up;
      case VoiceActivityStatus.idle:
      default:
        if (state.errorMessage != null) {
          return Icons.error_outline;
        }
        return Icons.mic_none;
    }
  }

  String _getStatusTitle() {
    if (state.errorMessage != null) {
      return 'Error';
    }

    switch (state.connectionStatus) {
      case VoiceConnectionStatus.connecting:
        return 'Connecting...';
      case VoiceConnectionStatus.connected:
        switch (state.activityStatus) {
          case VoiceActivityStatus.listening:
            return 'Listening';
          case VoiceActivityStatus.processing:
            return 'Processing';
          case VoiceActivityStatus.speaking:
            return 'Speaking';
          case VoiceActivityStatus.idle:
            return 'Ready';
        }
      case VoiceConnectionStatus.reconnecting:
        return 'Reconnecting...';
      case VoiceConnectionStatus.error:
        return 'Connection Error';
      case VoiceConnectionStatus.disconnected:
        return 'Disconnected';
    }
  }

  Color _getStatusColor() {
    if (state.errorMessage != null) {
      return AppTheme.errorColor;
    }

    switch (state.activityStatus) {
      case VoiceActivityStatus.listening:
        return Colors.green;
      case VoiceActivityStatus.processing:
        return Colors.orange;
      case VoiceActivityStatus.speaking:
        return Colors.blue;
      case VoiceActivityStatus.idle:
      default:
        return AppTheme.textSecondary;
    }
  }
}

