 // ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:ui_web' as ui;
import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

class VideoPlayerWidget extends StatefulWidget {
  final String url;

  const VideoPlayerWidget({super.key, required this.url});

  @override
  State<VideoPlayerWidget> createState() => _VideoPlayerWidgetState();
}

class _VideoPlayerWidgetState extends State<VideoPlayerWidget> {
  late String viewId;
  bool _registered = false;

  @override
  void initState() {
    super.initState();

    viewId = 'video-${widget.url.hashCode}';

    if (!_registered) {
      // ignore: undefined_prefixed_name
      ui.platformViewRegistry.registerViewFactory(viewId, (int id) {
        final video = web.HTMLVideoElement()
          ..src = widget.url
          ..controls = true
          ..autoplay = true
          ..muted = true
          ..loop = true
          ..style.width = '100%'
          ..style.height = '100%';

        return video;
      });

      _registered = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    return HtmlElementView(viewType: viewId);
  }
}