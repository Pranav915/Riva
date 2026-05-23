import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/voice_provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/voice_visualizer.dart';
import '../core/theme.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    _initializeVoice();
  }

  void _initializeVoice() {
    final voiceProvider = context.read<VoiceProvider>();
    final authProvider = context.read<AuthProvider>();
    
    Future.microtask(() async {
      await voiceProvider.initialize(authToken: authProvider.authToken);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: SafeArea(
        child: Consumer<VoiceProvider>(
          builder: (context, voiceProvider, _) {
            return Column(
              children: [
                // Top bar with greeting and avatar
                _buildTopBar(context),
                
                // Main content - centered mic button
                Expanded(
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Status text (dynamic)
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 300),
                          child: Text(
                            _getStatusText(voiceProvider),
                            key: ValueKey(voiceProvider.isVoiceActive),
                            style: GoogleFonts.poppins(
                              fontSize: 18,
                              color: AppTheme.textSecondary,
                              fontWeight: FontWeight.w500,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                        
                        const SizedBox(height: 48),
                        
                        // Voice visualizer button
                        VoiceVisualizer(
                          isActive: voiceProvider.isVoiceActive,
                          isSpeaking: voiceProvider.isSpeaking,
                          onTap: () => voiceProvider.toggleListening(),
                        ),
                        
                        const SizedBox(height: 48),
                        
                        // Subtle hint
                        AnimatedOpacity(
                          duration: const Duration(milliseconds: 300),
                          opacity: voiceProvider.isVoiceActive ? 0.0 : 1.0,
                          child: Text(
                            'Tap to speak',
                            style: GoogleFonts.poppins(
                              fontSize: 14,
                              color: AppTheme.textHint,
                              letterSpacing: 1,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                
                // Bottom quick actions (subtle)
                _buildBottomHint(),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // App branding
          Text(
            'RIVA',
            style: GoogleFonts.poppins(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: AppTheme.textPrimary,
              letterSpacing: 3,
            ),
          ),
          
          // User avatar
          Consumer<AuthProvider>(
            builder: (context, authProvider, _) {
              if (authProvider.userPhotoUrl != null) {
                return Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppTheme.primaryColor.withOpacity(0.5),
                      width: 2,
                    ),
                  ),
                  child: CircleAvatar(
                    radius: 20,
                    backgroundImage: NetworkImage(authProvider.userPhotoUrl!),
                  ),
                );
              }
              return Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceColor,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.person_outline,
                  color: AppTheme.textSecondary,
                  size: 20,
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildBottomHint() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.tips_and_updates_outlined,
            color: AppTheme.textHint,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            'Try: "What\'s on my schedule today?"',
            style: GoogleFonts.poppins(
              fontSize: 12,
              color: AppTheme.textHint,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  String _getStatusText(VoiceProvider provider) {
    if (provider.isSpeaking) {
      return 'Speaking...';
    } else if (provider.isListening) {
      return 'Listening...';
    } else if (provider.isVoiceActive) {
      return 'Processing...';
    } else {
      return 'How can I help?';
    }
  }
}
