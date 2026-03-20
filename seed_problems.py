import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from coding_challenge.models import Problem

if not Problem.objects.exists():
    Problem.objects.create(
        title="1. Two Sum",
        description="""Given an array of integers and a target integer, return the indices of the two numbers that add up to the target.

Input Format:
Line 1: Space-separated integers representing the array
Line 2: The target integer

Output Format:
Space-separated indices i and j (0-indexed).

Example Input:
2 7 11 15
9

Example Output:
0 1
""",
        test_cases=[
            {"input": "2 7 11 15\n9", "expected": "0 1"},
            {"input": "3 2 4\n6", "expected": "1 2"},
            {"input": "3 3\n6", "expected": "0 1"}
        ],
        language_id=71  # Python 3
    )

    Problem.objects.create(
        title="2. FizzBuzz Classic",
        description="""Write a program that prints numbers from 1 to N.
If a number is a multiple of 3, print "Fizz".
If a number is a multiple of 5, print "Buzz".
If a number is a multiple of both 3 and 5, print "FizzBuzz".

Input Format:
Line 1: A single integer N

Example Input:
5

Example Output:
1
2
Fizz
4
Buzz
""",
        test_cases=[
            {"input": "5", "expected": "1\n2\nFizz\n4\nBuzz"},
            {"input": "3", "expected": "1\n2\nFizz"},
            {"input": "15", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz"}
        ],
        language_id=71
    )

    print("✅ Successfully seeded 'Two Sum' and 'FizzBuzz' into the Problems database!")
else:
    print("Database already contains problems. Did not overwrite.")
