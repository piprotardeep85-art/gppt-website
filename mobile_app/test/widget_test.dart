// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('JobTrust home renders scanner', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(create: (_) => JobTrustController(), child: const JobTrustApp()),
    );

    expect(find.text('Check Before You Trust.'), findsOneWidget);
    expect(find.text('Analyze Job Offer'), findsOneWidget);
    expect(find.text('Your safety result will appear here'), findsOneWidget);
  });
}
