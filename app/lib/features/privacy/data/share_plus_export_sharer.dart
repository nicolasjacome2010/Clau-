import 'dart:convert';

import 'package:share_plus/share_plus.dart';

import '../domain/export_sharer.dart';

/// Production `ExportSharer`: the OS share sheet, with the export attached
/// as a real file.
///
/// Shared as an attachment rather than as body text so what the user
/// receives is a `.json` they can keep, re-read and feed to something
/// else — "portable format" in the sense the right actually means, not a
/// wall of text in a message.
class SharePlusExportSharer implements ExportSharer {
  const SharePlusExportSharer();

  @override
  Future<bool> share({
    required String filename,
    required String content,
  }) async {
    final result = await SharePlus.instance.share(
      ShareParams(
        files: [
          XFile.fromData(
            utf8.encode(content),
            mimeType: 'application/json',
            name: filename,
          ),
        ],
        fileNameOverrides: [filename],
      ),
    );
    // `dismissed` is a real outcome, not an error: the user changed their
    // mind, and telling them something failed would be false.
    return result.status != ShareResultStatus.unavailable;
  }
}
