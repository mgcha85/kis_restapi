import unittest

def place_buy_order(order_type='limit', qty=1, price=100):
    # Dummy implementation: 지정가('limit')와 시장가('market')만 허용
    if order_type not in ['limit', 'market']:
        raise ValueError('Invalid order type')
    return {'order_type': order_type, 'qty': qty, 'price': price}

class TestBuyOrder(unittest.TestCase):
    def test_limit_order(self):
        result = place_buy_order(order_type='limit', qty=10, price=150)
        self.assertEqual(result['order_type'], 'limit')
        self.assertEqual(result['qty'], 10)
        self.assertEqual(result['price'], 150)
        
    def test_market_order(self):
        result = place_buy_order(order_type='market', qty=5, price=0)
        self.assertEqual(result['order_type'], 'market')
        self.assertEqual(result['qty'], 5)
        
    def test_invalid_order_type(self):
        with self.assertRaises(ValueError):
            place_buy_order(order_type='invalid', qty=1, price=100)

if __name__ == '__main__':
    unittest.main()
