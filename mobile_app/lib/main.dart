import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(ChangeNotifierProvider(create: (_) => JobTrustController(), child: const JobTrustApp()));
}

class JobTrustApp extends StatelessWidget {
  const JobTrustApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI JobTrust',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1D63D8)),
        scaffoldBackgroundColor: const Color(0xFFF7F9FC),
      ),
      home: const HomeScreen(),
    );
  }
}

class JobTrustController extends ChangeNotifier {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000'),
    connectTimeout: const Duration(seconds: 10),
  ));

  bool isLoading = false;
  Map<String, dynamic>? result;
  String? error;

  Future<void> scanText(String text) async {
    isLoading = true;
    error = null;
    result = null;
    notifyListeners();
    try {
      final response = await _dio.post('/api/scan/text', data: {'text': text, 'language': 'en'});
      result = Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (exception) {
      error = 'Could not reach the analysis service. ${exception.message ?? ''}'.trim();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _textController = TextEditingController();
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _textController.addListener(_handleTextChanged);
  }

  void _handleTextChanged() {
    setState(() {});
  }

  @override
  void dispose() {
    _textController.removeListener(_handleTextChanged);
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<JobTrustController>();
    final isWide = MediaQuery.sizeOf(context).width > 800;

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.shield_rounded, color: Color(0xFF1D63D8)),
            SizedBox(width: 8),
            Text('AI JobTrust', style: TextStyle(fontWeight: FontWeight.w800)),
          ],
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: isWide
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 3, child: _scanner(controller)),
                      const SizedBox(width: 24),
                      Expanded(flex: 2, child: _result(controller)),
                    ],
                  )
                : Column(children: [_scanner(controller), const SizedBox(height: 20), _result(controller)]),
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (value) => setState(() => _tab = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
          NavigationDestination(icon: Icon(Icons.report_outlined), label: 'Reports'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }

  Widget _scanner(JobTrustController controller) {
    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: Color(0xFFE5EAF1)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Check Before You Trust.', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: Color(0xFF102A43))),
            const SizedBox(height: 8),
            const Text('Paste a job offer or recruitment message to check warning signs.', style: TextStyle(color: Color(0xFF627D98))),
            const SizedBox(height: 20),
            TextField(
              controller: _textController,
              minLines: 7,
              maxLines: 12,
              maxLength: 20000,
              decoration: InputDecoration(
                hintText: 'Paste the complete job message here...',
                filled: true,
                fillColor: const Color(0xFFF8FAFD),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: FilledButton.icon(
                onPressed: controller.isLoading || _textController.text.trim().isEmpty
                    ? null
                    : () => controller.scanText(_textController.text),
                icon: controller.isLoading
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.search),
                label: Text(controller.isLoading ? 'Analyzing...' : 'Analyze Job Offer'),
              ),
            ),
            if (controller.error != null) ...[
              const SizedBox(height: 12),
              Text(controller.error!, style: const TextStyle(color: Color(0xFFC62828))),
            ],
          ],
        ),
      ),
    );
  }

  Widget _result(JobTrustController controller) {
    if (controller.result == null) {
      return const Card(
        elevation: 0,
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            children: [
              Icon(Icons.verified_user_outlined, size: 48, color: Color(0xFF1D63D8)),
              SizedBox(height: 12),
              Text('Your safety result will appear here', textAlign: TextAlign.center),
            ],
          ),
        ),
      );
    }

    final result = controller.result!;
    final evidence = (result['evidence'] as List?) ?? const [];
    final risk = result['risk_label'] as String;
    final color = risk == 'High Risk'
        ? const Color(0xFFC62828)
        : risk == 'Suspicious'
            ? const Color(0xFFE67E22)
            : risk == 'Low Risk'
                ? const Color(0xFF278A54)
                : risk == 'Verified'
                    ? const Color(0xFF278A54)
                    : const Color(0xFF627D98);

    return Card(
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: const BorderSide(color: Color(0xFFE5EAF1))),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(color: color.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(99)),
              child: Text(risk, style: TextStyle(color: color, fontWeight: FontWeight.w800)),
            ),
            const SizedBox(height: 16),
            Text(result['explanation'] as String, style: const TextStyle(height: 1.5)),
            const SizedBox(height: 16),
            if (result['trust_score'] != null) ...[
              Text('Rule-risk score: ${result['trust_score']} / 100',
                  style: const TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              LinearProgressIndicator(
                value: ((result['trust_score'] as num).toDouble()) / 100,
                color: color,
                backgroundColor: const Color(0xFFE8EEF4),
              ),
              const SizedBox(height: 6),
              Text(result['trust_score_label'] as String? ?? '',
                  style: const TextStyle(color: Color(0xFF627D98), fontSize: 12)),
            ],
            const SizedBox(height: 16),
            const Text('Evidence detected', style: TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            if ((result['highlighted_suspicious_text'] as List?)?.isNotEmpty == true) ...[
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: (result['highlighted_suspicious_text'] as List)
                    .take(8)
                    .map((phrase) => Chip(
                          label: Text(phrase.toString()),
                          backgroundColor: const Color(0xFFFFF1E8),
                          labelStyle: const TextStyle(color: Color(0xFF9C4A12), fontSize: 12),
                        ))
                    .toList(),
              ),
              const SizedBox(height: 10),
            ],
            if (evidence.isEmpty)
              const Text('No configured warning rule matched.')
            else
              ...evidence.map((item) {
                final finding = item as Map<String, dynamic>;
                final matches = (finding['matched_evidence'] as List).join(' • ');
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.warning_amber_rounded, size: 20, color: Color(0xFFE67E22)),
                      const SizedBox(width: 8),
                      Expanded(child: Text('$matches\n${finding['explanation']}')),
                    ],
                  ),
                );
              }),
            const SizedBox(height: 12),
            Text(result['limitations'] as String, style: const TextStyle(color: Color(0xFF627D98), fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
