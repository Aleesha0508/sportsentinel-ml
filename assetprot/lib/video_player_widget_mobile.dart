import 'package:flutter/material.dart';

class VideoPlayerWidget extends StatelessWidget {
  final String url;

  const VideoPlayerWidget({super.key, required this.url});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        "Video playback supported on web only (demo mode)",
        style: TextStyle(color: Colors.white),
      ),
    );
  }
}