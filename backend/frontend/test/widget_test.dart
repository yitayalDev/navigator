import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uog_navigetor/main.dart';

void main() {
  testWidgets('App starts', (WidgetTester tester) async {
    await tester.pumpWidget(const UogNavigatorApp());
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
