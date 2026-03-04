import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'presentation/themes/kinfolk_theme.dart';
import 'presentation/screens/dashboard_screen.dart';

void main() {
  runApp(const ProviderScope(child: KinfolkApp()));
}

class KinfolkApp extends StatelessWidget {
  const KinfolkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kinfolk',
      debugShowCheckedModeBanner: false,
      theme: KinfolkTheme.light,
      darkTheme: KinfolkTheme.dark,
      themeMode: ThemeMode.dark,
      home: const DashboardScreen(),
    );
  }
}
