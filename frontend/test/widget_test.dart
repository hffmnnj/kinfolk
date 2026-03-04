import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:kinfolk/main.dart';

void main() {
  testWidgets('App renders Kinfolk title', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: KinfolkApp()));

    expect(find.text('Kinfolk'), findsOneWidget);
  });
}
