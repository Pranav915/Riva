import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'home_screen.dart';
import 'conversation_screen.dart';
import 'productivity_screen.dart';
import 'finance_screen.dart';
import 'settings_screen.dart';
import '../providers/voice_provider.dart';
import '../providers/finance_provider.dart';
import '../providers/auth_provider.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    HomeScreen(),
    ConversationScreen(),
    ProductivityScreen(),
    FinanceScreen(),
    SettingsScreen(),
  ];

  final List<BottomNavigationBarItem> _navItems = const [
    BottomNavigationBarItem(
      icon: Icon(Icons.home_outlined),
      activeIcon: Icon(Icons.home),
      label: 'Home',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.chat_outlined),
      activeIcon: Icon(Icons.chat),
      label: 'Chat',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.task_outlined),
      activeIcon: Icon(Icons.task),
      label: 'Tasks',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.account_balance_wallet_outlined),
      activeIcon: Icon(Icons.account_balance_wallet),
      label: 'Finance',
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.settings_outlined),
      activeIcon: Icon(Icons.settings),
      label: 'Settings',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });

          // Disconnect voice when leaving home screen
          if (index != 0) {
            final voiceProvider = context.read<VoiceProvider>();
            if (voiceProvider.isConnected) {
              voiceProvider.disconnect();
            }
          }
          
          // Refresh finance data when switching to finance tab (index 3)
          if (index == 3) {
            final authProvider = context.read<AuthProvider>();
            final financeProvider = context.read<FinanceProvider>();
            if (authProvider.userId != null && authProvider.authToken != null) {
              financeProvider.loadData(
                userId: authProvider.userId!,
                authToken: authProvider.authToken!,
              );
            }
          }
        },
        items: _navItems,
        type: BottomNavigationBarType.fixed,
        selectedFontSize: 12,
        unselectedFontSize: 12,
      ),
    );
  }
}

