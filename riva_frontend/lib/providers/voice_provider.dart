import 'dart:async';
import 'dart:developer';
import 'package:flutter/foundation.dart';
import '../models/voice_state_model.dart';
import '../services/voice_service.dart';
import 'conversation_provider.dart';

class VoiceProvider extends ChangeNotifier {
  final VoiceService _voiceService = VoiceService();
  final ConversationProvider _conversationProvider;

  VoiceState _state = VoiceState();
  StreamSubscription? _stateSubscription;
  StreamSubscription? _messageSubscription;
  
  // Explicit toggle state tracking
  bool _isVoiceActive = false;

  VoiceState get state => _state;
  bool get isConnected => _state.connectionStatus == VoiceConnectionStatus.connected;
  bool get isListening => _state.isRecording;
  bool get isSpeaking => _state.isSpeaking;
  bool get canInterrupt => _state.canInterrupt;
  String get statusMessage => _state.statusMessage;
  
  // Use explicit flag for toggle
  bool get isVoiceActive => _isVoiceActive;

  VoiceProvider(this._conversationProvider) {
    _init();
  }

  void _init() {
    // Listen to voice state changes
    _stateSubscription = _voiceService.stateStream.listen((newState) {
      _state = newState;
      notifyListeners();
    });

    // Listen to messages from assistant
    _messageSubscription = _voiceService.messageStream.listen((message) {
      log('Assistant message: $message');
      _conversationProvider.addAssistantMessage(message);
    });
  }

  Future<void> initialize({String? authToken}) async {
    try {
      await _voiceService.initialize(authToken: authToken);
      notifyListeners();
    } catch (e) {
      log('VoiceProvider initialization error: $e');
    }
  }

  Future<void> connect() async {
    try {
      await _voiceService.connect();
    } catch (e) {
      log('Connection error: $e');
    }
  }

  Future<void> startListening() async {
    try {
      log('[VOICE PROVIDER] startListening called - isConnected: $isConnected');
      if (!isConnected) {
        log('[VOICE PROVIDER] Not connected, connecting first...');
        await connect();
        // Wait a bit for connection to establish
        await Future.delayed(const Duration(milliseconds: 500));
      }
      log('[VOICE PROVIDER] Starting to listen...');
      await _voiceService.startListening();
      log('[VOICE PROVIDER] Listening started - isListening should be true');
    } catch (e) {
      log('[VOICE PROVIDER ERROR] Start listening error: $e');
    }
  }

  Future<void> stopListening() async {
    try {
      await _voiceService.stopListening();
    } catch (e) {
      log('Stop listening error: $e');
    }
  }

  Future<void> interrupt() async {
    try {
      await _voiceService.interrupt();
    } catch (e) {
      log('Interrupt error: $e');
    }
  }

  Future<void> disconnect() async {
    try {
      await _voiceService.disconnect();
    } catch (e) {
      log('Disconnect error: $e');
    }
  }

  Future<void> toggleListening() async {
    log('[VOICE DEBUG] toggleListening called - _isVoiceActive: $_isVoiceActive');
    
    if (_isVoiceActive) {
      // Stop listening and disconnect from backend
      log('[VOICE] Toggling OFF - Stopping and disconnecting...');
      _isVoiceActive = false;
      notifyListeners(); // Update UI immediately
      await stopListening();
      await disconnect();
      log('[VOICE] Disconnected from backend - Animation should stop');
    } else {
      // Connect and start listening
      log('[VOICE] Toggling ON - Connecting and starting to listen...');
      _isVoiceActive = true;
      notifyListeners(); // Update UI immediately
      try {
        await startListening();
        log('[VOICE] Connected and started listening - Animation should start');
      } catch (e) {
        log('[VOICE ERROR] Failed to start listening: $e');
        _isVoiceActive = false;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _stateSubscription?.cancel();
    _messageSubscription?.cancel();
    _voiceService.dispose();
    super.dispose();
  }
}

