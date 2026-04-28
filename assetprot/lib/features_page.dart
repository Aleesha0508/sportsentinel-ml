import 'package:flutter/material.dart';
import 'navbar.dart';

class FeaturesPage extends StatelessWidget {
  const FeaturesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEDEDED),
      body: SingleChildScrollView(
        child: Column(
          children: [

            const Navbar(),

            const SizedBox(height: 30),

            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Column(
                children: [
                  const Text(
                    "Protect Your Sports Content Automatically",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: "ChunkFive",
                      fontSize: 36,
                    ),
                  ),
                  const SizedBox(height: 15),
                  const Text(
                    "SportsSentinel scans the internet, detects unauthorized usage, and helps you take action instantly.",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontStyle: FontStyle.italic,
                      fontFamily: "SquadaOne",
                      fontSize: 25,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 40),

            Wrap(
              alignment: WrapAlignment.center,
              children: [
                featureCard(
                  "AI Content Detection",
                  "Detects stolen or reused content using visual, audio, and text similarity.",
                ),
                const SizedBox(width: 50),
                featureCard(
                  "Violation Dashboard",
                  "View flagged clips with severity levels, platform data, and scores.",
                ),
                const SizedBox(width: 50),
                featureCard(
                  "Deep Analysis Process",
                  "Breakdown of visual, audio, and text similarity with explanations.",
                ),
                const SizedBox(width: 50),
                featureCard(
                  "Content DNA Graph",
                  "Track how content spreads and evolves across platforms.",
                ),
                const SizedBox(width: 50),
                featureCard(
                  "DMCA Automation",
                  "Generate takedown notices instantly with evidence included.",
                ),
              ],
            ),

            const SizedBox(height: 50),

            Column(
              children: const [
                Text(
                  "How It Works",
                  style: TextStyle(
                    fontFamily: "ChunkFive",
                    fontSize: 36,
                  ),
                ),
                SizedBox(height: 20),
              ],
            ),

            Wrap(
              alignment: WrapAlignment.center,
              children: [
                stepCard("Upload your content"),
                arrow(),
                stepCard("AI scans the internet"),
                arrow(),
                stepCard("Violations are detected"),
                arrow(),
                stepCard("Take action instantly"),
              ],
            ),

            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  Widget featureCard(String title, String desc) {
    return Container(
      height: 320,
      width: 280,
      margin: const EdgeInsets.all(15),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFC75A75), Color(0xFF8B3E5C)],
        ),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(color: Colors.black26, blurRadius: 6),
        ],
      ),
      child: Column(
        children: [
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: "Bernoru",
              fontSize: 35,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 30),
          Text(
            desc,
            textAlign: TextAlign.left,
            style: const TextStyle(
              fontFamily: "SquadaOne",
              fontStyle: FontStyle.italic,
              fontSize: 25,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget stepCard(String text) {
    return Container(
      width: 220,
      margin: const EdgeInsets.all(10),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFC75A75), Color(0xFF8B3E5C)],
        ),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(color: Colors.black26, blurRadius: 6),
        ],
      ),
      child: Column(
        children: [
          const SizedBox(height: 10),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: "SquadaOne",
              fontSize: 30,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

Widget arrow() {
  return const SizedBox(
    height: 150,
    child: Icon(
      Icons.double_arrow,
      size: 100,
      color: Color(0xFFC75A75),
    ),
  );
}

}