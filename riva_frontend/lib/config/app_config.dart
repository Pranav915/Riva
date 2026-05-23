import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  // Single source of truth for backend URL
  // Change this to switch between local and production
  // static const String backendHost = 'riva-5x4h.onrender.com';
  static const String backendHost = 'riva-5x4h.onrender.com';  // Local dev
  
  static String get apiBaseUrl => 'https://$backendHost';
  static String get wsBaseUrl => 'wss://$backendHost';
  
  static const String appName = 'RIVA';
  static const String appVersion = '1.0.0';
  static const String appDescription = 'Your AI Personal Assistant';
  
  // Voice settings
  static const int sampleRate = 16000;
  static const int numChannels = 1;
  static const int bitDepth = 16;
  
  // WebSocket settings
  static const Duration reconnectDelay = Duration(seconds: 3);
  static const int maxReconnectAttempts = 5;
  
  // Storage keys
  static const String keyAuthToken = 'auth_token';
  static const String keyUserId = 'user_id';
  static const String keyUserEmail = 'user_email';
  static const String keyUserName = 'user_name';
  static const String keyConversations = 'conversations';
}
