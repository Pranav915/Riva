import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../models/conversation_model.dart';
import '../models/message_model.dart';

class StorageService {
  static SharedPreferences? _prefs;

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  static SharedPreferences get prefs {
    if (_prefs == null) {
      throw Exception('StorageService not initialized. Call init() first.');
    }
    return _prefs!;
  }

  // Auth
  static Future<void> saveAuthToken(String token) async {
    await prefs.setString(AppConfig.keyAuthToken, token);
  }

  static String? getAuthToken() {
    return prefs.getString(AppConfig.keyAuthToken);
  }

  static Future<void> saveUserId(String userId) async {
    await prefs.setString(AppConfig.keyUserId, userId);
  }

  static String? getUserId() {
    return prefs.getString(AppConfig.keyUserId);
  }

  static Future<void> saveUserEmail(String email) async {
    await prefs.setString(AppConfig.keyUserEmail, email);
  }

  static String? getUserEmail() {
    return prefs.getString(AppConfig.keyUserEmail);
  }

  static Future<void> saveUserName(String name) async {
    await prefs.setString(AppConfig.keyUserName, name);
  }

  static String? getUserName() {
    return prefs.getString(AppConfig.keyUserName);
  }

  static Future<void> clearAuth() async {
    await prefs.remove(AppConfig.keyAuthToken);
    await prefs.remove(AppConfig.keyUserId);
    await prefs.remove(AppConfig.keyUserEmail);
    await prefs.remove(AppConfig.keyUserName);
  }

  // Conversations
  static Future<void> saveConversation(Conversation conversation) async {
    final conversations = getConversations();
    final index = conversations.indexWhere((c) => c.id == conversation.id);
    
    if (index != -1) {
      conversations[index] = conversation;
    } else {
      conversations.add(conversation);
    }

    final jsonList = conversations.map((c) => c.toJson()).toList();
    await prefs.setString(AppConfig.keyConversations, json.encode(jsonList));
  }

  static List<Conversation> getConversations() {
    final jsonString = prefs.getString(AppConfig.keyConversations);
    if (jsonString == null) return [];

    try {
      final jsonList = json.decode(jsonString) as List;
      return jsonList.map((j) => Conversation.fromJson(j)).toList();
    } catch (e) {
      return [];
    }
  }

  static Conversation? getCurrentConversation() {
    final conversations = getConversations();
    if (conversations.isEmpty) return null;
    return conversations.last;
  }

  static Future<void> addMessageToCurrentConversation(Message message) async {
    var conversation = getCurrentConversation();
    
    if (conversation == null) {
      conversation = Conversation.create();
    }

    conversation = conversation.addMessage(message);
    await saveConversation(conversation);
  }

  static Future<void> clearConversations() async {
    await prefs.remove(AppConfig.keyConversations);
  }

  static Future<void> clearAllData() async {
    await prefs.clear();
  }
}

