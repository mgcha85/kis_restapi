import unittest
import yaml

def load_conditions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_stock_codes(conditions):
    # Dummy implementation: 조건식에 해당하는 주식코드를 반환 (예시)
    return conditions.get('stock_codes', [])

class TestConditionLoading(unittest.TestCase):
    def test_load_conditions_and_get_stock_codes(self):
        # 예시 조건식 데이터
        conditions = {
            'condition': 'example_condition',
            'stock_codes': ['AAPL', 'MSFT', 'GOOG']
        }
        self.assertEqual(get_stock_codes(conditions), ['AAPL', 'MSFT', 'GOOG'])

if __name__ == '__main__':
    unittest.main()
