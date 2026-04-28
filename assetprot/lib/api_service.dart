import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'package:web/web.dart' as web;
import 'dart:typed_data';
import 'package:url_launcher/url_launcher.dart';

class ApiService {
  static const String baseUrl = "http://127.0.0.1:8000";

  // ================= HEALTH CHECK =================
  static Future<bool> checkServer() async {
    final response = await http.get(Uri.parse("$baseUrl/health"));
    return response.statusCode == 200;
  }

  // ================= UPLOAD =================
  static Future<Map<String, dynamic>?> uploadFile({
    String? filePath,
    List<int>? fileBytes,
    required String fileName,
    required String title,
    required String sport,
    required String owner,
  }) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse("$baseUrl/assets/upload"),
    );

    request.fields['title'] = title;
    request.fields['sport'] = sport;
    request.fields['owner'] = owner;

    if (kIsWeb) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          fileBytes!,
          filename: fileName,
        ),
      );
    } else {
      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          filePath!,
        ),
      );
    }

    var response = await request.send();

    final respStr = await response.stream.bytesToString();

    if (response.statusCode == 200) {
      return jsonDecode(respStr); 
    } else {
      print("UPLOAD FAILED:");
      print(respStr);
      return null;
    }
  }

  // ================= GET VIOLATIONS =================
  static Future<List<dynamic>> getViolations() async {
    final response = await http.get(
      Uri.parse("$baseUrl/scanned/"),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      return [];
    }
  }

  // ================= GET VIOLATION DETAIL =================
  static Future<Map<String, dynamic>?> getViolation(String id) async {
    final response = await http.get(
      Uri.parse("$baseUrl/violations/$id"),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      return null;
    }
  }

  // ================= GRAPH =================
  static Future<Map<String, dynamic>?> getGraph() async {
    final response = await http.get(
      Uri.parse("$baseUrl/graph/video-timeline"),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      return null;
    }
  }

  // ================= DMCA =================
  static Future<void> generateDMCA(String violationId) async {
    final postUrl = "$baseUrl/dmca/$violationId";
    final downloadUrl = "$baseUrl/dmca/$violationId/download";

    await http.post(Uri.parse(postUrl));

    web.window.open(downloadUrl, "_blank");
  }

  static Future<Map<String, dynamic>?> matchFile({
    required Uint8List fileBytes,
    required String fileName,
  }) async {
    var request = http.MultipartRequest(
      "POST",
      Uri.parse("$baseUrl/match/"),
    );

    request.fields["title"] = "Test Asset";
    request.fields["platform"] = "youtube";

    request.files.add(
      http.MultipartFile.fromBytes(
        "file",
        fileBytes,
        filename: fileName,
      ),
    );

    var response = await request.send();
    final respStr = await response.stream.bytesToString();

    print("MATCH RESPONSE: $respStr");

    if (response.statusCode == 200) {
      return jsonDecode(respStr);
    } else {
      return null;
    }

  }

static Future<Map<String, dynamic>> getViolationView(String id) async {
  final res = await http.get(Uri.parse("$baseUrl/violations/$id/view"));
  return jsonDecode(res.body);
}

}