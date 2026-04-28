import 'package:assetprot/features_page.dart';
import 'package:assetprot/main.dart';
import 'package:flutter/material.dart';
import '../login_page.dart';
import '../auth_service.dart';

class Navbar extends StatelessWidget {
  const Navbar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 90,
      padding: const EdgeInsets.symmetric(horizontal: 40),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFFD88A9B), Color(0xFFB04A6A)],
        ),
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(30),
          bottomRight: Radius.circular(30),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            "Sports Sentinel",
            style: TextStyle(
              fontFamily: "Bernoru",
              color: Colors.white,
              fontSize: 26,
            ),
          ),
          Row(
            children: [
              navBtn(context, "Home"),
              navBtn(context, "Features"),
              AuthService.isLoggedIn
              ? navBtn(context, "Dashboard")
              : navBtn(context, "Login"),
            ],
          )
        ],
      ),
    );
  }

  Widget navBtn(BuildContext context, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFB54A68), Color(0xFFCD4A7D), Color(0xFFE89B9B)]
          ),
          borderRadius: BorderRadius.circular(25),
        ), 
        child: ElevatedButton(
          onPressed: () {
            if (text == "Home") {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const LandingPage(),
                ),
              );
            }
            
            else if (text == "Login") {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const LoginPage(),
                ),
              );
            }

            else if (text == "Dashboard") {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const LoginPage(),
                ),
              );
            }        

            else if (text == "Features") {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const FeaturesPage(),
                ),
              );
            } 

          },
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.transparent,
            shadowColor: Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(25),
            ),
          ),
          child: Text(
            text,
            style: const TextStyle(
              fontFamily: "Bernoru",
              color: Colors.white,
            ),
          ),
        ),
      ),
    );
  }
}