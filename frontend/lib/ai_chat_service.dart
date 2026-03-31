import 'dart:convert';
import 'package:http/http.dart' as http;

/// AI Chat Service for University of Gondar Navigator
/// Handles communication with the backend AI assistant

class AIChatService {
  // Use port 5000 for full server (with AI), 5001 for standalone AI server
  // Update IP to your computer's IP for physical device
  static const String baseUrl = 'https://navigator-b1wp.onrender.com';
  
  /// Send a message to the AI assistant
  static Future<AIChatResponse?> sendMessage(String message, {String? userId}) async {
    try {
      // Use a client with timeout to prevent hanging
      final client = http.Client();
      
      try {
        final response = await client.post(
          Uri.parse('$baseUrl/api/ai/chat'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'message': message,
            'user_id': userId,
          }),
        ).timeout(const Duration(seconds: 30));
        
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          return AIChatResponse.fromJson(data);
        }
        
        print('AI Chat response status: ${response.statusCode}');
        print('AI Chat response body: ${response.body}');
        return null;
      } finally {
        client.close();
      }
    } catch (e) {
      print('AI Chat Error: $e');
      return null;
    }
  }
  
  /// Get suggested questions
  static Future<List<String>> getSuggestions() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/ai/suggestions'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true) {
          return List<String>.from(data['suggestions'] ?? []);
        }
      }
      
      return _defaultSuggestions;
    } catch (e) {
      return _defaultSuggestions;
    }
  }
  
  /// Clear conversation history
  static Future<bool> clearHistory() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/ai/clear'),
      );
      
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Check AI health/status
  static Future<Map<String, dynamic>?> checkHealth() async {
    try {
      final client = http.Client();
      
      try {
        final response = await client.get(
          Uri.parse('$baseUrl/api/ai/health'),
        ).timeout(const Duration(seconds: 10));
        
        if (response.statusCode == 200) {
          return json.decode(response.body);
        }
        
        return null;
      } finally {
        client.close();
      }
    } catch (e) {
      print('AI Health Check Error: $e');
      return null;
    }
  }
  
  /// Default suggestions when API is unavailable
  static const List<String> _defaultSuggestions = [
    "Where is the library?",
    "How to get to Science Campus?",
    "What are the cafeteria hours?",
    "Where can I find WiFi?",
    "Tell me about the Medical Campus"
  ];
}

/// Model class for AI Chat Response
class AIChatResponse {
  final bool success;
  final String response;
  final List<String>? suggestions;
  final String? error;
  final String? provider;
  
  AIChatResponse({
    required this.success,
    required this.response,
    this.suggestions,
    this.error,
    this.provider,
  });
  
  factory AIChatResponse.fromJson(Map<String, dynamic> json) {
    return AIChatResponse(
      success: json['success'] ?? false,
      response: json['response'] ?? 'No response',
      suggestions: json['suggestions'] != null 
          ? List<String>.from(json['suggestions']) 
          : null,
      error: json['error'],
      provider: json['provider'],
    );
  }
  
  /// Get response as formatted message
  String get formattedResponse {
    return response;
  }
}

/// Model class for chat message
class ChatMessage {
  final String id;
  final String content;
  final bool isUser;
  final DateTime timestamp;
  
  ChatMessage({
    required this.id,
    required this.content,
    required this.isUser,
    required this.timestamp,
  });
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'isUser': isUser,
      'timestamp': timestamp.toIso8601String(),
    };
  }
  
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'],
      content: json['content'],
      isUser: json['isUser'],
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}

/// Quick action buttons for common queries
class QuickAction {
  final String label;
  final String icon;
  final String query;
  
  const QuickAction({
    required this.label,
    required this.icon,
    required this.query,
  });
  
  static const List<QuickAction> quickActions = [
    QuickAction(label: 'Library', icon: '📚', query: 'Where is the library?'),
    QuickAction(label: 'Directions', icon: '🧭', query: 'How to get to Science Campus?'),
    QuickAction(label: 'WiFi', icon: '📶', query: 'Where can I find WiFi?'),
    QuickAction(label: 'Food', icon: '🍽️', query: 'What are the cafeteria hours?'),
    QuickAction(label: 'Campus', icon: '🏛️', query: 'Tell me about the Main Campus'),
  ];
}
