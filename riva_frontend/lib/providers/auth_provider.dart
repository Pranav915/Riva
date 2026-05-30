import 'dart:developer';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../services/auth_service.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();
  
  AuthStatus _status = AuthStatus.unknown;
  User? _firebaseUser;
  String? _authToken;
  String? _errorMessage;
  bool _isLoading = false;

  AuthStatus get status => _status;
  User? get firebaseUser => _firebaseUser;
  String? get authToken => _authToken;
  String? get errorMessage => _errorMessage;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  String? get userId => _firebaseUser?.uid;
  String? get userEmail => _firebaseUser?.email;
  String? get userName => _firebaseUser?.displayName;
  String? get userPhotoUrl => _firebaseUser?.photoURL;

  AuthProvider() {
    _init();
  }

  void _init() {
    // Listen to Firebase auth state changes
    log('[AUTH] Initializing auth state listener');
    FirebaseAuth.instance.authStateChanges().listen((User? user) {
      log('[AUTH] Auth state changed: ${user?.email ?? "null"}');
      _firebaseUser = user;
      if (user != null) {
        log('[AUTH] User is logged in, calling _onUserLoggedIn');
        _onUserLoggedIn(user);
      } else {
        log('[AUTH] User is logged out, calling _onUserLoggedOut');
        _onUserLoggedOut();
      }
    });
  }

  Future<void> _onUserLoggedIn(User user) async {
    try {
      log('[AUTH] _onUserLoggedIn started for: ${user.email}');
      _authToken = await user.getIdToken();
      log('[AUTH] Got ID token: ${_authToken?.substring(0, 20)}...');
      
      // Save to local storage
      if (_authToken != null) {
        await StorageService.saveAuthToken(_authToken!);
        log('[AUTH] Saved auth token to storage');
      }
      if (user.uid.isNotEmpty) {
        await StorageService.saveUserId(user.uid);
      }
      if (user.email != null) {
        await StorageService.saveUserEmail(user.email!);
      }
      if (user.displayName != null) {
        await StorageService.saveUserName(user.displayName!);
      }

      log('[AUTH] Setting status to authenticated');
      _status = AuthStatus.authenticated;
      _errorMessage = null;
      log('[AUTH] Calling notifyListeners');
      notifyListeners();

      log('[AUTH] User authenticated: ${user.email}, status: $_status');
    } catch (e) {
      log('[AUTH ERROR] Error in _onUserLoggedIn: $e');
      _errorMessage = 'Failed to save user data';
      notifyListeners();
    }
  }

  void _onUserLoggedOut() {
    _status = AuthStatus.unauthenticated;
    _firebaseUser = null;
    _authToken = null;
    _errorMessage = null;
    notifyListeners();
    log('User logged out');
  }

  Future<bool> signInWithGoogle() async {
    log('[AUTH] signInWithGoogle started');
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      log('[AUTH] Calling Google Sign-In service');
      final userCredential = await _authService.signInWithGoogle();
      
      if (userCredential == null) {
        log('[AUTH] Google Sign-In cancelled by user');
        _errorMessage = 'Google Sign-In cancelled';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      log('[AUTH] Got user credential, getting ID token');
      final idToken = await userCredential.user?.getIdToken();
      if (idToken == null) {
        log('[AUTH ERROR] Failed to get ID token');
        _errorMessage = 'Failed to get authentication token';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      log('[AUTH] ID token obtained, calling backend API');
      // Send token to backend for verification and user creation
      final response = await ApiService.loginUser(idToken);
      if (response == null) {
        log('[AUTH WARNING] Backend login failed, but Firebase auth succeeded');
        // Still allow login even if backend fails (offline mode)
      } else {
        final isNewUser = response['is_new_user'] ?? false;
        final userName = response['user']['name'] ?? 'User';
        log('[AUTH OK] Backend login successful: $userName (${isNewUser ? 'New User' : 'Existing User'})');
        
        // Store backend token if different from Firebase token
        if (response['token'] != null) {
          await StorageService.saveAuthToken(response['token']);
          log('[AUTH] Stored backend token');
        }
      }

      // Directly call onUserLoggedIn instead of waiting for auth state listener
      // This ensures immediate navigation after login
      await _onUserLoggedIn(userCredential.user!);

      _isLoading = false;
      notifyListeners();  // Trigger UI rebuild
      log('[AUTH] signInWithGoogle completed successfully');
      return true;
    } catch (e) {
      log('[AUTH ERROR] Sign in error: $e');
      _errorMessage = 'Sign in failed: $e';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> signOut() async {
    _isLoading = true;
    notifyListeners();

    try {
      await _authService.signOut();
      await StorageService.clearAuth();
      await StorageService.clearConversations();
      
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      log('Sign out error: $e');
      _errorMessage = 'Sign out failed: $e';
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshToken() async {
    try {
      _authToken = await _authService.getIdToken();
      if (_authToken != null) {
        await StorageService.saveAuthToken(_authToken!);
      }
      notifyListeners();
    } catch (e) {
      log('Token refresh error: $e');
    }
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}

