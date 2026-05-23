import 'package:flutter/foundation.dart';
import '../services/finance_service.dart';

/// Provider for finance state management
class FinanceProvider extends ChangeNotifier {
  final FinanceService _financeService = FinanceService();
  
  List<Transaction> _transactions = [];
  FinanceSummary _summary = FinanceSummary.empty();
  List<CategoryInfo> _categories = [];
  bool _isLoading = false;
  String? _error;
  
  // Getters
  List<Transaction> get transactions => _transactions;
  FinanceSummary get summary => _summary;
  List<CategoryInfo> get categories => _categories;
  bool get isLoading => _isLoading;
  String? get error => _error;
  
  // Computed values
  List<Transaction> get recentTransactions => 
      _transactions.take(10).toList();
  
  List<MapEntry<String, double>> get sortedCategories {
    var entries = _summary.categories.entries.toList();
    entries.sort((a, b) => b.value.compareTo(a.value));
    return entries;
  }
  
  /// Load all finance data
  Future<void> loadData({
    required String userId,
    required String authToken,
    int days = 30,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      // Load categories first (static)
      if (_categories.isEmpty) {
        _categories = await _financeService.getCategories();
      }
      
      // Load summary and transactions in parallel
      final results = await Future.wait([
        _financeService.getSummary(
          userId: userId,
          authToken: authToken,
          days: days,
        ),
        _financeService.getTransactions(
          userId: userId,
          authToken: authToken,
          days: days,
        ),
      ]);
      
      _summary = results[0] as FinanceSummary;
      _transactions = results[1] as List<Transaction>;
      
    } catch (e) {
      _error = 'Failed to load finance data';
      print('[FinanceProvider] Error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  
  /// Refresh data
  Future<void> refresh({
    required String userId,
    required String authToken,
  }) async {
    await loadData(userId: userId, authToken: authToken);
  }
  
  /// Get category info by id
  CategoryInfo? getCategoryById(String id) {
    try {
      return _categories.firstWhere((c) => c.id == id);
    } catch (_) {
      return null;
    }
  }
  
  /// Get color for category
  String getCategoryColor(String categoryId) {
    final category = getCategoryById(categoryId);
    return category?.color ?? '#6B7280';
  }
  
  /// Get icon for category  
  String getCategoryIcon(String categoryId) {
    final category = getCategoryById(categoryId);
    return category?.icon ?? '📦';
  }
}
