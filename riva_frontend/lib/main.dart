import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'config/app_config.dart';
import 'core/theme.dart';
import 'providers/auth_provider.dart' as app_auth;
import 'providers/conversation_provider.dart';
import 'providers/voice_provider.dart';
import 'providers/finance_provider.dart';
import 'services/storage_service.dart';
import 'screens/login_screen.dart';
import 'screens/main_layout.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp();
  
  // Initialize Storage
  await StorageService.init();
  
  // Load environment variables (fail silently if .env doesn't exist)
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    debugPrint('Warning: .env file not found, using default configuration');
  }
  
  runApp(const RivaApp());
}

class RivaApp extends StatelessWidget {
  const RivaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Auth provider
        ChangeNotifierProvider(create: (_) => app_auth.AuthProvider()),
        
        // Conversation provider
        ChangeNotifierProvider(create: (_) => ConversationProvider()),
        
        // Finance provider
        ChangeNotifierProvider(create: (_) => FinanceProvider()),
        
        // Voice provider (depends on conversation provider)
        ChangeNotifierProxyProvider<ConversationProvider, VoiceProvider>(
          create: (context) => VoiceProvider(context.read<ConversationProvider>()),
          update: (context, conversationProvider, previous) {
            // VoiceProvider doesn't support updating the provider, just return previous
            return previous ?? VoiceProvider(conversationProvider);
          },
        ),
      ],
      child: MaterialApp(
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          primaryColor: AppTheme.primaryColor,
          scaffoldBackgroundColor: AppTheme.backgroundColor,
          colorScheme: ColorScheme.fromSeed(
            seedColor: AppTheme.primaryColor,
            brightness: Brightness.dark,
          ),
          appBarTheme: const AppBarTheme(
            backgroundColor: AppTheme.backgroundColor,
            elevation: 0,
          ),
          useMaterial3: true,
        ),
        home: Consumer<app_auth.AuthProvider>(
          builder: (context, auth, _) {
            if (auth.isLoading) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }
            return auth.isAuthenticated ? const MainLayout() : LoginScreen();
          },
        ),
      ),
    );
  }
}