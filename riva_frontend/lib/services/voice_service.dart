import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'dart:typed_data';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';
import '../config/voice_constants.dart';
import '../models/voice_state_model.dart';

class VoiceService {
  final FlutterSoundRecorder _recorder = FlutterSoundRecorder();
  final FlutterTts _flutterTts = FlutterTts();
  
  WebSocketChannel? _channel;
  StreamController<Uint8List>? _audioController;
  StreamController<VoiceState>? _stateController;
  StreamController<String>? _messageController;

  VoiceState _currentState = VoiceState();
  int _reconnectAttempts = 0;
  bool _isInitialized = false;
  bool _shouldReconnect = false;
  String? _authToken;

  Stream<VoiceState> get stateStream => _stateController?.stream ?? Stream.empty();
  Stream<String> get messageStream => _messageController?.stream ?? Stream.empty();
  VoiceState get currentState => _currentState;

  Future<void> initialize({String? authToken}) async {
    if (_isInitialized) return;

    _authToken = authToken;
    _stateController = StreamController<VoiceState>.broadcast();
    _messageController = StreamController<String>.broadcast();

    // Request microphone permission
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      _updateState(_currentState.copyWith(
        connectionStatus: VoiceConnectionStatus.error,
        errorMessage: 'Microphone permission denied',
      ));
      return;
    }

