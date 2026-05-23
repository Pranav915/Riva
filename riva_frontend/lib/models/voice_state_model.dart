enum VoiceConnectionStatus {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

enum VoiceActivityStatus {
  idle,
  listening,
  processing,
  speaking,
}

class VoiceState {
  final VoiceConnectionStatus connectionStatus;
  final VoiceActivityStatus activityStatus;
  final String? errorMessage;
  final bool isRecording;
  final bool isSpeaking;
  final bool canInterrupt;
  final int reconnectAttempts;

  VoiceState({
    this.connectionStatus = VoiceConnectionStatus.disconnected,
    this.activityStatus = VoiceActivityStatus.idle,
    this.errorMessage,
    this.isRecording = false,
    this.isSpeaking = false,
    this.canInterrupt = false,
    this.reconnectAttempts = 0,
  });

  VoiceState copyWith({
    VoiceConnectionStatus? connectionStatus,
    VoiceActivityStatus? activityStatus,
    String? errorMessage,
    bool? isRecording,
    bool? isSpeaking,
    bool? canInterrupt,
    int? reconnectAttempts,
    bool clearError = false,
  }) {
    return VoiceState(
      connectionStatus: connectionStatus ?? this.connectionStatus,
      activityStatus: activityStatus ?? this.activityStatus,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      isRecording: isRecording ?? this.isRecording,
      isSpeaking: isSpeaking ?? this.isSpeaking,
      canInterrupt: canInterrupt ?? this.canInterrupt,
      reconnectAttempts: reconnectAttempts ?? this.reconnectAttempts,
    );
  }

  String get statusMessage {
    if (errorMessage != null) return errorMessage!;

    switch (activityStatus) {
      case VoiceActivityStatus.idle:
        return 'Press the button and start speaking';
      case VoiceActivityStatus.listening:
        return 'Listening...';
      case VoiceActivityStatus.processing:
        return 'Processing...';
      case VoiceActivityStatus.speaking:
        return 'Speaking...';
    }
  }

  bool get isActive => 
    activityStatus != VoiceActivityStatus.idle && 
    connectionStatus == VoiceConnectionStatus.connected;
}

