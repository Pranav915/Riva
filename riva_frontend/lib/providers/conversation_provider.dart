import 'dart:developer';
import 'package:flutter/foundation.dart';
import '../models/conversation_model.dart';
import '../models/message_model.dart';
import '../services/storage_service.dart';

class ConversationProvider extends ChangeNotifier {
  Conversation? _currentConversation;
  List<Message> get messages => _currentConversation?.messages ?? [];
  
  bool get hasMessages => messages.isNotEmpty;
  int get messageCount => messages.length;

  ConversationProvider() {
    _loadCurrentConversation();
  }

  void _loadCurrentConversation() {
    _currentConversation = StorageService.getCurrentConversation();
    if (_currentConversation == null) {
      _currentConversation = Conversation.create();
      _saveConversation();
    }
    notifyListeners();
  }

  Future<void> addUserMessage(String content) async {
    final message = Message.user(content);
    await _addMessage(message);
  }

  Future<void> addAssistantMessage(String content) async {
    final message = Message.assistant(content);
    await _addMessage(message);
  }

  Future<void> addSystemMessage(String content) async {
    final message = Message.system(content);
    await _addMessage(message);
  }

  Future<void> addErrorMessage(String content) async {
    final message = Message.error(content);
    await _addMessage(message);
  }

  Future<void> _addMessage(Message message) async {
    if (_currentConversation == null) {
      _currentConversation = Conversation.create();
    }

    _currentConversation = _currentConversation!.addMessage(message);
    await _saveConversation();
    notifyListeners();
    
    log('Message added: ${message.type.name} - ${message.content}');
  }

  Future<void> _saveConversation() async {
    if (_currentConversation != null) {
      await StorageService.saveConversation(_currentConversation!);
    }
  }

  Future<void> clearConversation() async {
    _currentConversation = Conversation.create();
    await _saveConversation();
    notifyListeners();
    log('Conversation cleared');
  }

  Future<void> startNewConversation() async {
    _currentConversation = Conversation.create();
    await _saveConversation();
    notifyListeners();
    log('New conversation started');
  }

  List<Conversation> getAllConversations() {
    return StorageService.getConversations();
  }

  Future<void> loadConversation(String conversationId) async {
    final conversations = StorageService.getConversations();
    _currentConversation = conversations.firstWhere(
      (c) => c.id == conversationId,
      orElse: () => Conversation.create(),
    );
    notifyListeners();
  }
}