    // Initialize recorder
    try {
      await _recorder.openRecorder();
      _isInitialized = true;

      // Configure TTS with optimized settings - add delay to ensure binding
      await Future.delayed(const Duration(milliseconds: 500));
      
      // Get available engines and use Google TTS if available (Samsung issue workaround)
      var engines = await _flutterTts.getEngines;
      log('[VOICE] Available TTS engines: $engines');
      
      // Try to set Google TTS engine explicitly (fixes Samsung devices)
      if (engines != null && engines.toString().contains('com.google.android.tts')) {
        await _flutterTts.setEngine('com.google.android.tts');
        log('[VOICE] Set Google TTS engine');
      }
      
      await _flutterTts.awaitSpeakCompletion(true);
      await _flutterTts.setLanguage(VoiceConstants.language);
      await _flutterTts.setSpeechRate(VoiceConstants.speechRate);
      await _flutterTts.setVolume(VoiceConstants.volume);
      await _flutterTts.setPitch(VoiceConstants.pitch);

      _flutterTts.setCompletionHandler(() {
        _updateState(_currentState.copyWith(
          isSpeaking: false,
          canInterrupt: false,
          activityStatus: VoiceActivityStatus.idle,
        ));
        
        // Resume recording after TTS completes if still connected
        if (_currentState.connectionStatus == VoiceConnectionStatus.connected &&
            _currentState.isRecording) {
          _startRecorderStream();
        }
      });

      log('VoiceService initialized successfully');
    } catch (e) {
      log('VoiceService initialization error: $e');
      _updateState(_currentState.copyWith(
        connectionStatus: VoiceConnectionStatus.error,
        errorMessage: 'Failed to initialize voice system: $e',
      ));
    }
  }

  Future<void> connect() async {
    if (!_isInitialized) {
      await initialize();
    }

    if (_currentState.connectionStatus == VoiceConnectionStatus.connected) {
      log('Already connected');
      return;
    }

    _shouldReconnect = true;
    await _establishConnection();
  }

  Future<void> _establishConnection() async {
    try {
      _updateState(_currentState.copyWith(
        connectionStatus: VoiceConnectionStatus.connecting,
        activityStatus: VoiceActivityStatus.idle,
        clearError: true,
      ));

      final wsUrl = '${AppConfig.wsBaseUrl}/stream';
      final uri = _authToken != null 
        ? Uri.parse('$wsUrl?token=$_authToken')
        : Uri.parse(wsUrl);

      log('Connecting to WebSocket: $wsUrl');
      _channel = WebSocketChannel.connect(uri);

      _audioController = StreamController<Uint8List>();
      _audioController!.stream.listen((chunk) {
        log('[VOICE DEBUG] Audio chunk received: ${chunk.length} bytes');
        if (!_currentState.isSpeaking && _channel != null) {
          log('[VOICE DEBUG] Sending chunk to WebSocket');
          _channel!.sink.add(chunk);
        } else {
          log('[VOICE DEBUG] NOT sending - isSpeaking: ${_currentState.isSpeaking}, channel: ${_channel != null}');
        }
      });

      // Listen to messages from server
      _channel!.stream.listen(
        (message) {
          log('Received from server: $message');
          _handleServerMessage(message);
        },
        onError: (error) {
          log('WebSocket error: $error');
          _handleConnectionError(error);
        },
        onDone: () {
          log('WebSocket connection closed');
          _handleConnectionClosed();
        },
      );

      _updateState(_currentState.copyWith(
        connectionStatus: VoiceConnectionStatus.connected,
        activityStatus: VoiceActivityStatus.idle,
        reconnectAttempts: 0,
      ));
      _reconnectAttempts = 0;

      log('WebSocket connected successfully');
    } catch (e) {
      log('Connection error: $e');
      _handleConnectionError(e);
    }
  }

  Future<void> _handleServerMessage(dynamic message) async {
    try {
      // Parse JSON message from backend
      final messageStr = message.toString();
      Map<String, dynamic>? jsonData;
      
      try {
        jsonData = json.decode(messageStr) as Map<String, dynamic>;
      } catch (e) {
        // Not JSON, treat as plain string (backward compatibility)
        log('[VOICE] Message is not JSON, treating as plain string: $messageStr');
        _handlePlainMessage(messageStr);
        return;
      }

      // Only handle assistant responses (transcripts are not sent from backend)
      if (jsonData.containsKey('response')) {
        final response = jsonData['response'] as String;
        final messageType = jsonData['type'] as String? ?? 'assistant_response';
        
        log('[VOICE] Received assistant response ($messageType): $response');
        
        // Add to message stream for UI display
        _messageController?.add(response);

        // Stop recording while assistant speaks
        _pauseRecording();

        _updateState(_currentState.copyWith(
          activityStatus: VoiceActivityStatus.speaking,
          isSpeaking: true,
          canInterrupt: true,
        ));

        // Speak the response using TTS with re-init if needed
        await _speakWithRetry(response);
      } else {
        log('[VOICE WARNING] Received unexpected message format: $jsonData');
      }
    } catch (e) {
      log('[VOICE ERROR] Error handling server message: $e');
    }
  }
  
  Future<void> _speakWithRetry(String text) async {
    try {
      // Try to speak directly first
      var result = await _flutterTts.speak(text);
      if (result != 1) {
        // If failed, reinitialize TTS and try again
        log('[VOICE] TTS failed, reinitializing...');
        await _flutterTts.setLanguage(VoiceConstants.language);
        await _flutterTts.setSpeechRate(VoiceConstants.speechRate);
        await _flutterTts.setVolume(VoiceConstants.volume);
        await _flutterTts.setPitch(VoiceConstants.pitch);
        
        // Try again
        await _flutterTts.speak(text);
      }
    } catch (e) {
      log('[VOICE TTS ERROR] $e');
    }
  }

  void _handlePlainMessage(String message) {
    // Fallback for plain string messages (backward compatibility)
    log('[VOICE] Plain message: $message');
    _messageController?.add(message);

    // Stop recording while assistant speaks
    _pauseRecording();

    _updateState(_currentState.copyWith(
      activityStatus: VoiceActivityStatus.speaking,
      isSpeaking: true,
      canInterrupt: true,
    ));

    // Speak the response with retry
    _speakWithRetry(message);
  }

  void _handleConnectionError(dynamic error) {
    _updateState(_currentState.copyWith(
      connectionStatus: VoiceConnectionStatus.error,
      activityStatus: VoiceActivityStatus.idle,
      errorMessage: 'Connection error: $error',
    ));

    if (_shouldReconnect && _reconnectAttempts < AppConfig.maxReconnectAttempts) {
      _attemptReconnect();
    }
  }

  void _handleConnectionClosed() {
    if (_shouldReconnect && _reconnectAttempts < AppConfig.maxReconnectAttempts) {
      _attemptReconnect();
    } else {
      _updateState(_currentState.copyWith(
        connectionStatus: VoiceConnectionStatus.disconnected,
        activityStatus: VoiceActivityStatus.idle,
        isRecording: false,
        isSpeaking: false,
      ));
    }
  }

  void _attemptReconnect() {
    _reconnectAttempts++;
    
    _updateState(_currentState.copyWith(
      connectionStatus: VoiceConnectionStatus.reconnecting,
      reconnectAttempts: _reconnectAttempts,
    ));

    log('Attempting reconnection ($_reconnectAttempts/${AppConfig.maxReconnectAttempts})');

    Future.delayed(AppConfig.reconnectDelay, () {
      if (_shouldReconnect) {
        _establishConnection();
      }
    });
  }

  Future<void> startListening() async {
    // Wait for connection if not connected yet
    if (_currentState.connectionStatus != VoiceConnectionStatus.connected) {
      log('[VOICE SERVICE] Not connected, waiting for connection...');
      // Wait up to 5 seconds for connection
      int attempts = 0;
      while (_currentState.connectionStatus != VoiceConnectionStatus.connected && attempts < 10) {
        await Future.delayed(const Duration(milliseconds: 500));
        attempts++;
      }
      
      if (_currentState.connectionStatus != VoiceConnectionStatus.connected) {
        log('[VOICE SERVICE ERROR] Could not establish connection');
        return;
      }
    }

    log('[VOICE SERVICE] Starting to listen...');
    _updateState(_currentState.copyWith(
      activityStatus: VoiceActivityStatus.listening,
      isRecording: true,
    ));

    await _startRecorderStream();
    log('[VOICE SERVICE] Listening started - isRecording: true');
  }

  Future<void> _startRecorderStream() async {
    if (_recorder.isRecording || _currentState.isSpeaking) {
      log('[VOICE DEBUG] Not starting recorder - isRecording: ${_recorder.isRecording}, isSpeaking: ${_currentState.isSpeaking}');
      return;
    }

    try {
      log('[VOICE DEBUG] Starting recorder with:');
      log('[VOICE DEBUG] - Sample rate: ${AppConfig.sampleRate}');
      log('[VOICE DEBUG] - Channels: ${AppConfig.numChannels}');
      log('[VOICE DEBUG] - Audio controller ready: ${_audioController != null}');
      
      await _recorder.startRecorder(
        toStream: _audioController!.sink,
        codec: Codec.pcm16,
        sampleRate: AppConfig.sampleRate,
        numChannels: AppConfig.numChannels,
      );

      log('[VOICE DEBUG] Recorder started successfully');
    } catch (e) {
      log('[VOICE ERROR] Error starting recorder: $e');
      _updateState(_currentState.copyWith(
        errorMessage: 'Failed to start recording: $e',
      ));
    }
  }

  Future<void> _pauseRecording() async {
    if (_recorder.isRecording) {
      await _recorder.stopRecorder();
      log('Recorder paused for TTS');
    }
  }

  Future<void> stopListening() async {
    log('[VOICE SERVICE] Stopping listening...');
    
    if (_recorder.isRecording) {
      try {
        await _recorder.stopRecorder();
        log('[VOICE SERVICE] Recorder stopped');
      } catch (e) {
        log('[VOICE ERROR] Error stopping recorder: $e');
      }
    }
    
    _updateState(_currentState.copyWith(
      activityStatus: VoiceActivityStatus.idle,
      isRecording: false,
    ));

    log('[VOICE SERVICE] Stopped listening - isRecording: false, state updated');
  }

  Future<void> interrupt() async {
    log('Interrupting RIVA');
    
    await _flutterTts.stop();
    
    _updateState(_currentState.copyWith(
      activityStatus: VoiceActivityStatus.listening,
      isSpeaking: false,
      canInterrupt: false,
    ));

    // Resume recording after interrupt
    if (_currentState.isRecording && 
        _currentState.connectionStatus == VoiceConnectionStatus.connected) {
      await _startRecorderStream();
    }
  }

  Future<void> disconnect() async {
    log('[VOICE SERVICE] Disconnecting...');
    _shouldReconnect = false;
    
    // Stop recorder
    try {
      if (_recorder.isRecording) {
        await _recorder.stopRecorder();
        log('[VOICE SERVICE] Recorder stopped');
      }
    } catch (e) {
      log('[VOICE ERROR] Error stopping recorder: $e');
    }
    
    // Stop TTS
    try {
      await _flutterTts.stop();
    } catch (e) {
      log('[VOICE ERROR] Error stopping TTS: $e');
    }
    
    // Close audio controller
    try {
      await _audioController?.close();
      _audioController = null;
      log('[VOICE SERVICE] Audio controller closed');
    } catch (e) {
      log('[VOICE ERROR] Error closing audio controller: $e');
    }
    
    // Close WebSocket
    try {
      await _channel?.sink.close();
      _channel = null;
      log('[VOICE SERVICE] WebSocket closed');
    } catch (e) {
      log('[VOICE ERROR] Error closing WebSocket: $e');
    }

    _updateState(_currentState.copyWith(
      connectionStatus: VoiceConnectionStatus.disconnected,
      activityStatus: VoiceActivityStatus.idle,
      isRecording: false,
      isSpeaking: false,
      canInterrupt: false,
    ));

    log('[VOICE SERVICE] Disconnected - state updated');
  }

  void _updateState(VoiceState newState) {
    _currentState = newState;
    _stateController?.add(newState);
  }

  Future<void> dispose() async {
    _shouldReconnect = false;
    await disconnect();
    await _recorder.closeRecorder();
    await _stateController?.close();
    await _messageController?.close();
    _isInitialized = false;
    log('VoiceService disposed');
  }
}

