import 'package:flutter/material.dart';
import 'navbar.dart';
import 'auth_service.dart';
import 'login_page.dart';
import 'dashboard_page.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: LandingPage(),
    );
  }
}

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEDEDED),
      body: Stack(
        children: [

          Positioned.fill(
            child: Image.asset(
              "assets/center_emblem.png",
              fit: BoxFit.cover, 
            ),
          ),

          Column(
            children: [
              const Navbar(),
              const SizedBox(height: 30),

              Expanded(
                child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          SizedBox(
                            width: 500, 
                            child: LeftBox(),
                          ),

                          SizedBox(width: 650), 

                          SizedBox(
                            width: 520,
                            child: RightBox(),
                          ),
                        ],
                      )
              ),

              const BottomCTA(),
            ],
          ),


          Positioned(
            left: 40,   
            bottom: 10, 
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(
                    horizontal: 25, vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(30),
                ),
              ),
              onPressed: () {
              
              },
              child: const Text(
                "Help",
                style: TextStyle(
                  fontFamily: "Bernoru",
                  color: Colors.white,
                  fontSize: 30

                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

//////////////////////////////////////////////////////////
// LEFT BOX
//////////////////////////////////////////////////////////

class LeftBox extends StatelessWidget {
  const LeftBox({super.key});

  @override
  Widget build(BuildContext context) {
    return Transform.translate(
      offset: const Offset(50, 50),
      child: SizedBox(
        height: 510,
        child: Container(
          margin: const EdgeInsets.all(10),
          padding: const EdgeInsets.all(30),
          decoration: BoxDecoration(
            color: const Color(0xFFC75A75),
            borderRadius: BorderRadius.circular(25),
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 10,
                offset: Offset(0, 4),
              )
            ],
          ),
          child: const Text(
            "Sports organizations generate massive volumes of high-value digital media that rapidly scatter across global platforms, making it nearly impossible to track. This creates vulnerability to unauthorized redistribution, misappropriation, and IP violations.",
            style: TextStyle(
              fontStyle: FontStyle.italic,
              fontFamily: "SquadaOne",
              color: Colors.white,
              fontSize: 35,
              height: 1.4,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}


//////////////////////////////////////////////////////////
// RIGHT BOX
//////////////////////////////////////////////////////////

class RightBox extends StatelessWidget {
  const RightBox({super.key});

  @override
  Widget build(BuildContext context) {
    return Transform.translate(
      offset: const Offset(-70, 50),
      child: Container(
        margin: const EdgeInsets.all(20),
        padding: const EdgeInsets.all(25),
        decoration: BoxDecoration(
          color: const Color(0xFFC75A75),
          borderRadius: BorderRadius.circular(25),
          boxShadow: const [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 10,
              offset: Offset(0, 4),
            )
          ],
        ),
        child: const Text(
          "So we decided to help by introducing SportsSentinel a tool that scans the internet and finds violators accurately and helps relevant parties take action.",
          style: TextStyle(
            fontStyle: FontStyle.italic,
            fontFamily: "SquadaOne",
            color: Colors.white,
            fontSize: 35,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

//////////////////////////////////////////////////////////
// CTA
//////////////////////////////////////////////////////////

class BottomCTA extends StatelessWidget {
  const BottomCTA({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 300, bottom: 100),
      child: Align(
        alignment: Alignment.bottomRight, 
        child: SizedBox(
          height: 120, 
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [

              const Text(
                "Get Started Now!",
                style: TextStyle(
                  fontFamily: "ChunkFive",
                  fontSize: 40,
                ),
              ),

              const SizedBox(width: 20),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 35, vertical: 18),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(30),
                  ),
                ),
                onPressed: () {
                  if (AuthService.isLoggedIn) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const DashboardPage(),
                      ),
                    );
                  } else {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const LoginPage(),
                      ),
                    );
                  }
                },
                child: const Text(
                  "Upload",
                  style: TextStyle(
                    fontFamily: "Bernoru",
                    color: Colors.white,
                    fontSize: 30,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}