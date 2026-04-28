import 'package:flutter/material.dart';
import 'api_service.dart';
import 'package:file_picker/file_picker.dart';
import 'auth_service.dart';
import 'main.dart';
import 'dart:async';
import 'video_player_widget.dart';
import 'package:fl_chart/fl_chart.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  String? selectedViolationId;
  Map<String, dynamic>? selectedData;

  Map<String, dynamic>? graphData;

  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();

    loadGraph(); 

    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      setState(() {});
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  // ================= LOAD GRAPH =================
  Future<void> loadGraph() async {
    final data = await ApiService.getGraph();
    setState(() {
      graphData = data; 
    });
  }

  // ================= LOAD VIOLATION =================
  Future<void> loadViolation(String violationId) async {
    final detail = await ApiService.getViolationView(violationId);

    print("CLICKED VIDEO: ${detail["video_url"]}");

    setState(() {
      selectedViolationId = violationId;

      selectedData = {
        // KEEP LEFT (uploaded/original)
        "original_media_url":
            selectedData?["original_media_url"] ?? "",

        // UPDATE RIGHT (clicked violation)
        "suspicious_media_url":
            detail["video_url"] ??
            selectedData?["suspicious_media_url"] ??
            "",

        "violation": {
          ...detail,

          "modality_scores": detail["modality_scores"] ?? {
            "visual": detail["similarity_score"] ??
                detail["confidence"] ?? 0,
            "audio": 0,
            "text": 0,
          },
        },
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEDEDED),
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        automaticallyImplyLeading: false,
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.settings, color: Colors.black),
            onSelected: (value) {
              if (value == "home") {
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const LandingPage()),
                  (route) => false,
                );
              } else if (value == "logout") {
                AuthService.isLoggedIn = false;
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const LandingPage()),
                  (route) => false,
                );
              }
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: "home", child: Text("Home")),
              PopupMenuItem(value: "logout", child: Text("Logout")),
            ],
          ),
        ],
      ),

      body: Row(
        children: [
          // ================= LEFT SIDEBAR =================
          Container(
            width: 260,
            color: Colors.black,
            child: FutureBuilder(
              future: ApiService.getViolations(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) {
                  return const Center(
                      child: CircularProgressIndicator(color: Colors.white));
                }

                final data = snapshot.data as List;

                return ListView(
                  children: data.map((item) {
                    final isSelected =
                        selectedViolationId == item["violation_id"];

                    return GestureDetector(
                      onTap: () {
                        if (item["violation_id"] != null) {
                          loadViolation(item["violation_id"]);
                        }
                      },
                      child: Container(
                        margin: const EdgeInsets.all(10),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? Colors.red
                              : const Color(0xFFC75A75),
                          borderRadius: BorderRadius.circular(15),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(item["filename"] ?? "Unknown",
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold)),

                            Text(item["platform"] ?? "Internet",
                                style:
                                    const TextStyle(color: Colors.white70)),

                            Text(
                              item["match_found"] == true
                                  ? "Match Found"
                                  : "No Match",
                              style:
                                  const TextStyle(color: Colors.white),
                            ),

                            Text(
                              "Status: ${item["status"] ?? "pending"}",
                              style:
                                  const TextStyle(color: Colors.white),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ),

          // ================= MAIN CONTENT =================
          Expanded(
            child: Column(
              children: [
                const SizedBox(height: 20),

                // ================= VIDEOS =================
                Expanded(
                  flex: 2,
                  child: Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: Container(
                          margin: const EdgeInsets.all(10),
                          color: Colors.grey[800],
                          child: Row(
                            children: [
                              Expanded(child: videoBox("original")),   // LEFT
                              const SizedBox(width: 10),
                              Expanded(child: videoBox("suspicious")), // RIGHT
                            ],
                          ),
                        ),
                      ),
                      Expanded(
                        child: Container(
                          margin: const EdgeInsets.all(10),
                          padding: const EdgeInsets.all(15),
                          color: Colors.grey[700],
                          child: buildInfoPanel(),
                        ),
                      ),
                    ],
                  ),
                ),

                // ================= GRAPH =================
                Expanded(
                  child: Container(
                    margin: const EdgeInsets.all(10),
                    color: Colors.grey[600],
                    child: graphData == null
                        ? const Center(child: CircularProgressIndicator())
                        : buildGraph(),
                  ),
                ),
              ],
            ),
          ),

          // ================= RIGHT ACTIONS =================
          Container(
            width: 160,
            padding: const EdgeInsets.only(right: 20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 35, vertical: 20),
                  ),
                  onPressed: () async {
                    final result =
                        await FilePicker.pickFiles(withData: true);
                    if (result == null) return;

                    final file = result.files.single;

                    final uploadRes =
                        await ApiService.uploadFile(
                      fileBytes: file.bytes!,
                      fileName: file.name,
                      title: "Demo Clip",
                      sport: "Football",
                      owner: "User1",
                    );

                    if (uploadRes == null) return;

                    final matchResult =
                        await ApiService.matchFile(
                      fileBytes: file.bytes!,
                      fileName: file.name,
                    );

                    if (matchResult != null) {
                      final suspiciousUrl =
                          matchResult["video_url"] ?? "";

                    setState(() {
                      selectedData = {
                        "original_media_url": suspiciousUrl,
                        "suspicious_media_url": "",

                        "violation": {
                          "query_filename": file.name,
                          "modality_scores": matchResult["modality_scores"] ?? {
                            "visual": matchResult["similarity_score"] ?? 0,
                            "audio": 0,
                            "text": 0,
                          },
                          "explanation":
                              "Matched with ${matchResult["matched_title"] ?? "unknown"}",
                        },
                      };
                    });

                      await loadGraph(); 
                    }
                  },
                  child: const Text("Upload",
                      style: TextStyle(color: Colors.white)),
                ),

                const SizedBox(height: 20),

                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 35, vertical: 20),
                  ),
                  onPressed: selectedViolationId == null
                      ? null
                      : () async {
                          await ApiService.generateDMCA(
                              selectedViolationId!);
                        },
                  child: const Text("DMCA",
                      style: TextStyle(color: Colors.white)),
                ),

                const SizedBox(height: 40),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ================= VIDEO =================
  Widget videoBox(String type) {
    String? url;

    if (selectedData != null) {
      if (type == "original") {
        url = selectedData?["original_media_url"];
      } else {
        url = selectedData?["suspicious_media_url"];
      }
    }


    if (url == null || url.isEmpty) {
      return const Center(
        child: Text("No content",
            style: TextStyle(color: Colors.white)),
      );
    }

    return Container(
      key: ValueKey(url),
      color: Colors.black,
      child: Center(
        child: VideoPlayerWidget(url: url),
      ),
    );
  }

  // ================= GRAPH =================
  Widget buildGraph() {
    final data = graphData?["data"] ?? [];

    if (data.isEmpty) {
      return const Center(
        child: Text("No graph data",
            style: TextStyle(color: Colors.white)),
      );
    }

    List<FlSpot> spots = data.map<FlSpot>((item) {
      return FlSpot(
        (item["time_in_original_video"] ?? 0).toDouble(),
        (item["confidence"] ?? 0).toDouble(),
      );
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(10),
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: true),
          borderData: FlBorderData(show: true),
          titlesData: FlTitlesData(show: true),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              dotData: FlDotData(show: true),
            ),
          ],
        ),
      ),
    );
  }

  // ================= INFO =================
  Widget buildInfoPanel() {
    if (selectedData == null) {
      return const Center(
        child: Text("Select a violation",
            style: TextStyle(color: Colors.white)),
      );
    }

    final violation = selectedData!["violation"] ?? {};
    final modality = violation["modality_scores"] ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(violation["query_filename"] ?? "Unknown",
            style: const TextStyle(color: Colors.white)),
        const SizedBox(height: 10),
        Text("Visual: ${modality["visual"] ?? 0}",
            style: const TextStyle(color: Colors.white)),
        Text("Audio: ${modality["audio"] ?? 0}",
            style: const TextStyle(color: Colors.white)),
        Text("Text: ${modality["text"] ?? 0}",
            style: const TextStyle(color: Colors.white)),
        const SizedBox(height: 10),
        Text(violation["explanation"] ?? "",
            style: const TextStyle(color: Colors.white70)),
      ],
    );
  }
}