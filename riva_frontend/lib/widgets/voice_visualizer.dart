import 'package:flutter/material.dart';

class VoiceVisualizer extends StatefulWidget {
  final bool isActive;
  final bool isSpeaking;
  final VoidCallback onTap;

  const VoiceVisualizer({
    super.key,
    required this.isActive,
    required this.isSpeaking,
    required this.onTap,
  });

  @override
  State<VoiceVisualizer> createState() => _VoiceVisualizerState();
}

class _VoiceVisualizerState extends State<VoiceVisualizer>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _breathingController;
  late AnimationController _rotationController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _breathingAnimation;

  @override
  void initState() {
    super.initState();
    
    // Pulse animation for outer rings
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );

    // Breathing animation for the main button (slower, more subtle)
    _breathingController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _rotationController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Breathing animation: subtle scale and opacity change
    _breathingAnimation = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(
        parent: _breathingController,
        curve: Curves.easeInOut,
      ),
    );
    
    // Start animation if widget is already active
    if (widget.isActive) {
      _pulseController.repeat(reverse: true);
      _breathingController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(VoiceVisualizer oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    // Start/stop breathing animation when active state changes
    if (widget.isActive && !oldWidget.isActive) {
      // Start animations when button becomes active
      _pulseController.repeat(reverse: true);
      _breathingController.repeat(reverse: true);
      if (widget.isSpeaking) {
        _rotationController.repeat();
      }
    } else if (!widget.isActive && oldWidget.isActive) {
      // Stop all animations when button becomes inactive
      _pulseController.stop();
      _breathingController.stop();
      _rotationController.stop();
      _pulseController.reset();
      _breathingController.reset();
      _rotationController.reset();
    }

    // Handle speaking state changes
    if (widget.isSpeaking && !oldWidget.isSpeaking) {
      _rotationController.repeat();
    } else if (!widget.isSpeaking && oldWidget.isSpeaking) {
      _rotationController.stop();
      _rotationController.reset();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _breathingController.dispose();
    _rotationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 250,
      height: 250,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            debugPrint('[VOICE BUTTON] Tapped - isActive: ${widget.isActive}');
            widget.onTap();
          },
          borderRadius: BorderRadius.circular(125),
          child: Stack(
            alignment: Alignment.center,
            clipBehavior: Clip.none,
            children: [
          // Outer pulsing rings (breathing effect when active)
          if (widget.isActive)
            ...List.generate(3, (index) {
              return AnimatedBuilder(
                animation: _pulseAnimation,
                builder: (context, child) {
                  return Opacity(
                    opacity: (0.4 - (index * 0.1)) * (1.0 - _pulseAnimation.value * 0.3),
                    child: Transform.scale(
                      scale: _pulseAnimation.value,
                      child: Container(
                        width: 200 + (index * 20),
                        height: 200 + (index * 20),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: const Color(0xFF06B6D4).withOpacity(0.3 - (index * 0.1)),
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                  );
                },
              );
            }),

          // Rotating gradient ring (when speaking)
          if (widget.isSpeaking)
            RotationTransition(
              turns: _rotationController,
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: SweepGradient(
                    colors: [
                      Colors.deepPurple,
                      Colors.purpleAccent,
                      Colors.transparent,
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.3, 0.3, 1.0],
                  ),
                ),
              ),
            ),

          // Main button with breathing animation
          AnimatedBuilder(
            animation: _breathingAnimation,
            builder: (context, child) {
              return Transform.scale(
                scale: widget.isActive ? _breathingAnimation.value : 1.0,
                child: Container(
                    width: 160,
                    height: 160,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: widget.isActive
                            ? [
                                const Color(0xFF3B82F6),  // Electric blue
                                const Color(0xFF06B6D4),  // Cyan
                              ]
                            : [
                                const Color(0xFF3B82F6).withOpacity(0.5),
                                const Color(0xFF06B6D4).withOpacity(0.5),
                              ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF3B82F6).withOpacity(
                            widget.isActive ? 0.5 : 0.2,
                          ),
                          blurRadius: widget.isActive ? 35 : 20,
                          spreadRadius: widget.isActive ? 8 : 2,
                        ),
                      ],
                    ),
                    child: Icon(
                      widget.isActive ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: 70,
                    ),
                  ),
                );
            },
          ),
            ],
          ),
        ),
      ),
    );
  }
}

