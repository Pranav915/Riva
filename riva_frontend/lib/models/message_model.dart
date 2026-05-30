import 'package:intl/intl.dart';

enum MessageType { user, assistant, system, error }

class Message {
  final String id;
  final String content;
  final MessageType type;
  final DateTime timestamp;
  final bool hasAudio;

  Message({
    required this.id,
    required this.content,
    required this.type,
    required this.timestamp,
    this.hasAudio = false,
  });

  factory Message.user(String content) {
    return Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      type: MessageType.user,
      timestamp: DateTime.now(),
      hasAudio: true,
    );
  }

  factory Message.assistant(String content) {
    return Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      type: MessageType.assistant,
      timestamp: DateTime.now(),
      hasAudio: true,
    );
  }

  factory Message.system(String content) {
    return Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      type: MessageType.system,
      timestamp: DateTime.now(),
      hasAudio: false,
    );
  }

  factory Message.error(String content) {
    return Message(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      content: content,
      type: MessageType.error,
      timestamp: DateTime.now(),
      hasAudio: false,
    );
  }

  String get formattedTime {
    return DateFormat('HH:mm').format(timestamp);
  }

  String get formattedDateTime {
    return DateFormat('MMM dd, yyyy • HH:mm').format(timestamp);
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'type': type.name,
      'timestamp': timestamp.toIso8601String(),
      'hasAudio': hasAudio,
    };
  }

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      content: json['content'],
      type: MessageType.values.firstWhere((e) => e.name == json['type']),
      timestamp: DateTime.parse(json['timestamp']),
      hasAudio: json['hasAudio'] ?? false,
    );
  }
}

