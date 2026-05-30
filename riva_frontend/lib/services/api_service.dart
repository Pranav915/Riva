import 'dart:convert';
import 'dart:developer';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

class ApiService {
  static String get baseUrl => AppConfig.apiBaseUrl;

  static Future<Map<String, dynamic>?> loginUser(String idToken) async {
    try {
      log('Sending login request to: $baseUrl/auth/login');
      
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"idToken": idToken}),
      ).timeout(const Duration(seconds: 15));

      log('Login response status: ${response.statusCode}');
      log('Login response body: ${response.body}');

      // Accept both 200 (existing user) and 201 (new user)
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          // Log user info
          final isNewUser = data['is_new_user'] ?? false;
          final userName = data['user']['name'] ?? 'Unknown';
          log('[OK] ${isNewUser ? 'New user created' : 'Login successful'}: $userName');
          return data;
        } else {
          log('Login failed: ${data['message'] ?? 'Unknown error'}');
          return null;
        }
      } else {
        log('Login failed with status ${response.statusCode}: ${response.body}');
        return null;
      }
    } catch (e) {
      log('Login error: $e');
      return null;
    }
  }

  static Future<Map<String, dynamic>?> getUserProfile(String token) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/user/profile'),
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer $token",
        },
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      log('Get profile error: $e');
      return null;
    }
  }
}