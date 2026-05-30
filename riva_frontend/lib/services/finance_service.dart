import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';

/// Service for finance API calls
class FinanceService {
  final String baseUrl = AppConfig.apiBaseUrl;
  
  /// Get transactions with optional filters
  Future<List<Transaction>> getTransactions({
    required String userId,
    required String authToken,
    int days = 30,
    String? category,
    String? type,
    int limit = 50,
  }) async {
    try {
      final queryParams = {
        'user_id': userId,
        'days': days.toString(),
        'limit': limit.toString(),
        if (category != null) 'category': category,
        if (type != null) 'type': type,
      };
      
      final uri = Uri.parse('$baseUrl/finance/transactions')
          .replace(queryParameters: queryParams);
      
      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $authToken'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List transactions = data['transactions'] ?? [];
        return transactions.map((t) => Transaction.fromJson(t)).toList();
      }
      return [];
    } catch (e) {
      print('[FinanceService] Error fetching transactions: $e');
      return [];
    }
  }
  
  /// Get spending summary
  Future<FinanceSummary> getSummary({
    required String userId,
    required String authToken,
    int days = 30,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/finance/summary')
          .replace(queryParameters: {
            'user_id': userId,
            'days': days.toString(),
          });
      
      final response = await http.get(
        uri,
        headers: {'Authorization': 'Bearer $authToken'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return FinanceSummary.fromJson(data);
      }
      return FinanceSummary.empty();
    } catch (e) {
      print('[FinanceService] Error fetching summary: $e');
      return FinanceSummary.empty();
    }
  }
  
  /// Get category definitions
  Future<List<CategoryInfo>> getCategories() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/finance/categories'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List categories = data['categories'] ?? [];
        return categories.map((c) => CategoryInfo.fromJson(c)).toList();
      }
      return [];
    } catch (e) {
      print('[FinanceService] Error fetching categories: $e');
      return [];
    }
  }
}

/// Transaction model
class Transaction {
  final String id;
  final String type;
  final double amount;
  final String category;
  final String? subcategory;
  final String? description;
  final String? merchant;
  final String? paymentMethod;
  final DateTime date;
  
  Transaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.category,
    this.subcategory,
    this.description,
    this.merchant,
    this.paymentMethod,
    required this.date,
  });
  
  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id'] ?? '',
      type: json['type'] ?? 'expense',
      amount: (json['amount'] ?? 0).toDouble(),
      category: json['category'] ?? 'other',
      subcategory: json['subcategory'],
      description: json['description'],
      merchant: json['merchant'],
      paymentMethod: json['payment_method'],
      date: DateTime.tryParse(json['date'] ?? '') ?? DateTime.now(),
    );
  }
  
  bool get isExpense => type == 'expense';
  bool get isIncome => type == 'income';
}

/// Finance summary model
class FinanceSummary {
  final double totalIncome;
  final double totalExpense;
  final double balance;
  final Map<String, double> categories;
  
  FinanceSummary({
    required this.totalIncome,
    required this.totalExpense,
    required this.balance,
    required this.categories,
  });
  
  factory FinanceSummary.fromJson(Map<String, dynamic> json) {
    final categoriesMap = <String, double>{};
    if (json['categories'] != null) {
      (json['categories'] as Map).forEach((key, value) {
        categoriesMap[key] = (value ?? 0).toDouble();
      });
    }
    
    return FinanceSummary(
      totalIncome: (json['total_income'] ?? 0).toDouble(),
      totalExpense: (json['total_expense'] ?? 0).toDouble(),
      balance: (json['balance'] ?? 0).toDouble(),
      categories: categoriesMap,
    );
  }
  
  factory FinanceSummary.empty() {
    return FinanceSummary(
      totalIncome: 0,
      totalExpense: 0,
      balance: 0,
      categories: {},
    );
  }
}

/// Category info model
class CategoryInfo {
  final String id;
  final String name;
  final String icon;
  final String color;
  
  CategoryInfo({
    required this.id,
    required this.name,
    required this.icon,
    required this.color,
  });
  
  factory CategoryInfo.fromJson(Map<String, dynamic> json) {
    return CategoryInfo(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      icon: json['icon'] ?? '📦',
      color: json['color'] ?? '#6B7280',
    );
  }
}
