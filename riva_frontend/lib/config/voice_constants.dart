/// Voice processing constants
/// Centralized configuration for audio settings
class VoiceConstants {
  // Audio settings
  static const int sampleRate = 16000;
  static const int numChannels = 1;
  static const int bitDepth = 16;
  
  // Latency optimization
  static const int chunkDurationMs = 100; // Smaller chunks = lower latency
  static const int silenceThresholdMs = 800; // Backend setting mirror
  
  // Connection settings  
  static const Duration reconnectDelay = Duration(seconds: 2);
  static const int maxReconnectAttempts = 5;
  static const Duration connectionTimeout = Duration(seconds: 10);
  
  // TTS settings
  static const double speechRate = 0.52; // Slightly faster for responsiveness
  static const double volume = 1.0;
  static const double pitch = 1.0;
  static const String language = "en-US";
}

/// Provider types for future expansion
enum VoiceProviderType {
  /// Free, offline using Vosk
  vosk,
  
  /// Google Speech (free tier)
  google,
  
  /// OpenAI Realtime API (premium, lowest latency)
  /// TODO: Implement when user upgrades
  openaiRealtime,
  
  /// Deepgram (budget-friendly low latency)
  deepgram,
}
