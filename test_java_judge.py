import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from coding_challenge.judge0 import run_single_case

java_code = """import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String[] input = sc.nextLine().split(" ");
        int n = input.length;
        int[] nums = new int[n];
        for (int i = 0; i < n; i++) {
            nums[i] = Integer.parseInt(input[i]);
        }
        int target = sc.nextInt();
        HashMap<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < n; i++) {
            int complement = target - nums[i];
            if (map.containsKey(complement)) {
                System.out.println(map.get(complement) + " " + i);
                return;
            }
            map.put(nums[i], i);
        }
    }
}
"""

test_input = "2 7 11 15\n9"
print('--- testing java two sum ---')
try:
    res = run_single_case(java_code, 62, test_input)
    print('stdout:', repr(res.get('stdout')))
    print('stderr:', repr(res.get('stderr')))
    print('message:', repr(res.get('message')))
    print('compile_output:', repr(res.get('compile_output')))
    print('status:', res.get('status'))
except Exception as e:
    print('Error:', e)
