import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Midnight Sapphire Theme Colors
  static const Color primaryColor = Color(0xFF3B82F6);      // Electric blue
  static const Color secondaryColor = Color(0xFF06B6D4);    // Cyan
  static const Color accentColor = Color(0xFF0EA5E9);       // Sky blue
  
  // Dark slate backgrounds
  static const Color backgroundColor = Color(0xFF0F172A);   // Dark slate blue
  static const Color surfaceColor = Color(0xFF1E293B);      // Slate
  static const Color cardColor = Color(0xFF334155);         // Lighter slate
  static const Color errorColor = Color(0xFFEF4444);        // Red
  
  // Text colors for dark mode
  static const Color textPrimary = Color(0xFFF1F5F9);       // Slate 50
  static const Color textSecondary = Color(0xFF94A3B8);     // Slate 400
  static const Color textHint = Color(0xFF64748B);          // Slate 500
  
  // Primary gradient (blue-focused)
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primaryColor, secondaryColor],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: secondaryColor,
        tertiary: accentColor,
        surface: surfaceColor,
        error: errorColor,
        onPrimary: Colors.white,
        onSecondary: Colors.black,
        onSurface: textPrimary,
        onError: Colors.white,
      ),
      textTheme: GoogleFonts.poppinsTextTheme(ThemeData.dark().textTheme).apply(
        bodyColor: textPrimary,
        displayColor: textPrimary,
      ),
      scaffoldBackgroundColor: backgroundColor,
      appBarTheme: AppBarTheme(
        backgroundColor: backgroundColor,
        elevation: 0,
        centerTitle: true,
        iconTheme: const IconThemeData(color: textPrimary),
        titleTextStyle: GoogleFonts.poppins(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        color: cardColor,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surfaceColor,
        selectedItemColor: secondaryColor,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceColor,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        hintStyle: const TextStyle(color: textHint),
      ),
      dividerColor: const Color(0xFF334155),
      iconTheme: const IconThemeData(color: textSecondary),
    );
  }

  static ThemeData get lightTheme => darkTheme;
}
